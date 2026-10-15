#include "render_bobs.h"
#include "render_internal.h"
#include "render_boss.h"
#include "render_effects.h"
#include "render_scenes.h"
#include "render_shots.h"
#include "art.h"
#include "combat_perf.h"
#include "galaxy_trace.h"
#include <ace/managers/bob.h>

#define BOB_WIDTH 16
#define BONUS_HEIGHT 16
#define BONUS_FRAMES BONUS_KIND_COUNT
#define LANCE_FRAMES 2

typedef struct { tBitMap *pFrames, *pMask; } tStrip;

static tBitMap *s_pScreen;
static tStrip s_sBonus, s_sShot, s_sLance;
static UBYTE *s_pBonusData[BONUS_FRAMES], *s_pBonusMask[BONUS_FRAMES];
static tBob s_pBonusBobs[BONUS_COUNT];
static UBYTE s_isManagerCreated;
static UBYTE s_isFrameOpen;

static UBYTE stripLoad(tStrip *pStrip, tBitMap *pFrames, tBitMap *pMask, UWORD rows) {
	pStrip->pFrames = pFrames;
	pStrip->pMask = pMask;
	return stripValid(pFrames, BOB_WIDTH, rows) && stripValid(pMask, BOB_WIDTH, rows) &&
		bitmapIsChip(pFrames) && bitmapIsChip(pMask);
}

static void stripFree(tStrip *pStrip) {
	if(pStrip->pMask) bitmapDestroy(pStrip->pMask);
	if(pStrip->pFrames) bitmapDestroy(pStrip->pFrames);
	pStrip->pMask = pStrip->pFrames = 0;
}

UBYTE renderBobsCreate(tBitMap *pFront, tBitMap *pScreen) {
	if(s_isManagerCreated) return pScreen == s_pScreen;
	if(!stripValid(pScreen, WORLD_W, WORLD_H) || !bitmapIsChip(pScreen)) return 0;
	UBYTE ok = stripLoad(&s_sBonus, artBonusesCreate(), artBonusesCreateMask(),
		BONUS_HEIGHT * BONUS_FRAMES);
	ok = ok && stripLoad(&s_sShot, artPshotCreate(), artPshotCreateMask(), SHOT_H);
	ok = ok && stripLoad(&s_sLance, artLanceCreate(), artLanceCreateMask(),
		CHARGED_SHOT_H * LANCE_FRAMES);
	if(!ok) { renderBobsDestroy(); return 0; }
	for(UBYTE frame = 0; frame < BONUS_FRAMES; ++frame) {
		s_pBonusData[frame] = bobCalcFrameAddress(s_sBonus.pFrames, frame * BONUS_HEIGHT);
		s_pBonusMask[frame] = bobCalcFrameAddress(s_sBonus.pMask, frame * BONUS_HEIGHT);
	}
	if(!renderShotsCreate(pFront, pScreen, s_sShot.pFrames, s_sShot.pMask,
		s_sLance.pFrames, s_sLance.pMask)) { renderBobsDestroy(); return 0; }
	s_pScreen = pScreen;
	bobManagerCreate(pFront, pScreen, WORLD_H);
	s_isManagerCreated = 1;
	if(!renderBossCreate() || !renderEffectsCreate()) {
		renderBobsDestroy();
		return 0;
	}
	for(UBYTE i = 0; i < BONUS_COUNT; ++i)
		bobInit(&s_pBonusBobs[i], BOB_WIDTH, BONUS_HEIGHT, 1,
			s_pBonusData[0], s_pBonusMask[0], 0, PLAY_TOP);
	bobReallocateBuffers();
	if(!bobBuffersReady()) { renderBobsDestroy(); return 0; }
	return 1;
}

void renderBobsBind(tBitMap *pScreen) { s_pScreen = pScreen; renderShotsBind(pScreen); }

void renderBobsBegin(void) {
	if(!s_isManagerCreated || s_isFrameOpen) return;
	/* Select by identity, including after scenes where no BOB queue was run.
	 * Restore this bitmap's N-2 background, never the other bitmap's queue. */
	renderShotsRestore();
	bobSetCurrentBuffer(s_pScreen);
	bobBegin(s_pScreen);
	combatPerfBegin(CP_WAIT);
	blitWait();
	combatPerfEnd(CP_WAIT);
	s_isFrameOpen = 1;
}

static UBYTE fits(const tEntity *pEntity, UWORD height) {
	return pEntity->active && pEntity->x >= 0 && pEntity->x <= BOB_MAX_X &&
		pEntity->y >= PLAY_TOP && pEntity->y + height <= PLAY_BOTTOM;
}

static void push(tBob *pBob, const tEntity *pEntity) {
	pBob->sPos.uwX = pEntity->x;
	pBob->sPos.uwY = pEntity->y;
	bobPush(pBob);
}

static void drawPickups(tGameState *pState, UBYTE show) {
	for(UBYTE i = 0; i < BONUS_COUNT; ++i) {
		tEntity *pPickup = &pState->pickups[i];
		pPickup->visible = 0;
		if(!show || pPickup->kind >= BONUS_FRAMES || !fits(pPickup, BONUS_HEIGHT)) continue;
		bobSetFrame(&s_pBonusBobs[i], s_pBonusData[pPickup->kind], s_pBonusMask[pPickup->kind]);
		push(&s_pBonusBobs[i], pPickup);
		hudBobPushed(HB_PICKUP, pPickup->x);
		pPickup->visible = 1;
	}
}

void renderBobsDraw(tGameState *pState) {
	hudBobMark(HB_BOBS_BEGIN);
	combatPerfBegin(CP_BOBS);
	UBYTE show = 0;
	if(pState) {
		show = s_isFrameOpen && (pState->phase == PLAY || pState->phase == BOSS ||
			pState->phase == SECTOR_INTRO || pState->phase == BOSS_INTRO);
		renderBossQueue(pState, s_isFrameOpen);
		hudBobMark(HB_BOSS_QUEUE_END);
		/* Upper-lane blasts must reach the beam before lower reward objects.
		 * Shots and badges remain readable in front of cosmetic explosions. */
		if(s_isFrameOpen) renderEffectsQueue(pState);
		hudBobMark(HB_EFFECTS_QUEUE_END);
		drawPickups(pState, show);
		hudBobMark(HB_PICKUPS_END);
	}
	if(!s_isFrameOpen) { renderShotsDraw(pState, 0); combatPerfEnd(CP_BOBS); return; }
	bobEnd();
	/* Shot backgrounds include current BOB pixels. Their next restoration
	 * therefore precedes ACE's own restore, and their draw follows its wait. */
	blitWait();
	renderShotsDraw(pState, show);
	hudBobMark(HB_SHOTS_END);
	hudBobMark(HB_FLUSH_END);
	combatPerfBegin(CP_WAIT);
	blitWait();
	hudBobMark(HB_WAIT_END);
	combatPerfEnd(CP_WAIT);
	s_isFrameOpen = 0;
	combatPerfEnd(CP_BOBS);
	galaxyTraceMark(5);
}

void renderBobsDiscard(void) {
	if(!s_isManagerCreated || s_isFrameOpen) return;
	blitWait();
	bobDiscardUndraw();
	renderShotsDiscard();
}

void renderBobsDestroy(void) {
	blitWait();
	renderShotsDestroy();
	if(s_isManagerCreated) bobManagerDestroy();
	s_isManagerCreated = 0;
	s_isFrameOpen = 0;
	renderEffectsDestroy();
	renderBossDestroy();
	stripFree(&s_sLance);
	stripFree(&s_sShot);
	stripFree(&s_sBonus);
	s_pScreen = 0;
}
