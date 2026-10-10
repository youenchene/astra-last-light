"""Execute the production composition functions with bounded host drawing spies."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


def function(source, name):
    start = re.search(r"^(?:static )?(?:void|UBYTE) " + name +
                      r"\([^;{}]*\)\s*\{", source, re.M).start()
    brace = source.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


class TitleCompositionTests(unittest.TestCase):
    def test_extractor_skips_forward_declaration(self):
        source = ("static UBYTE combatBackground(tPhase phase);\n"
                  "static UBYTE sceneryBackground(tPhase phase) { return 0; }\n"
                  "static UBYTE combatBackground(tPhase phase) { return 1; }")
        self.assertEqual(function(source, "combatBackground"),
                         "static UBYTE combatBackground(tPhase phase) { return 1; }")

    def test_physical_provenance_and_bounded_repair(self):
        source = (ROOT / "game/src/render_world.c").read_text()
        source = source.replace('__attribute__((noinline)) ', '')
        declarations = source[source.index("static UBYTE s_ubLevel"):source.index("/* All display writes")]
        functions = "\n".join(function(source, name) for name in (
            "numberText", "queueText", "queueRect", "queueCentered", "panelQueue", "combatBackground",
            "renderWorldBind", "renderWorldInvalidate", "renderWorldBegin", "renderWorldStep"))
        prelude = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "logic.h"
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
typedef struct {
    unsigned char pixels[256][320], *Planes[4];
    UWORD BytesPerRow;
} tBitMap;
typedef struct { UWORD pPalette[32]; } tVPort;
#define STAR_COUNT 36
#define DECOR_HEIGHT 24
#define DECOR_TOP 29
#define DECOR_BOTTOM 220
static tBitMap bitmaps[2], *s_buffers[2] = {bitmaps, bitmaps + 1}, *s_pScreen;
static tVPort viewport, *s_pVPort = &viewport;
static unsigned rows, glyphs, outside, clearing, scenery, hud;
static void blitWait(void) {}
static UBYTE titleIconStep(UWORD x,UWORD y,UBYTE right,UWORD *cursor) {
    (void)x;(void)y;(void)right;
    rows += 3; *cursor += 3; return *cursor == 9;
}
static void blitRect(tBitMap *b, UWORD x, UWORD y, UWORD w, UWORD h, UBYTE color) {
    rows += h;
    if(x == 0 && w == 320 && y != 224) ++clearing;
    for(unsigned yy = y; yy < y + h; ++yy)
        for(unsigned xx = x; xx < x + w; ++xx) {
            if(!((xx >= 96 && xx < 224 && yy >= 26 && yy < 122) ||
                 (yy >= 224 && yy < 232))) ++outside;
            b->pixels[yy][xx] = color;
        }
}
static void starsReset(void) {}
static UWORD galaxyStep(unsigned char *const planes[4], UWORD stride,
    UBYTE level, UWORD x, UWORD y, UWORD width, UWORD height, UWORD row, UBYTE cleared) {
    (void)planes;(void)stride;(void)level;(void)x;(void)y;(void)width;(void)height;
    (void)cleared; assert(!"TITLE must never decode a galaxy"); return row;
}
static void starToggle(UBYTE i, UWORD x) {(void)i; (void)x; ++scenery;}
static void decorRows(UWORD a,UWORD b,UWORD c,UWORD d,UWORD e) {
    (void)a;(void)b;(void)c;(void)d;(void)e; ++scenery;
}
static UWORD presentationHudStep(unsigned char *const planes[4], UWORD stride,
                                UBYTE variant, UWORD row) {
    (void)planes;(void)stride;(void)variant; ++hud; return row + 4;
}
static UBYTE renderWorldTextStep(UWORD x,UWORD y,const char *text,
                               UBYTE scale,UBYTE color,UWORD *cursor) {
    (void)x;(void)y;(void)scale;(void)color;
    for(unsigned i=0; i<2 && text[*cursor]; ++i) {++*cursor; ++glyphs;}
    return !text[*cursor];
}
static void queueNumber(UWORD x,UWORD y,ULONG value,UBYTE digits) {
    (void)x;(void)y;(void)value;(void)digits;
}
'''
        plate = r'''
static void titleRows(UWORD row) {
    blitRect(s_pScreen,96,26+row,128,8,s_ubLevel+2);
}
'''
        exercise = r'''
static unsigned complete(void) {
    unsigned ticks = 0;
    while(s_preparing) {
        rows = glyphs = 0;
        renderWorldStep();
        assert(rows <= 8 && glyphs <= 2 && !(rows && glyphs));
        assert(++ticks < 200);
    }
    return ticks;
}
int main(void) {
    tGameState state = {0};
    state.phase = TITLE;
    renderWorldBind(bitmaps);
    renderWorldBegin(&state);
    assert(complete() > 60);
    /* One complete physical title must not confer provenance on the cold one. */
    renderWorldBind(bitmaps+1);
    state.level = 1;
    renderWorldBegin(&state);
    assert(s_history[1].stage == 0 && s_history[0].stage == 1);
    assert(complete() > 60);
    renderWorldBind(bitmaps);
    outside = clearing = 0;
    assert(complete() < 30 && !outside && !clearing);
    for(unsigned level=0; level<4; ++level) {
        state.level = level;
        renderWorldBegin(&state);
        /* Retap during plate repair; provenance survives incomplete content. */
        rows = glyphs = 0;
        renderWorldStep();
        state.level = (level+1)&3;
        renderWorldBegin(&state);
        outside = clearing = 0;
        assert(complete() < 30 && !outside && !clearing);
        renderWorldBind(s_buffers[!s_buffer]);
        assert(complete() < 30 && !outside && !clearing);
    }
    /* Starting gameplay destroys title provenance even before it is finished. */
    state.phase = SECTOR_INTRO;
    renderWorldBegin(&state);
    assert(!s_titleStable[0] && !s_titleStable[1]);
    state.phase = TITLE;
    renderWorldBegin(&state);
    assert(s_history[0].stage == 0 && s_history[1].stage == 0);
    complete();
    renderWorldInvalidate(1);
    assert(!s_titleStable[0] && !s_titleStable[1]);
    state.phase = GAMEOVER;
    renderWorldBegin(&state);
    complete();
    state.phase = TITLE;
    renderWorldBegin(&state);
    assert(complete() > 60);
    /* WIN must clear both dirty physical bitmaps without visiting any world
     * painter. A TITLE restart must rebuild rather than reuse stale provenance. */
    memset(bitmaps[0].pixels, 15, sizeof(bitmaps[0].pixels));
    memset(bitmaps[1].pixels, 7, sizeof(bitmaps[1].pixels));
    state.phase = WIN; state.level = 3;
    renderWorldInvalidate(0);
    renderWorldBegin(&state);
    scenery = hud = 0;
    assert(s_commandCount == 0 && viewport.pPalette[0] == 0);
    for(unsigned buffer = 0; buffer < 2; ++buffer) {
        renderWorldBind(bitmaps + buffer);
        assert(complete() == 32);
        assert(!scenery && !hud && !glyphs);
        for(unsigned y = 0; y < 256; ++y)
            for(unsigned x = 0; x < 320; ++x) assert(!bitmaps[buffer].pixels[y][x]);
    }
    assert(!sceneryBackground(WIN) && sceneryBackground(CLEAR) && sceneryBackground(BOSS_DYING));
    state.phase = TITLE;
    renderWorldBegin(&state);
    assert(complete() > 60 && viewport.pPalette[0] == 0x001);
    puts("PASS cold/repair/retap/fire/invalidation/GAMEOVER; 8 rows or 2 glyphs");
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / "title.c").write_text(prelude + declarations + plate + functions + exercise)
            subprocess.run(["cc", "-std=c11", "-I", str(ROOT / "game/src"),
                            str(path / "title.c"), str(ROOT / "game/src/logic.c"),
                            "-o", str(path / "title")], check=True)
            subprocess.run([str(path / "title")], check=True)


if __name__ == "__main__":
    unittest.main()
