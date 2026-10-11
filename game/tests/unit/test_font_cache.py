"""Verify compact cached rows against independent source glyphs at every scale."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT, function
from test_presentation_rows import source_fonts, catalog


class FontCacheTests(unittest.TestCase):
    def test_all_glyphs_scales_and_unaligned_write_bounds(self):
        source = (ROOT / 'game/src/render_world.c').read_text()
        declaration = re.search(r'static ULONG s_pGlyphMasks[^;]+;', source)[0]
        _, glyphs = source_fonts()
        glyphs += [glyph['regular'] for glyph in catalog()['glyphs'].values()]
        prelude = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "../art/localization.h"
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
typedef struct { UBYTE *Planes[4]; } tBitMap;
static UBYTE pixels[40960];
static tBitMap bitmap, *s_pScreen = &bitmap, *s_pFont;
static void blitWait(void) {}
'''
        prelude += 'static const UBYTE glyphs[LOCALIZATION_GLYPHS][7] = {' + ','.join(
            '{' + ','.join(map(str, row)) + '}' for row in glyphs) + '};\n'
        prelude += r'''
static UBYTE pixelRead(const tBitMap *b, UWORD x, UWORD y) {
    (void)b; return (glyphs[y / 7][y % 7] >> (4 - x)) & 1;
}
'''
        exercise = r'''
int main(void) {
    assert(sizeof(s_pGlyphMasks) == 3 * LOCALIZATION_GLYPHS * 7 * 4);
    fontMasksCreate();
    for(unsigned plane = 0; plane < 4; ++plane) bitmap.Planes[plane] = pixels + plane * 40;
    for(unsigned glyph = 0; glyph < LOCALIZATION_GLYPHS; ++glyph) for(unsigned scale = 1; scale <= 4; scale *= 2) {
        memset(pixels, 0xa5, sizeof(pixels));
        unsigned char code = glyph < 26 ? 'A' + glyph : '0' + glyph - 26;
        if(glyph >= 36) for(unsigned b=1; b<256; ++b)
            if(localizedGlyph(b) == glyph) { code=b; break; }
        char text[2] = {(char)code, 0};
        textDraw(5, 40, text, scale, 6);
        for(unsigned y = 0; y < 256; ++y) for(unsigned x = 0; x < 320; ++x) {
            unsigned ink = (0xa5 & (128 >> (x & 7))) ? 15 : 0;
            if(x >= 5 && x < 5 + 5 * scale && y >= 40 && y < 40 + 7 * scale &&
               (glyphs[glyph][(y - 40) / scale] & (1 << (4 - (x - 5) / scale)))) ink = 6;
            for(unsigned plane = 0; plane < 4; ++plane)
                assert(!!(bitmap.Planes[plane][y * 160 + x / 8] & (128 >> (x & 7))) == !!(ink & (1 << plane)));
        }
    }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'font.c').write_text(prelude + declaration + '\n' +
                function(source, 'fontMasksCreate') + '\n' + function(source, 'textDraw') + exercise)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-I', str(ROOT / 'game/src'),
                            str(path / 'font.c'), '-o', str(path / 'font')], check=True)
            subprocess.run([str(path / 'font')], check=True)
