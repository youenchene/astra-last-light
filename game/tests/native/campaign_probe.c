/* NON-SHIPPING: accelerate quotas and inject collisions, never phases/input. */
#include "campaign_probe.h"
#include <agk/debug.h>
#include <string.h>

static tPhase s_beforePhase;
static uint32_t s_beforeSim, s_beforeFrame;
static uint16_t s_beforeStage, s_beforeTick;
static uint8_t s_beforeLives;
static uint32_t s_pauseFrame;
static uint16_t s_scenes;
static uint8_t s_playDeath[4], s_bossDeath[4], s_channels[4], s_kills[4];
static tBoss s_drawnBoss;
static tEffect s_drawnEffects[EFFECT_COUNT];
static tEntity s_drawnShots[SHOT_COUNT];
static uint8_t s_announced, s_complete;

static void fail(uint16_t code) {
	agkState("qa_fail", code); agkEnd();
}

static void clockReport(const char *tag, const tGameState *s, uint16_t id) {
	agkState(tag, id); agkState("level", s->level + 1);
	agkState("phase", s->phase); agkState("frame", s->frame);
	agkState("sim", s->simFrame); agkState("stage", s->stageFrame);
	agkState("tick", s->boss.tick); agkState("pf", s->phaseFrame);
	agkState("lives", s->lives); agkEnd();
}

static void shot(tEntity *e, int16_t x, int16_t y, uint8_t damage) {
	memset(e, 0, sizeof(*e));
	e->active = e->visible = 1; e->hp = damage;
	e->kind = SHOT_CHARGED; e->x = x; e->y = y;
}

static void heroCollision(tGameState *s) {
	/* Refill lives explicitly so eight independent death fixtures can finish. */
	s->lives = 5; s->shield = 0; s->invulnerable = 0;
	memset(s->hostile, 0, sizeof(s->hostile));
	tEntity *e = &s->hostile[0];
	e->active = e->visible = 1; e->channel = 6;
	e->x = s->x + PLAYER_HIT_X; e->y = s->y + PLAYER_HIT_Y;
}

static void injectPlay(tGameState *s) {
	/* Explicit non-shipping F fixtures: display badge first, reposition for a
	 * real pickup collision, then inject a short-release latch (neutral input). */
	if(s->level == 0) {
		if(s->stageFrame == 10 || s->stageFrame == 18) {
			tEntity *p = &s->pickups[0];
			memset(p, 0, sizeof(*p));
			p->active = 1; p->kind = BONUS_FIRE; p->x = 80; p->y = 126;
			agkState("qa_inject_F_pickup", s->stageFrame); agkEnd();
		}
		if(s->stageFrame == 12 || s->stageFrame == 20) {
			s->pickups[0].x = s->x; s->pickups[0].y = s->y;
		}
		if(s->stageFrame == 14 || s->stageFrame == 24) {
			memset(s->shots, 0, sizeof(s->shots));
			s->charge = 1;
			agkState("qa_inject_release_latch", s->stageFrame); agkEnd();
		}
	}
	/* This fixture checks six unobstructed blast silhouettes. Reward collection
	 * has its own ordinary-input scenarios; its foreground badge would cover FX5. */
	if(s->stageFrame == 51 && s_kills[s->level])
		memset(s->pickups, 0, sizeof(s->pickups));
	if(s->stageFrame == 50 && !s_kills[s->level]) {
		uint8_t count = 0;
		for(uint8_t i = 0; i < ENEMY_COUNT; ++i) {
			tEntity *e = &s->enemies[i];
			if(e->active && e->visible && count < SHOT_COUNT)
				shot(&s->shots[count++], e->x, e->y, 3);
		}
		s_kills[s->level] = count;
		agkState("qa_inject_kills", count); agkState("level", s->level + 1); agkEnd();
		if(count != 6) fail(1);
	}
	if(s->stageFrame == 100 && !s_playDeath[s->level]) {
		s_playDeath[s->level] = 1; heroCollision(s);
	}
	if(s->stageFrame == 160) {
		memset(s->enemies, 0, sizeof(s->enemies));
		memset(s->waves, 0, sizeof(s->waves));
		s->wave = g_stageWaveQuota[s->level];
		clockReport("qa_inject_quota", s, s->wave);
	}
}

void campaignProbeBeforeUpdate(tGameState *s) {
	if(!s_announced) {
		agkPrint("AGK qa_NON_SHIPPING_injected_fixture\n"); s_announced = 1;
	}
	s_drawnBoss = s->boss;
	memcpy(s_drawnEffects, s->effects, sizeof(s_drawnEffects));
	memcpy(s_drawnShots, s->shots, sizeof(s_drawnShots));
	if(logicCombatActive(s) && !s->presentationBusy) {
		s->invulnerable = 300;
		if(s->phase == PLAY) injectPlay(s);
		else {
			if(s->boss.tick == 80 || s->boss.tick == 220) {
				if(s->boss.tick == 220) s->boss.hp = 6;
				shot(&s->shots[0], s->boss.x + 16, s->boss.y + 16, 6);
			}
			if(s->boss.tick == 120 && !s_bossDeath[s->level]) {
				s_bossDeath[s->level] = 1; heroCollision(s);
			}
		}
	}
	s_beforePhase = s->phase; s_beforeSim = s->simFrame;
	s_beforeFrame = s->frame; s_beforeStage = s->stageFrame;
	s_beforeTick = s->boss.tick; s_beforeLives = s->lives;
}

