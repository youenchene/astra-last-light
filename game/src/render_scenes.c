#include "render_scenes.h"
#include "render_world.h"
#include "render_internal.h"
#include "art.h"
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
static tVPort *s_viewport;
static UBYTE s_id, s_active, s_tick, s_buffer, s_targetScan;
static UWORD s_epoch;
typedef struct {
	UBYTE ready, stage, line, scan, tick;
	UWORD row, cursor;
} tSceneBuffer;
static tSceneBuffer s_history[2];
#define HISTORY (s_history[s_buffer])
#define s_ready HISTORY.ready
#define s_stage HISTORY.stage
#define s_line HISTORY.line
#define s_scan HISTORY.scan
#define s_row HISTORY.row
#define s_cursor HISTORY.cursor
static const UBYTE s_accents[4] = {5, 11, 7, 14};

void renderScenesBind(tBitMap *screen) {
	s_screen = screen; s_buffer = screen == s_buffers[1];
}

UBYTE renderScenesCreate(tBitMap *front, tBitMap *screen, tVPort *viewport) {
	if(!screen || !viewport || s_manga) return 0;
	s_screen = screen; s_viewport = viewport;
	s_buffers[0] = screen; s_buffers[1] = front;
	s_manga = artCampaignMangaCreate();
	return stripValid(s_manga, 160, 480) && bitmapIsChip(s_manga);
}

void renderScenesBegin(UBYTE id, UWORD epoch) {
	s_ready = 0; s_active = id < 13;
	if(!s_active) return;
	s_id = id; s_epoch = epoch;
	s_stage = s_line = s_tick = s_scan = 0;
	s_row = s_cursor = 0;
	HISTORY.tick = s_targetScan = 0;
	s_history[!s_buffer] = HISTORY;
	/* Restore the authored playfield inks, not the world's bright dust ink.
	 * Sprite registers 16..31 remain owned by the coordinator. */
	UWORD palette[32] = {0};
	artPaletteApply(palette);
	for(UBYTE i = 0; i < 16; ++i) s_viewport->pPalette[i] = palette[i];
}

static void sceneText(void) {
	const tScene *scene = &s_scenes[s_id];
	const char *text;
	UWORD x, y;
	UBYTE scale = 1, color = 6;
	if(s_line == 0) {
		text = scene->title; y = 22; scale = 2; color = s_accents[scene->style];
	}
	else if(s_line == 1) { text = scene->caption; y = 182; }
	else if(s_line == 2) { text = scene->reply; y = 200; color = 14; }
	else { text = "RELEASE THEN FIRE TO CONTINUE"; y = 235; color = 4; }
	UBYTE length = 0;
	while(text[length]) ++length;
	UWORD advance = 6 * scale;
	x = (320 - length * advance) >> 1;
	if(renderWorldTextStep(x, y, text, scale, color, &s_cursor)) {
		s_cursor = 0;
		if(++s_line == 4) { blitWait(); s_ready = 1; }
	}
}

void renderScenesStep(void) {
	if(!s_active || !s_manga) return;
	const tScene *scene = &s_scenes[s_id];
	UBYTE accent = s_accents[scene->style];
	if(s_ready) {
		if(!renderScenesReady()) return;
		if(!(++s_tick & 3) && ++s_targetScan == 94) s_targetScan = 0;
		/* Tiny animated scanner and helmet/salute glint. Restore from the cached
		 * opaque plate before highlighting; never accumulate XOR damage. */
		if(HISTORY.tick != (s_tick >> 2)) {
			blitRect(s_screen, 252, 64 + s_scan, 4, 2, 0);
			s_scan = s_targetScan;
			blitRect(s_screen, 252, 64 + s_scan, 4, 2, accent);
			UWORD sourceY = scene->panel * 96 + 8;
			blitCopy(s_manga, 16, sourceY, s_screen, 96, 72, 32, 8, MINTERM_COOKIE);
			if(s_tick & 16) blitRect(s_screen, 100 + ((s_tick >> 2) & 15), 75, 3, 1, 6);
			HISTORY.tick = s_tick >> 2;
		}
		return;
	}
	if(s_stage == 0) {
		blitRect(s_screen, 0, s_row, 320, 8, 0);
		if((s_row += 8) == 256) { s_row = 0; ++s_stage; }
	}
	else if(s_stage == 1) {
		/* Entry: fine cyan frame; arrival: red alert rails; defeat: bright
		 * open-looking frame; victory: broad dawn frame. All use bounded bands. */
		blitRect(s_screen, 72, 56 + s_row, 176, 8, accent);
		if((s_row += 8) == 112) { s_row = 0; ++s_stage; }
	}
	else if(s_stage == 2) {
		blitCopy(s_manga, 0, scene->panel * 96 + s_row,
			s_screen, 80, 64 + s_row, 160, 8, MINTERM_COOKIE);
		if((s_row += 8) == 96) { s_row = 0; ++s_stage; }
	}
	else if(s_stage == 3) {
		/* Distinct geometric frame grammar per beat, outside the opaque plate. */
		if(scene->style == 0) blitRect(s_screen, 76, s_row ? 165 : 58, 168, 1, 0);
		else if(scene->style == 1) {
			blitRect(s_screen, 64, 64 + s_row, 4, 4, accent);
			blitRect(s_screen, 252, 64 + s_row, 4, 4, accent);
		}
		else if(scene->style == 2) {
			blitRect(s_screen, 72, 72 + s_row, 8, 4, 0);
			blitRect(s_screen, 240, 72 + s_row, 8, 4, 0);
		}
		else blitRect(s_screen, 56, s_row ? 172 : 52, 208, 2, accent);
		s_row += 88;
		if(s_row == 176) ++s_stage;
	}
	else sceneText();
}

UBYTE renderScenesReady(void) {
	return s_active && s_history[0].ready && s_history[1].ready;
}
UWORD renderScenesReadyEpoch(void) { return s_epoch; }

void renderScenesDestroy(void) {
	blitWait();
	if(s_manga) bitmapDestroy(s_manga);
	s_manga = s_screen = 0; s_viewport = 0;
	s_active = s_ready = 0;
}
