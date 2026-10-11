#include "render_boss.h"
#include "render_internal.h"
#include "art.h"
#include "hud_bob_trace.h"
#include <ace/managers/bob.h>

static tBitMap *s_pFrames, *s_pMask, *s_pFlash;
static UBYTE *s_pData[LEVEL_COUNT], *s_pMasks[LEVEL_COUNT];
static tBob s_sBob;
static UBYTE s_isReady, s_flashLevel;

UBYTE renderBossCreate(void) {
	s_pFrames = artCampaignBossCreate();
	s_pMask = artCampaignBossCreateMask();
	/* White is world ink 7: three silhouette planes, then a zero plane.
	 * Cache only the current sector's white frame, saving 10,752 chip bytes
	 * over a separate four-frame flash strip and its duplicate mask. */
	s_pFlash = bitmapCreate(BOSS_W, BOSS_H, 4, BMF_CLEAR | BMF_INTERLEAVED);
	if(!stripValid(s_pFrames, BOSS_W, BOSS_H * LEVEL_COUNT) ||
		!stripValid(s_pMask, BOSS_W, BOSS_H * LEVEL_COUNT) ||
		!stripValid(s_pFlash, BOSS_W, BOSS_H) ||
		!bitmapIsChip(s_pFrames) || !bitmapIsChip(s_pMask) || !bitmapIsChip(s_pFlash)) {
		renderBossDestroy();
		return 0;
	}
	for(UBYTE i = 0; i < LEVEL_COUNT; ++i) {
		s_pData[i] = bobCalcFrameAddress(s_pFrames, i * BOSS_H);
		s_pMasks[i] = bobCalcFrameAddress(s_pMask, i * BOSS_H);
	}
	bobInit(&s_sBob, BOSS_W, BOSS_H, 1, s_pData[0], s_pMasks[0], 0, PLAY_TOP);
	s_flashLevel = LEVEL_COUNT;
	s_isReady = 1;
	return 1;
}

static void cacheFlash(UBYTE level) {
	if(s_flashLevel == level) return;
	const UWORD *pMask = (const UWORD *)s_pMasks[level];
	UWORD *pDest = (UWORD *)s_pFlash->Planes[0];
	for(UBYTE row = 0; row < BOSS_H; ++row) {
		for(UBYTE word = 0; word < 12; ++word) *pDest++ = *pMask++;
		pDest += 4;
		pMask += 4;
	}
	s_flashLevel = level;
}

void renderBossQueue(tGameState *pState, UBYTE show) {
	tBoss *pBoss = &pState->boss;
	pBoss->visible = 0;
	UBYTE phaseVisible = pState->phase == BOSS || pState->phase == BOSS_DYING ||
		(pState->phase == HERO_DYING && pState->resumePhase == BOSS);
	if(!show || !s_isReady || !phaseVisible || !pBoss->active ||
		pState->level >= LEVEL_COUNT || pBoss->x < 0 ||
		pBoss->x > WORLD_W - BOSS_W - 1 || pBoss->y < PLAY_TOP ||
		pBoss->y > PLAY_BOTTOM - BOSS_H) return;
	UBYTE level = pState->level;
	cacheFlash(level);
	/* Starts white on the six-tick hit, alternates without hiding the body. */
	UBYTE flash = pBoss->flashTicks && !(pBoss->flashTicks & 1);
	bobSetFrame(&s_sBob, flash ? s_pFlash->Planes[0] : s_pData[level], s_pMasks[level]);
	s_sBob.sPos.uwX = pBoss->x;
	s_sBob.sPos.uwY = pBoss->y;
	bobPush(&s_sBob);
	hudBobPushed(HB_BOSS, pBoss->x);
	pBoss->visible = 1;
}

void renderBossDestroy(void) {
	if(s_pFlash) bitmapDestroy(s_pFlash);
	if(s_pMask) bitmapDestroy(s_pMask);
	if(s_pFrames) bitmapDestroy(s_pFrames);
	s_pFlash = s_pMask = s_pFrames = 0;
	s_isReady = 0;
}