static void checkPause(tGameState *s) {
	uint8_t wasDeath = s_beforePhase == HERO_DYING || s_beforePhase == BOSS_DYING;
	uint8_t death = s->phase == HERO_DYING || s->phase == BOSS_DYING;
	if(!wasDeath && death) {
		s_pauseFrame = s->frame;
		clockReport("qa_pause_begin", s, s->phase);
	}
	if(!wasDeath) return;
	if(s->simFrame != s_beforeSim || s->stageFrame != s_beforeStage ||
		s->boss.tick != s_beforeTick || s->lives != s_beforeLives ||
		s->frame != s_beforeFrame + 1) fail(2);
	if(!death) {
		uint16_t duration = s_beforePhase == HERO_DYING ? 40 : 75;
		if(s->frame - s_pauseFrame != duration) fail(3);
		clockReport("qa_pause_end", s, s_beforePhase);
	}
}

static void checkBullets(tGameState *s) {
	for(uint8_t i = 0; i < HOSTILE_COUNT; ++i) {
		const tEntity *e = &s->hostile[i];
		if(!e->active || e->x < 0 || e->x >= WORLD_W ||
			e->y < PLAY_TOP || e->y + HOSTILE_H > PLAY_BOTTOM) continue;
		if(!e->visible || e->channel < 4 || e->channel > 7 ||
			!(logicHostileChannelMask(s) & (1u << e->channel))) fail(4);
		if(s->phase == BOSS && e->visible) s_channels[s->level] |= 1u << e->channel;
	}
}

static void captureBoss(tGameState *s, const char *tag) {
	agkState(tag, s->level + 1); agkState("x", s_drawnBoss.x);
	agkState("y", s_drawnBoss.y); agkState("hp", s->boss.hp);
	agkState("maxhp", s->boss.maxHp); agkState("flash", s_drawnBoss.flashTicks);
	agkState("tick", s->boss.tick); agkEnd();
}

static void captureEffect(tGameState *s, uint8_t slot, const char *tag, uint16_t id) {
	const tEffect *e = &s_drawnEffects[slot];
	agkState(tag, id); agkState("level", s->level + 1);
	agkState("slot", slot); agkState("x", e->x); agkState("y", e->y);
	agkState("age", e->age); agkState("life", e->lifetime); agkEnd();
}

void campaignProbeAfterFrame(tGameState *s) {
	checkPause(s); checkBullets(s);
	if(s->level == 0 && s->phase == PLAY) {
		if(s->stageFrame == 12) { agkState("qa_F_badge", 1); agkEnd(); }
		if(s->stageFrame == 16 || s->stageFrame == 26) {
			uint8_t count = 0;
			for(uint8_t i = 0; i < SHOT_COUNT; ++i) {
				const tEntity *e = &s_drawnShots[i];
				if(!e->active) continue;
				++count;
				agkState("qa_F_shot", s->shotLevel + 1); agkState("slot", i);
				agkState("x", e->x); agkState("y", e->y);
				agkState("kind", e->kind); agkState("damage", e->hp); agkEnd();
			}
			if(count != s->shotLevel + 1 || s->weaponLevel != 0) fail(8);
			agkState("qa_F_pattern", s->shotLevel + 1); agkEnd();
		}
	}
	if(s->sceneReady && !(s_scenes & (1u << s->sceneId))) {
		s_scenes |= 1u << s->sceneId;
		clockReport("qa_scene", s, s->sceneId);
	}
	if(s_beforePhase != s->phase)
		clockReport("qa_transition", s, s_beforePhase);
	/* Sample inside a two-tick animation frame, not on its change boundary:
	 * screenshots describe the completed video frame, not current bitplane RAM. */
	if(s->phase == PLAY && s->stageFrame == 55) {
		for(uint8_t i = 0; i < SMALL_EFFECT_COUNT; ++i) {
			if(!s_drawnEffects[i].active) fail(5);
			captureEffect(s, i, "qa_fx_slot", i);
		}
		clockReport("qa_fx", s, s->level + 1);
	}
	if(s->phase == BOSS && s->boss.tick == 70) captureBoss(s, "qa_boss");
	if(s->phase == BOSS && s->boss.tick == 82) {
		if(s->boss.hp != s->boss.maxHp - 6 || !s_drawnBoss.flashTicks) fail(6);
		captureBoss(s, "qa_flash");
	}
	if(s->phase == HERO_DYING && s->phaseFrame == 10)
		captureEffect(s, HERO_EFFECT_SLOT, "qa_hero", 2 * s->level + (s->resumePhase == BOSS));
	if(s->phase == BOSS_DYING && s->phaseFrame == 10) {
		captureEffect(s, BOSS_EFFECT_SLOT, "qa_dead", s->level + 1);
		agkState("qa_channels", s->level + 1); agkState("mask", s_channels[s->level]); agkEnd();
		if(s_channels[s->level] != 240) fail(7);
	}
	if(s->phase == WIN && s->sceneReady && s->phaseFrame == 150 && !s_complete) {
		s_complete = 1;
		clockReport("qa_complete", s, s_scenes);
	}
}
