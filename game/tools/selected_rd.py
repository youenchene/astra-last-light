"""Deterministic offline conversion of preserved original RGB to existing OCS inks."""
import hashlib
import json
from pathlib import Path
import re

ART = Path(__file__).resolve().parents[1] / 'art'

def panels():
    manifest = json.loads((ART / 'selected-rd/manifest.json').read_text())
    palette_data = (ART / 'palette.txt').read_bytes()
    assert hashlib.sha256(palette_data).hexdigest() == manifest['palette_sha256']
    values = [int(value, 16) for _, value in re.findall(
        r'^(\d+)\s+0x([0-9a-fA-F]{3})\b', palette_data.decode(), re.M)]
    palette = [tuple((value >> shift & 15) * 17 for shift in (8, 4, 0)) for value in values]
    assert len(palette) == 16
    result = []
    for index, job in enumerate(manifest['jobs']):
        png = ART / 'selected-rd' / job['durable_image']
        assert hashlib.sha256(png.read_bytes()).hexdigest() == job['image_sha256']
        rgb = bytes.fromhex(png.with_suffix('.rgb.hex').read_text())
        assert len(rgb) == 160 * 96 * 3
        assert hashlib.sha256(rgb).hexdigest() == job['rgb_sha256']
        colors = {}
        image = []
        width, height = (320, 192) if index == 4 else (140, 84)
        for y in range(height):
            row = [] if index == 4 else [0, 0]
            for x in range(width):
                pos = ((y * 96 // height) * 160 + x * 160 // width) * 3
                pixel = tuple(rgb[pos:pos+3])
                if pixel not in colors:
                    colors[pixel] = min(range(16), key=lambda i: sum((a-b)**2 for a,b in zip(pixel, palette[i])))
                row.append(colors[pixel])
            image.append(row if index == 4 else row + [0, 0])
        result.append(image)
    assert len(result) == 5
    return result
