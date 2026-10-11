#include "render_status.h"
#include "scene_font.h"
#include <ace/managers/memory.h>
#include <ace/utils/custom.h>

#define STRIP_BYTES 96
#define STRIP_COUNT 8
static UBYTE *s_pixels;
static tVPort *s_port;
static UBYTE s_tick;
static tUiStatus s_previous = (tUiStatus)255;
static UWORD s_y;
/* Fixed 320px OCS display: normal DDF $38..$d0, centered 96px $70..$98.
 * Compact register/value tables avoid duplicating setup code for every MOVE. */
static const UWORD s_registers[16] = {
	0,0x100,0x108,0xe0,0xe2,0x180,0x182,0x92,0x94,0,0x100,0x108,0x180,0x182,0x92,0x94
};
static const UWORD s_values[16] = {
	0,0x1200,0,0,0,0x011,0xfff,0x70,0x98,0,0x4200,120,0,0,0x38,0xd0
};
static const char *const s_labels[2][4] = {
	{"CHARGEMENT", "RELACHEZ FEU", "PATIENTEZ", "FEU POUR CONTINUER"},
	{"LOADING", "RELEASE FIRE", "PLEASE WAIT", "FIRE TO CONTINUE"}
};

/* Runs once before takeover. Avoid -O3 unrolling this font rasterizer: its code
 * competes with DMA allocations on the 512K+512K baseline, not frame time. */
UBYTE __attribute__((optimize("Os"))) renderStatusCreate(tVPort *port) {
	s_port = port;
	s_y = port->pView->ubPosY + port->uwOffsY;
	s_pixels = memAllocChipClear(STRIP_BYTES * STRIP_COUNT);
	if(!s_pixels) return 0;
	for(UBYTE language = 0; language < 2; ++language) {
		for(UBYTE label = 0; label < 4; ++label) {
			const char *text = s_labels[language][label];
			UBYTE length = 0;
			while(text[length]) ++length;
			UWORD x = (96 - length * 5) >> 1;
			UBYTE *pixels = s_pixels + (language * 4 + label) * STRIP_BYTES;
			for(UBYTE ch = 0; ch < length; ++ch, x += 5) {
				if(text[ch] == ' ') continue;
				for(UBYTE row = 0; row < 6; ++row)
					for(UBYTE col = 0; col < 4; ++col)
						if(s_sceneFont[text[ch] - 'A'][row] & (8 >> col))
							pixels[(row + 1) * 12 + ((x + col) >> 3)] |= 0x80 >> ((x + col) & 7);
			}
		}
	}
	for(UBYTE buffer = 0; buffer < 2; ++buffer) {
		tCopBfr *copper = buffer ? port->pView->pCopList->pFrontBfr : port->pView->pCopList->pBackBfr;
		tCopCmd *cmd = &copper->pList[ASTRA_COP_STATUS];
		for(UBYTE i = 1; i < ASTRA_COP_STATUS_COUNT; ++i) {
			if(i != 9) copSetMove(&cmd[i].sMove,
				(volatile UBYTE *)g_pCustom + s_registers[i], s_values[i]);
		}
		copSetWait(&cmd[0].sWait, 0xdf, s_y + 255);
		copSetWait(&cmd[9].sWait, 0xdf, s_y + 255);
	}
	return 1;
}

void renderStatusUpdate(tUiStatus status, tLanguage language) {
	++s_tick;
	/* No recurring CPU work in ordinary gameplay or an interactive menu. */
	if(status == UI_IDLE && s_previous == UI_IDLE) return;
	s_previous = status;
	for(UBYTE buffer = 0; buffer < 2; ++buffer) {
		tCopBfr *copper = buffer ? s_port->pView->pCopList->pFrontBfr : s_port->pView->pCopList->pBackBfr;
		tCopCmd *cmd = &copper->pList[ASTRA_COP_STATUS];
		/* Decor's unconditional line-255 guard has already crossed PAL wrap.
		 * Immutable 96px one-plane text replaces the last eight display rows;
		 * idle delays all overrides until AFTER the last visible fetch. */
		copSetWait(&cmd[0].sWait, 0xdf, s_y + (status == UI_IDLE ? 255 : 247));
		if(status != UI_IDLE) {
			ULONG pixels = (ULONG)(s_pixels + (language * 4 + status - 1) * STRIP_BYTES);
			copSetMoveVal(&cmd[3].sMove, pixels >> 16);
			copSetMoveVal(&cmd[4].sMove, pixels & 0xffff);
		}
		copSetMoveVal(&cmd[6].sMove, status == UI_LOADING && (s_tick & 16) ? 0xaaa : 0xfff);
		copSetMoveVal(&cmd[12].sMove, copper->pList[ASTRA_COP_PALETTE].sMove.bfValue);
		copSetMoveVal(&cmd[13].sMove, copper->pList[ASTRA_COP_PALETTE + 1].sMove.bfValue);
	}
}

void renderStatusDestroy(void) {
	if(s_pixels) memFree(s_pixels, STRIP_BYTES * STRIP_COUNT);
	s_pixels = 0;
	s_previous = (tUiStatus)255;
}
