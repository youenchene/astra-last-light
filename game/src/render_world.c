#include "render_world.h"
#include "render_internal.h"
#include "art.h"
#include "render.h"
#include <ace/managers/blit.h>
#include <ace/utils/custom.h>
#include <ace/utils/fetchmode.h>

#define STAR_COUNT 96
#define DECOR_HEIGHT 24
#define DECOR_TOP 29
#define DECOR_BOTTOM 220

/* Cache by physical copper list, independent of bitmap swapping. */
static tCopBfr *s_pDecorCopperA;
static struct {
	tBitMap *screen;
	UBYTE enabled, level, top, bottom;
} s_decorCopper[2];

static tVPort *s_pVPort;
static tBitMap *s_pScreen, *s_pFont, *s_pDecor, *s_pCommonTitle;
static tBitMap *s_buffers[2];
static tBitMap *s_pLabels;
static UBYTE s_ubLevel, s_buffer;
static tPhase s_ePhase;
static UBYTE s_ubDecorTick, s_topScroll, s_bottomScroll;
static UWORD s_pStarX[STAR_COUNT], s_pStarRow[STAR_COUNT];
static UWORD s_uwOriginalStarColor;
static ULONG s_pGlyphMasks[3][36][28];
static UBYTE s_hasScroll;
/* Pixel history and composition cursors belong to a bitmap, not a tick.
 * Each tick advances only the back target (8 rows / two glyphs total). */
typedef struct {
	ULONG score;
	UWORD hp, row, cursor, stars[STAR_COUNT];
	UBYTE valid, preparing, stage, command;
	UBYTE lives, charge, weapon, speed, shield, shotLevel, top, bottom, chargeInk;
} tWorldBuffer;
static tWorldBuffer s_history[2];
#define HISTORY (s_history[s_buffer])
#define s_isValid HISTORY.valid
#define s_preparing HISTORY.preparing
#define s_prepareStage HISTORY.stage
#define s_prepareRow HISTORY.row
#define s_command HISTORY.command
#define s_commandCursor HISTORY.cursor
#define s_ulScore HISTORY.score
#define s_uwHp HISTORY.hp
#define s_ubLives HISTORY.lives
#define s_ubCharge HISTORY.charge
#define s_ubWeapon HISTORY.weapon
#define s_ubSpeed HISTORY.speed
#define s_ubShield HISTORY.shield
#define s_ubShotLevel HISTORY.shotLevel
#define s_ubTopScroll HISTORY.top
#define s_ubBottomScroll HISTORY.bottom
/* Fixed slow-memory command queue; no allocation or full-screen staging bitmap. */
typedef struct {
	UWORD x, y, width, height;
	UBYTE scale, color;
	char text[32];
} tWorldCommand;
static tWorldCommand s_commands[32];
static UBYTE s_commandCount;
static UBYTE combatBackground(tPhase phase);


/* All display writes are bounded; CPU pixels are used only for tiny dirty
 * regions and scene-entry composition, never a whole-frame redraw. */
static UBYTE pixelRead(const tBitMap *pBitmap, UWORD x, UWORD y) {
	UBYTE color = 0, mask = 0x80 >> (x & 7);
	UWORD offset = y * pBitmap->BytesPerRow + (x >> 3);
	for(UBYTE plane = 0; plane < pBitmap->Depth; ++plane) {
		if(pBitmap->Planes[plane][offset] & mask) color |= 1 << plane;
	}
	return color;
}

static void fontMasksCreate(void) {
	for(UBYTE size = 0; size < 3; ++size) {
		UBYTE scale = 1 << size;
		for(UBYTE glyph = 0; glyph < 36; ++glyph)
			for(UBYTE row = 0; row < 7; ++row) {
				ULONG mask = 0;
				for(UBYTE col = 0; col < 5; ++col)
					if(pixelRead(s_pFont, col, glyph * 7 + row))
						for(UBYTE dx = 0; dx < scale; ++dx)
							mask |= 0x80000000UL >> (col * scale + dx);
				for(UBYTE dy = 0; dy < scale; ++dy)
					s_pGlyphMasks[size][glyph][row * scale + dy] = mask;
			}
	}
}

/* Startup only: rasterize cached glyph masks without touching blitter/DMA.
 * Four 96x7 rows: LANCE, READY, HOLD TO CHARGE, RELEASE FIRE. */
