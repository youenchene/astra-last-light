#include "render_effects.h"
#include "render_internal.h"
#include "art.h"
#include "hud_bob_trace.h"
#include <ace/managers/bob.h>

#define FX_FRAMES 8
#define FX_SIZES 3
typedef struct {
	tBitMap *pFrames, *pMask;
	UBYTE *pData[FX_FRAMES], *pMasks[FX_FRAMES];
} tEffectStrip;
static tEffectStrip s_pStrips[FX_SIZES];
static const UBYTE s_pWidths[FX_SIZES] = {16, 32, 64};
static const UBYTE s_pHeights[FX_SIZES] = {16, 32, 48};
static tBob s_pBobs[EFFECT_COUNT];
static UBYTE s_isReady;

static UBYTE loadStrip(UBYTE size, tBitMap *pFrames, tBitMap *pMask) {
	tEffectStrip *pStrip = &s_pStrips[size];
	pStrip->pFrames = pFrames;
	pStrip->pMask = pMask;
	UWORD rows = s_pHeights[size] * FX_FRAMES;
	if(!stripValid(pFrames, s_pWidths[size], rows) ||
		!stripValid(pMask, s_pWidths[size], rows) ||
		!bitmapIsChip(pFrames) || !bitmapIsChip(pMask)) return 0;
	for(UBYTE frame = 0; frame < FX_FRAMES; ++frame) {
		pStrip->pData[frame] = bobCalcFrameAddress(pFrames, frame * s_pHeights[size]);
		pStrip->pMasks[frame] = bobCalcFrameAddress(pMask, frame * s_pHeights[size]);
	}
	return 1;
}

UBYTE renderEffectsCreate(void) {
	if(!loadStrip(0, artCampaignFx16Create(), artCampaignFx16CreateMask()) ||
		!loadStrip(1, artCampaignFx32Create(), artCampaignFx32CreateMask()) ||
		!loadStrip(2, artCampaignFx64Create(), artCampaignFx64CreateMask())) {
		renderEffectsDestroy();
		return 0;
	}
	for(UBYTE i = 0; i < EFFECT_COUNT; ++i) {
		UBYTE size = i < SMALL_EFFECT_COUNT ? 0 : (i == HERO_EFFECT_SLOT ? 1 : 2);
		bobInit(&s_pBobs[i], s_pWidths[size], s_pHeights[size], 1,
			s_pStrips[size].pData[0], s_pStrips[size].pMasks[0], 0, PLAY_TOP);
	}
	s_isReady = 1;
	return 1;
}

/* Bounded seven comparisons avoid a variable division in the video loop. */
static UBYTE effectFrame(const tEffect *pEffect) {
	UWORD scaledAge = (UWORD)pEffect->age << 3;
	UWORD threshold = pEffect->lifetime;
	UBYTE frame = 0;
	while(frame < FX_FRAMES - 1 && scaledAge >= threshold) {
		++frame;
		threshold += pEffect->lifetime;
	}
	return frame;
}

void renderEffectsQueue(const tGameState *pState) {
	if(!s_isReady || !(logicCombatActive(pState) ||
		pState->phase == HERO_DYING || pState->phase == BOSS_DYING)) return;
	for(UBYTE i = 0; i < EFFECT_COUNT; ++i) {
		const tEffect *pEffect = &pState->effects[i];
		if(!pEffect->active || !pEffect->lifetime || pEffect->kind > FX_BOSS) continue;
		UBYTE size = i < SMALL_EFFECT_COUNT ? 0 : (i == HERO_EFFECT_SLOT ? 1 : 2);
		if((size == 0 && pEffect->kind > FX_ASTEROID) ||
			(size == 1 && pEffect->kind != FX_HERO) ||
			(size == 2 && pEffect->kind != FX_BOSS)) continue;
		WORD x = pEffect->x, y = pEffect->y;
		WORD maxX = WORLD_W - s_pWidths[size] - 1;
		WORD maxY = PLAY_BOTTOM - s_pHeights[size];
		if(x < 0) x = 0;
		if(x > maxX) x = maxX;
		if(y < PLAY_TOP) y = PLAY_TOP;
		if(y > maxY) y = maxY;
		UBYTE frame = effectFrame(pEffect);
		tBob *pBob = &s_pBobs[i];
		bobSetFrame(pBob, s_pStrips[size].pData[frame], s_pStrips[size].pMasks[frame]);
		pBob->sPos.uwX = x;
		pBob->sPos.uwY = y;
		bobPush(pBob);
		hudBobPushed(size == 0 ? HB_SMALL_FX : (size == 1 ? HB_HERO_FX : HB_BOSS_FX), x);
	}
}

void renderEffectsDestroy(void) {
	for(UBYTE size = 0; size < FX_SIZES; ++size) {
		if(s_pStrips[size].pMask) bitmapDestroy(s_pStrips[size].pMask);
		if(s_pStrips[size].pFrames) bitmapDestroy(s_pStrips[size].pFrames);
		s_pStrips[size].pMask = s_pStrips[size].pFrames = 0;
	}
	s_isReady = 0;
}
