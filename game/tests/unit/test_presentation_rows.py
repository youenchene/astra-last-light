"""Independent pixel oracle for the compiled production row decoder.

The reference uses the former rectangle/glyph painter, with standard-library
word wrapping. It never imports the generator or reads its packed tables.
Every byte outside the requested rows must retain its sentinel, on each step.
"""
import ast
import json
import ctypes
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from selected_rd_oracle import original_panels


def catalog():
    return json.loads((ROOT / 'game/art/localization.json').read_text(encoding='utf-8'))


def source_fonts():
    source = (ROOT / 'game/src/scene_font.h').read_text()
    small = ast.literal_eval(source[source.index('=') + 1:source.index(';')]
                             .replace('{', '[').replace('}', ']'))
    regular, current = [], None
    for line in (ROOT / 'game/art/font.txt').read_text().splitlines():
        if line == 'frame':
            current = []
            regular.append(current)
        elif current is not None and len(line) == 5 and set(line) <= {'.', 'X'}:
            current.append(sum(1 << (4 - x) for x, ch in enumerate(line) if ch == 'X'))
    return small, regular


def paint_text(image, message, x, y, color, font, width):
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    for column, letter in enumerate(message):
        # Production textDraw folds ASCII lowercase before indexing the atlas.
        if 'a' <= letter <= 'z':
            letter = chr(ord(letter) - 32)
        if letter == ' ':
            continue
        glyph = (font[alphabet.index(letter)] if letter in alphabet else
                 catalog()['glyphs'][letter]['regular' if width == 5 else 'small'])
        for row, bits in enumerate(glyph):
            for bit in range(width):
                if bits >> (width - bit - 1) & 1:
                    image[y + row][x + column * (width + 1) + bit] = color


