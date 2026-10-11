#ifndef ASTRA_LANGUAGE_SELECT_H
#define ASTRA_LANGUAGE_SELECT_H
#include <stdint.h>

typedef enum { LANGUAGE_FR, LANGUAGE_EN } tLanguage;

/* Session preference, intentionally outside tGameState: logicInit, death,
 * ESC, WIN and new games cannot reset it. Cold launch defaults to French.
 * No disk persistence. Runtime text and generated rows use languageGet(),
 * not a gameplay phase/sector; selection completes before world composition. */
tLanguage languageGet(void);

typedef struct {
	tLanguage selected, drawn[2], visible;
	uint16_t row[2];
	uint8_t borderRow[2], published, armed, previousDirs, confirmed;
} tLanguageSelect;

/* Startup-only, borrowing the two existing 320x256x4 bitmaps. Begin never
 * resets the preference. Direction bits: left=1, right=2 (left wins ties).
 * fire combines joystick button, Space and Return. Input returns 1 only
 * after a visible confirmation AND release; no input queues during drawing. */
void languageSelectBegin(tLanguageSelect *choice);
uint8_t languageSelectInput(tLanguageSelect *choice, uint8_t dirs, uint8_t fire);

/* Write only the bound unpublished target (index 0/1, stable bitmap identity).
 * planes are byte pointers; stride is BytesPerRow (160 when interleaved).
 * Initial work: two scanlines/tick; selection repair: eight border rows/tick.
 * No allocation, blitter, OS or palette access. Caller waits for old blits.
 * Never publish an incomplete target. Presented must follow actual vblank,
 * not composition completion; readiness requires both targets and publication. */
void languageSelectStep(tLanguageSelect *choice, uint8_t target,
	uint8_t *const planes[4], uint16_t stride);
uint8_t languageSelectTargetReady(const tLanguageSelect *choice, uint8_t target);
uint8_t languageSelectReady(const tLanguageSelect *choice);
void languageSelectPresented(tLanguageSelect *choice, uint8_t target);

/* Reference RGB24 converted by truncation to OCS RGB12, not AGA colors. */
extern const uint16_t g_languagePalette[4];
#endif
