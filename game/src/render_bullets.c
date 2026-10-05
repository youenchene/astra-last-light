#include "render_bullets.h"
#include "render_stream.h"
#include "art.h"

#define BULLET_FIRST_CHANNEL 4
#define BULLET_CHANNELS 4
#define BULLET_FRAME_HEIGHT 10
#define BULLET_HOSTILE_FRAME 2

static const tView *s_pView;
static ULONG *s_pBlank;
static tSpriteStream s_pStreams[BULLET_CHANNELS];
static ULONG s_pPixels[2][HOSTILE_H];
/* Hostile pool indices per channel, kept in Y order between frames. A
 * channel's bullets never cross (logic admission), so order is stable. */
static UBYTE s_pOrder[BULLET_CHANNELS][BULLET_SPRITE_CAPACITY];
static UBYTE s_pCount[BULLET_CHANNELS];
static UBYTE s_mask;

#if HOSTILE_COUNT > 32
#error Hostile membership masks require at most 32 pool slots
#endif

/* Map opaque bullet inks to the nearest existing hero ink 9..11 (hardware
 * registers 25..27). Never change the attached hero's palette. Startup only. */
static UBYTE heroInk(UWORD color) {
	UWORD best = 0xffff;
	UBYTE ink = 1;
	for(UBYTE candidate = 1; candidate <= 3; ++candidate) {
		UWORD other = g_pArtHero32Palette[8 + candidate];
		WORD r = ((color >> 8) & 15) - ((other >> 8) & 15);
		WORD g = ((color >> 4) & 15) - ((other >> 4) & 15);
		WORD b = (color & 15) - (other & 15);
		UWORD distance = r * r + g * g + b * b;
		if(distance < best) { best = distance; ink = candidate; }
	}
	return ink;
}

static void cachePixels(const ULONG *pRows) {
	UBYTE inks[4] = {0, heroInk(g_pArtBulletsPalette[1]),
		heroInk(g_pArtBulletsPalette[2]), heroInk(g_pArtBulletsPalette[3])};
	for(UBYTE row = 0; row < HOSTILE_H; ++row) {
		ULONG pixels = pRows[row];
		UWORD low = pixels >> 16, high = pixels, mappedLow = 0, mappedHigh = 0;
		for(UWORD bit = 0x8000; bit; bit >>= 1) {
			UBYTE ink = inks[((low & bit) ? 1 : 0) | ((high & bit) ? 2 : 0)];
			if(ink & 1) mappedLow |= bit;
			if(ink & 2) mappedHigh |= bit;
		}
		s_pPixels[0][row] = ((ULONG)mappedLow << 16) | mappedHigh;
		s_pPixels[1][row] = pixels;
	}
}

UBYTE renderBulletsCreate(const tView *pView, ULONG *pBlank) {
	if(s_pView || !pView || !pBlank) return 0;
	tBitMap *pStrip = artBulletsCreate();
	UBYTE ok = pStrip && pStrip->Depth == 2 && pStrip->BytesPerRow == 4 &&
		(pStrip->Flags & BMF_INTERLEAVED) &&
		pStrip->Rows >= (BULLET_HOSTILE_FRAME + 1) * BULLET_FRAME_HEIGHT;
	if(ok) {
		/* 2bpp interleaved rows are already plane0/plane1 word pairs. */
		const ULONG *pRows = (const ULONG *)(pStrip->Planes[0] +
			BULLET_HOSTILE_FRAME * BULLET_FRAME_HEIGHT * 4);
		cachePixels(pRows);
	}
	if(pStrip) bitmapDestroy(pStrip);
	if(!ok) return 0;
	s_pView = pView;
	s_pBlank = pBlank;
	s_mask = 0;
	for(UBYTE channel = 0; channel < BULLET_CHANNELS; ++channel) {
		s_pCount[channel] = 0;
		if(!spriteStreamCreate(&s_pStreams[channel], pView, BULLET_FIRST_CHANNEL + channel,
			HOSTILE_H, BULLET_SPRITE_CAPACITY)) {
			renderBulletsDestroy();
			return 0;
		}
	}
	return 1;
}

