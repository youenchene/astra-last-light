#include "render_enemies.h"
#include "render_internal.h"
#include "render_stream.h"
#include "art.h"

#define ENEMY_CHANNEL 4
#define ACTOR_HEIGHT 16
#define ACTOR_KINDS 6
#define ACTOR_FRAMES (LEVEL_COUNT * ACTOR_KINDS)

static const tView *s_pView;
static ULONG *s_pBlank;
/* Attached pair: channel 4 carries planes 0/1, channel 5 planes 2/3. */
static tSpriteStream s_pStreams[2];
static ULONG s_pPixels[ACTOR_FRAMES][2][ACTOR_HEIGHT];

UBYTE renderEnemiesCreate(const tView *pView, ULONG *pBlank) {
	if(s_pView || !pView || !pBlank) return 0;
	tBitMap *pStrip = artSectorEnemiesCreate();
	if(!pStrip) return 0;
	UBYTE ok = stripValid(pStrip, 16, ACTOR_FRAMES * ACTOR_HEIGHT);
	if(ok) stripSplit(pStrip, 16, ACTOR_FRAMES, ACTOR_HEIGHT, &s_pPixels[0][0][0]);
	bitmapDestroy(pStrip);
	if(!ok) return 0;
	s_pView = pView;
	s_pBlank = pBlank;
	for(UBYTE part = 0; part < 2; ++part)
		if(!spriteStreamCreate(&s_pStreams[part], pView, ENEMY_CHANNEL + part,
			ACTOR_HEIGHT, ENEMY_SPRITE_CAPACITY)) {
			renderEnemiesDestroy();
			return 0;
		}
	return 1;
}

/* Visible channel-4 enemies in ascending Y (at most six: insertion sort). */
static UBYTE gatherEnemies(tGameState *pState, tEntity **pList) {
	UBYTE count = 0;
	UBYTE show = pState->phase == PLAY ||
		(pState->phase == HERO_DYING && pState->resumePhase == PLAY);
	for(UBYTE i = 0; i < ENEMY_COUNT; ++i) {
		tEntity *pEntity = &pState->enemies[i];
		if(!show) { pEntity->visible = 0; continue; }
		pEntity->visible = 0;
		if(!pEntity->active) continue;
		if(pEntity->channel != ENEMY_CHANNEL || pEntity->kind > ENEMY_ASTEROID ||
			pEntity->kind == ENEMY_BOSS || pEntity->x <= -ENEMY_W || pEntity->x >= WORLD_W ||
			pEntity->y < PLAY_TOP || pEntity->y > PLAY_BOTTOM - ACTOR_HEIGHT ||
			count >= ENEMY_SPRITE_CAPACITY) { pEntity->visible = 0; continue; }
		UBYTE j = count++;
		for(; j && pList[j - 1]->y > pEntity->y; --j) pList[j] = pList[j - 1];
		pList[j] = pEntity;
	}
	return count;
}

void renderEnemiesDraw(tGameState *pState) {
	if(!pState || !s_pView) return;
	tEntity *pList[ENEMY_SPRITE_CAPACITY];
	UBYTE count = gatherEnemies(pState, pList);
	/* The bullet writer alone owns the pair in boss combat/death pause. */
	if(logicHostileChannelMask(pState) & (1U << ENEMY_CHANNEL)) return;
	UBYTE buffer = spriteStreamBuffer(&s_pStreams[0], s_pView);
	tSpriteWriter low, high;
	spriteWriterBegin(&low, &s_pStreams[0], buffer);
	spriteWriterBegin(&high, &s_pStreams[1], buffer);
	UWORD posX = s_pView->ubPosX - 1, posY = s_pView->ubPosY;
	UBYTE sector = pState->level < LEVEL_COUNT ? pState->level : 0;
	WORD nextY = -32767;
	for(UBYTE i = 0; i < count; ++i) {
		tEntity *pEntity = pList[i];
		/* Logic keeps formation lanes ENEMY_H + 2 apart; never expected. */
		if(pEntity->y < nextY) { pEntity->visible = 0; continue; }
		UWORD x = posX + pEntity->x, start = posY + pEntity->y;
		UBYTE frame = sector * ACTOR_KINDS + pEntity->kind;
		spriteWriterPut(&low, x, start, 0, s_pPixels[frame][0]);
		spriteWriterPut(&high, x, start, 0x80, s_pPixels[frame][1]);
		pEntity->visible = 1;
		nextY = pEntity->y + ACTOR_HEIGHT + 1;
	}
	spriteWriterPublish(&low, s_pView);
	spriteWriterPublish(&high, s_pView);
}

void renderEnemiesDestroy(void) {
	for(UBYTE part = 0; part < 2; ++part)
		spriteStreamDestroy(&s_pStreams[part], s_pView, s_pBlank);
	s_pView = 0;
	s_pBlank = 0;
}
