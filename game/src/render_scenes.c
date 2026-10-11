#include "render_scenes.h"
#include "render_world.h"
#include "render_internal.h"
#include "art.h"
#include "presentation_rows.h"
#include <ace/managers/blit.h>

/* Text/style/panel mapping is authored once in art/localization.json. */
static tBitMap *s_screen;
static tBitMap *s_buffers[2];
static UBYTE s_id, s_active, s_buffer;
static UWORD s_epoch;
typedef struct {
	UBYTE ready, stage, line;
	UWORD row, cursor;
} tSceneBuffer;
static tSceneBuffer s_history[2];
#define HISTORY (s_history[s_buffer])
#define s_ready HISTORY.ready
#define s_stage HISTORY.stage
#define s_line HISTORY.line
#define s_row HISTORY.row
#define s_cursor HISTORY.cursor

void renderScenesBind(tBitMap *screen) {
	s_screen = screen; s_buffer = screen == s_buffers[1];
}

UBYTE renderScenesCreate(tBitMap *front, tBitMap *screen, tVPort *viewport) {
	if(!front || !screen || !viewport) return 0;
	s_screen = screen;
	s_buffers[0] = screen; s_buffers[1] = front;
	return 1;
}

void renderScenesBegin(UBYTE id, UWORD epoch) {
	s_ready = 0; s_active = id < 13;
	if(!s_active) return;
	s_id = id; s_epoch = epoch;
	s_stage = s_line = 0;
	s_row = s_cursor = 0;
	s_history[!s_buffer] = HISTORY;
	/* Keep the sector's global palette: exterior scenery must not recolor. */
}

void renderScenesStep(void) {
	if(!s_active) return;
	UBYTE panel = presentationScenePanel(s_id);
	if(s_ready) return;
	if(s_stage == 0) {
		blitWait();
		s_row = presentationCardStep(s_screen->Planes, s_screen->BytesPerRow, s_id, s_row);
		if(s_row == presentationCardHeight(s_id)) { s_row = 0; ++s_stage; }
	}
	else if(s_stage == 1) {
		blitWait();
		s_row = presentationMangaStep(s_screen->Planes, s_screen->BytesPerRow, panel, s_row);
		if(s_row == presentationMangaHeight(panel)) s_ready = 1;
	}
}

void renderScenesClose(void) {
	for(UBYTE i = 0; i < 2; ++i) { s_history[i].ready = 0; s_history[i].row = 0; }
}

void renderScenesCopyReady(void) {
	s_history[s_buffer] = s_history[!s_buffer];
}

void renderScenesEraseStep(void) {
	if(s_ready) return;
	/* Finishing the patch and submitting a large boss BOB in the same frame
	 * exceeds the PAL budget. The completed background stays unpublished;
	 * next frame's readiness lets renderFrame add HUD/BOBs/sprites and publish
	 * one complete image. This is a separate work step, not a timed idle. */
	if(s_row == SCENE_H) { s_ready = 1; return; }
	if(renderWorldRestoreCorridor(SCENE_X, SCENE_Y + s_row, SCENE_W, 8))
		s_row += 8;
}

UBYTE renderScenesReady(void) {
	return s_active && s_history[0].ready && s_history[1].ready;
}
UBYTE renderScenesTargetReady(void) { return s_active && s_ready; }
UWORD renderScenesReadyEpoch(void) { return s_epoch; }

void renderScenesDestroy(void) {
	blitWait();
	s_screen = 0;
	s_active = s_ready = 0;
}
