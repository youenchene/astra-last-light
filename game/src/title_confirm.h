#ifndef ASTRA_TITLE_CONFIRM_H
#define ASTRA_TITLE_CONFIRM_H
#include "logic.h"

#define TITLE_CONFIRM_FRAMES 6
/* Main owns this input/publication bridge. No ninth bit in the byte event mask.
 * Only acknowledgements of complete, published TITLE frames advance it. */
typedef struct { uint8_t active, visible; } tTitleConfirm;

static inline uint8_t titleConfirmFilter(tTitleConfirm *confirm,
	const tGameState *state, tInput *input) {
	if(confirm->active) {
		input->dx = input->dy = 0;
		input->fire = confirm->visible == TITLE_CONFIRM_FRAMES;
		if(input->fire) confirm->active = 0;
		return 0;
	}
	if(state->phase != TITLE || state->titleInputBlocked ||
		!input->fire || state->fireWasDown) return 0;
	confirm->active = 1;
	confirm->visible = 0;
	input->fire = 0;
	return 1;
}

static inline void titleConfirmPresented(tTitleConfirm *confirm) {
	if(confirm->active && confirm->visible < TITLE_CONFIRM_FRAMES) ++confirm->visible;
}
#endif
