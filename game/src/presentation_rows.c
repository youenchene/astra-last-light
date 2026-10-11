#include "presentation_rows.h"
#include "language_select.h"
#include "../art/presentation-rows.h"

#ifdef ASTRA_PRESENTATION_TIMING
#include <ace/managers/timer.h>
#include <ace/utils/custom.h>
#include <agk/debug.h>
/* Diagnostic build only. Measure the decoder including music interrupts;
 * serial reporting happens afterwards and is not counted as decoder work. */
static struct { UWORD calls, peak; ULONG total; } s_timing[3];
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

/* Trusted, host-validated generated commands never cross a plane. Count is in
 * the low six bits: repeat, prior-framebuffer copy, literal, packed literal.
 * Zero escapes to a same-column previous-row copy; all references point only
 * into bytes already decoded for this layer on this bound physical bitmap. */
static void rowWrite(unsigned char *const planes[4], unsigned short stride,
	unsigned short y, unsigned char x, unsigned char span, unsigned short id,
	const unsigned char *literals) {
	unsigned short position = y * stride + x;
	for(unsigned char plane = 0; plane < 4; ++plane) {
		const unsigned char *source = s_presentationBytes + s_presentationPlanes[id][plane];
		unsigned char *dest = planes[plane] + position;
		unsigned char remaining = span;
		for(unsigned char op = 0; remaining && op < span; ++op) {
			unsigned char token = *source++, count = token ? token & 63 : *source++;
			if(!count || count > remaining) return;
			remaining -= count;
			if(!token) {
				while(count--) { *dest = *(dest - stride); ++dest; }
			}
			else if((token & 192) == 192) {
				while(count >= 2) {
					unsigned char packed = *source++;
					*dest++ = literals[packed >> 4];
					*dest++ = literals[packed & 15];
					count -= 2;
				}
				if(count) *dest++ = literals[*source++ >> 4];
			}
			else if(token & 128) {
				while(count--) *dest++ = *source++;
			}
			else if(token & 64) {
				unsigned short from = *source++ * stride;
				from += *source++;
				const unsigned char *copy = planes[0] + from;
				while(count--) *dest++ = *copy++;
			}
			else {
				unsigned char value = *source++;
				while(count--) *dest++ = value;
			}
		}
	}
}

static unsigned short layerStep(unsigned char *const planes[4], unsigned short stride,
	const tPresentationLayout *layout, const unsigned short *rows, unsigned short row) {
	unsigned short bytes = PRESENTATION_BYTE_BUDGET;
	unsigned short costBytes = layout->span * 4;
	unsigned char operations = PRESENTATION_OP_BUDGET;
	while(row < layout->height && bytes >= costBytes) {
		unsigned short offset = rows[layout->first + row];
		unsigned char cost = s_presentationCosts[offset];
		if(cost > operations) break;
		operations -= cost;
		bytes -= costBytes;
		unsigned short y = layout->y + row;
		if(row >= layout->split) y += layout->gap;
		rowWrite(planes, stride, y, layout->x, layout->span, offset, s_presentationLiterals[layout->literals]);
		++row;
	}
	return row;
}

unsigned short presentationCardHeight(unsigned char id) {
	return id < 13 ? s_cardLayouts[id].height : 0;
}

unsigned char presentationScenePanel(unsigned char id) {
	return id < 13 ? s_scenePanels[id] : 255;
}

unsigned short presentationMangaHeight(unsigned char panel) {
	return panel < 5 ? s_mangaLayouts[panel].height : 0;
}

unsigned short presentationCardStep(unsigned char *const planes[4],
	unsigned short stride, unsigned char id, unsigned short row) {
	if(id >= 13 || row >= s_cardLayouts[id].height) return row;
	id += languageGet() * 13;
	timingBegin(0, row);
	row = layerStep(planes, stride, &s_cardLayouts[id], s_cardRows, row);
	timingEnd(0, id, row, s_cardLayouts[id].height);
	return row;
}

unsigned short presentationHudStep(unsigned char *const planes[4],
	unsigned short stride, unsigned char variant, unsigned short row) {
	if(variant >= 8 || row >= 40) return row;
	variant += languageGet() * 8;
	timingBegin(1, row);
	unsigned short end = row + PRESENTATION_BYTE_BUDGET / 160;
	if(end > 40) end = 40;
	unsigned char operations = PRESENTATION_OP_BUDGET;
	while(row < end) {
		unsigned short offset = s_hudRows[variant * 40 + row];
		unsigned char cost = s_presentationCosts[offset];
		if(cost > operations) break;
		operations -= cost;
		rowWrite(planes, stride, row < 29 ? row : row + 216,
			0, 40, offset, s_presentationLiterals[0]);
		++row;
	}
	timingEnd(1, variant, row, 40);
	return row;
}

unsigned short presentationMangaStep(unsigned char *const planes[4],
	unsigned short stride, unsigned char panel, unsigned short row) {
	if(panel >= 5 || row >= s_mangaLayouts[panel].height) return row;
	timingBegin(2, row);
	row = layerStep(planes, stride, &s_mangaLayouts[panel], s_mangaRows, row);
	timingEnd(2, panel, row, s_mangaLayouts[panel].height);
	return row;
}
