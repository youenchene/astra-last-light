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


def check_scene(path, scene, language='en'):
    spec = importlib.util.spec_from_file_location('oracle', ROOT/'game/tests/unit/test_presentation_rows.py')
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    from selected_rd_oracle import original_panels
    pixels = oracle.reference_card(scene, language)
    panel = 4 if scene == 12 else scene // 3
    x0, y0 = (0, 32) if scene == 12 else (144, 68)
    for y, row in enumerate(original_panels()[panel]):
        pixels[y0+y][x0:x0+len(row)] = row
    palette = {int(index): int(value,16) for index,value in re.findall(
        r'^(\d+)\s+0x([0-9a-fA-F]{3})\b', (ROOT/'game/art/palette.txt').read_text(), re.M)}
    palette[0] = 0 if scene == 12 else (0x001, 0x102, 0x101, 0x001)[scene//3]
    palette[4] = 0xbdf
    if scene == 12:
        palette[11] = 0xfa9
    rgb = {ink: tuple((value >> shift & 15)*17 for shift in (8,4,0))
           for ink,value in palette.items()}
    image = Image.load_png(path)
    assert (image.width, image.height) == (320, 256), path
    count = 0
    for y in (range(256) if scene == 12 else range(56,208)):
        for x in (range(320) if scene == 12 else range(136,312)):
            assert image.pixel(x,y) == rgb[pixels[y][x]], (path,x,y)
            count += 1
    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directories', nargs='+', type=Path)
    parser.add_argument('--scene', type=int, choices=range(13))
    parser.add_argument('--language', choices=('fr', 'en'), default='en')
    args = parser.parse_args()
    for folder in args.directories:
        count = 0
        scenes = range(13) if args.scene is None else [args.scene]
        for scene in scenes:
            for suffix in ('', '_late'):
                path = folder/f'scene{scene:02}{suffix}.screen.png'
                count += check_scene(path, scene, args.language)
        print(f'PASS {folder}: {count} exact native pixels, {len(scenes)} scenes twice')
