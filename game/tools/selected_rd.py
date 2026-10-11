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
        effective_palette = list(palette)
        if index == 4:
            effective_palette[0] = (0, 0, 0)
            effective_palette[4] = (187, 221, 255)
            effective_palette[11] = (255, 170, 153)
        png = ART / 'selected-rd' / job['durable_image']
        assert hashlib.sha256(png.read_bytes()).hexdigest() == job['image_sha256']
        rgb = bytes.fromhex(png.with_suffix('.rgb.hex').read_text())
        assert len(rgb) == 160 * 96 * 3
        assert hashlib.sha256(rgb).hexdigest() == job['rgb_sha256']
        width, height = (320, 192) if index == 4 else (160, 96)
        if index < 4:
            derivative = ART / 'selected-rd/story-eyes'
            provenance = json.loads((derivative / 'provenance.json').read_text())['panels'][index]
            assert provenance['name'] == job['id']
            assert provenance['original_sha256'] == job['image_sha256']
            png = derivative / job['durable_image']
            header = png.read_bytes()
            assert hashlib.sha256(header).hexdigest() == provenance['output_sha256']
            assert header[:8] == b'\x89PNG\r\n\x1a\n'
            assert int.from_bytes(header[16:20], 'big') == width
            assert int.from_bytes(header[20:24], 'big') == height
            rgb = bytes.fromhex(png.with_suffix('.rgb.hex').read_text())
            assert len(rgb) == width * height * 3
            assert hashlib.sha256(rgb).hexdigest() == provenance['rgb_sha256']
        if index == 4:
            derivative = ART / 'selected-rd/victory-eyes-almond'
            provenance = json.loads((derivative / 'provenance.json').read_text())
            assert provenance['input_sha256'] == job['image_sha256']
            assert hashlib.sha256((derivative / 'master.png').read_bytes()).hexdigest() == provenance['master_sha256']
            png = derivative / 'victory.png'
            header = png.read_bytes()
            assert hashlib.sha256(header).hexdigest() == provenance['image_sha256']
            assert header[:8] == b'\x89PNG\r\n\x1a\n'
            assert int.from_bytes(header[16:20], 'big') == width
            assert int.from_bytes(header[20:24], 'big') == height
            rgb = bytes.fromhex((derivative / 'victory.rgb.hex').read_text())
            assert len(rgb) == width * height * 3
            assert hashlib.sha256(rgb).hexdigest() == provenance['rgb_sha256']
        colors = {}
        image = []
        for y in range(height):
            row = []
            for x in range(width):
                if index == 4 and (x < 2 or x >= width - 2 or y < 2 or y >= height - 2):
                    row.append(7)  # White inset frame; retain the full 320x192 footprint.
                    continue
                pos = (y * width + x) * 3
                pixel = tuple(rgb[pos:pos+3])
                if pixel not in colors:
                    colors[pixel] = min(range(16), key=lambda i: sum((a-b)**2 for a,b in zip(pixel, effective_palette[i])))
                row.append(colors[pixel])
            image.append(row)
        result.append(image)
    assert len(result) == 5
    return result
