#!/usr/bin/env python3
"""Offline, explicit-pixel story-eye proposals; never modifies imported assets."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'game/art/selected-rd'
OUTPUT = SOURCE / 'story-eyes'
NAMES = ('graveyard-b', 'nebula-b', 'foundry-b', 'citadel-b')
CROPS = ((10, 43, 42, 63), (13, 16, 45, 36),
         (12, 45, 44, 65), (19, 43, 51, 63))
# Coordinates are zero-based in the original 160x96 panel, viewer-left/right.
# Each role lists literal pixel assignments, never a filled bounding rectangle.
EYES = (
    ({'blue': [(23, 53), (24, 53), (24, 54)], 'pupil': [(23, 54)], 'glint': [(23, 52)]},
     {'blue': [(36, 54)], 'pupil': [(35, 54)], 'glint': [(35, 53)]}),
    ({'blue': [(25, 24), (25, 25), (27, 25)], 'pupil': [(26, 25)], 'glint': [(26, 24)]},
     {'blue': [(39, 24), (39, 25), (38, 26)], 'pupil': [(38, 25)], 'glint': [(38, 24)]}),
    ({'blue': [(25, 55), (26, 56), (26, 57), (25, 57)], 'pupil': [(25, 56)], 'glint': [(26, 55)]},
     {'blue': [(39, 56), (39, 57), (38, 57)], 'pupil': [(38, 56)], 'glint': [(38, 55)]}),
    ({'blue': [(29, 53), (29, 54), (30, 54), (31, 53), (32, 54)], 'pupil': [(31, 54)], 'glint': [(30, 53)]},
     {'blue': [(46, 54), (48, 54), (48, 55), (46, 55)], 'pupil': [(47, 55)], 'glint': [(47, 54)]}),
)
INKS = {'blue': 15, 'pupil': 1, 'glint': 7}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def palette():
    entries = re.findall(r'^(\d+)\s+0x([0-9A-Fa-f]{3})\b',
                         (ROOT / 'game/art/palette.txt').read_text(), re.M)
    return [tuple(int(c, 16) * 17 for c in word) for _, word in entries]


def displayed(image, index, colors):
    """Match ordinary importer quantization, then hardware palette overrides."""
    live = list(colors)
    live[0] = ((0, 0, 17), (17, 0, 34), (17, 0, 17), (0, 0, 17))[index]
    live[4] = (187, 221, 255)
    mapping = {rgb: min(range(16), key=lambda ink: sum(
        (a - b) ** 2 for a, b in zip(rgb, colors[ink]))) for rgb in set(image.getdata())}
    result = Image.new('RGB', image.size)
    result.putdata([live[mapping[rgb]] for rgb in image.getdata()])
    return result


def edit_panel(original, eyes, colors):
    result = original.copy()
    mask = Image.new('L', original.size)
    records = []
    for side, eye in zip(('viewer-left', 'viewer-right'), eyes):
        pixels = []
        for role, points in eye.items():
            for point in points:
                assert mask.getpixel(point) == 0, 'Overlapping eye assignments'
                color = colors[INKS[role]]
                result.putpixel(point, color)
                mask.putpixel(point, 255)
                pixels.append(dict(x=point[0], y=point[1], role=role, ink=INKS[role],
                                   before=list(original.getpixel(point)), after=list(color)))
        records.append(dict(side=side, pixels=pixels))
    return result, mask, records


def verify_panel(before, after, mask, eyes, colors, index):
    assert before.size == after.size == mask.size == (160, 96)
    changes = [(x, y) for y in range(96) for x in range(160)
               if before.getpixel((x, y)) != after.getpixel((x, y))]
    assert all(mask.getpixel(point) == 255 for point in changes)
    shown = displayed(after, index, colors)
    for eye in eyes:
        for role, points in eye.items():
            for point in points:
                assert shown.getpixel(point) == colors[INKS[role]]
    return changes


def protected_hashes():
    files = [p for p in SOURCE.rglob('*') if p.is_file() and OUTPUT not in p.parents]
    files += [ROOT / 'game/art/palette.txt']
    return {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in sorted(files)}


def previews(pairs):
    eyes = Image.new('RGB', (800, 4 * 210), '#303030')
    panels = Image.new('RGB', (680, 244), '#303030')
    eye_draw, panel_draw = ImageDraw.Draw(eyes), ImageDraw.Draw(panels)
    panel_draw.text((8, 4), 'BEFORE: displayed palette / native 160x96', fill='white')
    panel_draw.text((8, 126), 'AFTER: offline proposal / native 160x96', fill='white')
    for index, ((before, after), box, name) in enumerate(zip(pairs, CROPS, NAMES)):
        y = index * 210
        eye_draw.text((8, y + 4), f'{name} BEFORE (12x)', fill='white')
        eye_draw.text((408, y + 4), 'AFTER (12x) - displayed palette', fill='white')
        # Use an 8-row eye band, retaining brows and face context in inspection sheet.
        band = (box[0], box[1] + 6, box[2], box[1] + 16)
        for image, x in ((before, 8), (after, 408)):
            eyes.paste(image.crop(band).resize((384, 120), Image.Resampling.NEAREST), (x, y + 26))
        for row, image in enumerate((before, after)):
            panels.paste(image, (8 + index * 168, 24 + row * 122))
        panel_draw.text((8 + index * 168, 14), name, fill='white')
    return {'eyes-before-after.png': png_bytes(eyes),
            'panels-native-before-after.png': png_bytes(panels)}


def generate():
    protected = protected_hashes()
    colors = palette()
    manifest = json.loads((SOURCE / 'manifest.json').read_text())
    outputs, records, pairs = {}, [], []
    for index, (name, eyes) in enumerate(zip(NAMES, EYES)):
        source = SOURCE / f'{name}.png'
        before = Image.open(source).convert('RGB')
        job = manifest['jobs'][index]
        assert digest(source.read_bytes()) == job['image_sha256']
        assert digest(before.tobytes()) == job['rgb_sha256']
        assert bytes.fromhex(source.with_suffix('.rgb.hex').read_text()) == before.tobytes()
        after, mask, eye_records = edit_panel(before, eyes, colors)
        changes = verify_panel(before, after, mask, eyes, colors, index)
        live_before, live_after = (displayed(im, index, colors) for im in (before, after))
        # Baseline comes directly from hash-validated original RGB and PAL rules.
        # Gallery images are mutable presentation outputs, never source evidence.
        pairs.append((live_before, live_after))
        outputs[f'{name}.png'] = png_bytes(after)
        outputs[f'{name}.rgb.hex'] = (after.tobytes().hex() + '\n').encode()
        outputs[f'{name}.mask.png'] = png_bytes(mask)
        outputs[f'{name}.displayed.png'] = png_bytes(live_after)
        records.append(dict(name=name, width=160, height=96, eyes=eye_records,
                            original_sha256=digest(source.read_bytes()),
                            output_sha256=digest(outputs[f'{name}.png']),
                            rgb_sha256=digest(after.tobytes()), changed_pixels=len(changes),
                            displayed_changed_pixels=sum(a != b for a, b in zip(
                                live_before.getdata(), live_after.getdata())),
                            changed_coordinates=changes, outside_mask_changes=0))
    outputs.update(previews(pairs))
    provenance = dict(status='parent visually approved; phase2 integration',
                      method='Literal per-eye pixel assignments only; no generation, resampling or dithering',
                      coordinates='zero-based panel-local x,y; viewer-left/right; screen offset (144,68)',
                      mask='255 = declared assignment (including unchanged palette-exact pixels); 0 = immutable',
                      cost_usd=0, protected_sha256=protected, panels=records,
                      script_sha256=digest(Path(__file__).read_bytes()),
                      output_files_sha256={name: digest(data) for name, data in outputs.items()})
    outputs['provenance.json'] = (json.dumps(provenance, indent=2) + '\n').encode()
    assert protected_hashes() == protected, 'Protected inputs changed during generation'
    return outputs, records


def png_bytes(image):
    stream = io.BytesIO()
    image.save(stream, format='PNG')
    return stream.getvalue()


def save_new(path, data):
    """Reproduction is allowed; differing existing artifacts are never overwritten."""
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f'Refusing differing overwrite: {path}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def inspect_sources():
    sheet = Image.new('RGB', (820, 4 * 390), '#303030')
    draw = ImageDraw.Draw(sheet)
    for index, (name, box) in enumerate(zip(NAMES, CROPS)):
        image = Image.open(SOURCE / f'{name}.png').convert('RGB')
        y = index * 390
        draw.text((4, y + 4), f'{name}: source x={box[0]}..{box[2]-1}, y={box[1]}..{box[3]-1}', fill='white')
        sheet.paste(image.crop(box).resize((576, 360), Image.Resampling.NEAREST), (40, y + 24))
        for x in range(32):
            draw.text((40 + x * 18, y + 12), str(box[0] + x), fill='white')
        for row in range(20):
            draw.text((18, y + 26 + row * 18), str(box[1] + row), fill='white')
        sheet.paste(image.resize((160, 96)), (640, y + 40))
    save_new(OUTPUT / 'inspection-source-eyes.png', png_bytes(sheet))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--check', action='store_true', help='Verify reproducibility without writing')
    parser.add_argument('--refresh-provenance', action='store_true',
                        help='Refresh metadata only, requiring byte-identical approved assets')
    args = parser.parse_args()
    if args.inspect:
        inspect_sources()
    else:
        artifacts, records = generate()
        if args.refresh_provenance:
            assert not args.check
            old = json.loads((OUTPUT / 'provenance.json').read_text())
            new = json.loads(artifacts['provenance.json'])
            assert old['panels'] == new['panels']
            assert old['output_files_sha256'] == new['output_files_sha256']
            assert all(old['protected_sha256'][p] == h for p, h in new['protected_sha256'].items())
            for name, data in artifacts.items():
                if name != 'provenance.json':
                    assert (OUTPUT / name).read_bytes() == data
            (OUTPUT / 'provenance.json').write_bytes(artifacts['provenance.json'])
        for name, data in artifacts.items():
            path = OUTPUT / name
            if args.check:
                assert path.read_bytes() == data, f'Stale derivative: {path}'
            else:
                save_new(path, data)
        for record in records:
            print(f"{record['name']}: {record['changed_pixels']} source / "
                  f"{record['displayed_changed_pixels']} displayed pixels changed; outside mask=0")
        print('PASS: original/ending hashes, source/PAL baseline, per-eye inks, masks and reproducibility')
