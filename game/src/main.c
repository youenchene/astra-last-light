#include <ace/generic/main.h>
#include <ace/managers/blit.h>
#include <ace/managers/joy.h>
#include <ace/managers/key.h>
#include <ace/managers/memory.h>
#include <ace/managers/viewport/simplebuffer.h>
#include <ace/utils/custom.h>
#include <hardware/dmabits.h>
#include <proto/exec.h>
#include <agk/debug.h>
#include <agk/perf.h>
#include "logic.h"
#include "render.h"
#include "sound.h"
#include "audio_assets.h"
#include "intro.h"
#include "campaign_audio.h"
#include "title_confirm.h"
#include "combat_perf.h"
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
static tBitMap *s_firstBitmap;
static tCopBfr *s_firstCopper;
static UBYTE s_submitted, s_cutPending, s_visibleValid, s_audioStarted, s_mutePending;
static UBYTE s_visibleLevel, s_cutBoth, s_cutBitmap, s_cutCopper;
static tPhase s_visiblePhase;
static UWORD s_cutRevision, s_lastRevision = 0xffff, s_holdFrames;
static UBYTE s_lastBoth;
static tTitleConfirm s_confirm;
static UBYTE s_confirmSubmitted;

static tInput readInput(void) {
	tInput input = {0};
	if(keyCheck(KEY_LEFT) || joyCheck(JOY1_LEFT)) input.dx = -1;
	if(keyCheck(KEY_RIGHT) || joyCheck(JOY1_RIGHT)) input.dx = 1;
	if(keyCheck(KEY_UP) || joyCheck(JOY1_UP)) input.dy = -1;
	if(keyCheck(KEY_DOWN) || joyCheck(JOY1_DOWN)) input.dy = 1;
	input.fire = keyCheck(KEY_SPACE) || joyCheck(JOY1_FIRE);
	return input;
}

/* TITLE has no live combat pools. Request WIN without acknowledging it: the
 * normal renderer/publication path must prepare both buffers before fire arms. */
static void previewEnding(const tInput *input) {
	s_confirm.active = s_confirm.visible = s_confirmSubmitted = 0;
	s_sState.phase = WIN;
	s_sState.level = LEVEL_COUNT - 1;
	s_sState.phaseFrame = 0;
	s_sState.sceneId = 12;
	++s_sState.sceneEpoch;
	s_sState.sceneReady = s_sState.sceneArmed = 0;
	s_sState.charge = s_sState.fireCooldown = 0;
	s_sState.fireWasDown = input->fire != 0;
	s_sState.events = EVENT_LEVEL;
	logicSetPresentationBusy(&s_sState, 1);
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
	agkState("display_memory", 0);
	agkState("chip_free", memGetFreeChipSize());
	agkState("chip_largest", AvailMem(MEMF_CHIP | MEMF_LARGEST));
	agkState("ram_free", memGetFreeSize()); agkEnd();
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
	s_firstBitmap = s_pBuffer->pBack;
	s_firstCopper = s_pView->pCopList->pBackBfr;
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
	agkState("enemy_tick", s_sState.enemyMotionFrame);
	agkState("enemy_acc", s_sState.enemyAccumulator);
	agkState("pf", s_sState.phaseFrame);
	agkState("title_blocked", s_sState.titleInputBlocked);
	agkState("scene", s_sState.sceneId);
	agkState("scene_ready", s_sState.sceneReady);
	agkState("preparing", s_sState.presentationBusy);
	agkState("paused", s_sState.manualPause);
	agkState("pattern", s_sState.shotLevel + 1);
	agkEnd();
}

static void reportCut(const char *tag) {
	agkState(tag, s_cutRevision);
	agkState("phase", s_visiblePhase); agkState("level", s_visibleLevel + 1);
	agkState("bitmap", s_cutBitmap); agkState("copper", s_cutCopper);
	agkState("both", s_cutBoth); agkState("vblank", timerGet());
	agkEnd();
}

