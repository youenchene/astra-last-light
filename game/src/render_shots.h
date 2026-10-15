#ifndef ASTRA_RENDER_SHOTS_H
#define ASTRA_RENDER_SHOTS_H
#include <ace/utils/bitmap.h>
#include "logic.h"

/* Fixed-geometry player blits with owned CHIP backgrounds, no frame allocation.
 * Borrows the coordinator's normal/lance image and mask strips until destroy. */
UBYTE renderShotsCreate(tBitMap *front, tBitMap *back, const tBitMap *normal,
	const tBitMap *normalMask, const tBitMap *lance, const tBitMap *lanceMask);
void renderShotsBind(tBitMap *back);
/* Restore before ACE BOBs, whose pixels were under this bitmap's old shots. */
void renderShotsRestore(void);
/* Save all backgrounds, then draw in shot-pool order after ACE bobEnd/wait. */
void renderShotsDraw(tGameState *state, UBYTE show);
void renderShotsDiscard(void);
void renderShotsDestroy(void);
#endif
