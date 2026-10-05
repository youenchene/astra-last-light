#ifndef ASTRA_RENDER_WORLD_H
#define ASTRA_RENDER_WORLD_H

#include <ace/utils/extview.h>
#include <ace/utils/bitmap.h>
#include "logic.h"

/* Borrows viewport/screen; owns world bitmaps and dirty caches, including a
 * 1344-byte chip label atlas rasterized on the CPU before hardware takeover. */
UBYTE renderWorldCreate(tVPort *pVPort, tBitMap *pFront, tBitMap *pScreen);
void renderWorldBind(tBitMap *pScreen);
/* Capture base palette color 4 before scene-specific viewport changes. */
void renderWorldSetStarColor(UWORD color);
/* Dirty HUD history is independent for each pixel buffer. */
void renderWorldHud(const tGameState *pState);
/* Publish band DMA into the back copper only; disabled during composition,
 * title, game over and presentations. Restores the bound physical bitmap. */
void renderWorldCopper(const tGameState *pState, UBYTE ready);
/* After BOB restore, before BOB draw: scroll state and staggered star updates.
 * Catch up this bitmap's stars from its last use; decor is direct DMA.
 * BOSS/death freeze both stars and decor. Star steps are batched by two pixels
 * at twice their former period, preserving all four average velocities. */
void renderWorldAnimate(const tGameState *pState);
/* Begin initializes both targets. Step advances only the bound back bitmap,
 * at most eight rows / two glyphs. Ready requires both complete.
 * Death/combat phases share a background; scene overlays invalidate it. */
void renderWorldInvalidate(UBYTE resetScroll);
UBYTE renderWorldMatches(const tGameState *pState);
void renderWorldBegin(const tGameState *pState);
void renderWorldStep(void);
UBYTE renderWorldReady(void);
/* Shared cached font: at most two glyphs per call, including spaces. */
UBYTE renderWorldTextStep(UWORD x, UWORD y, const char *text,
	UBYTE scale, UBYTE color, UWORD *cursor);
/* Partial-create-safe; caller has waited for the blitter. */
void renderWorldDestroy(void);

#endif
