#include <ace/generic/main.h>
#include <ace/managers/blit.h>
#include <ace/managers/joy.h>
#include <ace/managers/key.h>
#include <ace/managers/memory.h>
#include <ace/managers/viewport/simplebuffer.h>
#include <ace/utils/custom.h>
#include <hardware/dmabits.h>
#include <agk/debug.h>
#include <agk/perf.h>
#include "logic.h"
#include "render.h"
#include "sound.h"
#include "audio_assets.h"
#include "intro.h"
#include "campaign_audio.h"
#ifdef ASTRA_CAMPAIGN_PROBE
#include "../tests/native/campaign_probe.h"
#endif

/* Main owns lifecycle/input/audio and frame publication; render orchestrates
 * hero, enemies, bullets, BOB bonuses and world before/after input/logic. */
static tView *s_pView;
static tVPort *s_pVPort;
static tSimpleBufferManager *s_pBuffer;
static tGameState s_sState;
static UBYTE s_isLoaded, s_isSystemUnused, s_isSound, s_isIntro, s_isIntroDone;
static UBYTE s_ubReadyFrames;
static UBYTE s_ubReportTicks;

static tInput readInput(void) {
	tInput input = {0};
	if(keyCheck(KEY_LEFT) || joyCheck(JOY1_LEFT)) input.dx = -1;
	if(keyCheck(KEY_RIGHT) || joyCheck(JOY1_RIGHT)) input.dx = 1;
	if(keyCheck(KEY_UP) || joyCheck(JOY1_UP)) input.dy = -1;
	if(keyCheck(KEY_DOWN) || joyCheck(JOY1_DOWN)) input.dy = 1;
	input.fire = keyCheck(KEY_SPACE) || joyCheck(JOY1_FIRE);
	return input;
}

static UBYTE createDisplay(void) {
	UWORD count = ASTRA_COP_DECOR + ASTRA_COP_DECOR_COUNT;
	s_pView = viewCreate(0,
		TAG_VIEW_COPLIST_MODE, VIEW_COPLIST_MODE_RAW,
		TAG_VIEW_COPLIST_RAW_COUNT, count,
		TAG_VIEW_GLOBAL_PALETTE, 1,
		TAG_VIEW_WINDOW_WIDTH, WORLD_W, TAG_VIEW_WINDOW_HEIGHT, WORLD_H, TAG_DONE);
	if(!s_pView) return 0;
	s_pVPort = vPortCreate(0, TAG_VPORT_VIEW, s_pView,
		TAG_VPORT_BPP, 4, TAG_VPORT_WIDTH, WORLD_W, TAG_VPORT_HEIGHT, WORLD_H, TAG_DONE);
	if(!s_pVPort || !s_pVPort->pPalette) return 0;
	s_pBuffer = simpleBufferCreate(0, TAG_SIMPLEBUFFER_VPORT, s_pVPort,
		TAG_SIMPLEBUFFER_COPLIST_OFFSET, ASTRA_COP_BUFFER,
		TAG_SIMPLEBUFFER_BITMAP_FLAGS, BMF_CLEAR | BMF_INTERLEAVED,
		TAG_SIMPLEBUFFER_IS_DBLBUF, 1,
		TAG_SIMPLEBUFFER_USE_X_SCROLLING, 0, TAG_DONE);
	return s_pBuffer && s_pBuffer->pBack;
}

void genericCreate(void) {
	agkDebugInit();
	agkPrint("AGK boot astra\n");
	keyCreate();
	joyOpen();
	logicInit(&s_sState);
	if(!createDisplay() || !renderCreate(s_pView, s_pVPort, s_pBuffer)) {
		agkPrint("AGK allocation failure\n");
		gameExit();
		return;
	}
	if(!astraSoundCreate()) {
		agkPrint("AGK sound allocation failure\n");
		gameExit();
		return;
	}
	s_isSound = 1;
	campaignAudioReset();
	introCreate(s_pBuffer, s_pVPort);
	s_isIntro = 1;
	/* Exec memory queries belong before hardware takeover, never in gameplay. */
	agkState("chip_free", memGetFreeChipSize());
	agkState("ram_free", memGetFreeSize());
	agkEnd();
	blitWait();
	systemUnuse();
	s_isSystemUnused = 1;
	viewLoad(s_pView);
	systemSetDmaBit(DMAB_SPRITE, 1);
	/* BOB save/restore waits otherwise contend with CPU polling for chip slots. */
	systemSetDmaBit(DMAB_BLITHOG, 1);
	g_pCustom->bplcon2 = 0x24;
	s_isLoaded = 1;
	agkDebugAsync(1);
	vPortWaitForEnd(s_pVPort);
}

