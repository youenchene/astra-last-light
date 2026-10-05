#include "render_hero.h"
#include "render_internal.h"
#include "render_stream.h"
#include "art.h"

#define HERO_HEIGHT 24
#define HERO_FRAMES 2
/* Two 16px columns, each an attached pair: channels 0/1 and 2/3. */
#define HERO_PARTS 4

static const tView *s_pView;
static ULONG *s_pBlank;
static tSpriteStream s_pStreams[HERO_PARTS];
static ULONG s_pPixels[HERO_FRAMES][HERO_PARTS][HERO_HEIGHT];

UBYTE renderHeroCreate(const tView *pView, ULONG *pBlank) {
	if(s_pView || !pView || !pBlank) return 0;
	tBitMap *pStrip = artHero32Create();
	if(!pStrip) return 0;
	UBYTE ok = stripValid(pStrip, 32, HERO_FRAMES * HERO_HEIGHT);
	if(ok) stripSplit(pStrip, 32, HERO_FRAMES, HERO_HEIGHT, &s_pPixels[0][0][0]);
	bitmapDestroy(pStrip);
	if(!ok) return 0;
	s_pView = pView;
	s_pBlank = pBlank;
	for(UBYTE part = 0; part < HERO_PARTS; ++part)
		if(!spriteStreamCreate(&s_pStreams[part], pView, part, HERO_HEIGHT, 1)) {
			renderHeroDestroy();
			return 0;
		}
	return 1;
}

void renderHeroDraw(const tGameState *pState) {
	if(!s_pView) return;
	UBYTE show = pState->phase == PLAY || pState->phase == BOSS;
	UBYTE enabled = show && (!pState->invulnerable || !(pState->invulnerable & 4));
	UBYTE frame = (pState->frame >> 3) & 1;
	UBYTE buffer = spriteStreamBuffer(&s_pStreams[0], s_pView);
	UWORD x = s_pView->ubPosX - 1 + pState->x, start = s_pView->ubPosY + pState->y;
	for(UBYTE part = 0; part < HERO_PARTS; ++part) {
		tSpriteWriter writer;
		spriteWriterBegin(&writer, &s_pStreams[part], buffer);
		if(enabled) spriteWriterPut(&writer, x + ((part >> 1) << 4), start,
			(part & 1) << 7, s_pPixels[frame][part]);
		spriteWriterPublish(&writer, s_pView);
	}
}

void renderHeroDestroy(void) {
	for(UBYTE part = 0; part < HERO_PARTS; ++part)
		spriteStreamDestroy(&s_pStreams[part], s_pView, s_pBlank);
	s_pView = 0;
	s_pBlank = 0;
}
