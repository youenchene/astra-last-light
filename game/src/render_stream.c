#include "render_stream.h"
#include <ace/managers/memory.h>

static void pointChannel(tCopBfr *pBuffer, UBYTE ubChannel, ULONG ulAddress) {
	tCopCmd *pCommands = &pBuffer->pList[ASTRA_COP_SPRITES + ubChannel * 2];
	copSetMoveVal(&pCommands[0].sMove, ulAddress >> 16);
	copSetMoveVal(&pCommands[1].sMove, ulAddress & 0xffff);
}

UBYTE spriteStreamCreate(tSpriteStream *pStream, const tView *pView,
	UBYTE ubChannel, UBYTE ubHeight, UBYTE ubSlots) {
	if(!pStream || !pView || ubChannel > 7 || !ubHeight || !ubSlots || ubSlots > 16) return 0;
	pStream->ubChannel = ubChannel;
	pStream->ubHeight = ubHeight;
	pStream->ubSlots = ubSlots;
	pStream->pCopperA = pView->pCopList->pBackBfr;
	pStream->uwBytes = ((ubHeight + 1) * ubSlots + 1) * 4;
	for(UBYTE buffer = 0; buffer < 2; ++buffer) {
		pStream->pRows[buffer] = memAllocChipClear(pStream->uwBytes);
		if(!pStream->pRows[buffer]) return 0;
		for(UBYTE slot = 0; slot < 16; ++slot) pStream->pLoaded[buffer][slot] = 0;
	}
	return 1;
}

void spriteStreamDestroy(tSpriteStream *pStream, const tView *pView, ULONG *pBlank) {
	if(!pStream) return;
	if(pView && pBlank && (pStream->pRows[0] || pStream->pRows[1])) {
		pointChannel(pView->pCopList->pBackBfr, pStream->ubChannel, (ULONG)pBlank);
		pointChannel(pView->pCopList->pFrontBfr, pStream->ubChannel, (ULONG)pBlank);
	}
	for(UBYTE buffer = 0; buffer < 2; ++buffer) {
		if(pStream->pRows[buffer]) memFree(pStream->pRows[buffer], pStream->uwBytes);
		pStream->pRows[buffer] = 0;
	}
}
