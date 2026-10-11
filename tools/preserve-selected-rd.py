#!/usr/bin/env python3.12
"""One-time offline import of the user's five approved, already generated masters."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(os.environ.get('AGK_KIT', Path.home() / 'Code/amiga/amiga-game-kit')) / 'harness'))
from agk.image import Image

source = ROOT / '.tmp/manga-proposals'
target = ROOT / 'game/art/selected-rd'
selected = ('graveyard-b', 'nebula-b', 'foundry-b', 'citadel-b', 'victory-a')
manifest = json.loads((source / 'manifest.json').read_text())
jobs = {job['id']: job for job in manifest['jobs']}

def preserve(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise SystemExit(f'refusing to overwrite {path}')
    else:
        path.write_bytes(data)

target.mkdir(exist_ok=True)
records = []
for name in selected:
    job = jobs[name]
    original = source / job['image']
    data = original.read_bytes()
    assert hashlib.sha256(data).hexdigest() == job['image_sha256']
    image = Image.load_png(original)
    assert (image.width, image.height) == (160, 96)
    rgb = bytes(channel for y in range(96) for x in range(160) for channel in image.pixel(x, y))
    preserve(target / f'{name}.png', data)
    # Standard-library build input, lossless original RGB, not quantized pixels.
    preserve(target / f'{name}.rgb.hex', (rgb.hex() + '\n').encode())
    records.append(dict(job, durable_image=f'{name}.png', rgb_sha256=hashlib.sha256(rgb).hexdigest()))
record = dict(provider=manifest['provider'], selection='1B 2B 3B 4B 5A',
              palette_sha256=manifest['palette_sha256'], jobs=records,
              conversion='128x72 floor nearest sample (x*160//128,y*96//72); nearest squared RGB distance to palette.txt expanded nibble*17; lowest index tie; no dithering; runtime ink 0 sector override and ink 4 BDF retained')
preserve(target / 'manifest.json', (json.dumps(record, indent=2, ensure_ascii=False) + '\n').encode())
print('Preserved five selected PNG masters, lossless RGB inputs and full generation metadata')
