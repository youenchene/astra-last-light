#ifndef ASTRA_RENDER_SCENES_H
#define ASTRA_RENDER_SCENES_H

#include <ace/utils/extview.h>
#include <ace/utils/bitmap.h>

#define SCENE_X 136
#define SCENE_Y 56
#define SCENE_W 176
#define SCENE_H 152

static inline UBYTE renderScenesOccludes(WORD x, WORD y, UWORD width, UWORD height) {
	return x < SCENE_X + SCENE_W && x + width > SCENE_X &&
		y < SCENE_Y + SCENE_H && y + height > SCENE_Y;
}

/* Borrows both world screens and viewport; no owned bitmap allocation.
 * Create must run before OS ownership is released. Begin performs no drawing.
 * Each Step advances only the bound back bitmap: <=8 rows OR <=2 glyphs.
 * Static window (136,56)-(312,208); exterior and palette belong to the world.
 * Ready requires both complete; TargetReady gates atomic publication. */
UBYTE renderScenesCreate(tBitMap *front, tBitMap *screen, tVPort *viewport);
void renderScenesBind(tBitMap *screen);
void renderScenesBegin(UBYTE id, UWORD epoch);
void renderScenesStep(void);
void renderScenesClose(void);
void renderScenesEraseStep(void);
UBYTE renderScenesReady(void);
UBYTE renderScenesTargetReady(void);
/* Valid only while Ready is true: epoch zero is a legitimate wrapped epoch. */
UWORD renderScenesReadyEpoch(void);
void renderScenesDestroy(void);

#endif
