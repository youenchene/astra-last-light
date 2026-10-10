#include "render_bobs.h"
#include "render_internal.h"
#include "render_boss.h"
#include "render_effects.h"
#include "render_scenes.h"
#include "art.h"
#include "combat_perf.h"
#include <ace/managers/bob.h>

#define BOB_WIDTH 16
#define BONUS_HEIGHT 16
#define BONUS_FRAMES BONUS_KIND_COUNT
#define LANCE_FRAMES 2
/* At most two lances live at once (50-tick charge, 70-tick flight). */
#define LANCE_BOBS 4

typedef struct { tBitMap *pFrames, *pMask; } tStrip;

static tBitMap *s_pScreen;
static tStrip s_sBonus, s_sShot, s_sLance;
static UBYTE *s_pBonusData[BONUS_FRAMES], *s_pBonusMask[BONUS_FRAMES];
static UBYTE *s_pLanceData[LANCE_FRAMES], *s_pLanceMask[LANCE_FRAMES];
static tBob s_pBonusBobs[BONUS_COUNT];
static tBob s_pShotBobs[SHOT_COUNT];
static tBob s_pLanceBobs[LANCE_BOBS];
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
	for(UBYTE frame = 0; frame < LANCE_FRAMES; ++frame) {
		s_pLanceData[frame] = bobCalcFrameAddress(s_sLance.pFrames, frame * CHARGED_SHOT_H);
		s_pLanceMask[frame] = bobCalcFrameAddress(s_sLance.pMask, frame * CHARGED_SHOT_H);
	}
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
	for(UBYTE i = 0; i < SHOT_COUNT; ++i)
		bobInit(&s_pShotBobs[i], BOB_WIDTH, SHOT_H, 1,
			s_sShot.pFrames->Planes[0], s_sShot.pMask->Planes[0], 0, PLAY_TOP);
	for(UBYTE i = 0; i < LANCE_BOBS; ++i)
		bobInit(&s_pLanceBobs[i], BOB_WIDTH, CHARGED_SHOT_H, 1,
			s_pLanceData[0], s_pLanceMask[0], 0, PLAY_TOP);
	bobReallocateBuffers();
	if(!bobBuffersReady()) { renderBobsDestroy(); return 0; }
	return 1;
}

void renderBobsBind(tBitMap *pScreen) { s_pScreen = pScreen; }

void renderBobsBegin(void) {
	if(!s_isManagerCreated || s_isFrameOpen) return;
	/* Select by identity, including after scenes where no BOB queue was run.
	 * Restore this bitmap's N-2 background, never the other bitmap's queue. */
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
		pPickup->visible = 1;
	}
}

static void drawShots(tGameState *pState, UBYTE show) {
	UBYTE lances = 0, flash = (pState->frame >> 2) & 1;
	for(UBYTE i = 0; i < SHOT_COUNT; ++i) {
		tEntity *pShot = &pState->shots[i];
		UBYTE charged = pShot->kind == SHOT_CHARGED;
		pShot->visible = 0;
		if(!show || pShot->kind > SHOT_CHARGED ||
			!fits(pShot, charged ? CHARGED_SHOT_H : SHOT_H)) continue;
		if((pState->phase == SECTOR_INTRO || pState->phase == BOSS_INTRO) && renderScenesOccludes(pShot->x, pShot->y,
			BOB_WIDTH, charged ? CHARGED_SHOT_H : SHOT_H)) continue;
		if(!charged) { push(&s_pShotBobs[i], pShot); pShot->visible = 1; continue; }
		if(lances >= LANCE_BOBS) continue;
		tBob *pBob = &s_pLanceBobs[lances++];
		bobSetFrame(pBob, s_pLanceData[flash], s_pLanceMask[flash]);
		push(pBob, pShot);
		pShot->visible = 1;
	}
}

void renderBobsDraw(tGameState *pState) {
	combatPerfBegin(CP_BOBS);
	if(pState) {
		UBYTE show = s_isFrameOpen && (pState->phase == PLAY || pState->phase == BOSS ||
			pState->phase == SECTOR_INTRO || pState->phase == BOSS_INTRO);
		renderBossQueue(pState, s_isFrameOpen);
		/* Upper-lane blasts must reach the beam before lower reward objects.
		 * Shots and badges remain readable in front of cosmetic explosions. */
		if(s_isFrameOpen) renderEffectsQueue(pState);
		drawPickups(pState, show);
		drawShots(pState, show);
	}
	if(!s_isFrameOpen) { combatPerfEnd(CP_BOBS); return; }
	bobEnd();
	combatPerfBegin(CP_WAIT);
	blitWait();
	combatPerfEnd(CP_WAIT);
	s_isFrameOpen = 0;
	combatPerfEnd(CP_BOBS);
}

void renderBobsDiscard(void) {
	if(!s_isManagerCreated || s_isFrameOpen) return;
	blitWait();
	bobDiscardUndraw();
}

void renderBobsDestroy(void) {
	blitWait();
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
