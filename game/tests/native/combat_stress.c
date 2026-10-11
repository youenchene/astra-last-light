/* NON-SHIPPING: same deterministic pre-update actors at each X band.
 * Public logic still moves, collides, fires/admit rays and retires projectiles.
 * Resetting actors every tick is injection, not ordinary play evidence. */
#include "combat_perf.h"
#include <agk/debug.h>
#include <ace/managers/timer.h>
#include <string.h>
static unsigned short s_case, s_tick;
static unsigned char s_started, s_done, s_captureHeld;
unsigned char combatStressCaptureHeld(void) { return s_captureHeld; }
void combatStressRelease(void) { s_captureHeld = 0; }
static struct {
	unsigned short caseId, tick;
	unsigned char requested, submitted, bitmap, copper, phase, level;
	unsigned long clock;
} s_capture;
unsigned short combatStressCase(void) { return s_started ? s_case : 65535; }
static void actors(tGameState *s) {
	unsigned char band = s_case % 3, dense = (s_case / 3) & 1;
	short x = 16 + band * 96 + (s_tick & 15);
	memset(s->enemies, 0, sizeof(s->enemies));
	memset(s->hostile, 0, sizeof(s->hostile));
	memset(s->shots, 0, sizeof(s->shots));
	memset(s->pickups, 0, sizeof(s->pickups));
	memset(s->effects, 0, sizeof(s->effects));
	s->x = 280; s->y = 180; s->invulnerable = 100; s->waveTimer = 100;
	s->simFrame = s_tick; s->enemyMotionFrame = s_tick; s->enemyAccumulator = 0;
	s->stageFrame = 0; s->wave = 0;
	if(s->phase == PLAY) {
		for(unsigned char i = 0; i < (dense ? 6 : 1); ++i)
			s->enemies[i] = (tEntity){.x=x, .y=58+i*26, .active=1,
				.visible=1, .kind=ENEMY_GUNNER, .hp=3, .vx=-2,
				.waveMember=i, .fireCountdown=(s_tick % 16 == 0 ? 1 : 2)};
	}
	/* Boss stays at the same reference position in all three bands; moving
	 * projectiles/BOBs must not change their collision overlap with it. */
	else s->boss = (tBoss){.x=240, .y=104, .active=1, .visible=1,
		.hp=480, .maxHp=480, .kind=s->level, .tick=112,
		.cooldown=(s_tick % 16 == 0 ? 1 : 2)};
	for(unsigned char i = 0; i < (dense ? 24 : 2); ++i)
		s->hostile[i] = (tEntity){.x=x, .y=58+(i/2)*12, .active=1,
			.visible=1, .kind=s->level, .hp=1, .vx=HOSTILE_VX, .channel=6+i%2};
	/* Two edge rays exercise -width..0 retirement in every band equally. */
	s->hostile[30] = (tEntity){.x=-5, .y=204, .active=1, .visible=1,
		.vx=HOSTILE_VX, .channel=6};
	s->hostile[31] = (tEntity){.x=-1, .y=204, .active=1, .visible=1,
		.vx=HOSTILE_VX, .channel=7};
	for(unsigned char i = 0; i < (dense ? 12 : 1); ++i)
		s->shots[i] = (tEntity){.x=x+32, .y=58+(i%4)*10, .active=1,
			.visible=1, .hp=1, .vx=6};
	for(unsigned char i = 0; i < (dense ? 6 : 1); ++i)
		s->effects[i] = (tEffect){.x=x+16, .y=60+i*26, .active=1,
			.kind=FX_ENEMY, .age=4, .lifetime=SMALL_EFFECT_FRAMES};
}
void combatStressBefore(tGameState *s) {
	if(s_captureHeld) return;
	if(s_done || (!s_started && (s->phase != PLAY || s->presentationBusy))) return;
	s_started = 1;
	if(s_tick == 200) { ++s_case; s_tick = 0; }
	if(s_case == 48) { s_done = 1; agkPrint("AGK stress_complete\n"); return; }
	tPhase phase = (s_case / 6) & 1 ? BOSS : PLAY;
	unsigned char level = s_case / 12;
	if(s->phase != phase || s->level != level) {
		s->phase = phase; s->level = level; s->boss.active = phase == BOSS;
		return; /* Renderer owns preparation and acknowledgement. */
	}
	if(s->presentationBusy) return;
	actors(s);
	++s_tick;
}
void combatStressAfter(const tGameState *s) {
	if(!s_started || s_done || s->presentationBusy) return;
	for(unsigned char i = 0; i < HOSTILE_COUNT; ++i) {
		const tEntity *e = &s->hostile[i];
		if(e->active && e->x > -HOSTILE_W && e->x < WORLD_W && !e->visible)
			agkPrint("AGK stress_fail hidden\n");
	}
	if(s_tick == 100 || s_tick == 200) {
		s_capture.caseId = s_case; s_capture.tick = s_tick;
		s_capture.phase = s->phase; s_capture.level = s->level;
		s_capture.requested = 1;
	}
}

void combatStressSubmitted(unsigned char bitmap, unsigned char copper, unsigned long clock) {
	if(!s_capture.requested) return;
	s_capture.requested = 0; s_capture.submitted = 1;
	s_capture.bitmap = bitmap; s_capture.copper = copper; s_capture.clock = clock;
}

void combatStressAcknowledged(unsigned char bitmap, unsigned char copper, unsigned long clock) {
	if(!s_capture.submitted) return;
	s_capture.submitted = 0;
	if(bitmap != s_capture.bitmap || copper != s_capture.copper || clock == s_capture.clock) {
		agkPrint("AGK stress_fail acknowledgement\n");
		return;
	}
	/* This is the completed submission, not the state about to be simulated.
	 * Main acknowledges its activation at vblank. A screenshot needs the whole
	 * scanout, not just activation: retain the submitted front list untouched
	 * until the next vblank completes that display. This fixture-only hardware
	 * fence stays inside agkPerfBegin/End and every affected window is retained. */
	while(timerGet() == clock) { }
	unsigned long scannedAt = timerGet();
	s_captureHeld = 1;
	agkState("stress_case", s_capture.caseId); agkState("tick", s_capture.tick);
	agkState("phase", s_capture.phase); agkState("level", s_capture.level);
	agkState("bitmap", bitmap); agkState("copper", copper);
	agkState("submitted", s_capture.clock); agkState("ack", clock);
	agkState("scanout", scannedAt); agkEnd();
}
