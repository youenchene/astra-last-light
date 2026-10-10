#ifndef ASTRA_PRESENTATION_H
#define ASTRA_PRESENTATION_H

/* Pure bounded planar writer. Caller waits for blits and supplies the bound back
 * bitmap's planes/stride. At most 320 output bytes and 64 decode operations per call;
 * no allocations, staging bitmap, font interpretation, or publication. */
#define PRESENTATION_BYTE_BUDGET 320
#define PRESENTATION_OP_BUDGET 64
unsigned short presentationCardStep(unsigned char *const planes[4],
	unsigned short stride, unsigned char id, unsigned short row);
unsigned short presentationHudStep(unsigned char *const planes[4],
	unsigned short stride, unsigned char variant, unsigned short row);

#endif