static UBYTE labelsCreate(void) {
	static const char *const labels[4] = {
		"LANCE", "READY", "HOLD TO CHARGE", "RELEASE FIRE"
	};
	static const UBYTE colors[4] = {4, 7, 4, 14};
	s_pLabels = bitmapCreate(96, 28, 4, BMF_INTERLEAVED);
	if(!s_pLabels) return 0;
	for(UWORD y = 0; y < 28; ++y)
		for(UBYTE plane = 0; plane < 4; ++plane) {
			UBYTE *dest = s_pLabels->Planes[plane] + y * 48;
			UBYTE background = y < 14 && plane == 0 ? 0xff : 0;
			for(UBYTE byte = 0; byte < 12; ++byte) dest[byte] = background;
		}
	for(UBYTE label = 0; label < 4; ++label) {
		const char *text = labels[label];
		UWORD x = 0;
		while(*text) {
			char letter = *text++;
			if(letter >= 'A' && letter <= 'Z') {
				for(UBYTE row = 0; row < 7; ++row) {
					ULONG bits = s_pGlyphMasks[0][letter - 'A'][row] >> (x & 7);
					UWORD y = label * 7 + row;
					UWORD offset = y * 48 + (x >> 3);
					UBYTE bytes = ((x & 7) + 12) >> 3;
					for(UBYTE byte = 0; byte < bytes; ++byte) {
						UBYTE mask = bits >> 24;
						for(UBYTE plane = 0; plane < 4; ++plane) {
							UBYTE *dest = &s_pLabels->Planes[plane][offset + byte];
							if(colors[label] & (1 << plane)) *dest |= mask;
							else *dest &= ~mask;
						}
						bits <<= 8;
					}
				}
			}
			x += 6;
		}
	}
	return 1;
}

static void textDraw(UWORD x, UWORD y, const char *pText, UBYTE scale, UBYTE color) {
	blitWait();
	UBYTE size = scale == 4 ? 2 : (scale == 2 ? 1 : 0);
	while(*pText) {
		char letter = *pText++;
		if(letter >= 'a' && letter <= 'z') letter -= 'a' - 'A';
		UBYTE glyph = letter >= 'A' && letter <= 'Z' ? letter - 'A' :
			(letter >= '0' && letter <= '9' ? letter - '0' + 26 : 255);
		if(glyph != 255) {
			for(UWORD row = 0; row < 7 * scale; ++row) {
				ULONG bits = s_pGlyphMasks[size][glyph][row] >> (x & 7);
				UWORD sy = y + row;
				UWORD offset = (sy << 7) + (sy << 5) + (x >> 3);
				UBYTE bytes = ((x & 7) + 5 * scale + 7) >> 3;
				for(UBYTE b = 0; b < bytes; ++b) {
					UBYTE mask = bits >> 24;
					for(UBYTE plane = 0; plane < 4; ++plane) {
						UBYTE *dest = &s_pScreen->Planes[plane][offset + b];
						if(color & (1 << plane)) *dest |= mask;
						else *dest &= ~mask;
					}
					bits <<= 8;
				}
			}
		}
		x += 6 * scale;
	}
}

static void __attribute__((noinline)) numberText(char *text, ULONG value, UBYTE digits) {
	static const ULONG powers[] = {1, 10, 100, 1000, 10000, 100000,
		1000000, 10000000, 100000000};
	/* Only eight-digit scores and byte-sized one-digit counters are used.
	 * Fixed binary subtraction prevents GCC -O3 turning a modulo-like loop
	 * back into a costly 32-bit divide helper. */
	for(UBYTE shift = digits == 8 ? 6 : 5; shift; ) {
		ULONG amount = powers[digits] << --shift;
		if(value >= amount) value -= amount;
	}
	for(UBYTE i = digits; i; --i) {
		char digit = '0';
		ULONG place = powers[i - 1];
		for(UBYTE shift = 4; shift; ) {
			ULONG amount = place << --shift;
			if(value >= amount) { value -= amount; digit += 1 << shift; }
		}
		*text++ = digit;
	}
	*text = 0;
}

UBYTE renderWorldTextStep(UWORD x, UWORD y, const char *text,
	UBYTE scale, UBYTE color, UWORD *cursor) {
	char glyph[2] = {0, 0};
	for(UBYTE i = 0; i < 2 && text[*cursor]; ++i) {
		glyph[0] = text[*cursor];
		textDraw(x + *cursor * (6 * scale), y, glyph, scale, color);
		++*cursor;
	}
	return !text[*cursor];
}

