#include "render_shots.h"
#include "render_internal.h"
#include "render_scenes.h"
#include "hud_bob_trace.h"
#include <ace/managers/blit.h>
#include <ace/managers/memory.h>
#include <ace/utils/custom.h>

#define LANCE_SLOTS 4
typedef struct {
	UBYTE *dest, *background, *pixels, *mask;
	UWORD size;
	UBYTE shift;
} tShotRecord;
typedef struct { tShotRecord records[SHOT_COUNT]; UBYTE count; } tShotHistory;
typedef struct {
	UBYTE normal[SHOT_COUNT][SHOT_H * 16];
	UBYTE lance[LANCE_SLOTS][CHARGED_SHOT_H * 16];
} tShotBacking;
static tShotBacking *s_background;
static tShotHistory s_history[2];
static tBitMap *s_buffers[2], *s_screen;
static UBYTE s_buffer;
static UBYTE *s_normalData, *s_normalMask, *s_lanceData[2], *s_lanceMask[2];

static inline void submit(UWORD size) { g_pCustom->bltsize = size; }
static void copySetup(WORD sourceModulo, WORD destModulo) {
	blitWait();
	g_pCustom->bltcon0 = USEA | USED | MINTERM_A;
	g_pCustom->bltcon1 = 0;
	g_pCustom->bltafwm = g_pCustom->bltalwm = 0xffff;
	g_pCustom->bltamod = sourceModulo; g_pCustom->bltdmod = destModulo;
}

UBYTE renderShotsCreate(tBitMap *front, tBitMap *back, const tBitMap *normal,
	const tBitMap *normalMask, const tBitMap *lance, const tBitMap *lanceMask) {
	if(s_background) return 0;
	if(!stripValid(normal, 16, SHOT_H) || !stripValid(normalMask, 16, SHOT_H) ||
		!stripValid(lance, 16, CHARGED_SHOT_H * 2) ||
		!stripValid(lanceMask, 16, CHARGED_SHOT_H * 2)) return 0;
	s_background = memAllocChipClear(sizeof(tShotBacking) * 2);
	if(!s_background) return 0;
	s_normalData = normal->Planes[0]; s_normalMask = normalMask->Planes[0];
	for(UBYTE frame = 0; frame < 2; ++frame) {
		s_lanceData[frame] = lance->Planes[0] + frame * CHARGED_SHOT_H * 8;
		s_lanceMask[frame] = lanceMask->Planes[0] + frame * CHARGED_SHOT_H * 8;
	}
	s_history[0].count = s_history[1].count = 0;
	s_buffers[0] = front; s_buffers[1] = back;
	renderShotsBind(back);
	return 1;
}

void renderShotsBind(tBitMap *back) { s_screen = back; s_buffer = back == s_buffers[1]; }

void renderShotsRestore(void) {
	if(!s_background || !s_history[s_buffer].count) return;
	tShotHistory *history = &s_history[s_buffer];
	copySetup(0, 36);
	for(UBYTE i = 0; i < history->count; ++i) {
		const tShotRecord *record = &history->records[i];
		blitWait();
		g_pCustom->bltapt = record->background; g_pCustom->bltdpt = record->dest;
		submit(record->size);
	}
	blitWait();
	history->count = 0;
}

void renderShotsDraw(tGameState *state, UBYTE show) {
	if(!state || !s_background) return;
	tShotHistory *history = &s_history[s_buffer];
	tShotBacking *backing = &s_background[s_buffer];
	UBYTE lances = 0, frame = (state->frame >> 2) & 1;
	history->count = 0;
	for(UBYTE i = 0; i < SHOT_COUNT; ++i) {
		tEntity *shot = &state->shots[i];
		shot->visible = 0;
		UBYTE charged = shot->kind == SHOT_CHARGED, height = charged ? CHARGED_SHOT_H : SHOT_H;
		if(!show || !shot->active || shot->kind > SHOT_CHARGED || shot->x < 0 || shot->x > BOB_MAX_X ||
			shot->y < PLAY_TOP || shot->y + height > PLAY_BOTTOM) continue;
		if((state->phase == SECTOR_INTRO || state->phase == BOSS_INTRO) &&
			renderScenesOccludes(shot->x, shot->y, 16, height)) continue;
		if(charged && lances == LANCE_SLOTS) continue;
		tShotRecord *record = &history->records[history->count++];
		UWORD offset = (UWORD)shot->y * 160 + (UWORD)(shot->x >> 4) * 2;
		record->dest = s_screen->Planes[0] + offset;
		record->background = charged ? backing->lance[lances++] : backing->normal[i];
		record->pixels = charged ? s_lanceData[frame] : s_normalData;
		record->mask = charged ? s_lanceMask[frame] : s_normalMask;
		record->size = ((height * 4) << HSIZEBITS) | 2;
		record->shift = shot->x & 15;
		shot->visible = 1;
		hudBobPushed(charged ? HB_LANCE : HB_SHOT, shot->x);
	}
	if(!history->count) return;
	/* Save all backgrounds before drawing any player shots. These backgrounds
	 * contain current ACE foregrounds, so restore them before ACE bobBegin. */
	copySetup(36, 0);
	for(UBYTE i = 0; i < history->count; ++i) {
		const tShotRecord *record = &history->records[i];
		blitWait();
		g_pCustom->bltapt = record->dest; g_pCustom->bltdpt = record->background;
		submit(record->size);
	}
	blitWait();
	g_pCustom->bltafwm = 0xffff; g_pCustom->bltalwm = 0;
	g_pCustom->bltamod = g_pCustom->bltbmod = -2;
	g_pCustom->bltcmod = g_pCustom->bltdmod = 36;
	UBYTE lastShift = 255;
	for(UBYTE i = 0; i < history->count; ++i) {
		const tShotRecord *record = &history->records[i];
		blitWait();
		if(record->shift != lastShift) {
			UWORD shift = (UWORD)record->shift << ASHIFTSHIFT;
			g_pCustom->bltcon0 = shift | USEA | USEB | USEC | USED | MINTERM_COOKIE;
			g_pCustom->bltcon1 = shift;
			lastShift = record->shift;
		}
		g_pCustom->bltapt = record->mask; g_pCustom->bltbpt = record->pixels;
		g_pCustom->bltcpt = g_pCustom->bltdpt = record->dest;
		submit(record->size);
	}
	blitWait();
}
void renderShotsDiscard(void) { s_history[0].count = s_history[1].count = 0; }
void renderShotsDestroy(void) {
	blitWait();
	if(s_background) memFree(s_background, sizeof(tShotBacking) * 2);
	s_background = 0; s_screen = s_buffers[0] = s_buffers[1] = 0;
	renderShotsDiscard();
}
