#ifndef ASTRA_RENDER_INTERNAL_H
#define ASTRA_RENDER_INTERNAL_H

#include <ace/utils/bitmap.h>

static inline UBYTE stripValid(const tBitMap *pStrip, UWORD width, UWORD rows) {
	if(!pStrip || pStrip->Depth != 4 || pStrip->Rows != rows ||
		!(pStrip->Flags & BMF_INTERLEAVED) || pStrip->BytesPerRow != width / 2 ||
		!pStrip->Planes[0]) return 0;
	for(UBYTE plane = 1; plane < 4; ++plane)
		if(pStrip->Planes[plane] != pStrip->Planes[0] + plane * (width / 8)) return 0;
	return 1;
}

/* Split a validated 4bpp interleaved strip into attached-sprite rows:
 * pOut[frame][part][row], part = column * 2 + (0: planes 0/1, 1: planes 2/3),
 * each ULONG = (low plane word << 16) | high plane word, as sprite DMA reads. */
static inline __attribute__((always_inline)) void stripSplit(const tBitMap *pStrip, UWORD width, UBYTE frames,
	UBYTE height, ULONG *pOut) {
	UBYTE columns = width / 16;
	UWORD bytesPerPlane = width / 8;
	for(UBYTE frame = 0; frame < frames; ++frame)
		for(UBYTE part = 0; part < columns * 2; ++part)
			for(UBYTE row = 0; row < height; ++row) {
				const UBYTE *pRow = pStrip->Planes[0] +
					(ULONG)(frame * height + row) * pStrip->BytesPerRow + (part >> 1) * 2;
				const UWORD *pLow = (const UWORD *)(pRow + (part & 1) * 2 * bytesPerPlane);
				const UWORD *pHigh = (const UWORD *)(pRow + ((part & 1) * 2 + 1) * bytesPerPlane);
				*pOut++ = ((ULONG)*pLow << 16) | *pHigh;
			}
}

#endif