/* One pass over the pool: keep last frame's order for survivors, append
 * newcomers, then insertion-sort (linear for already ordered survivors).
 * Reused pool slots simply re-sort by their new Y. */
static void gatherChannels(tEntity *pHostile, UBYTE mask, UBYTE show) {
	ULONG drawn[BULLET_CHANNELS] = {0, 0, 0, 0};
	for(UBYTE index = 0; index < HOSTILE_COUNT; ++index) {
		tEntity *pEntity = &pHostile[index];
		pEntity->visible = 0;
		if(!show || !pEntity->active || pEntity->x <= -HOSTILE_W ||
			pEntity->x >= WORLD_W || pEntity->y < PLAY_TOP ||
			pEntity->y > PLAY_BOTTOM - HOSTILE_H) continue;
		if(pEntity->channel < BULLET_FIRST_CHANNEL || pEntity->channel > 7 ||
			!(mask & (1U << pEntity->channel))) continue;
		drawn[pEntity->channel - BULLET_FIRST_CHANNEL] |= 1UL << index;
	}
	for(UBYTE channel = 0; channel < BULLET_CHANNELS; ++channel) {
		UBYTE *pOrder = s_pOrder[channel];
		UBYTE count = 0;
		ULONG pending = drawn[channel];
		for(UBYTE i = 0; i < s_pCount[channel]; ++i) {
			ULONG bit = 1UL << pOrder[i];
			if(!(pending & bit)) continue;
			pending &= ~bit;
			pOrder[count++] = pOrder[i];
		}
		for(UBYTE index = 0; pending && count < BULLET_SPRITE_CAPACITY; ++index, pending >>= 1)
			if(pending & 1) pOrder[count++] = index;
		for(UBYTE i = 1; i < count; ++i) {
			UBYTE index = pOrder[i];
			WORD y = pHostile[index].y;
			UBYTE j = i;
			for(; j && pHostile[pOrder[j - 1]].y > y; --j) pOrder[j] = pOrder[j - 1];
			pOrder[j] = index;
		}
		s_pCount[channel] = count;
	}
}

void renderBulletsDraw(tGameState *pState) {
	if(!pState || !s_pView) return;
	UBYTE mask = logicHostileChannelMask(pState);
	if(mask != s_mask) {
		for(UBYTE channel = 0; channel < BULLET_CHANNELS; ++channel) s_pCount[channel] = 0;
		s_mask = mask;
	}
	gatherChannels(pState->hostile, mask, logicCombatActive(pState));
	UWORD posX = s_pView->ubPosX - 1, posY = s_pView->ubPosY;
	for(UBYTE channel = 0; channel < BULLET_CHANNELS; ++channel) {
		/* Enemies publish 4/5 (including blank) unless logic lends the pair.
		 * Only the selected back buffer is touched, even on ownership changes. */
		if(channel < 2 && !(mask & (1U << BULLET_FIRST_CHANNEL))) continue;
		UBYTE buffer = spriteStreamBuffer(&s_pStreams[channel], s_pView);
		tSpriteWriter writer;
		spriteWriterBegin(&writer, &s_pStreams[channel], buffer);
		WORD nextY = -32767;
		const UBYTE *pOrder = s_pOrder[channel];
		for(UBYTE i = s_pCount[channel]; i; --i) {
			tEntity *pEntity = &pState->hostile[*pOrder++];
			/* Admission keeps HOSTILE_H + 2 lines between neighbours. */
			if(pEntity->y < nextY) { pEntity->visible = 0; continue; }
			spriteWriterPut(&writer, posX + pEntity->x, posY + pEntity->y, 0,
				s_pPixels[channel >> 1]);
			pEntity->visible = 1;
			nextY = pEntity->y + HOSTILE_H + 1;
		}
		spriteWriterPublish(&writer, s_pView);
	}
}

void renderBulletsDestroy(void) {
	for(UBYTE channel = 0; channel < BULLET_CHANNELS; ++channel) {
		spriteStreamDestroy(&s_pStreams[channel], s_pView, s_pBlank);
		s_pCount[channel] = 0;
	}
	s_pView = 0;
	s_pBlank = 0;
}