static void soundEvents(UBYTE events) {
	if(events & EVENT_LANCE) soundPlay(SOUND_SFX_LANCE);
	else if(events & EVENT_SHOT) soundPlay(SOUND_SFX_SHOT);
	if(events & EVENT_EXPLOSION) soundPlay(SOUND_SFX_EXPLOSION);
	if(events & EVENT_HIT) soundPlay(SOUND_SFX_HIT);
	if(events & EVENT_CHARGE) soundPlay(SOUND_SFX_CHARGE);
	if(events & EVENT_LEVEL) soundPlay(SOUND_SFX_WARP);
	if(events & EVENT_BONUS_DROP) {
		soundPlay(SOUND_SFX_BONUS_DROP);
		agkPrint("AGK bonus_drop\n");
	}
	if(events & EVENT_BONUS_PICKUP) {
		soundPlay(SOUND_SFX_BONUS_PICKUP);
		agkPrint("AGK bonus_pickup\n");
	}
}

static void reportState(void) {
	UBYTE visibleHostile = 0;
	UBYTE bullet4 = 0, bullet5 = 0, bullet6 = 0, bullet7 = 0;
	UBYTE enemies = 0, hidden = 0, shots = 0, effects = 0;
	for(UBYTE i = 0; i < HOSTILE_COUNT; ++i) {
		const tEntity *e = &s_sState.hostile[i];
		if(!e->active) continue;
		/* An on-screen thrown bullet that is not displayed must never happen. */
		if(!e->visible) { if(e->x >= 0) ++hidden; continue; }
		++visibleHostile;
		if(e->channel == 4) ++bullet4;
		if(e->channel == 5) ++bullet5;
		if(e->channel == 6) ++bullet6;
		if(e->channel == 7) ++bullet7;
	}
	for(UBYTE i = 0; i < SHOT_COUNT; ++i) shots += s_sState.shots[i].active && s_sState.shots[i].visible;
	for(UBYTE i = 0; i < ENEMY_COUNT; ++i)
		if(s_sState.enemies[i].active && s_sState.enemies[i].visible) ++enemies;
	agkState("frame", s_sState.frame);
	agkState("phase", s_sState.phase);
	agkState("level", s_sState.level + 1);
	agkState("score", s_sState.score);
	agkState("lives", s_sState.lives);
	agkState("boss", s_sState.boss.hp);
	agkState("x", s_sState.x);
	agkState("y", s_sState.y);
	agkState("weapon", s_sState.weaponLevel);
	agkState("speed", s_sState.speedLevel);
	agkState("shield", s_sState.shield);
	agkState("wave", s_sState.wave);
	agkState("hostile_bullets", visibleHostile);
	agkState("bullet4", bullet4); agkState("bullet5", bullet5);
	agkState("bullet6", bullet6); agkState("bullet7", bullet7);
	agkState("bullet_hidden", hidden); agkState("shot_bobs", shots);
	agkState("enemies", enemies);
	for(UBYTE i = 0; i < EFFECT_COUNT; ++i) effects += s_sState.effects[i].active;
	agkState("effects", effects);
	agkState("stage", s_sState.stageFrame);
	agkState("sim", s_sState.simFrame);
	agkState("scene", s_sState.sceneId);
	agkState("scene_ready", s_sState.sceneReady);
	agkState("preparing", s_sState.presentationBusy);
	agkState("pattern", s_sState.shotLevel + 1);
	agkEnd();
}

