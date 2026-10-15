#include "render_hero.h"
#include "render_internal.h"
#include "render_stream.h"
#include "render_scenes.h"
#include "art.h"
#include "hero_presentation.h"

#define HERO_HEIGHT 24
#define HERO_FRAMES 2
/* Two 16px columns, each an attached pair: channels 0/1 and 2/3. */
#define HERO_PARTS 4

static const tView *s_pView;
static ULONG *s_pBlank;
static tSpriteStream s_pStreams[HERO_PARTS];

/* Cold conversion must not consume RAM with unrolled setup loops. */
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC push_options
#pragma GCC optimize ("Os")
#endif
UBYTE renderHeroCreate(const tView *pView, ULONG *pBlank) {
	ULONG pixels[HERO_FRAMES][HERO_PARTS][HERO_HEIGHT];
	if(s_pView || !pView || !pBlank) return 0;
	tBitMap *pStrip = artHero32Create();
	if(!pStrip) return 0;
	UBYTE ok = stripValid(pStrip, 32, HERO_FRAMES * HERO_HEIGHT);
	if(ok) stripSplit(pStrip, 32, HERO_FRAMES, HERO_HEIGHT, &pixels[0][0][0]);
	bitmapDestroy(pStrip);
	if(!ok) return 0;
	s_pView = pView;
	s_pBlank = pBlank;
	for(UBYTE part = 0; part < HERO_PARTS; ++part) {
		if(!spriteStreamCreate(&s_pStreams[part], pView, part, HERO_HEIGHT, HERO_FRAMES)) {
			renderHeroDestroy();
			return 0;
		}
		/* Both images reside in each physical back stream. Runtime animation
		 * selects a slot; it never recopies the 384-byte attached ship image. */
		for(UBYTE buffer = 0; buffer < 2; ++buffer)
			for(UBYTE frame = 0; frame < HERO_FRAMES; ++frame) {
				ULONG *dest = s_pStreams[part].pRows[buffer] + frame * (HERO_HEIGHT + 1) + 1;
				for(UBYTE row = 0; row < HERO_HEIGHT; ++row) *dest++ = pixels[frame][part][row];
			}
	}
	return 1;
}
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC pop_options
#endif

void renderHeroDraw(const tGameState *pState) {
	if(!s_pView) return;
	UBYTE enabled = heroPresentationVisible(pState);
	UBYTE frame = (pState->frame >> 3) & 1;
	UWORD x = s_pView->ubPosX - 1 + heroPresentationX(pState), start = s_pView->ubPosY + pState->y;
	for(UBYTE part = 0; part < HERO_PARTS; ++part) {
		tSpriteStream *stream = &s_pStreams[part];
		ULONG *base = spriteStreamRows(stream, s_pView) + frame * (HERO_HEIGHT + 1);
		ULONG *end = base;
		if(enabled) {
			end = spriteSlotPlace(base, x + ((part >> 1) << 4), start, HERO_HEIGHT);
			if(part & 1) ((UWORD *)base)[1] |= 0x80;
		}
		spriteStreamPublishAt(stream, s_pView, base, end);
	}
}

void renderHeroDestroy(void) {
	for(UBYTE part = 0; part < HERO_PARTS; ++part)
		spriteStreamDestroy(&s_pStreams[part], s_pView, s_pBlank);
	s_pView = 0;
	s_pBlank = 0;
}