static void acknowledgeFrame(void) {
	if(!s_submitted) return;
	s_submitted = 0;
	combatStressAcknowledged(s_pBuffer->pFront != s_firstBitmap,
		s_pView->pCopList->pFrontBfr != s_firstCopper, timerGet());
	if(s_confirmSubmitted) {
		s_confirmSubmitted = 0;
		titleConfirmPresented(&s_confirm);
		agkState("title_confirm_visible", s_confirm.visible);
		agkState("level", s_sState.level + 1); agkState("vblank", timerGet()); agkEnd();
	}
	UBYTE busy = s_sState.presentationBusy, sceneReady = s_sState.sceneReady;
	renderAcknowledge(&s_sState);
	if(s_cutPending) { reportCut("cut_visible"); s_cutPending = 0; }
	if(busy && !s_sState.presentationBusy) {
		agkState("publication_ready", renderRevision());
		agkState("phase", s_sState.phase); agkState("level", s_sState.level + 1);
		agkState("scene_ready", s_sState.sceneReady);
		agkState("preparing", s_sState.presentationBusy);
		agkState("vblank", timerGet()); agkEnd();
		if(logicCombatActive(&s_sState)) agkPrint("AGK combat_ready\n");
		else if(s_sState.phase == TITLE) agkPrint("AGK title_ready\n");
		else if(s_sState.phase == GAMEOVER) agkPrint("AGK gameover_ready\n");
		else if(s_sState.sceneReady) agkPrint("AGK scene_ready\n");
		reportState();
	}
	else if(!sceneReady && s_sState.sceneReady) reportState();
}

static void publishFrame(void) {
	if(s_isIntroDone && !renderTargetReady()) {
		if(!s_holdFrames) {
			agkState("cut_hold", renderRevision());
			agkState("bitmap", s_pBuffer->pBack != s_firstBitmap);
			agkState("copper", s_pView->pCopList->pBackBfr != s_firstCopper);
			agkEnd();
		}
		++s_holdFrames;
		/* ACE swaps even if not dirty. Leave both managers AND copper alone:
		 * visible pixels, palette and DMA stream identities remain immutable. */
		return;
	}
	renderSyncPalette();
	if(s_isIntroDone && s_sState.phase == TITLE && s_confirm.active && renderBothReady()) {
		s_confirmSubmitted = 1;
		if(!s_confirm.visible) soundPlay(SOUND_SFX_CONFIRM);
		/* Last publication is normal, so the scene's hidden work retains a
		 * complete, normally colored title rather than a stuck flash. */
		renderTitleFlash(!(s_confirm.visible & 1));
		agkState("title_confirm_submit", s_confirm.visible + 1);
		agkState("vblank", timerGet()); agkEnd();
	}
	if(s_isIntroDone) {
		s_visibleValid = s_submitted = 1;
		s_visibleLevel = s_sState.level; s_visiblePhase = s_sState.phase;
		s_cutRevision = renderRevision(); s_cutBoth = renderBothReady();
		s_cutBitmap = s_pBuffer->pBack != s_firstBitmap;
		s_cutCopper = s_pView->pCopList->pBackBfr != s_firstCopper;
		if(s_cutRevision != s_lastRevision || s_cutBoth != s_lastBoth) {
			s_cutPending = 1;
			agkState("cut_target_ready", renderTargetReady()); agkEnd();
			reportCut("cut_submit");
			agkState("cut_work", s_holdFrames); agkEnd();
		}
		s_lastRevision = s_cutRevision; s_lastBoth = s_cutBoth;
	}
	s_holdFrames = 0;
	s_pBuffer->ubDirtyCounter = 1;
	viewProcessManagers(s_pView);
	copProcessBlocks();
	combatStressSubmitted(s_cutBitmap, s_cutCopper, timerGet());
}

