#include "language_select.h"

/* Geometry, flag diagonals and seven-row lettering match SuperRugbyV
 * language_select.inc (68abf2e0dc655c5a13b12bd9ea20f7c1fccd84ec).
 * Small label-only bitmap alphabet includes the original compact cedilla. */
static const uint8_t s_glyphs[][7] = {
	{31,16,16,30,16,16,16}, /* F */
	{30,17,17,30,20,18,17}, /* R */
	{14,17,17,31,17,17,17}, /* A */
	{17,25,21,19,17,17,17}, /* N */
	{14,17,16,16,17,14,4},  /* C cedilla */
	{14,4,4,4,4,4,14},     /* I */
	{15,16,16,14,1,1,30},  /* S */
	{31,16,16,30,16,16,31},/* E */
	{14,17,16,23,17,17,15},/* G */
	{16,16,16,16,16,16,31},/* L */
	{17,17,17,31,17,17,17} /* H */
};
static const uint8_t s_french[8] = {0,1,2,3,4,2,5,6};
static const uint8_t s_english[7] = {7,3,8,9,5,6,10};
const uint16_t g_languagePalette[4] = {0x011,0x149,0xfed,0xc23};
static tLanguage s_language = LANGUAGE_FR;

tLanguage languageGet(void) { return s_language; }

void languageSelectBegin(tLanguageSelect *choice) {
	*choice = (tLanguageSelect){0};
	choice->selected = s_language;
	/* Treat directions already down on entry as consumed. */
	choice->previousDirs = 3;
}

uint8_t languageSelectTargetReady(const tLanguageSelect *choice, uint8_t target) {
	return choice->row[target] == 256 && choice->borderRow[target] == 72 &&
		choice->drawn[target] == choice->selected;
}

uint8_t languageSelectReady(const tLanguageSelect *choice) {
	return choice->published == 3 && choice->visible == choice->selected &&
		languageSelectTargetReady(choice, 0) && languageSelectTargetReady(choice, 1);
}

void languageSelectPresented(tLanguageSelect *choice, uint8_t target) {
	if(!languageSelectTargetReady(choice, target)) return;
	choice->published |= (uint8_t)(1 << target);
	choice->visible = choice->drawn[target];
}

uint8_t languageSelectInput(tLanguageSelect *choice, uint8_t dirs, uint8_t fire) {
	uint8_t edge = dirs & (uint8_t)~choice->previousDirs;
	choice->previousDirs = dirs;
	if(choice->confirmed) return !fire;
	if(!languageSelectReady(choice)) {
		if(fire) choice->armed = 0;
		return 0;
	}
	if(!fire) choice->armed = 1;
	if(edge & 3) {
		tLanguage selected = dirs & 1 ? LANGUAGE_FR : LANGUAGE_EN;
		if(selected != choice->selected) {
			choice->selected = selected;
			choice->published = 0;
			choice->borderRow[0] = choice->borderRow[1] = 0;
			/* Simultaneous direction/fire must not confirm an unseen choice. */
			if(fire) choice->armed = 0;
			return 0;
		}
	}
	if(fire && choice->armed) {
		s_language = choice->selected;
		choice->confirmed = 1;
	}
	return 0;
}

/* Only inks 0..3 are used; the upper two planes were cleared on row entry. */
static void pixel(uint8_t *const planes[4], uint16_t offset,
	uint16_t x, uint8_t ink) {
	uint8_t bit = 0x80 >> (x & 7);
	offset += x >> 3;
	for(uint8_t p = 0; p < 2; ++p) {
		if(ink & (1 << p)) planes[p][offset] |= bit;
		else planes[p][offset] &= (uint8_t)~bit;
	}
}

static void border(uint8_t *const planes[4], uint16_t offset,
	uint16_t y, tLanguage selected) {
	if(y < 74 || y >= 146) return;
	for(uint8_t item = 0; item < 2; ++item) {
		uint16_t x = item ? 192 : 34;
		uint8_t ink = item == selected ? 2 : 0;
		if(y < 76 || y >= 144) {
			for(uint8_t col = 0; col < 80; ++col) pixel(planes, offset, x + col, ink);
		}
		else {
			pixel(planes, offset, x, ink); pixel(planes, offset, x + 1, ink);
			pixel(planes, offset, x + 78, ink); pixel(planes, offset, x + 79, ink);
		}
	}
}

static void flags(uint8_t *const planes[4], uint16_t offset, uint16_t row) {
	/* Signed 16-bit differences stay within +/-2520; no 32-bit division. */
	int16_t d = -(int16_t)(row << 6), e = 2520 + d;
	for(uint16_t col = 0; col < 64; ++col, d += 40, e -= 40) {
		pixel(planes, offset, 42 + col, col < 21 ? 1 : col < 43 ? 2 : 3);
		uint8_t ink = 1;
		if((d > -160 && d < 160) || (e > -160 && e < 160)) ink = 2;
		if((d > -50 && d < 50) || (e > -50 && e < 50)) ink = 3;
		if((col >= 26 && col < 38) || (row >= 14 && row < 26)) ink = 2;
		if((col >= 29 && col < 35) || (row >= 17 && row < 23)) ink = 3;
		pixel(planes, offset, 200 + col, ink);
	}
}

static void labels(uint8_t *const planes[4], uint16_t offset, uint8_t row) {
	for(uint8_t item = 0; item < 2; ++item) {
		const uint8_t *text = item ? s_english : s_french;
		uint16_t x = item ? 211 : 50;
		for(uint8_t letter = 0; letter < (item ? 7 : 8); ++letter, x += 6) {
			uint8_t bits = s_glyphs[text[letter]][row];
			for(uint8_t col = 0; col < 5; ++col)
				if(bits & (16 >> col)) pixel(planes, offset, x + col, 2);
		}
	}
}

void languageSelectStep(tLanguageSelect *choice, uint8_t target,
	uint8_t *const planes[4], uint16_t stride) {
	if(choice->row[target] < 256) {
		for(uint8_t count = 0; count < 2; ++count) {
			uint16_t y = choice->row[target]++;
			uint16_t offset = y * stride;
			for(uint8_t p = 0; p < 4; ++p)
				for(uint8_t b = 0; b < 40; ++b) planes[p][offset + b] = 0;
			if(y >= 82 && y < 122) flags(planes, offset, y - 82);
			if(y >= 130 && y < 137) labels(planes, offset, y - 130);
			border(planes, offset, y, choice->selected);
		}
		if(choice->row[target] == 256) {
			choice->drawn[target] = choice->selected;
			choice->borderRow[target] = 72;
		}
		return;
	}
	if(languageSelectTargetReady(choice, target)) return;
	for(uint8_t count = 0; count < 8 && choice->borderRow[target] < 72; ++count) {
		uint16_t y = 74 + choice->borderRow[target]++;
		border(planes, y * stride, y, choice->selected);
	}
	choice->drawn[target] = choice->selected;
}
