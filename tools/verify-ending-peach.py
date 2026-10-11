#!/usr/bin/env python3.12
"""Check production WIN pixels, explicit skin/sky colors and exit restoration."""
import argparse
import importlib.util
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cards', ROOT / 'tools/verify-precomputed-cards.py')
cards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cards)


def check(folder):
    source = cards.Image.load_png(
        ROOT / 'game/art/selected-rd/victory-identity-master/victory.png')
    skin = [(x, y) for y in range(88, 104) for x in range(80, 115)
            if source.pixel(x, y) == (252, 169, 139)]
    assert len(skin) == 498
    candidate = cards.Image.load_png(
        ROOT / 'game/art/selected-rd/victory-eyes-almond/victory.png')
    current_skin = {(x, y) for y in range(88, 104) for x in range(80, 115)
                    if candidate.pixel(x, y) == (252, 169, 139)}
    additions = {(80, 88), (80, 89), (81, 88), (82, 88),
                 (83, 88), (113, 88), (114, 88)}
    assert set(skin) <= current_skin, 'Original 498 peach pixels must survive'
    assert current_skin - set(skin) == additions, 'Only seven approved skin-fill additions'
    count = 0
    for state in ('ready', 'held', 'released'):
        path = folder / f'ending_preview_{state}.screen.png'
        count += cards.check_scene(path, 12)
        image = cards.Image.load_png(path)
        for x, y in skin:
            assert image.pixel(x, y + 32) == (255, 170, 153), (path, x, y)
        for x, y in additions:
            assert image.pixel(x, y + 32) == (255, 170, 153), (path, x, y)
        for y in range(4, 20):
            for x in range(4, 20):
                assert image.pixel(x, y + 32) == (255, 170, 102), (path, x, y)
    for state in ('restarted', 'ignored'):
        count += cards.check_scene(folder / f'ending_preview_{state}.screen.png', 0)
    before = cards.Image.load_png(folder / 'ending_preview_initial_title.screen.png')
    after = cards.Image.load_png(folder / 'ending_preview_returned_title.screen.png')
    for y in range(256):
        for x in range(320):
            assert before.pixel(x, y) == after.pixel(x, y), ('title restoration', x, y)
    print(f'PASS {folder}: {count} source pixels; original 498 peach skin + 7 approved additions + 256 orange sky '
          'pixels in each of 3 WIN captures; ordinary scene and all 81920 title pixels restored')
    serial = (folder / 'serial.txt').read_text()
    windows = re.findall(r'AGK perf frames=(\d+) dropped=(\d+) load=(\d+) maxload=(\d+)', serial)
    assert windows, 'missing performance telemetry'
    print(f'{len(windows)} performance windows: drops={sum(int(w[1]) for w in windows)}, '
          f'load={min(int(w[2]) for w in windows)}..{max(int(w[2]) for w in windows)}%, '
          f'peak={max(int(w[3]) for w in windows)}%')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directories', nargs='+', type=Path)
    directories = parser.parse_args().directories
    for directory in directories:
        check(directory)
    for directory in directories[1:]:
        paths = sorted(directories[0].glob('*.screen.png'))
        assert len(paths) == 7
        for path in paths:
            assert path.read_bytes() == (directory / path.name).read_bytes(), path.name
        print(f'PASS all 7 complete captures byte-identical: {directories[0]} / {directory}')