static void queueText(UWORD x, UWORD y, const char *text, UBYTE scale, UBYTE color) {
	tWorldCommand *cmd = &s_commands[s_commandCount++];
	cmd->x = x; cmd->y = y; cmd->scale = scale; cmd->color = color;
	UBYTE i = 0;
	while(text[i] && i < sizeof(cmd->text) - 1) { cmd->text[i] = text[i]; ++i; }
	cmd->text[i] = 0;
}

static void queueRect(UWORD x, UWORD y, UWORD width, UWORD height, UBYTE color) {
	tWorldCommand *cmd = &s_commands[s_commandCount++];
	cmd->x = x; cmd->y = y; cmd->width = width; cmd->height = height;
	cmd->scale = 0; cmd->color = color;
}

static void queueNumber(UWORD x, UWORD y, ULONG value, UBYTE digits) {
	char text[9];
	numberText(text, value, digits);
	queueText(x, y, text, 1, 6);
}

static void numberDraw(UWORD x, UWORD y, ULONG value, UBYTE digits) {
	char text[9];
	numberText(text, value, digits);
	textDraw(x, y, text, 1, 6);
}

static void scoreDraw(ULONG score, UBYTE dirty) {
	if(dirty) {
		blitRect(s_pScreen, 92, 6, 90, 7, 1);
		numberDraw(92, 6, score, 8);
		return;
	}
	char before[9], after[9], glyph[2] = {0, 0};
	numberText(before, s_ulScore, 8);
	numberText(after, score, 8);
	/* Updating all eight digits here can delay player-shot BOBs past the beam.
	 * Only changed glyphs need clearing; their spacing and colors stay intact. */
	for(UBYTE i = 0; i < 8; ++i) {
		if(before[i] == after[i]) continue;
		UWORD x = 92 + i * 6;
		blitRect(s_pScreen, x, 6, 6, 7, 1);
		glyph[0] = after[i];
		textDraw(x, 6, glyph, 1, 6);
	}
}

void renderWorldSetStarColor(UWORD color) {
	s_uwOriginalStarColor = color;
}

void renderWorldBind(tBitMap *pScreen) {
	s_pScreen = pScreen;
	s_buffer = pScreen == s_buffers[1];
}

static void decorCopperDisable(tCopCmd *commands) {
	for(UBYTE i = 0; i < ASTRA_COP_DECOR_COUNT; ++i)
		copSetMove(&commands[i].sMove, &g_pCustom->bplcon2, 0x24);
}

/* ACE simplebuffer/fetchmode.h schedules controls after the preceding line's
 * final fetch, then pointers across hblank. Same 13 MOVEs at 4bpp here.
 * Phase zero uses ordinary fetch: no negative prefetch before the CHIP asset.
 * Other phases use ACE's exact (x-1)/16 pointer and (-x)&15 delay mapping. */
static void decorCopperSwitch(tCopCmd *commands, UWORD y, const tBitMap *bitmap,
	UWORD sourceY, UBYTE scroll, UBYTE decor) {
	UWORD start = fetchModeGetDDfStrt(s_pVPort);
	UWORD modulo = bitmap->BytesPerRow - 40;
	LONG offset = (ULONG)sourceY * bitmap->BytesPerRow;
	UWORD shift = 0;
	if(decor && scroll) {
		fetchModeApplyXScrollCopper(s_pVPort, &start, &modulo);
		offset += fetchModeCalcBplOffsetX(s_pVPort, scroll, 0);
		shift = fetchModeCalcBplShift(s_pVPort, scroll, 0);
	}
	copSetWait(&commands[0].sWait, fetchModeGetCopWaitX(s_pVPort),
		s_pVPort->pView->ubPosY + s_pVPort->uwOffsY + y - 1);
	copSetMove(&commands[1].sMove, &g_pCustom->ddfstop, fetchModeGetDDfStop(s_pVPort));
	copSetMove(&commands[2].sMove, &g_pCustom->ddfstrt, start);
	copSetMove(&commands[3].sMove, &g_pCustom->bpl1mod, modulo);
	copSetMove(&commands[4].sMove, &g_pCustom->bpl2mod, modulo);
	copSetMove(&commands[5].sMove, &g_pCustom->bplcon1, shift);
	for(UBYTE plane = 0; plane < 4; ++plane) {
		ULONG address = (ULONG)bitmap->Planes[plane] + offset;
		copSetMove(&commands[6 + plane * 2].sMove, &g_pBplFetch[plane].uwHi, address >> 16);
		copSetMove(&commands[7 + plane * 2].sMove, &g_pBplFetch[plane].uwLo, address & 0xffff);
	}
}

