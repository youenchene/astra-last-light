#ifndef ASTRA_RENDER_BULLETS_H
#define ASTRA_RENDER_BULLETS_H

#include <ace/utils/extview.h>
#include "logic.h"

/* Independent hostile streams: 6/7 in PLAY, 4..7 in BOSS. Logic's mask
 * retains ownership through HERO_DYING, with empty streams during the pause.
 * Each channel owns two chip buffers, selected by back-copper identity.
 * Pixels are cached per slot; each frame rewrites controls in Y order.
 * Channels 4/5 map to existing hero inks 9..11, 6/7 retain inks 13..15.
 * No palette writes. Borrows the view and blank sprite word. */
UBYTE renderBulletsCreate(const tView *pView, ULONG *pBlank);
/* Draws every active hostile on its logic-assigned channel. A bullet that
 * would break the hardware stream (never expected) gets visible=0. */
void renderBulletsDraw(tGameState *pState);
/* Idempotent/partial-create-safe; restores blank pointers in both copper
 * buffers before freeing the streams. Stop sprite DMA first. */
void renderBulletsDestroy(void);

#endif
