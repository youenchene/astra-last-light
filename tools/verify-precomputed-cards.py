#!/usr/bin/env python3.12
"""Check complete native story windows against the independent host painter + art."""
import argparse
import importlib.util
from pathlib import Path
import re
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
KIT = Path(os.environ.get('AGK_KIT', str(Path.home()/'Code/amiga/amiga-game-kit')))
sys.path.insert(0, str(KIT/'harness'))
from agk.image import Image


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directories', nargs='+', type=Path)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('oracle', ROOT/'game/tests/unit/test_presentation_rows.py')
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    frames = []
    for line in (ROOT/'game/art/campaign_manga_compact.txt').read_text().splitlines():
        if line == 'frame':
            frames.append([])
        elif len(line) == 112 and set(line) <= set('.123456789ABCDEF'):
            frames[-1].append(['.123456789ABCDEF'.index(ch) for ch in line])
    assert len(frames) == 5 and all(len(frame) == 64 for frame in frames)
    colors = {int(index): int(value,16) for index,value in re.findall(
        r'^(\d+)\s+0x([0-9a-fA-F]{3})\b', (ROOT/'game/art/palette.txt').read_text(), re.M)}
    entries = re.findall(r'\{"[^"]+", "[^"]+", "[^"]+", (\d), (\d)\}',
                         (ROOT/'game/src/render_scenes.c').read_text())
    for folder in args.directories:
        count = 0
        for scene in range(13):
            pixels = oracle.reference_card(scene)
            panel = int(entries[scene][0])
            for y in range(64):
                pixels[72+y][176:288] = frames[panel][y]
            palette = dict(colors)
            palette[0] = (0x001, 0x102, 0x101, 0x001)[min(scene//3,3)]
            palette[4] = 0xbdf
            rgb = {ink: tuple((value >> shift & 15)*17 for shift in (8,4,0))
                   for ink,value in palette.items()}
            for suffix in ('', '_late'):
                path = folder/f'scene{scene:02}{suffix}.screen.png'
                image = Image.load_png(path)
                for y in range(56,192):
                    for x in range(152,312):
                        assert image.pixel(x,y) == rgb[pixels[y][x]], (path,x,y)
                        count += 1
        print(f'PASS {folder}: {count} exact native window pixels, all 13 cards twice')
