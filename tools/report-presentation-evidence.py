#!/usr/bin/env python3.12
"""Summarize preserved native evidence and make uncropped native-size review sheets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

KIT = Path(os.environ.get('AGK_KIT', str(Path.home() / 'Code/amiga/amiga-game-kit')))
sys.path.insert(0, str(KIT / 'harness'))
from agk.image import Image


def summary(folder):
    windows, context = [], {}
    text = (folder / 'serial.txt').read_text()
    for line in text.splitlines():
        fields = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', line)}
        if line.startswith('AGK frame='):
            context = fields
        elif line.startswith('AGK enemy_acc='):
            context.update(fields)
        elif line.startswith('AGK perf '):
            windows.append(dict(fields, context=context.copy()))
    memory = re.search(r'AGK chip_free=(\d+) ram_free=(\d+)', text)
    return {'folder': str(folder), 'memory': list(map(int, memory.groups())) if memory else None,
            'drops': sum(w['dropped'] for w in windows),
            'peak': max((w['maxload'] for w in windows), default=None), 'windows': windows}


def sheets(folder):
    paths = sorted(folder.glob('*.screen.png'))
    pages = []
    for start in range(0, len(paths), 12):
        selected = paths[start:start+12]
        width, height = 1280, ((len(selected) + 3) // 4) * 256
        rgb = bytearray(width * height * 3)
        for slot, path in enumerate(selected):
            image = Image.load_png(path)
            assert (image.width, image.height) == (320, 256)
            for y in range(256):
                dest = (((slot // 4) * 256 + y) * width + slot % 4 * 320) * 3
                rgb[dest:dest+960] = image.rgb[y*960:(y+1)*960]
        target = folder / f'review-presentation-{start//12+1}.png'
        Image(bytes(rgb), width, height).save_png(target)
        pages.append({'sheet': str(target), 'row_major': [p.name for p in selected]})
    return pages


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folders', nargs='+', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--compare', nargs=2, action='append', type=Path, default=[])
    args = parser.parse_args()
    report = {'runs': [summary(p) for p in args.folders],
              'review': [page for folder in args.folders for page in sheets(folder)], 'comparisons': []}
    for before, after in args.compare:
        matched, different = [], []
        for source in sorted(before.glob('*.screen.png')):
            target = after / source.name
            old, new = Image.load_png(source), Image.load_png(target)
            if old.rgb == new.rgb:
                matched.append(source.name)
            else:
                pixels = [(x, y) for y in range(256) for x in range(320)
                          if old.pixel(x, y) != new.pixel(x, y)]
                different.append({'name': source.name, 'pixels': len(pixels),
                                  'bounds': [min(x for x,y in pixels), min(y for x,y in pixels),
                                             max(x for x,y in pixels), max(y for x,y in pixels)]})
        report['comparisons'].append({'before': str(before), 'after': str(after),
                                      'identical': matched, 'different': different})
    build = Path(__file__).resolve().parents[1] / 'game/build'
    report['production'] = {name: {'bytes': (build/name).stat().st_size,
                          'sha256': hashlib.sha256((build/name).read_bytes()).hexdigest()}
                            for name in ('astra', 'astra.adf')}
    report['production']['probe_off'] = 'ASTRA_CAMPAIGN_PROBE:BOOL=OFF' in (build/'CMakeCache.txt').read_text()
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    for run in report['runs']:
        print(f"{run['folder']}: free={run['memory']} drops={run['drops']} peak={run['peak']}")
    for comparison in report['comparisons']:
        print(f"{comparison['before']} -> {comparison['after']}: "
              f"{len(comparison['identical'])} identical; differences={comparison['different']}")
