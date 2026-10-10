#include "presentation_rows.h"
#include "../art/presentation-rows.h"

#ifdef ASTRA_PRESENTATION_TIMING
#include <ace/managers/timer.h>
#include <ace/utils/custom.h>
#include <agk/debug.h>
/* Diagnostic build only. Measure the decoder including music interrupts;
 * serial reporting happens afterwards and is not counted as decoder work. */
static struct { UWORD calls, peak; ULONG total; } s_timing[2];
static ULONG s_startVblank;
static UWORD s_startLine;
static UWORD sampleLine(ULONG *vblank) {
	ULONG before, after;
	UWORD line;
	do {
		before = timerGet(); line = getRayPos().bfPosY; after = timerGet();
	} while(before != after);
	*vblank = after;
	return line;
}
static void timingBegin(UBYTE kind, UWORD row) {
	if(!row) { s_timing[kind].calls = s_timing[kind].peak = 0; s_timing[kind].total = 0; }
	s_startLine = sampleLine(&s_startVblank);
}
static void timingEnd(UBYTE kind, UBYTE id, UWORD row, UWORD last) {
	ULONG vblank;
	UWORD line = sampleLine(&vblank), blanks = vblank - s_startVblank;
	if(blanks * 313 + line < s_startLine) ++blanks;
	UWORD elapsed = blanks * 313 + line - s_startLine;
	++s_timing[kind].calls; s_timing[kind].total += elapsed;
	if(elapsed > s_timing[kind].peak) s_timing[kind].peak = elapsed;
	if(row != last) return;
	agkState("row_cost", kind); agkState("id", id);
	agkState("calls", s_timing[kind].calls); agkState("lines", s_timing[kind].total);
	agkState("peak_lines", s_timing[kind].peak); agkEnd();
}
#else
#define timingBegin(kind, row) ((void)0)
#define timingEnd(kind, id, row, last) ((void)0)
#endif

/* Generated runs are nonzero and sum to span for each of four planes. Bound
 * both decoding and output even if an invalid generated stream is supplied. */
static void rowWrite(unsigned char *const planes[4], unsigned short stride,
	unsigned short y, unsigned char x, unsigned char span, unsigned short offset) {
	const unsigned char *source = s_presentationBytes + offset + 1;
	unsigned short position = y * stride + x;
	for(unsigned char plane = 0; plane < 4; ++plane) {
		unsigned char *dest = planes[plane] + position;
		unsigned char remaining = span;
		for(unsigned char op = 0; remaining && op < span; ++op) {
			unsigned char token = *source++, count = token & 127;
			if(!count || count > remaining) return;
			remaining -= count;
			if(token & 128) {
				while(count--) *dest++ = *source++;
			}
			else {
				unsigned char value = *source++;
				while(count--) *dest++ = value;
			}
		}
	}
}

unsigned short presentationCardStep(unsigned char *const planes[4],
	unsigned short stride, unsigned char id, unsigned short row) {
	if(id >= 13 || row >= 136) return row;
	timingBegin(0, row);
	unsigned short end = row + PRESENTATION_BYTE_BUDGET / 80;
	if(end > 136) end = 136;
	unsigned char operations = PRESENTATION_OP_BUDGET;
	while(row < end) {
		unsigned char cost = s_presentationBytes[s_cardRows[id][row]];
		if(cost > operations) break;
		operations -= cost;
		rowWrite(planes, stride, 56 + row, 19, 20, s_cardRows[id][row]);
		++row;
	}
	timingEnd(0, id, row, 136);
	return row;
}

unsigned short presentationHudStep(unsigned char *const planes[4],
	unsigned short stride, unsigned char variant, unsigned short row) {
	if(variant >= 8 || row >= 40) return row;
	timingBegin(1, row);
	unsigned short end = row + PRESENTATION_BYTE_BUDGET / 160;
	if(end > 40) end = 40;
	unsigned char operations = PRESENTATION_OP_BUDGET;
	while(row < end) {
		unsigned char cost = s_presentationBytes[s_hudRows[variant][row]];
		if(cost > operations) break;
		operations -= cost;
		rowWrite(planes, stride, row < 29 ? row : row + 216,
			0, 40, s_hudRows[variant][row]);
		++row;
	}
	timingEnd(1, variant, row, 40);
	return row;
}
