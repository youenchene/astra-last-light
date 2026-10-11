#!/usr/bin/env python3.12
"""Source-font checks for the production French replay and initial English HUD."""
import argparse
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'game/tests/unit'))
from test_presentation_rows import catalog, paint_text, reference_hud, source_fonts


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sector = load('sector_pixels', 'verify-sector-presentation.py')
cards = load('card_pixels', 'verify-precomputed-cards.py')


def region(path, expected, colors, x0, y0, width, height):
    image = sector.screen(path)
    for y in range(y0, y0 + height):
        for x in range(x0, x0 + width):
            assert image.pixel(x, y) == colors[expected[y][x]], (path, x, y)
    return width * height


def initial_hud(path, language):
    expected = reference_hud(0, language)
    font = source_fonts()[1]
    for x, y, text in ((162, 6, '00000000'), (254, 6, '3'), (308, 6, '1'),
                       (50, 249, '0'), (98, 249, '0'), (158, 249, '0'), (206, 249, '1')):
        paint_text(expected, text, x, y, 6, font, 5)
    for y in range(19, 23):
        expected[y][44:144] = [2] * 100
    colors = sector.palette()
    colors[0], colors[4] = sector.rgb(0x001), sector.rgb(0xbdf)
    return sum(region(path, expected, colors, 0, y, 320, height)
               for y, height in ((0, 29), (245, 11)))


def french(folder):
    data, font = catalog(), source_fonts()[1]
    count = initial_hud(folder / 'fr_hud.screen.png', 'fr')
    for level in range(4):
        colors = sector.palette()
        colors[0] = sector.rgb(sector.SPACE[level])
        expected = [[0] * 320 for _ in range(256)]
        expected[190:197] = [[1] * 320 for _ in range(7)]
        prompt = data['ui']['DEFEND'][0]
        paint_text(expected, prompt, (321 - len(prompt) * 6) // 2, 190, 7, font, 5)
        caption = data['scenes'][level * 3]['fr'][0]
        paint_text(expected, caption, (321 - len(caption) * 6) // 2, 224, 5, font, 5)
        path = folder / f'fr_title{level + 1}.screen.png'
        count += region(path, expected, colors, 24, 190, 272, 7)
        count += region(path, expected, colors, 0, 224, 320, 8)
    colors = sector.palette()
    colors[0], colors[4] = sector.rgb(0x001), sector.rgb(0xbdf)
    for capture, label, ink in (('fr_ready', 'READY', 7), ('fr_pause', 'PAUSE', 14)):
        expected = reference_hud(1, 'fr')
        for y in range(18, 25):
            expected[y][8:40] = [1] * 32
        paint_text(expected, data['ui'][label][0], 8, 18, ink, font, 5)
        path = folder / f'{capture}.screen.png'
        count += region(path, expected, colors, 8, 18, 32, 7)
        count += region(path, expected, colors, 224, 249, 96, 7)
    count += cards.check_scene(folder / 'fr_ending.screen.png', 12, 'fr')
    count += cards.check_scene(folder / 'fr_opening.screen.png', 0, 'fr')
    print(f'PASS {folder}: {count} source-derived French UI/story pixels')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--french', nargs='+', type=Path, required=True)
    parser.add_argument('--english-hud', nargs='+', type=Path, required=True)
    args = parser.parse_args()
    for folder in args.french:
        french(folder)
    for path in args.english_hud:
        print(f'PASS {path}: {initial_hud(path, "en")} English HUD pixels')
    for folder in args.french[1:]:
        captures = sorted(args.french[0].glob('*.screen.png'))
        assert len(captures) == 13
        for path in captures:
            assert path.read_bytes() == (folder / path.name).read_bytes(), path.name
        print('PASS 13 complete French captures byte-identical across profiles')


if __name__ == '__main__':
    main()
