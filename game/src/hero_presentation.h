#ifndef ASTRA_HERO_PRESENTATION_H
#define ASTRA_HERO_PRESENTATION_H
#include "logic.h"

/* Visibility is independent of hostile admission and both-buffer readiness.
 * Blocking stories project an overlapping ship to the left edge of the window;
 * logical coordinates stay frozen. Opening flight already stays in this lane. */
static inline uint8_t heroPresentationVisible(const tGameState *s) {
	uint8_t combat = s->phase == PLAY || s->phase == BOSS;
	uint8_t story = s->phase == SECTOR_INTRO || s->phase == BOSS_INTRO ||
		s->phase == BOSS_DYING || s->phase == CLEAR;
	return story || (combat && (s->manualPause || s->presentationBusy ||
		!s->heroBlink || !s->invulnerable || !(s->invulnerable & 4)));
}

static inline int16_t heroPresentationX(const tGameState *s) {
	uint8_t window = s->phase == SECTOR_INTRO || s->phase == BOSS_INTRO ||
		s->phase == CLEAR;
	return window && s->x + PLAYER_W > 152 && s->x < 312 && s->y < 192
		? 152 - PLAYER_W : s->x;
}
#endif
