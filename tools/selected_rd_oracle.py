"""Independent original-PNG pixel oracle; never reads converter RGB or packed rows."""
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(os.environ.get('AGK_KIT', Path.home() / 'Code/amiga/amiga-game-kit')) / 'harness'))
from agk.image import Image

@lru_cache(maxsize=1)
def original_panels():
    folder = ROOT / 'game/art/selected-rd'
    records = json.loads((folder / 'manifest.json').read_text())['jobs']
    assert [r['id'] for r in records] == ['graveyard-b', 'nebula-b', 'foundry-b', 'citadel-b', 'victory-a']
    palette = {int(i): tuple(int(c, 16)*17 for c in word) for i, word in re.findall(
        r'^(\d+)\s+0x([0-9a-fA-F]{3})\b', (ROOT / 'game/art/palette.txt').read_text(), re.M)}
    panels = []
    for index, record in enumerate(records):
        displayed = dict(palette)
        if index == 4:
            for ink, word in ((0, 0x000), (4, 0xbdf), (11, 0xfa9)):
                displayed[ink] = tuple((word >> shift & 15) * 17 for shift in (8, 4, 0))
        path = folder / record['durable_image']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record['image_sha256']
        source = Image.load_png(path)
        assert (source.width, source.height) == (160, 96)
        if index < 4:
            derivative = folder / 'story-eyes'
            entry = json.loads((derivative / 'provenance.json').read_text())['panels'][index]
            assert entry['name'] == record['id']
            assert entry['original_sha256'] == record['image_sha256']
            path = derivative / record['durable_image']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['output_sha256']
            source = Image.load_png(path)
            assert (source.width, source.height) == (160, 96)
            pixels = bytes(c for y in range(96) for x in range(160) for c in source.pixel(x, y))
            assert hashlib.sha256(pixels).hexdigest() == entry['rgb_sha256']
        if index == 4:
            derivative = folder / 'victory-eyes-almond'
            provenance = json.loads((derivative / 'provenance.json').read_text())
            assert provenance['input_sha256'] == record['image_sha256']
            assert hashlib.sha256((derivative / 'master.png').read_bytes()).hexdigest() == provenance['master_sha256']
            path = derivative / 'victory.png'
            assert hashlib.sha256(path.read_bytes()).hexdigest() == provenance['image_sha256']
            source = Image.load_png(path)
            assert (source.width, source.height) == (320, 192)
            rgb = bytes(channel for y in range(source.height) for x in range(source.width)
                        for channel in source.pixel(x, y))
            assert hashlib.sha256(rgb).hexdigest() == provenance['rgb_sha256']
        mapping = {}
        rows = []
        width, height = source.width, source.height
        for y in range(height):
            row = []
            for x in range(width):
                if index == 4 and not (2 <= x < 318 and 2 <= y < 190):
                    row.append(7)
                    continue
                rgb = source.pixel(x, y)
                if rgb not in mapping:
                    distances = [(sum((rgb[c]-color[c])**2 for c in range(3)), index)
                                 for index, color in displayed.items()]
                    mapping[rgb] = min(distances)[1]
                row.append(mapping[rgb])
            rows.append(row)
        panels.append(rows)
    return panels

def scene_rgb(scene):
    palette = {int(i): int(word,16) for i, word in re.findall(
        r'^(\d+)\s+0x([0-9a-fA-F]{3})\b', (ROOT / 'game/art/palette.txt').read_text(), re.M)}
    palette[0] = 0 if scene == 12 else (0x001, 0x102, 0x101, 0x001)[scene//3]
    palette[4] = 0xbdf
    if scene == 12:
        palette[11] = 0xfa9
    rgb = {i: tuple((v >> shift & 15)*17 for shift in (8,4,0)) for i,v in palette.items()}
    return [[rgb[i] for i in row] for row in original_panels()[4 if scene == 12 else scene//3]]
