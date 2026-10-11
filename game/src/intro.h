#ifndef ASTRA_INTRO_H
#define ASTRA_INTRO_H

#include <ace/managers/viewport/simplebuffer.h>
#include <ace/utils/extview.h>

/* Borrow a 320x256, 4bpp buffer and OCS viewport (game uses interleaved planes).
 * Call once after soundCreate(), while the OS is available. Draws ACE,
 * allocates its original PCM and precomputes a 10,240-byte chip Micrix cache.
 * Cache allocation failure is logged and falls back to the original slow draw.
 * Caller owns display, synchronization and the shared audio player. */
void introCreate(tSimpleBufferManager *pBuffer, tVPort *pVPort);

/* Once per PAL frame: 1 = intro owns frame, 0 = complete (latched).
 * Skips require release then press in EACH stage. Unskipped: 250 calls.
 * Sync pVPort->pPalette into raw copper after create and every active tick.
 * On 0, restore game palette and redraw the game; no buffers are freed. */
UBYTE introProcess(UBYTE ubFire);

/* Idempotent: wait for blits, free owned Micrix cache and ACE PCM,
 * and forget borrowed pointers.
 * Call soundDestroy() FIRST so sample DMA is stopped before freeing memory. */
void introDestroy(void);

#endif
