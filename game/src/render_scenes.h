#ifndef ASTRA_RENDER_SCENES_H
#define ASTRA_RENDER_SCENES_H

#include <ace/utils/extview.h>
#include <ace/utils/bitmap.h>

/* Borrows both world screens and viewport; owns one 160x480x4 strip.
 * Create must run before OS ownership is released. Begin performs no drawing.
 * Each Step advances only the bound back bitmap: <=8 rows OR <=2 glyphs.
 * Ready requires both complete; animation catches up each bitmap on reuse. */
UBYTE renderScenesCreate(tBitMap *front, tBitMap *screen, tVPort *viewport);
void renderScenesBind(tBitMap *screen);
void renderScenesBegin(UBYTE id, UWORD epoch);
void renderScenesStep(void);
UBYTE renderScenesReady(void);
/* Valid only while Ready is true: epoch zero is a legitimate wrapped epoch. */
UWORD renderScenesReadyEpoch(void);
void renderScenesDestroy(void);

#endif
