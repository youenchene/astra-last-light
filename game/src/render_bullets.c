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
/* 68000 register-count shifts cost more as pool indices grow. Survivor
 * membership uses fixed lookups; the linear gather carries a single bit. */
static const ULONG s_membership[32] = {
	0x00000001UL, 0x00000002UL, 0x00000004UL, 0x00000008UL,
	0x00000010UL, 0x00000020UL, 0x00000040UL, 0x00000080UL,
	0x00000100UL, 0x00000200UL, 0x00000400UL, 0x00000800UL,
	0x00001000UL, 0x00002000UL, 0x00004000UL, 0x00008000UL,
	0x00010000UL, 0x00020000UL, 0x00040000UL, 0x00080000UL,
	0x00100000UL, 0x00200000UL, 0x00400000UL, 0x00800000UL,
	0x01000000UL, 0x02000000UL, 0x04000000UL, 0x08000000UL,
	0x10000000UL, 0x20000000UL, 0x40000000UL, 0x80000000UL
};

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
		/* One hostile image for every level: pixels are written once here,
		 * frames rewrite only control words. */
		spriteStreamFill(&s_pStreams[channel], s_pPixels[channel >> 1]);
	}
	return 1;
}

/* One pass over the pool marks drawable hostiles per channel. */
static void gatherChannels(tEntity *pHostile, UBYTE mask, UBYTE show, ULONG *pDrawn) {
	ULONG membership = 1;
	UBYTE firstChannel = mask == 0xc0 ? 6 : 4;
	for(UBYTE index = 0; index < HOSTILE_COUNT; ++index, membership <<= 1) {
		tEntity *pEntity = &pHostile[index];
		pEntity->visible = 0;
		if(!show || !pEntity->active || pEntity->x <= -HOSTILE_W ||
			pEntity->x >= WORLD_W || pEntity->y < PLAY_TOP ||
			pEntity->y > PLAY_BOTTOM - HOSTILE_H) continue;
		if(!mask || pEntity->channel < firstChannel || pEntity->channel > 7) continue;
		pDrawn[pEntity->channel - BULLET_FIRST_CHANNEL] |= membership;
	}
}

/* Insertion by cached Y key: one comparison when already in order. */
static inline void insertOrdered(WORD *pKeys, tEntity **pList, UBYTE *pOrder,
	UBYTE count, tEntity *pEntity, UBYTE index) {
	WORD y = pEntity->y;
	for(; count && pKeys[count - 1] > y; --count) {
		pKeys[count] = pKeys[count - 1];
		pList[count] = pList[count - 1];
		pOrder[count] = pOrder[count - 1];
	}
	pKeys[count] = y;
	pList[count] = pEntity;
	pOrder[count] = index;
}

/* Survivors first in last frame's order, then newcomers in pool order.
 * Reused pool slots simply re-sort by their new Y. */
static UBYTE orderChannel(UBYTE channel, tEntity *pHostile, ULONG pending, tEntity **pList) {
	UBYTE *pOrder = s_pOrder[channel];
	WORD keys[BULLET_SPRITE_CAPACITY];
	UBYTE count = 0;
	for(UBYTE i = 0; i < s_pCount[channel]; ++i) {
		UBYTE index = pOrder[i];
		ULONG bit = s_membership[index];
		if(!(pending & bit)) continue;
		pending &= ~bit;
		insertOrdered(keys, pList, pOrder, count++, &pHostile[index], index);
	}
	for(UBYTE index = 0; pending && count < BULLET_SPRITE_CAPACITY; ++index, pending >>= 1)
		if(pending & 1) insertOrdered(keys, pList, pOrder, count++, &pHostile[index], index);
	s_pCount[channel] = count;
	return count;
}

void renderBulletsDraw(tGameState *pState) {
	if(!pState || !s_pView) return;
	UBYTE mask = logicHostileChannelMask(pState);
	if(mask != s_mask) {
		for(UBYTE channel = 0; channel < BULLET_CHANNELS; ++channel) s_pCount[channel] = 0;
		s_mask = mask;
	}
	ULONG drawn[BULLET_CHANNELS] = {0, 0, 0, 0};
	gatherChannels(pState->hostile, mask, logicCombatActive(pState), drawn);
	UWORD posX = s_pView->ubPosX - 1, posY = s_pView->ubPosY;
	for(UBYTE channel = 0; channel < BULLET_CHANNELS; ++channel) {
		/* Enemies publish 4/5 (including blank) unless logic lends the pair.
		 * Only the selected back buffer is touched, even on ownership changes. */
		if(channel < 2 && !(mask & (1U << BULLET_FIRST_CHANNEL))) continue;
		tEntity *pList[BULLET_SPRITE_CAPACITY];
		UBYTE count = orderChannel(channel, pState->hostile, drawn[channel], pList);
		tSpriteStream *pStream = &s_pStreams[channel];
		ULONG *pBase = spriteStreamRows(pStream, s_pView), *pSlot = pBase;
		WORD nextY = -32767;
		for(tEntity **ppEntity = pList; count; --count) {
			tEntity *pEntity = *ppEntity++;
			WORD y = pEntity->y;
			/* Admission keeps HOSTILE_H + 2 lines between neighbours. */
			if(y < nextY) continue;
			pSlot = spriteSlotPlace(pSlot, posX + pEntity->x, posY + y, HOSTILE_H);
			pEntity->visible = 1;
			nextY = y + HOSTILE_H + 1;
		}
		spriteStreamPublishAt(pStream, s_pView, pBase, pSlot);
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
