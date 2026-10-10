#include "render_scenes.h"
#include "render_world.h"
#include "render_internal.h"
#include "art.h"
#include "presentation_rows.h"
#include <ace/managers/blit.h>

typedef struct {
	const char *title, *caption, *reply;
	UBYTE panel, style;
} tScene;

/* IDs are the portable logic contract, not art-frame numbers. These are five
 * original local plates, reused with thirteen distinct narrative treatments. */
static const tScene s_scenes[13] = {
	{"ORBITAL GRAVEYARD", "THE WRECKS STILL CALL OUR NAMES", "KEEP THE LAST LIGHT ALIVE", 0, 0},
	{"SALVAGE CLAW", "A REACTOR WAKES AMONG THE DEAD", "THOSE JAWS WILL NOT TAKE US", 0, 1},
	{"WRECK FIELD FREED", "THE CLAW FALLS SILENT", "SET COURSE FOR THE VEIL", 0, 2},
	{"VEIL NEBULA", "SOMETHING MOVES IN THE CLOUDS", "FOLLOW THE SIGNAL THROUGH", 1, 0},
	{"THE MANTA WAKES", "THAT SHADOW IS ALIVE", "WATCH THE FINS AND HOLD FAST", 1, 1},
	{"VEIL PIERCED", "THE GREAT SHADOW BREAKS APART", "THE FOUNDRY LIES AHEAD", 1, 2},
	{"IMPERIAL FOUNDRY", "THEIR FURNACES NEVER SLEEP", "WE WILL END THIS WAR MACHINE", 2, 0},
	{"FURNACE CARRIER", "THE FACTORY SHIP TURNS TO FIRE", "STAY CLEAR OF ITS GUN DECKS", 2, 1},
	{"FURNACES SILENCED", "NO MORE SHIPS FROM THESE FIRES", "ONE LAST JUMP TO THE CITADEL", 2, 2},
	{"STELLAR CITADEL", "THE CROWN ECLIPSES OUR STAR", "THIS IS WHERE WE MAKE OUR STAND", 3, 0},
	{"REACTOR CROWN", "ITS HALO IS GATHERING LIGHT", "BREAK THE CROWN BEFORE THE DAWN", 3, 1},
	{"THE CROWN FALLS", "THE REACTOR GOES DARK", "LOOK BEYOND THE FALLING TOWERS", 3, 2},
	{"DAWN RESTORED", "THE LAST LIGHT BURNS AGAIN", "WE MADE IT HOME", 4, 3}
};
static tBitMap *s_screen, *s_manga;
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
	if(!screen || !viewport || s_manga) return 0;
	s_screen = screen;
	s_buffers[0] = screen; s_buffers[1] = front;
	s_manga = artCampaignMangaCreate();
	return stripValid(s_manga, 112, 320) && bitmapIsChip(s_manga);
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
	if(!s_active || !s_manga) return;
	const tScene *scene = &s_scenes[s_id];
	if(s_ready) return;
	if(s_stage == 0) {
		blitWait();
		s_row = presentationCardStep(s_screen->Planes, s_screen->BytesPerRow, s_id, s_row);
		if(s_row == SCENE_H) { s_row = 0; ++s_stage; }
	}
	else if(s_stage == 1) {
		blitCopy(s_manga, 0, scene->panel * 64 + s_row,
			s_screen, 176, 72 + s_row, 112, 8, MINTERM_COOKIE);
		if((s_row += 8) == 64) { blitWait(); s_ready = 1; }
	}
}

void renderScenesClose(void) {
	for(UBYTE i = 0; i < 2; ++i) { s_history[i].ready = 0; s_history[i].row = 0; }
}

void renderScenesEraseStep(void) {
	if(s_ready) return;
	renderWorldRestoreCorridor(SCENE_X, SCENE_Y + s_row, SCENE_W, 8);
	if((s_row += 8) == SCENE_H) s_ready = 1;
}

UBYTE renderScenesReady(void) {
	return s_active && s_history[0].ready && s_history[1].ready;
}
UBYTE renderScenesTargetReady(void) { return s_active && s_ready; }
UWORD renderScenesReadyEpoch(void) { return s_epoch; }

void renderScenesDestroy(void) {
	blitWait();
	if(s_manga) bitmapDestroy(s_manga);
	s_manga = s_screen = 0;
	s_active = s_ready = 0;
}
