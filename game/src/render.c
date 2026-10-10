#include "render.h"
#include "render_hero.h"
#include "render_enemies.h"
#include "render_bullets.h"
#include "render_bobs.h"
#include "render_world.h"
#include "render_scenes.h"
#include "art.h"
#include "combat_perf.h"
#include <ace/managers/blit.h>
#include <ace/managers/memory.h>
#include <ace/utils/sprite.h>
#include <ace/utils/custom.h>
#include <agk/debug.h>

static tView *s_pView;
static tVPort *s_pVPort;
static ULONG *s_pBlank;
static UBYTE s_inScene, s_sceneId, s_closingOpening;
static UWORD s_sceneEpoch;
static UWORD s_revision;
static UBYTE s_targetReady;
/* DMA renderers need a phase gate, not a per-frame copy of the entity pools.
 * This zero-initialized display-only state is never passed to portable logic. */
static tGameState s_blankState;

static UBYTE constructionResult(UBYTE ok, UBYTE owner) {
	if(!ok) {
		agkState("render_allocation_owner", owner);
		agkState("chip_free", memGetFreeChipSize());
		agkState("ram_free", memGetFreeSize()); agkEnd();
	}
	return ok;
}

static UBYTE isScene(tPhase phase) {
	return phase == SECTOR_INTRO || phase == BOSS_INTRO || phase == CLEAR || phase == WIN;
}

void renderSyncPalette(void) {
	for(UBYTE index = 0; index < 32; ++index)
		copSetMoveVal(&s_pView->pCopList->pBackBfr->pList[ASTRA_COP_PALETTE + index].sMove,
			s_pVPort->pPalette[index]);
}

void renderPreparePalette(void) {
	UWORD palette[32] = {0};
	artPaletteApply(palette);
	renderWorldSetStarColor(palette[4]);
	for(UBYTE ink = 1; ink < 16; ++ink) palette[16 + ink] = g_pArtHero32Palette[ink];
	for(UBYTE index = 0; index < 32; ++index)
		s_pVPort->pPalette[index] = palette[index];
}

void renderTitleFlash(UBYTE bright) {
	if(!bright) return;
	for(UBYTE ink = 6; ink <= 14; ink += 8)
		copSetMoveVal(&s_pView->pCopList->pBackBfr->pList[ASTRA_COP_PALETTE + ink].sMove, 0xfff);
}

void renderPalette(void) {
	renderPreparePalette();
	for(UBYTE index = 0; index < 32; ++index) {
		UWORD color = s_pVPort->pPalette[index];
		g_pCustom->color[index] = color;
		copSetMove(&s_pView->pCopList->pBackBfr->pList[ASTRA_COP_PALETTE + index].sMove,
			&g_pCustom->color[index], color);
		copSetMove(&s_pView->pCopList->pFrontBfr->pList[ASTRA_COP_PALETTE + index].sMove,
			&g_pCustom->color[index], color);
	}
}

UBYTE renderCreate(tView *pView, tVPort *pVPort, tSimpleBufferManager *pBuffer) {
	s_pView = pView;
	s_pVPort = pVPort;
	s_pBlank = memAllocChipClear(sizeof(ULONG));
	if(!constructionResult(s_pBlank != 0, 0)) return 0;
	/* Initialize the entire reservation, including padding overwritten by
 * older manager constructors. Never leave zero words as copper commands. */
	for(UBYTE i = 0; i < ASTRA_COP_BUFFER; ++i) {
		copSetMove(&pView->pCopList->pBackBfr->pList[i].sMove, &g_pCustom->bplcon2, 0x24);
		copSetMove(&pView->pCopList->pFrontBfr->pList[i].sMove, &g_pCustom->bplcon2, 0x24);
	}
	/* All eight sprite pointers start blank in both copper buffers; each
	 * renderer then publishes its own hand-built DMA streams. */
	spriteDisableInCopRawMode(pView->pCopList, 0xFF, ASTRA_COP_SPRITES, s_pBlank);
	if(!constructionResult(renderHeroCreate(pView, s_pBlank), 1)) return 0;
	if(!constructionResult(renderEnemiesCreate(pView, s_pBlank), 2)) return 0;
	if(!constructionResult(renderBulletsCreate(pView, s_pBlank), 3)) return 0;
	if(!constructionResult(renderWorldCreate(pVPort, pBuffer->pFront, pBuffer->pBack), 4)) return 0;
	if(!constructionResult(renderScenesCreate(pBuffer->pFront, pBuffer->pBack, pVPort), 5)) return 0;
	if(!constructionResult(renderBobsCreate(pBuffer->pFront, pBuffer->pBack), 6)) return 0;
	renderPalette();
	return 1;
}

void renderBindBack(tBitMap *pBack) {
	renderWorldBind(pBack);
	renderScenesBind(pBack);
	renderBobsBind(pBack);
}