void genericProcess(void) {
	agkPerfBegin();
	if(!s_isLoaded) { agkPerfEnd(); gameExit(); return; }
	renderBindBack(s_pBuffer->pBack);
	UBYTE acknowledged = 0;
	if(s_isIntroDone && !s_sState.sceneReady && renderSceneReady()) {
		logicScenePresented(&s_sState, renderSceneReadyEpoch());
		acknowledged = s_sState.sceneReady;
	}
	if(s_isIntroDone) renderAnimate(&s_sState);
	keyProcess();
	joyProcess();
	if(keyCheck(KEY_ESCAPE)) { agkPerfEnd(); gameExit(); return; }
	UBYTE muteToggle = s_isIntroDone && keyUse(KEY_M);
	tInput input = readInput();
	UBYTE introEnded = 0;

	if(!s_isIntroDone && !introProcess(input.fire)) {
		s_isIntroDone = 1;
		introEnded = 1;
		renderPalette();
		/* A fire used to skip an intro must not also skip the title. */
		s_sState.fireWasDown = input.fire;
	}
	if(s_isIntroDone) {
		UBYTE heartbeat = ++s_ubReportTicks == 50;
		if(heartbeat) s_ubReportTicks = 0;
		tPhase oldPhase = s_sState.phase;
		UWORD oldWave = s_sState.wave;
		UBYTE wasPreparing = s_sState.presentationBusy;
#ifdef ASTRA_CAMPAIGN_PROBE
		campaignProbeBeforeUpdate(&s_sState);
#endif
		logicUpdate(&s_sState, &input);
		/* Spread logo clearing and initial module setup over adjacent video
		 * ticks; music still starts after both original intros finish. */
		if(!introEnded) campaignAudioUpdate(s_sState.level, s_sState.phase, muteToggle);
		soundEvents(s_sState.events);
		renderFrame(&s_sState);
#ifdef ASTRA_CAMPAIGN_PROBE
		campaignProbeAfterFrame(&s_sState);
#endif
		if(wasPreparing && !s_sState.presentationBusy) {
			if(logicCombatActive(&s_sState)) agkPrint("AGK combat_ready\n");
			else if(s_sState.phase == TITLE) agkPrint("AGK title_ready\n");
		}
		if(acknowledged || wasPreparing != s_sState.presentationBusy ||
			(s_sState.events & (EVENT_EXPLOSION | EVENT_HIT | EVENT_LEVEL |
				EVENT_BONUS_DROP | EVENT_BONUS_PICKUP)) ||
			oldPhase != s_sState.phase || oldWave != s_sState.wave ||
			heartbeat) reportState();
	}
	blitWait();
	/* Intros own viewport colors while active; palette MOVEs must follow them
	 * because viewLoad only initializes the 16 playfield colors at 4bpp. */
	renderSyncPalette();
	/* Raw ACE lists only refresh pointers when dirty. Explicitly associate the
	 * completed pixels with the same back copper list as the sprite streams. */
	s_pBuffer->ubDirtyCounter = 1;
	viewProcessManagers(s_pView);
	copProcessBlocks();
	/* If performance reporting itself crosses the next vblank, that already
	 * acknowledges this list: do not accidentally wait for a second blank. */
	ULONG publishedAt = timerGet();
	agkPerfEnd();
	/* The newly published copper list becomes active at vblank. Start the
	 * next logic tick only after that acknowledgement, not at line 300 while
	 * the just-submitted DMA stream is still waiting to be displayed. */
	while(timerGet() == publishedAt) { }
	/* Lifetime display frames, not the logic counter (which is frozen in intros). */
	if(s_ubReadyFrames < 2 && ++s_ubReadyFrames == 2) agkReady();
}

void genericDestroy(void) {
	agkDebugAsync(0);
	blitWait();
	if(s_isLoaded) { systemSetDmaBit(DMAB_SPRITE, 0); viewLoad(0); }
	if(s_isSystemUnused) systemUse();
	if(s_isSound) { soundDestroy(); s_isSound = 0; }
	if(s_isIntro) introDestroy();
	renderDestroy();
	if(s_pView) viewDestroy(s_pView);
	joyClose();
	keyDestroy();
}
