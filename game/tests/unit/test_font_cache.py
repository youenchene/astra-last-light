"""Verify compact cached rows against independent source glyphs at every scale."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT, function
from test_presentation_rows import source_fonts


class FontCacheTests(unittest.TestCase):
    def test_all_glyphs_scales_and_unaligned_write_bounds(self):
        source = (ROOT / 'game/src/render_world.c').read_text()
        declaration = re.search(r'static ULONG s_pGlyphMasks[^;]+;', source)[0]
        _, glyphs = source_fonts()
        prelude = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
typedef struct { UBYTE *Planes[4]; } tBitMap;
static UBYTE pixels[40960];
static tBitMap bitmap, *s_pScreen = &bitmap, *s_pFont;
static void blitWait(void) {}
'''
        prelude += 'static const UBYTE glyphs[36][7] = {' + ','.join(
            '{' + ','.join(map(str, row)) + '}' for row in glyphs) + '};\n'
        prelude += r'''
static UBYTE pixelRead(const tBitMap *b, UWORD x, UWORD y) {
    (void)b; return (glyphs[y / 7][y % 7] >> (4 - x)) & 1;
}
'''
        exercise = r'''
int main(void) {
    assert(sizeof(s_pGlyphMasks) == 3024);
    fontMasksCreate();
    for(unsigned plane = 0; plane < 4; ++plane) bitmap.Planes[plane] = pixels + plane * 40;
    for(unsigned glyph = 0; glyph < 36; ++glyph) for(unsigned scale = 1; scale <= 4; scale *= 2) {
      for(unsigned left = 0; left < 8; ++left) for(unsigned color = 0; color < 16; ++color) {
        if(glyph && color != 6) continue;
        memset(pixels, 0xa5, sizeof(pixels));
        char text[2] = {glyph < 26 ? 'A' + glyph : '0' + glyph - 26, 0};
        textDraw(left, 40, text, scale, color);
        for(unsigned y = 0; y < 256; ++y) for(unsigned x = 0; x < 320; ++x) {
            unsigned ink = (0xa5 & (128 >> (x & 7))) ? 15 : 0;
            if(x >= left && x < left + 5 * scale && y >= 40 && y < 40 + 7 * scale &&
               (glyphs[glyph][(y - 40) / scale] & (1 << (4 - (x - left) / scale)))) ink = color;
            for(unsigned plane = 0; plane < 4; ++plane)
                assert(!!(bitmap.Planes[plane][y * 160 + x / 8] & (128 >> (x & 7))) == !!(ink & (1 << plane)));
        }
      }
    }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'font.c').write_text(prelude + declaration + '\n' +
                function(source, 'fontMasksCreate') + '\n' + function(source, 'textDraw') + exercise)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(path / 'font.c'), '-o', str(path / 'font')], check=True)
            subprocess.run([str(path / 'font')], check=True)
