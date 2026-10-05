#include "render.h"
#include "render_hero.h"
#include "render_enemies.h"
#include "render_bullets.h"
#include "render_bobs.h"
#include "render_world.h"
#include "render_scenes.h"
#include "art.h"
#include <ace/managers/blit.h>
#include <ace/managers/memory.h>
#include <ace/utils/sprite.h>
#include <ace/utils/custom.h>

static tView *s_pView;
static tVPort *s_pVPort;
static ULONG *s_pBlank;
static UBYTE s_inScene, s_sceneId;
static UWORD s_sceneEpoch;
/* DMA renderers need a phase gate, not a per-frame copy of the entity pools.
 * This zero-initialized display-only state is never passed to portable logic. */
static tGameState s_blankState;

static UBYTE isScene(tPhase phase) {
	return phase == SECTOR_INTRO || phase == BOSS_INTRO || phase == CLEAR || phase == WIN;
}

void renderSyncPalette(void) {
	for(UBYTE index = 0; index < 32; ++index)
		copSetMoveVal(&s_pView->pCopList->pBackBfr->pList[ASTRA_COP_PALETTE + index].sMove,
			s_pVPort->pPalette[index]);
}

void renderPalette(void) {
	UWORD palette[32] = {0};
	artPaletteApply(palette);
	renderWorldSetStarColor(palette[4]);
	for(UBYTE ink = 1; ink < 16; ++ink) palette[16 + ink] = g_pArtHero32Palette[ink];
	for(UBYTE index = 0; index < 32; ++index) {
		s_pVPort->pPalette[index] = palette[index];
		g_pCustom->color[index] = palette[index];
		copSetMove(&s_pView->pCopList->pBackBfr->pList[ASTRA_COP_PALETTE + index].sMove,
			&g_pCustom->color[index], palette[index]);
		copSetMove(&s_pView->pCopList->pFrontBfr->pList[ASTRA_COP_PALETTE + index].sMove,
			&g_pCustom->color[index], palette[index]);
	}
}

UBYTE renderCreate(tView *pView, tVPort *pVPort, tSimpleBufferManager *pBuffer) {
	s_pView = pView;
	s_pVPort = pVPort;
	s_pBlank = memAllocChipClear(sizeof(ULONG));
	if(!s_pBlank) return 0;
	/* Initialize the entire reservation, including padding overwritten by
 * older manager constructors. Never leave zero words as copper commands. */
	for(UBYTE i = 0; i < ASTRA_COP_BUFFER; ++i) {
		copSetMove(&pView->pCopList->pBackBfr->pList[i].sMove, &g_pCustom->bplcon2, 0x24);
		copSetMove(&pView->pCopList->pFrontBfr->pList[i].sMove, &g_pCustom->bplcon2, 0x24);
	}
	/* All eight sprite pointers start blank in both copper buffers; each
	 * renderer then publishes its own hand-built DMA streams. */
	spriteDisableInCopRawMode(pView->pCopList, 0xFF, ASTRA_COP_SPRITES, s_pBlank);
	if(!renderHeroCreate(pView, s_pBlank)) return 0;
	if(!renderEnemiesCreate(pView, s_pBlank)) return 0;
	if(!renderBulletsCreate(pView, s_pBlank)) return 0;
	if(!renderWorldCreate(pVPort, pBuffer->pFront, pBuffer->pBack)) return 0;
	if(!renderScenesCreate(pBuffer->pFront, pBuffer->pBack, pVPort)) return 0;
	if(!renderBobsCreate(pBuffer->pFront, pBuffer->pBack)) return 0;
	renderPalette();
	return 1;
}

void renderBindBack(tBitMap *pBack) {
	renderWorldBind(pBack);
	renderScenesBind(pBack);
	renderBobsBind(pBack);
}

void renderAnimate(tGameState *pState) {
	if(s_inScene || !renderWorldMatches(pState) || !renderWorldReady()) return;
	/* All writes target unpublished pixels; caches belong to this bitmap. */
	renderBobsBegin();
	renderWorldAnimate(pState);
}

void renderFrame(tGameState *pState) {
	if(isScene(pState->phase)) {
		renderBobsDraw(0);
		if(!s_inScene || s_sceneId != pState->sceneId || s_sceneEpoch != pState->sceneEpoch) {
			renderBobsDiscard();
			renderWorldInvalidate(pState->phase == SECTOR_INTRO);
			s_sceneId = pState->sceneId; s_sceneEpoch = pState->sceneEpoch;
			s_inScene = 1;
			renderScenesBegin(s_sceneId, s_sceneEpoch);
		}
		logicSetPresentationBusy(pState, 0);
		renderScenesStep();
	}
	else {
		s_inScene = 0;
		if(!renderWorldMatches(pState)) {
			renderBobsDraw(0);
			/* Discard before any incremental clear, never between Begin/Draw. */
			renderBobsDiscard();
			renderWorldBegin(pState);
		}
		logicSetPresentationBusy(pState, !renderWorldReady());
		renderWorldStep();
		logicSetPresentationBusy(pState, !renderWorldReady());
		if(renderWorldReady()) renderWorldHud(pState);
		renderBobsDraw(pState);
	}
	/* Every channel owner publishes an empty back stream during preparation.
	 * Real phase, collision feedback and channel ownership stay untouched. */
	tGameState *display = s_inScene || !renderWorldReady() ? &s_blankState : pState;
	renderWorldCopper(pState, !s_inScene && renderWorldReady());
	renderHeroDraw(display);
	renderEnemiesDraw(display);
	renderBulletsDraw(display);
}

UBYTE renderSceneReady(void) { return s_inScene && renderScenesReady(); }
UBYTE renderReadyScene(void) { return renderSceneReady(); }
UWORD renderSceneReadyEpoch(void) { return renderScenesReadyEpoch(); }

void renderDestroy(void) {
	blitWait();
	renderBobsDestroy();
	renderBulletsDestroy();
	renderEnemiesDestroy();
	renderHeroDestroy();
	renderScenesDestroy();
	renderWorldDestroy();
	if(s_pBlank) memFree(s_pBlank, sizeof(ULONG));
	s_pBlank = 0;
	s_inScene = 0;
}
