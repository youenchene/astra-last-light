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
        path = folder / record['durable_image']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record['image_sha256']
        source = Image.load_png(path)
        assert (source.width, source.height) == (160, 96)
        mapping = {}
        rows = []
        width, height = (320, 192) if index == 4 else (140, 84)
        for y in range(height):
            row = []
            for x in range(width):
                rgb = source.pixel(x // 2, y // 2) if index == 4 else source.pixel(x * 8 // 7, y * 8 // 7)
                if rgb not in mapping:
                    distances = [(sum((rgb[c]-color[c])**2 for c in range(3)), index)
                                 for index, color in palette.items()]
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
    rgb = {i: tuple((v >> shift & 15)*17 for shift in (8,4,0)) for i,v in palette.items()}
    return [[rgb[i] for i in row] for row in original_panels()[4 if scene == 12 else scene//3]]
