"""Deterministic offline conversion of preserved original RGB to existing OCS inks."""
import hashlib
import json
from pathlib import Path
import re

ART = Path(__file__).resolve().parents[1] / 'art'

def character_rgb(parent_png, parent_rgb, original, width, height, index):
    """Validate the approved runtime-only layer after the historical chain."""
    folder = ART / 'selected-rd/story-character'
    provenance = json.loads((folder / 'provenance.json').read_text())
    protected = json.loads((folder / 'protected-sha256.json').read_text())
    entry = provenance['panels'][index]
    name = original['id'] if index < 4 else 'victory'
    parent_key = 'game/art/' + parent_png.relative_to(ART).as_posix()
    assert entry['name'] == name and entry['parent'] == parent_key
    assert entry['parent_sha256'] == protected[parent_key] == hashlib.sha256(parent_png.read_bytes()).hexdigest()
    assert protected['game/art/selected-rd/' + original['durable_image']] == original['image_sha256']
    assert hashlib.sha256((folder / 'recipe.json').read_bytes()).hexdigest() == provenance['recipe_sha256']
    png = (folder / f'{name}.png').read_bytes()
    export = (folder / f'{name}.rgb.hex').read_bytes()
    for filename, data in ((f'{name}.png', png), (f'{name}.rgb.hex', export)):
        assert hashlib.sha256(data).hexdigest() == provenance['output_sha256'][filename]
    assert png[:8] == b'\x89PNG\r\n\x1a\n'
    assert (int.from_bytes(png[16:20], 'big'), int.from_bytes(png[20:24], 'big')) == (width, height)
    rgb = bytes.fromhex(export.decode())
    assert len(rgb) == width * height * 3
    expected = bytearray(parent_rgb)
    seen = set()
    for change in entry['changes']:
        x, y = change['x'], change['y']
        assert 0 <= x < width and 0 <= y < height and (x, y) not in seen
        seen.add((x, y))
        offset = (y * width + x) * 3
        assert list(parent_rgb[offset:offset+3]) == change['before']
        expected[offset:offset+3] = bytes(change['after'])
    assert len(seen) == entry['changed_pixels'] and bytes(expected) == rgb
    return rgb


def bold_rgb(parent_rgb, name, width, height, index):
    """Apply only the approved additions to the validated historical character."""
    parent = ART / 'selected-rd/story-character'
    folder = parent / 'bold-marks'
    provenance = json.loads((folder / 'provenance.json').read_text())
    protected = json.loads((folder / 'protected-sha256.json').read_text())
    entry = provenance['panels'][index]
    key = f'game/art/selected-rd/story-character/{name}.png'
    assert entry['name'] == name and entry['parent'] == key
    assert entry['dimensions'] == [width, height]
    assert entry['parent_sha256'] == protected[key] == hashlib.sha256((parent/f'{name}.png').read_bytes()).hexdigest()
    assert hashlib.sha256((parent/'recipe.json').read_bytes()).hexdigest() == provenance['parent_recipe_sha256']
    assert hashlib.sha256((ART/'palette.txt').read_bytes()).hexdigest() == protected['game/art/palette.txt']
    png, export = [(folder / f'{name}{suffix}').read_bytes() for suffix in ('.png', '.rgb.hex')]
    for filename, data in ((f'{name}.png', png), (f'{name}.rgb.hex', export)):
        assert hashlib.sha256(data).hexdigest() == provenance['output_sha256'][filename]
    assert png[:8] == b'\x89PNG\r\n\x1a\n'
    assert (int.from_bytes(png[16:20], 'big'), int.from_bytes(png[20:24], 'big')) == (width, height)
    rgb = bytes.fromhex(export.decode())
    assert len(rgb) == width * height * 3
    expected, seen = bytearray(parent_rgb), set()
    for change in entry['changes']:
        x, y = change['x'], change['y']
        assert 0 <= x < width and 0 <= y < height and (x, y) not in seen
        seen.add((x, y))
        offset = (y * width + x) * 3
        assert list(parent_rgb[offset:offset+3]) == change['before']
        assert change['after'] == [170, 68, 51] and change['before'] != change['after']
        expected[offset:offset+3] = bytes(change['after'])
    assert len(seen) == entry['changed_pixels'] == (8 if index == 4 else 2)
    assert bytes(expected) == rgb
    return rgb


def panels(*, layer='bold-marks'):
    assert layer in ('story-eyes', 'story-character', 'bold-marks')
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
        if layer in ('story-character', 'bold-marks'):
            rgb = character_rgb(png, rgb, job, width, height, index)
        if layer == 'bold-marks':
            rgb = bold_rgb(rgb, job['id'] if index < 4 else 'victory', width, height, index)
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