void renderAnimate(tGameState *pState) {
	if(s_inScene && (pState->phase == SECTOR_INTRO || pState->phase == BOSS_INTRO) && pState->sceneReady &&
		!pState->presentationBusy) {
		/* Live BOBs restore the actual back bitmap, including its overlay
		 * pixels. Stars and decor stay frozen until the window has gone. */
		renderBobsBegin();
		return;
	}
	if(s_inScene || pState->presentationBusy ||
		!renderWorldMatches(pState) || !renderWorldReady()) return;
	/* All writes target unpublished pixels; caches belong to this bitmap. */
	renderBobsBegin();
	renderWorldAnimate(pState);
}

void renderFrame(tGameState *pState) {
	if(s_inScene && s_sceneId < 12 &&
		((s_sceneId % 3 == 0 && pState->phase == PLAY) ||
		 (s_sceneId % 3 == 1 && pState->phase == BOSS))) {
		if(!s_closingOpening) {
			s_closingOpening = 1;
			renderScenesClose();
			++s_revision;
			logicSetPresentationBusy(pState, 1);
		}
		/* Each bitmap's old BOBs must be restored before erasing its panel.
		 * Never discard the other bitmap's still-needed restore queue. */
		renderBobsBegin();
		renderBobsDraw(0);
		renderScenesEraseStep();
		s_targetReady = renderScenesTargetReady();
		if(s_targetReady) {
			renderBobsBegin();
			renderWorldHud(pState);
			renderBobsDraw(pState);
		}
	}
	else if(isScene(pState->phase)) {
		if(!s_inScene || s_sceneId != pState->sceneId || s_sceneEpoch != pState->sceneEpoch) {
			renderBobsDraw(0);
			renderBobsDiscard();
			renderWorldInvalidate(pState->phase == SECTOR_INTRO);
			renderWorldBegin(pState);
			s_sceneId = pState->sceneId; s_sceneEpoch = pState->sceneEpoch;
			s_inScene = 1;
			renderScenesBegin(s_sceneId, s_sceneEpoch);
			++s_revision;
			logicSetPresentationBusy(pState, 1);
		}
		/* One bounded step total, not one world step plus one overlay step.
		 * Both targets rebuild the same frozen scenery before their window. */
		if(!renderWorldTargetReady()) renderWorldStep();
		else renderScenesStep();
		s_targetReady = renderWorldTargetReady() && renderScenesTargetReady();
		if((pState->phase == SECTOR_INTRO || pState->phase == BOSS_INTRO) && renderBothReady()) {
			renderBobsBegin();
			renderWorldHud(pState);
			renderBobsDraw(pState);
		}
		else renderBobsDraw(0);
	}
	else {
		s_inScene = 0;
		if(!renderWorldMatches(pState)) {
			renderBobsDraw(0);
			/* Discard before any incremental clear, never between Begin/Draw. */
			renderBobsDiscard();
			renderWorldBegin(pState);
			++s_revision;
			logicSetPresentationBusy(pState, 1);
		}
		renderWorldStep();
		s_targetReady = renderWorldTargetReady();
		if(s_targetReady) {
			renderBobsBegin();
			renderWorldHud(pState);
		}
		renderBobsDraw(pState);
	}
	/* Every channel owner publishes an empty back stream during preparation.
	 * Real phase, collision feedback and channel ownership stay untouched. */
	UBYTE liveOpening = (pState->phase == SECTOR_INTRO || pState->phase == BOSS_INTRO) && renderBothReady();
	tGameState *display = !s_targetReady || (s_inScene && !liveOpening && !s_closingOpening)
		? &s_blankState : pState;
	combatPerfBegin(CP_COPPER);
	renderWorldCopper(pState, s_targetReady);
	combatPerfEnd(CP_COPPER);
	if(s_targetReady) renderWorldPause(pState);
	combatPerfBegin(CP_SPRITES);
	renderHeroDraw(s_targetReady ? pState : &s_blankState);
	renderEnemiesDraw(display);
	renderBulletsDraw(display);
	combatPerfEnd(CP_SPRITES);
}

UBYTE renderTargetReady(void) { return s_targetReady; }
UBYTE renderBothReady(void) {
	return renderWorldReady() && (!s_inScene || renderScenesReady());
}
UWORD renderRevision(void) { return s_revision; }

void renderAcknowledge(tGameState *state) {
	/* Main calls only after the complete target's copper passed vblank. */
	if(!renderBothReady()) return;
	logicSetPresentationBusy(state, 0);
	if(s_closingOpening) {
		s_closingOpening = s_inScene = 0;
		renderWorldResumeCombat(state->phase);
		return;
	}
	if(s_inScene) logicScenePresented(state, s_sceneEpoch);
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
	s_closingOpening = 0;
}