void renderWorldCopper(const tGameState *pState, UBYTE ready) {
	tCopBfr *back = s_pVPort->pView->pCopList->pBackBfr;
	UBYTE buffer = back != s_pDecorCopperA;
	tCopCmd *commands = &back->pList[ASTRA_COP_DECOR];
	/* Sector two is open nebula: fetch the space-colored framebuffer all the
	 * way to the HUD/footer rather than overlaying the retained crystal art. */
	UBYTE enabled = ready && combatBackground(pState->phase) && pState->level != 1;
	if(!enabled) {
		if(s_decorCopper[buffer].enabled) decorCopperDisable(commands);
		s_decorCopper[buffer].enabled = 0;
		return;
	}
	UBYTE changed = !s_decorCopper[buffer].enabled || s_decorCopper[buffer].level != s_ubLevel;
	if(changed || s_decorCopper[buffer].top != s_topScroll)
		decorCopperSwitch(commands, DECOR_TOP, s_pDecor, s_ubLevel * 48, s_topScroll, 1);
	if(changed || s_decorCopper[buffer].bottom != s_bottomScroll)
		decorCopperSwitch(commands + 29, DECOR_BOTTOM, s_pDecor,
			s_ubLevel * 48 + DECOR_HEIGHT, s_bottomScroll, 1);
	if(!s_decorCopper[buffer].enabled || s_decorCopper[buffer].screen != s_pScreen) {
		decorCopperSwitch(commands + 14, DECOR_TOP + DECOR_HEIGHT, s_pScreen,
			DECOR_TOP + DECOR_HEIGHT, 0, 0);
		/* Bottom starts at PAL beam 264; low-byte WAIT alone would fire early. */
		copSetWait(&commands[28].sWait, 0xdf, 0xff);
		decorCopperSwitch(commands + 43, DECOR_BOTTOM + DECOR_HEIGHT, s_pScreen,
			DECOR_BOTTOM + DECOR_HEIGHT, 0, 0);
	}
	s_decorCopper[buffer].enabled = 1;
	s_decorCopper[buffer].screen = s_pScreen;
	s_decorCopper[buffer].level = s_ubLevel;
	s_decorCopper[buffer].top = s_topScroll;
	s_decorCopper[buffer].bottom = s_bottomScroll;
}

UBYTE renderWorldCreate(tVPort *pVPort, tBitMap *pFront, tBitMap *pScreen) {
	s_pVPort = pVPort;
	s_pDecorCopperA = pVPort->pView->pCopList->pBackBfr;
	decorCopperDisable(&s_pDecorCopperA->pList[ASTRA_COP_DECOR]);
	decorCopperDisable(&pVPort->pView->pCopList->pFrontBfr->pList[ASTRA_COP_DECOR]);
	s_decorCopper[0].enabled = s_decorCopper[1].enabled = 0;
	s_buffers[0] = pScreen; s_buffers[1] = pFront;
	renderWorldBind(pScreen);
	s_pFont = artFontCreate();
	if(!s_pFont) return 0;
	fontMasksCreate();
	if(!labelsCreate()) return 0;
	/* Title-only sharing saves 3 * 6144 chip bytes; source plates are retained.
	 * Gameplay decor and all five manga plates remain sector-specific. */
	s_pCommonTitle = artGraveyardCreate();
	if(!s_pCommonTitle) return 0;
	tBitMap *pStrip = artDecorCreate();
	if(!pStrip) return 0;
	if(!stripValid(pStrip, 64, 8 * DECOR_HEIGHT)) { bitmapDestroy(pStrip); return 0; }
	s_pDecor = bitmapCreate(384, 192, 4, BMF_CLEAR | BMF_INTERLEAVED);
	if(!s_pDecor) { bitmapDestroy(pStrip); return 0; }
	/* Do not depend on the OS blitter/DMA state during asset initialization.
	 * Expand the repeated source on the CPU before hardware takeover. */
	for(UBYTE plane = 0; plane < 4; ++plane) {
		const UWORD *source = (const UWORD *)pStrip->Planes[plane];
		UWORD *dest = (UWORD *)s_pDecor->Planes[plane];
		for(UWORD row = 0; row < 192; ++row) {
			for(UBYTE tile = 0; tile < 6; ++tile)
				for(UBYTE word = 0; word < 4; ++word) dest[tile * 4 + word] = source[word];
			source += 16;
			dest += 96;
		}
	}
	bitmapDestroy(pStrip);
	return 1;
}

