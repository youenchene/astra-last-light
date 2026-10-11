#ifndef ASTRA_PRESENTATION_H
#define ASTRA_PRESENTATION_H

/* Bounded writer for the 320px, four-plane interleaved back bitmap. Caller waits
 * for blits and starts each layer at row zero, then resumes its returned cursor
 * on the SAME physical bitmap: copy tokens borrow already-decoded layer bytes.
 * At most 320 output bytes / 64 commands per call; no allocation, staging,
 * font interpretation, runtime resizing or publication. */
#define PRESENTATION_BYTE_BUDGET 320
#define PRESENTATION_OP_BUDGET 64
unsigned short presentationCardHeight(unsigned char id);
unsigned char presentationScenePanel(unsigned char id);
unsigned short presentationMangaHeight(unsigned char panel);
unsigned short presentationCardStep(unsigned char *const planes[4],
	unsigned short stride, unsigned char id, unsigned short row);
unsigned short presentationHudStep(unsigned char *const planes[4],
	unsigned short stride, unsigned char variant, unsigned short row);
unsigned short presentationMangaStep(unsigned char *const planes[4],
	unsigned short stride, unsigned char panel, unsigned short row);

#endif