def reference_card(index, language='en'):
    entry = catalog()['scenes'][index]
    title, caption, reply = entry[language]
    accent = (5, 11, 7, 14)[entry['style']]
    if index == 12:
        image = [[0] * 320 for _ in range(256)]
        _, font = source_fonts()
        prompt = catalog()['ui']['RESTART'][language == 'en']
        paint_text(image, title, (321 - len(title) * 6) // 2, 12, 14, font, 5)
        paint_text(image, prompt, (321 - len(prompt) * 6) // 2, 237, 6, font, 5)
        return image
    image = [[accent if 142 <= x < 306 and 66 <= y < 166 else 0
              for x in range(320)] for y in range(256)]
    font, _ = source_fonts()
    messages = [(caption, 168, 6), (reply, 186, 14)]
    if index not in (0, 3, 6, 9):
        messages.insert(0, (title, 59, accent))
    for message, y, color in messages:
        for row, line in enumerate(textwrap.wrap(message, 28)):
            paint_text(image, line, 144, y + row * 8, color, font, 4)
    return image


def reference_hud(variant, language='en'):
    data = catalog()
    names = [data['scenes'][i][language][0] for i in (0, 3, 6, 9)]
    ui = {key: pair[language == 'en'] for key, pair in data['ui'].items()}
    image = [[15 if y == 28 else 3 if y == 245 else 1 if y < 28 else 0
              for _ in range(320)] for y in range(256)]
    _, font = source_fonts()
    ready = variant % 2
    labels = [(names[variant // 2], 8, 6, 5), (ui['SCORE'], 126, 6, 5), (ui['LIVES'], 218, 6, 5),
              (ui['SECTOR'], 266, 6, 5), (ui['READY' if ready else 'LANCE'], 8, 18, 7 if ready else 4),
              (ui['DAMAGE'], 8, 249, 4), (ui['SPEED'], 62, 249, 4),
              (ui['SHIELD'], 116, 249, 4), (ui['FIRE'], 176, 249, 4),
              (ui['RELEASE' if ready else 'HOLD'], 224, 249, 14 if ready else 4)]
    for message, x, y, color in labels:
        paint_text(image, message, x, y, color, font, 5)
    return image


class PresentationRowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        library = Path(cls.temp.name) / 'rows.so'
        wrapper = Path(cls.temp.name) / 'rows.c'
        wrapper.write_text('#include "' + str(ROOT / 'game/src/presentation_rows.c') + '"\n' + r'''
static tLanguage selected;
tLanguage languageGet(void) { return selected; }
void selectLanguage(unsigned language) { selected = language; }
unsigned testOperations(unsigned card, unsigned id, unsigned first, unsigned end) {
    if(card != 2) id += selected * (card ? 13 : 8);
    unsigned operations = 0;
    for(unsigned row = first; row < end; ++row) {
        unsigned rowId = card == 2 ? s_mangaRows[s_mangaLayouts[id].first + row] :
             card ? s_cardRows[s_cardLayouts[id].first + row] : s_hudRows[id * 40 + row];
        if(rowId >= sizeof(s_presentationCosts)) return 9999;
        unsigned declared = s_presentationCosts[rowId], actual = 0;
        for(unsigned plane = 0; plane < 4; ++plane) {
            const unsigned char *p = s_presentationBytes + s_presentationPlanes[rowId][plane];
            const unsigned char *end = s_presentationBytes + sizeof(s_presentationBytes);
            unsigned remaining = card == 2 ? s_mangaLayouts[id].span :
                card ? s_cardLayouts[id].span : 40;
            while(remaining) {
                if(p >= end) return 9999;
                unsigned token = *p++;
                if(!token && p >= end) return 9999;
                unsigned count = token ? token & 63 : *p++;
                if(!count || count > remaining) return 9999;
                remaining -= count;
                if(token) p += (token & 192) == 192 ? (count + 1) / 2 :
                    token & 128 ? count : token & 64 ? 2 : 1;
                if(p > end) return 9999;
                ++actual;
            }
        }
        if(actual != declared) return 9999;
        operations += actual;
    }
    return operations;
}
''')
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC',
                        str(wrapper), '-o', str(library)], check=True)
        cls.lib = ctypes.CDLL(str(library))
        for name in ('presentationCardStep', 'presentationHudStep', 'presentationMangaStep'):
            function = getattr(cls.lib, name)
            function.argtypes = [ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
                                 ctypes.c_ushort, ctypes.c_ubyte, ctypes.c_ushort]
            function.restype = ctypes.c_ushort

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check_layer(self, function, variant, image, x0, width, ys, rows_per_step, kind):
        memory = (ctypes.c_ubyte * (40960 + 32))(*([0xa5] * (40960 + 32)))
        planes = (ctypes.POINTER(ctypes.c_ubyte) * 4)(*[
            ctypes.cast(ctypes.byref(memory, 16 + plane * 40), ctypes.POINTER(ctypes.c_ubyte))
            for plane in range(4)])
        expected = bytearray(memory)
        row = 0
        while row < len(ys):
            end = function(planes, 160, variant, row)
            self.assertGreater(end, row)
            self.assertLessEqual(end, min(row + rows_per_step, len(ys)))
            self.assertLessEqual(self.lib.testOperations(kind, variant, row, end), 64)
            self.assertLessEqual((end - row) * width // 2, 320)
            for y in ys[row:end]:
                for x in range(x0, x0 + width):
                    for plane in range(4):
                        address = 16 + y * 160 + plane * 40 + x // 8
                        mask = 128 >> (x % 8)
                        expected[address] &= ~mask
                        if image[y][x] & (1 << plane):
                            expected[address] |= mask
            self.assertEqual(bytes(memory), expected, f'variant {variant}, rows {row}:{end}')
            row = end
        self.assertEqual(function(planes, 160, variant, row), row)
        self.assertEqual(bytes(memory), expected)

    def test_all_thirteen_cards_exact_pixels_and_write_bounds(self):
        for language in ('fr', 'en'):
            self.lib.selectLanguage(language == 'en')
            for scene in range(13):
                with self.subTest(language=language, scene=scene):
                    ending = scene == 12
                    self.check_layer(self.lib.presentationCardStep, scene, reference_card(scene, language),
                                     0 if ending else 136, 320 if ending else 176,
                                     list(range(32)) + list(range(224, 256)) if ending else list(range(56, 208)),
                                     2 if ending else 3, 1)

    def test_shared_hud_all_sectors_and_charge_labels(self):
        for language in ('fr', 'en'):
            self.lib.selectLanguage(language == 'en')
            for variant in range(8):
                with self.subTest(language=language, variant=variant):
                    self.check_layer(self.lib.presentationHudStep, variant, reference_hud(variant, language),
                                     0, 320, list(range(29)) + list(range(245, 256)), 2, 0)

    def test_generator_is_current(self):
        subprocess.run([sys.executable, str(ROOT / 'tools/make-presentation.py'), '--check'], check=True)

    def test_enlarged_panels_and_all_narrative_fit(self):
        master = (ROOT / 'game/art/campaign_manga.txt').read_text().split('\nframe\n')[1:]
        compact = (ROOT / 'game/art/campaign_manga_compact.txt').read_text().split('\nframe\n')[1:]
        self.assertEqual(len(compact), 5)
        for original, derivative in zip(master, compact):
            source, rows = original.strip().splitlines(), derivative.strip().splitlines()
            self.assertEqual(len(rows), 64)
            for y, row in enumerate(rows):
                self.assertEqual(len(row), 112)
                self.assertEqual(row, ''.join(source[y * 3 // 2][x * 10 // 7] for x in range(112)))
        entries = catalog()['scenes']
        self.assertEqual(len(entries), 13)
        self.assertEqual([entry['en'][0] for i, entry in enumerate(entries) if i not in (0, 3, 6, 9)],
                         ['SALVAGE CLAW', 'WRECK FIELD FREED', 'THE MANTA WAKES', 'VEIL PIERCED',
                          'FURNACE CARRIER', 'FURNACES SILENCED', 'REACTOR CROWN',
                          'THE CROWN FALLS', 'DAWN RESTORED'])
        for language in ('fr', 'en'):
            for entry in entries[:12]:
                title, caption, reply = entry[language]
                for message, y, bottom in ((title, 59, 66), (caption, 168, 184), (reply, 186, 208)):
                    lines = textwrap.wrap(message, 28)
                    self.assertEqual(' '.join(lines), message)
                    self.assertLessEqual(y + (len(lines) - 1) * 8 + 6, bottom)
                    self.assertTrue(all(144 + len(line) * 5 - 1 < 312 for line in lines))

    def test_selected_png_pixels_all_thirteen_mappings(self):
        entries = catalog()['scenes']
        self.assertEqual([e['panel'] for e in entries], [0]*3 + [1]*3 + [2]*3 + [3]*3 + [4])
        for scene, entry in enumerate(entries):
            panel = entry['panel']
            self.assertEqual(self.lib.presentationScenePanel(scene), panel)
            image = [[0]*320 for _ in range(256)]
            x0, y0 = (0, 32) if panel == 4 else (144, 68)
            for y, row in enumerate(original_panels()[panel]):
                image[y0+y][x0:x0+len(row)] = row
            with self.subTest(scene=scene):
                self.check_layer(self.lib.presentationMangaStep, panel, image,
                                 0 if panel == 4 else 144, 320 if panel == 4 else 160,
                                 list(range(y0, y0 + (192 if panel == 4 else 96))),
                                 2 if panel == 4 else 4, 2)

    def test_invalid_panel_and_finished_cursor_do_not_write(self):
        memory = (ctypes.c_ubyte * 40960)(*([0xa5]*40960))
        planes = (ctypes.POINTER(ctypes.c_ubyte) * 4)(*[
            ctypes.cast(ctypes.byref(memory, plane*40), ctypes.POINTER(ctypes.c_ubyte))
            for plane in range(4)])
        for panel, row in ((5,0), (255,0), (0,96), (4,192), (0,65535)):
            self.assertEqual(self.lib.presentationMangaStep(planes,160,panel,row),row)
            self.assertEqual(bytes(memory), bytes([0xa5])*40960)

    def test_ending_border_is_two_white_pixels_inside_image(self):
        image = [[0]*320 for _ in range(256)]
        for y, row in enumerate(original_panels()[4]):
            image[y+32] = row
        self.assertTrue(all(image[y][x] == 7
                            for y in range(32, 224) for x in range(320)
                            if x < 2 or x >= 318 or y < 34 or y >= 222))
        self.assertTrue(all(ink == 0 for row in image[:32] + image[224:] for ink in row))
        self.check_layer(self.lib.presentationMangaStep, 4, image,
                         0, 320, list(range(32, 224)), 2, 2)

    def test_mixed_case_sector_caption_preserves_lowercase_letters(self):
        # The second character is lowercase 'r' in the authored stage name.
        # Original textDraw produces this full uppercase R, not a blank cell.
        image = reference_hud(0)
        expected = ['11110', '10001', '10001', '11110', '10100', '10010', '10001']
        self.assertEqual([''.join('1' if image[6+y][14+x] == 5 else '0'
                                 for x in range(5)) for y in range(7)], expected)


if __name__ == '__main__':
    unittest.main()