static void decorRows(UWORD scroll, UWORD band, UWORD destY, UWORD row, UWORD rows) {
	UWORD sourceY = s_ubLevel * 48 + band + row;
	destY += row;
	UBYTE shift = scroll & 15;
	if(!shift) {
		blitCopyAligned(s_pDecor, scroll, sourceY, s_pScreen, 0, destY,
			WORLD_W, rows);
		return;
	}
	/* 384px source/320px destination, four interleaved planes: 96 physical
	 * rows of 20 words. Ascending A->D with ASHIFT=16-shift starts at the
	 * next source word. Words 1..19 then combine the correct adjacent pair;
	 * word 0 inherits the previous row's shifter carry and is repaired below.
	 * The source's 64px guard tile contains the last word even at scroll=63. */
	const UBYTE *source = s_pDecor->Planes[0] + sourceY * s_pDecor->BytesPerRow +
		((scroll & 48) >> 3);
	UBYTE *dest = s_pScreen->Planes[0] + destY * s_pScreen->BytesPerRow;
	UBYTE rightShift = 16 - shift;
	blitWait();
	g_pCustom->bltcon0 = (rightShift << ASHIFTSHIFT) | USEA | USED | MINTERM_A;
	g_pCustom->bltcon1 = 0;
	g_pCustom->bltafwm = 0xffff;
	g_pCustom->bltalwm = 0xffff;
	g_pCustom->bltamod = 48 - 40;
	g_pCustom->bltdmod = 0;
	g_pCustom->bltapt = (APTR)(source + 2);
	g_pCustom->bltdpt = dest;
	g_pCustom->bltsize = ((rows * 4) << HSIZEBITS) | (WORLD_W / 16);
	blitWait();
	/* Bounded scene composition only; runtime bands are fetched by copper. */
	for(UBYTE line = 0; line < rows * 4; ++line) {
		const UWORD *words = (const UWORD *)source;
		*(UWORD *)dest = (UWORD)(words[0] << shift) | (words[1] >> rightShift);
		source += 48;
		dest += 40;
	}
}

static void starsReset(void) {
	s_ubDecorTick = 0;
	s_topScroll = s_bottomScroll = 0;
	UWORD starSeed = 0xace1;
	UWORD y = PLAY_TOP, remainder = 0;
	for(UBYTE i = 0; i < STAR_COUNT; ++i) {
		starSeed = (starSeed >> 1) ^ ((starSeed & 1) ? 0xb400 : 0);
		s_pStarX[i] = starSeed % 316;
		/* Unique ascending rows keep CPU writes in beam order. */
		s_pStarRow[i] = (y << 7) + (y << 5);
		++y;
		remainder += (PLAY_BOTTOM - PLAY_TOP - 1) - (STAR_COUNT - 1);
		if(remainder >= STAR_COUNT - 1) { ++y; remainder -= STAR_COUNT - 1; }
	}
}

static void starToggle(UBYTE index, UWORD x) {
	UBYTE layer = index & 3;
	UWORD shape = layer >= 2 ? 0xc000 : 0x8000;
	UWORD mask = shape >> (x & 7);
	UWORD offset = s_pStarRow[index] + (x >> 3);
	/* The gameplay corridor is empty behind these bright trails; XOR erases
	 * their previous positions without a saved bitmap or full-screen blit. */
	s_pScreen->Planes[2][offset] ^= mask >> 8;
	if(mask & 255) s_pScreen->Planes[2][offset + 1] ^= mask & 255;
}

/* Only the stars due this tick are visited: layer L (index 4k+L) moves when
 * (tick + k) is a multiple of its period. Two-pixel batches at twice the
 * former period preserve all four average speeds while halving CPU updates. */
