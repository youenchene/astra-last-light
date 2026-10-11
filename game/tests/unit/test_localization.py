"""Approved copy, byte encoding, runtime pixels and pre-selector label caches."""
import ctypes
import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from test_presentation_rows import ROOT, catalog, paint_text, source_fonts
from test_title_composition import function


class LocalizationTests(unittest.TestCase):
    def test_catalog_matches_every_approved_pair(self):
        proposal = (ROOT / 'docs/french-translation-proposal.md').read_text()
        approved = re.findall(r'^\| ([^|]+) \| ([^|]+) \|$', proposal, re.M)
        data = catalog()
        actual = {(en, fr) for fr, en in data['ui'].values()}
        actual.update((en, fr) for scene in data['scenes'] for en, fr in zip(scene['en'], scene['fr']))
        approved = {(en, fr) for en, fr in approved if en not in ('English', '---')}
        self.assertEqual(actual, approved)
        self.assertEqual(data['ui']['LAST_LIGHT'], ['LAST LIGHT', 'LAST LIGHT'])

    def test_encoding_is_one_byte_per_glyph_and_rejects_unknowns(self):
        spec = importlib.util.spec_from_file_location('localization', ROOT / 'game/tools/localization.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data = module.load_catalog()
        for messages in data['ui'].values():
            for message in messages:
                self.assertEqual(len(module.encode(message, data)), len(message))
                self.assertLess(len(module.encode(message, data)), 32)
        with self.assertRaisesRegex(ValueError, 'unsupported localization glyph'):
            module.encode('A☃B', data)
        self.assertTrue(set('ÀÂÇÉÈÊÎ’-.') <= data['glyphs'].keys())
        # Fit checks include the dynamic number cells, not just screen edges.
        for lang in range(2):
            for key, x, end in (('SECTOR', 266, 308), ('DAMAGE', 8, 50),
                                ('SPEED', 62, 98), ('SHIELD', 116, 158),
                                ('FIRE', 176, 206), ('HOLD', 224, 320),
                                ('RELEASE', 224, 320), ('READY', 8, 40)):
                self.assertLessEqual(x + len(data['ui'][key][lang]) * 6 - 1, end)
            for scene in (0, 3, 6, 9):
                name = data['scenes'][scene][('fr', 'en')[lang]][0]
                self.assertLess(8 + len(name) * 6 - 1, 126)

    def test_production_labels_and_two_glyph_steps_after_language_selection(self):
        source = (ROOT / 'game/src/render_world.c').read_text()
        regular = source_fonts()[1]
        prelude = r'''
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "../art/localization.h"
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
typedef struct { UBYTE *Planes[4]; UWORD BytesPerRow; UBYTE Depth; } tBitMap;
#define BMF_INTERLEAVED 1
static UBYTE screens[2][40960], labelPixels[2688];
static tBitMap screen, labels, font;
static tBitMap *s_pScreen=&screen, *s_pLabels, *s_pFont=&font;
static tLanguage selected=LANGUAGE_FR;
tLanguage languageGet(void) { return selected; }
void selectLanguage(unsigned value) { selected=value; }
static void blitWait(void) {}
static tBitMap *bitmapCreate(unsigned w,unsigned h,unsigned depth,unsigned flags) {
    if(w!=96 || h!=56 || depth!=4 || flags!=BMF_INTERLEAVED) abort();
    labels.BytesPerRow=48; labels.Depth=4;
    for(unsigned p=0;p<4;++p) labels.Planes[p]=labelPixels+p*12;
    return &labels;
}
'''
        prelude += 'static const UBYTE fontRows[36][7] = {' + ','.join(
            '{' + ','.join(map(str, rows)) + '}' for rows in regular) + '};\n'
        prelude += r'''
static UBYTE pixelRead(const tBitMap *bitmap,UWORD x,UWORD y) {
    (void)bitmap; return !!(fontRows[y/7][y%7] & (16>>x));
}
'''
        declarations = re.search(r'static ULONG s_pGlyphMasks[^;]+;', source)[0]
        declarations += re.search(r'static ULONG s_bossLabel[^;]+;', source)[0]
        functions = '\n'.join(function(source, name) for name in (
            'fontMasksCreate', 'labelsCreate', 'textDraw', 'renderWorldTextStep'))
        wrapper = r'''
void create(void) { fontMasksCreate(); if(!labelsCreate()) abort(); }
void labelPixelsFor(unsigned label,UBYTE *out) {
    unsigned y0=selected*28+label*7;
    for(unsigned y=0;y<7;++y) for(unsigned x=0;x<96;++x) {
        unsigned ink=0;
        for(unsigned p=0;p<4;++p)
            if(s_pLabels->Planes[p][(y0+y)*48+x/8] & (128>>(x&7))) ink|=1<<p;
        out[y*96+x]=ink;
    }
}
unsigned drawStep(unsigned buffer,unsigned id,unsigned cursor,UBYTE *out) {
    for(unsigned p=0;p<4;++p) screen.Planes[p]=screens[buffer]+p*40;
    if(!cursor) memset(screens[buffer],0,sizeof(screens[buffer]));
    unsigned short position=cursor;
    renderWorldTextStep(5,40,localizedText(id),1,6,&position);
    for(unsigned y=0;y<256;++y) for(unsigned x=0;x<320;++x) {
        unsigned ink=0;
        for(unsigned p=0;p<4;++p)
            if(screen.Planes[p][y*160+x/8] & (128>>(x&7))) ink|=1<<p;
        out[y*320+x]=ink;
    }
    return position;
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'local.c').write_text(prelude + declarations + functions + wrapper)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC',
                            '-I', str(ROOT / 'game/src'), str(path / 'local.c'), '-o', str(path / 'local.so')], check=True)
            lib = ctypes.CDLL(str(path / 'local.so'))
            lib.create()  # French default, BEFORE the later English choice.
            data = catalog()
            for language in (1, 0, 1):
                lib.selectLanguage(language)
                for label, key in enumerate(('LANCE', 'READY', 'HOLD', 'RELEASE')):
                    out = (ctypes.c_ubyte * (96 * 7))()
                    lib.labelPixelsFor(label, out)
                    expected = [[1 if label < 2 else 0] * 96 for _ in range(7)]
                    paint_text(expected, data['ui'][key][language], 0, 0, (4, 7, 4, 14)[label], regular, 5)
                    self.assertEqual(list(out), [p for row in expected for p in row], (language, key))
                for index, pair in enumerate(data['ui'].values()):
                    message = pair[language]
                    cursors = [0, 0]
                    for _ in range((len(message) + 1) // 2):
                        for buffer in (0, 1):
                            out = (ctypes.c_ubyte * (320 * 256))()
                            end = lib.drawStep(buffer, index, cursors[buffer], out)
                            self.assertEqual(end, min(cursors[buffer] + 2, len(message)))
                            cursors[buffer] = end
                            expected = [[0] * 320 for _ in range(256)]
                            paint_text(expected, message[:end], 5, 40, 6, regular, 5)
                            self.assertEqual(list(out), [p for row in expected for p in row])


if __name__ == '__main__':
    unittest.main()
