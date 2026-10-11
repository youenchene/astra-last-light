#ifndef ASTRA_UI_STATUS_H
#define ASTRA_UI_STATUS_H

#include "language_select.h"
#include "logic.h"

typedef enum { UI_IDLE, UI_LOADING, UI_RELEASE, UI_WAIT, UI_CONTINUE } tUiStatus;

/* Same readiness/arming gates as input; preparation always wins over prompts. */
static inline tUiStatus uiStatus(const tGameState *state,
	const tLanguageSelect *choice, uint8_t language, uint8_t started, uint8_t confirming) {
	if(language) {
		if(!languageSelectReady(choice)) return UI_LOADING;
		return choice->confirmed || !choice->armed ? UI_RELEASE : UI_IDLE;
	}
	if(!started) return UI_IDLE;
	if(state->presentationBusy || confirming) return UI_LOADING;
	if(state->phase == TITLE) return state->titleInputBlocked ? UI_RELEASE : UI_IDLE;
	if(state->manualPause) return UI_IDLE;
	if(state->phase == WIN || state->phase == CLEAR || state->phase == GAMEOVER) {
		if(state->phaseFrame < SCENE_SKIP_FRAMES) return UI_WAIT;
		return state->sceneArmed ? UI_CONTINUE : UI_RELEASE;
	}
	return UI_IDLE;
}
#endif