static void starsProcess(void) {
	static const UBYTE periods[4] = {16, 8, 4, 2};
	for(UBYTE layer = 0; layer < 4; ++layer) {
		UBYTE period = periods[layer];
		for(UBYTE k = (UBYTE)(-s_ubDecorTick) & (period - 1); k < STAR_COUNT / 4; k += period) {
			UBYTE index = (k << 2) | layer;
			UWORD x = s_pStarX[index];
			s_pStarX[index] = x < 2 ? x + 314 : x - 2;
		}
	}
}

void renderWorldAnimate(const tGameState *pState) {
	if(!renderWorldReady() || !combatBackground(pState->phase)) return;
	if(logicWorldScrolling(pState)) {
		++s_ubDecorTick;
		if(s_ubDecorTick & 1) s_bottomScroll = (s_ubDecorTick >> 2) & 63;
		else s_topScroll = (s_ubDecorTick >> 2) & 63;
		starsProcess();
	}
	/* Catch up N-2 pixels even when simulation has just frozen. */
	blitWait();
	for(UBYTE i = 0; i < STAR_COUNT; ++i) {
		UWORD before = HISTORY.stars[i], after = s_pStarX[i];
		if(before == after) continue;
		if(before >= 2 && before - 2 == after) {
			UWORD mask = ((i & 3) >= 2 ? 0xf000 : 0xa000) >> (after & 7);
			UBYTE *pixel = s_pScreen->Planes[2] + s_pStarRow[i] + (after >> 3);
			pixel[0] ^= mask >> 8;
			if(mask & 255) pixel[1] ^= mask & 255;
		}
		else { starToggle(i, before); starToggle(i, after); }
		HISTORY.stars[i] = after;
	}
}

static void panelQueue(tPhase phase) {
	if(phase != TITLE && phase != GAMEOVER) return;
	queueRect(24, 122, 272, 94, 1);
	queueRect(24, 122, 272, 1, 15);
	queueRect(24, 215, 272, 1, 3);
	if(phase == TITLE) {
		queueText(102, 131, "ASTRA", 4, 6);
		queueText(102, 166, "LAST LIGHT", 2, 14);
		queueText(91, 190, "FIRE TO DEFEND THE DAWN", 1, 7);
		queueText(88, 203, "LEFT RIGHT SELECT SECTOR", 1, 4);
	}
	else {
		queueText(106, 142, "GAME OVER", 2, 11);
		queueText(70, 169, "THE FLEET WILL REMEMBER YOU", 1, 6);
		queueText(109, 196, "FIRE TO TRY AGAIN", 1, 7);
	}
}

static void hudDraw(const tGameState *pState, UBYTE dirty) {
	if(dirty || s_ubWeapon != pState->weaponLevel || s_ubSpeed != pState->speedLevel ||
		s_ubShield != pState->shield || s_ubShotLevel != pState->shotLevel) {
		blitRect(s_pScreen, 20, 249, 6, 7, 0);
		blitRect(s_pScreen, 44, 249, 6, 7, 0);
		blitRect(s_pScreen, 68, 249, 6, 7, 0);
		blitRect(s_pScreen, 92, 249, 6, 7, 0);
		numberDraw(20, 249, pState->weaponLevel, 1);
		numberDraw(44, 249, pState->speedLevel, 1);
		numberDraw(68, 249, pState->shield, 1);
		numberDraw(92, 249, pState->shotLevel + 1, 1);
	}
	if(dirty || s_ulScore != pState->score) {
		scoreDraw(pState->score, dirty);
	}
	if(dirty || s_ubLives != pState->lives) {
		blitRect(s_pScreen, 230, 6, 18, 7, 1);
		numberDraw(230, 6, pState->lives, 1);
	}
	UBYTE ready = pState->charge >= CHARGE_FRAMES;
	if(dirty || ready != (s_ubCharge >= CHARGE_FRAMES)) {
		blitCopy(s_pLabels, 0, ready ? 7 : 0, s_pScreen, 8, 18, 32, 7, MINTERM_COOKIE);
		blitCopyAligned(s_pLabels, 0, ready ? 21 : 14, s_pScreen, 224, 249, 96, 7);
	}
	if(dirty || s_ubCharge != pState->charge ||
		(ready && HISTORY.chargeInk != (pState->frame & 8))) {
		blitRect(s_pScreen, 44, 19, 100, 4, 2);
		if(pState->charge) blitRect(s_pScreen, 44, 19,
			ready ? 100 : pState->charge << 1, 4, ready ? ((pState->frame & 8) ? 7 : 14) : 15);
	}
	if(dirty || s_uwHp != pState->boss.hp) {
		UBYTE labelChanged = dirty || !s_uwHp || !pState->boss.hp;
		if(labelChanged) blitRect(s_pScreen, 166, 18, 146, 7, 1);
		if(pState->phase == BOSS && pState->boss.maxHp) {
			if(labelChanged) textDraw(166, 18, "BOSS", 1, 11);
			UWORD width = (UWORD)(pState->boss.hp * 112u) / pState->boss.maxHp;
			blitRect(s_pScreen, 198, 19, 112, 4, 2);
			if(width) blitRect(s_pScreen, 198, 19, width, 4, 11);
		}
	}
	s_ulScore = pState->score;
	s_ubLives = pState->lives;
	s_ubCharge = pState->charge;
	s_uwHp = pState->boss.hp;
	s_ubWeapon = pState->weaponLevel;
	s_ubSpeed = pState->speedLevel;
	s_ubShield = pState->shield;
	s_ubShotLevel = pState->shotLevel;
	HISTORY.chargeInk = pState->frame & 8;
}

