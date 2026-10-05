#ifndef ASTRA_RENDER_STREAM_H
#define ASTRA_RENDER_STREAM_H

#include <ace/utils/extview.h>
#include "render.h"

/* One hardware sprite channel's DMA stream, double-buffered per copper
 * buffer: [control row, height pixel rows] per slot, then a zero control
 * row. Slots are written in ascending Y; each must start at least one line
 * after the previous one stops (the VSTOP line fetches the next control).
 * Replaces ACE's generic multiplexer, whose per-frame bookkeeping cost
 * 20+ scanlines per logical sprite on the A500. Hot paths are inline and
 * multiply-free: the 68000 runs only ~100 instructions per scanline. */
typedef struct {
	ULONG *pRows[2];
	tCopBfr *pCopperA;
	UWORD uwBytes;
	UBYTE ubChannel, ubHeight, ubSlots;
	/* Per buffer and slot: which pixel source the slot holds (0 = none). */
	const ULONG *pLoaded[2][16];
} tSpriteStream;

/* Cursor over one buffer of one stream for this frame. */
typedef struct {
	tSpriteStream *pStream;
	ULONG *pBase, *pSlot;
	const ULONG **pLoaded;
	UBYTE ubCount;
} tSpriteWriter;

/* Allocates both chip buffers, cleared (an empty stream). Returns 0 on failure. */
UBYTE spriteStreamCreate(tSpriteStream *pStream, const tView *pView,
	UBYTE ubChannel, UBYTE ubHeight, UBYTE ubSlots);
/* Points the channel at pBlank in both copper buffers, then frees. Idempotent. */
void spriteStreamDestroy(tSpriteStream *pStream, const tView *pView, ULONG *pBlank);

/* Buffer to write this frame: the one the back copper list will display. */
static inline UBYTE spriteStreamBuffer(const tSpriteStream *pStream, const tView *pView) {
	return pView->pCopList->pBackBfr != pStream->pCopperA;
}

static inline void spriteWriterBegin(tSpriteWriter *pWriter, tSpriteStream *pStream, UBYTE ubBuffer) {
	pWriter->pStream = pStream;
	pWriter->pBase = pWriter->pSlot = pStream->pRows[ubBuffer];
	pWriter->pLoaded = pStream->pLoaded[ubBuffer];
	pWriter->ubCount = 0;
}

/* Hardware coordinates: uwX = view X - 1 + x, uwStart = view Y + y. */
static inline void spriteWriterPut(tSpriteWriter *pWriter, UWORD uwX, UWORD uwStart,
	UWORD uwAttach, const ULONG *pPixels) {
	UBYTE ubHeight = pWriter->pStream->ubHeight;
	UWORD uwStop = uwStart + ubHeight;
	UWORD *pControl = (UWORD *)pWriter->pSlot;
	pControl[0] = (UWORD)(uwStart << 8) | ((uwX >> 1) & 255);
	pControl[1] = (UWORD)(uwStop << 8) | uwAttach | ((uwStart >> 6) & 4) |
		((uwStop >> 7) & 2) | (uwX & 1);
	if(*pWriter->pLoaded != pPixels) {
		*pWriter->pLoaded = pPixels;
		ULONG *pDest = pWriter->pSlot + 1;
		for(UBYTE row = ubHeight; row; --row) *pDest++ = *pPixels++;
	}
	pWriter->pSlot += ubHeight + 1;
	++pWriter->pLoaded;
	++pWriter->ubCount;
}

/* Zero control row after the last slot (pixels below it stay cached), then
 * point the back copper list at this buffer. */
static inline void spriteWriterPublish(tSpriteWriter *pWriter, const tView *pView) {
	*pWriter->pSlot = 0;
	ULONG ulAddress = (ULONG)pWriter->pBase;
	tCopCmd *pCommands = &pView->pCopList->pBackBfr->pList[
		ASTRA_COP_SPRITES + (pWriter->pStream->ubChannel << 1)];
	copSetMoveVal(&pCommands[0].sMove, ulAddress >> 16);
	copSetMoveVal(&pCommands[1].sMove, ulAddress & 0xffff);
}

#endif