void genericProcess(void) {
	agkPerfBegin();
	if(!s_isLoaded) { agkPerfEnd(); gameExit(); return; }
	renderBindBack(s_pBuffer->pBack);
	acknowledgeFrame();
	keyProcess();
	joyProcess();
#ifdef ASTRA_COMBAT_STRESS
	/* The harness releases only after copying the acknowledged complete image.
	 * Keep all held ticks in whole-frame metrics; never reuse its DMA buffers. */
	if(combatStressCaptureHeld()) {
		if(keyUse(KEY_F10)) combatStressRelease();
		ULONG heldAt = timerGet();
		agkPerfEnd();
		while(timerGet() == heldAt) { }
		return;
	}
#endif
	combatPerfBegin(CP_INJECT);
	combatStressBefore(&s_sState);
	combatPerfEnd(CP_INJECT);
	UBYTE escapePressed = keyUse(KEY_ESCAPE);
	if(escapePressed && (!s_isIntroDone || s_sState.phase == TITLE)) {
		s_confirm.active = s_confirm.visible = s_confirmSubmitted = 0;
		agkPrint("AGK escape_quit\n");
		agkPerfEnd(); gameExit(); return;
	}
	s_mutePending ^= s_isIntroDone && keyUse(KEY_M);
	/* Consume intro/title edges too, so a held P cannot leak into live play. */
	UBYTE pausePressed = keyUse(KEY_P);
	/* Consume edges outside TITLE too; held F9 must not leak across phases. */
	UBYTE previewPressed = keyUse(KEY_F9);
	if(s_isIntroDone && pausePressed) logicTogglePause(&s_sState);
	combatPerfBegin(CP_RESTORE);
	if(s_isIntroDone) renderAnimate(&s_sState);
	combatPerfEnd(CP_RESTORE);
	/* Select music for the acknowledged visible frame, never the hidden work.
	 * This runs at the start of that display tick, within perf measurement. */
	combatPerfBegin(CP_AUDIO);
	if(s_visibleValid) {
		campaignAudioUpdate(s_visibleLevel, s_visiblePhase, s_mutePending);
		s_mutePending = 0;
		if(!s_audioStarted) {
			s_audioStarted = 1;
			agkState("music_visible", s_cutRevision);
			agkState("vblank", timerGet()); agkEnd();
		}
	}
	combatPerfEnd(CP_AUDIO);
	tInput input = readInput();

	if(!s_isIntroDone && !introProcess(input.fire)) {
		s_isIntroDone = 1;
		renderPreparePalette();
		agkPrint("AGK intro_released\n");
		/* A fire used to skip an intro must not also skip the title. */
		s_sState.fireWasDown = input.fire;
	}
	if(s_isIntroDone) {
		UBYTE heartbeat = ++s_ubReportTicks == 50;
		if(heartbeat) s_ubReportTicks = 0;
		tPhase oldPhase = s_sState.phase;
		UBYTE oldLevel = s_sState.level;
		UWORD oldWave = s_sState.wave;
		UBYTE wasPreparing = s_sState.presentationBusy;
#ifdef ASTRA_CAMPAIGN_PROBE
		campaignProbeBeforeUpdate(&s_sState);
#endif
		combatPerfBegin(CP_LOGIC);
		UBYTE confirming = 0;
		if(escapePressed) {
			s_confirm.active = s_confirm.visible = s_confirmSubmitted = 0;
			logicReturnToTitle(&s_sState, &input);
			agkPrint("AGK escape_title\n");
		}
		else if(previewPressed && s_sState.phase == TITLE && !s_sState.presentationBusy) {
			previewEnding(&input);
			agkPrint("AGK ending_preview\n");
		}
		else {
			confirming = titleConfirmFilter(&s_confirm, &s_sState, &input);
			logicUpdate(&s_sState, &input);
		}
		combatPerfEnd(CP_LOGIC);
		if(confirming) {
			agkState("title_confirm_input", 1);
			agkState("vblank", timerGet()); agkEnd();
		}
		ULONG acceptedAt = timerGet();
		UWORD previousRevision = renderRevision();
		/* Confirm has its own sound; retain warp for later sector transitions. */
		combatPerfBegin(CP_AUDIO);
		soundEvents(oldPhase == TITLE ? s_sState.events & ~EVENT_LEVEL : s_sState.events);
		combatPerfEnd(CP_AUDIO);
		combatPerfBegin(CP_RENDER);
		renderFrame(&s_sState);
		combatPerfEnd(CP_RENDER);
		combatStressAfter(&s_sState);
		if(oldPhase == TITLE && (oldLevel != s_sState.level || s_sState.phase != TITLE)) {
			agkState("title_input", renderRevision());
			agkState("phase", s_sState.phase); agkState("level", s_sState.level + 1);
			agkState("vblank", acceptedAt); agkEnd();
		}
		else if(s_sState.phase == TITLE && previousRevision != renderRevision()) {
			agkState("title_begin", renderRevision());
			agkState("from", oldPhase); agkState("vblank", acceptedAt); agkEnd();
		}
#ifdef ASTRA_CAMPAIGN_PROBE
		campaignProbeAfterFrame(&s_sState);
#endif
		if(oldPhase == GAMEOVER && s_sState.phase == TITLE)
			agkPrint("AGK gameover_title\n");
		if(wasPreparing != s_sState.presentationBusy ||
			(s_sState.events & (EVENT_EXPLOSION | EVENT_HIT | EVENT_LEVEL |
				EVENT_BONUS_DROP | EVENT_BONUS_PICKUP)) ||
			oldPhase != s_sState.phase || oldWave != s_sState.wave || pausePressed ||
			heartbeat) reportState();
	}
	combatPerfBegin(CP_WAIT);
	blitWait();
	combatPerfEnd(CP_WAIT);
	combatPerfBegin(CP_PUBLISH);
	publishFrame();
	combatPerfEnd(CP_PUBLISH);
	combatPerfFrame(&s_sState);
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