void renderWorldHud(const tGameState *pState) {
	if(s_isValid) hudDraw(pState, 0);
}

static UBYTE combatBackground(tPhase phase) {
	return phase == PLAY || phase == BOSS || phase == HERO_DYING || phase == BOSS_DYING;
}

void renderWorldInvalidate(UBYTE resetScroll) {
	for(UBYTE i = 0; i < 2; ++i) s_history[i].valid = s_history[i].preparing = 0;
	if(resetScroll) s_hasScroll = 0;
}

UBYTE renderWorldMatches(const tGameState *pState) {
	return (s_isValid || s_preparing) && s_ubLevel == pState->level &&
		(s_ePhase == pState->phase ||
		(combatBackground(s_ePhase) && combatBackground(pState->phase)));
}

UBYTE renderWorldReady(void) { return s_history[0].valid && s_history[1].valid; }

void renderWorldBegin(const tGameState *pState) {
	static const UWORD space[4] = {0x001, 0x102, 0x101, 0x001};
	UBYTE level = pState->level;
	if(!s_hasScroll || s_ubLevel != level) starsReset();
	s_hasScroll = 1;
	s_ubLevel = pState->level;
	s_ePhase = pState->phase;
	s_isValid = 0; s_preparing = 1;
	s_prepareStage = 0; s_prepareRow = 0;
	s_commandCount = s_command = 0; s_commandCursor = 0;
	s_pVPort->pPalette[0] = space[level];
	s_pVPort->pPalette[4] = s_ePhase == TITLE ? s_uwOriginalStarColor : 0xbdf;
	queueRect(0, 0, 320, 28, 1);
	queueRect(0, 28, 320, 1, 15);
	queueRect(0, 245, 320, 1, 3);
	queueText(8, 6, "ASTRA", 1, 15);
	queueText(56, 6, "SCORE", 1, 5);
	queueText(194, 6, "LIVES", 1, 5);
	queueText(260, 6, "SECTOR", 1, 5);
	queueNumber(302, 6, level + 1, 1);
	queueText(8, 18, pState->charge >= CHARGE_FRAMES ? "READY" : "LANCE", 1,
		pState->charge >= CHARGE_FRAMES ? 7 : 4);
	queueText(8, 249, "W   S   R   F", 1, 4);
	queueText(104, 249, g_stageNames[level], 1, 5);
	queueText(224, 249, pState->charge >= CHARGE_FRAMES ? "RELEASE FIRE" : "HOLD TO CHARGE",
		1, pState->charge >= CHARGE_FRAMES ? 14 : 4);
	queueNumber(20, 249, pState->weaponLevel, 1);
	queueNumber(44, 249, pState->speedLevel, 1);
	queueNumber(68, 249, pState->shield, 1);
	queueNumber(92, 249, pState->shotLevel + 1, 1);
	queueNumber(92, 6, pState->score, 8);
	queueNumber(230, 6, pState->lives, 1);
	queueRect(44, 19, 100, 4, 2);
	if(pState->charge) queueRect(44, 19,
		pState->charge >= CHARGE_FRAMES ? 100 : pState->charge << 1, 4, 15);
	if(s_ePhase == BOSS && pState->boss.maxHp) {
		queueText(166, 18, "BOSS", 1, 11);
		queueRect(198, 19, 112, 4, 2);
		UWORD width = (UWORD)(pState->boss.hp * 112u) / pState->boss.maxHp;
		if(width) queueRect(198, 19, width, 4, 11);
	}
	panelQueue(s_ePhase);
	s_ulScore = pState->score; s_ubLives = pState->lives;
	s_ubCharge = pState->charge; s_uwHp = pState->boss.hp;
	s_ubWeapon = pState->weaponLevel; s_ubSpeed = pState->speedLevel;
	s_ubShield = pState->shield;
	s_ubShotLevel = pState->shotLevel;
	HISTORY.chargeInk = pState->frame & 8;
	/* Identical command stream and frozen world snapshot for both targets;
	 * only the bound back bitmap advances each tick. */
	s_history[!s_buffer] = HISTORY;
}

void renderWorldStep(void) {
	if(!s_preparing) return;
	if(s_prepareStage == 0) {
		blitRect(s_pScreen, 0, s_prepareRow, WORLD_W, 8, 0);
		s_prepareRow += 8;
		if(s_prepareRow == WORLD_H) { ++s_prepareStage; s_prepareRow = 0; }
	}
	else if(s_prepareStage == 1) {
		if(s_ePhase == TITLE) {
			blitCopy(s_pCommonTitle, 0, s_prepareRow, s_pScreen,
				184, 56 + s_prepareRow, 128, 8, MINTERM_COOKIE);
			s_prepareRow += 8;
			if(s_prepareRow == 96) ++s_prepareStage;
		}
		else if(s_ubLevel == 1) {
			/* Both physical framebuffers were cleared to ink zero above. */
			s_ubTopScroll = s_topScroll; s_ubBottomScroll = s_bottomScroll;
			++s_prepareStage;
		}
		else {
			UBYTE bottom = s_prepareRow >= DECOR_HEIGHT;
			decorRows(bottom ? s_bottomScroll : s_topScroll,
				bottom ? DECOR_HEIGHT : 0, bottom ? DECOR_BOTTOM : DECOR_TOP,
				bottom ? s_prepareRow - DECOR_HEIGHT : s_prepareRow, 8);
			s_prepareRow += 8;
			if(s_prepareRow == 2 * DECOR_HEIGHT) {
				s_ubTopScroll = s_topScroll; s_ubBottomScroll = s_bottomScroll;
				++s_prepareStage;
			}
		}
	}
	else if(s_prepareStage == 2) {
		if(s_command < s_commandCount) {
			tWorldCommand *cmd = &s_commands[s_command];
			if(cmd->scale) {
				if(renderWorldTextStep(cmd->x, cmd->y, cmd->text, cmd->scale,
					cmd->color, &s_commandCursor)) { ++s_command; s_commandCursor = 0; }
			}
			else {
				UWORD rows = cmd->height - s_commandCursor;
				if(rows > 8) rows = 8;
				blitRect(s_pScreen, cmd->x, cmd->y + s_commandCursor, cmd->width, rows, cmd->color);
				s_commandCursor += rows;
				if(s_commandCursor == cmd->height) { ++s_command; s_commandCursor = 0; }
			}
		}
		else { ++s_prepareStage; s_prepareRow = 0; }
	}
	else {
		if(combatBackground(s_ePhase)) {
			blitWait();
			for(UBYTE i = 0; i < 8; ++i, ++s_prepareRow) {
				starToggle(s_prepareRow, s_pStarX[s_prepareRow]);
				HISTORY.stars[s_prepareRow] = s_pStarX[s_prepareRow];
			}
			if(s_prepareRow < STAR_COUNT) return;
		}
		blitWait();
		s_isValid = 1; s_preparing = 0;
	}
}

void renderWorldDestroy(void) {
	if(s_pLabels) bitmapDestroy(s_pLabels);
	s_pLabels = 0;
	if(s_pDecor) bitmapDestroy(s_pDecor);
	if(s_pCommonTitle) bitmapDestroy(s_pCommonTitle);
	if(s_pFont) bitmapDestroy(s_pFont);
	s_pDecor = s_pFont = 0;
	s_pCommonTitle = 0;
	s_pVPort = 0;
	s_pScreen = 0;
	s_isValid = 0;
	s_hasScroll = s_preparing = 0;
}
