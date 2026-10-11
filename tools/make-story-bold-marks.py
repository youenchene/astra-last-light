#!/usr/bin/env python3
"""Reproduce approved cheek-mark assets and palette-accurate review artifacts."""
import argparse
import importlib.util
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('character', ROOT / 'tools/make-story-character.py')
assert SPEC is not None and SPEC.loader is not None
character = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(character)
PARENT = character.OUTPUT
OUTPUT = PARENT / 'bold-marks'
# Inclusive horizontal runs: one-pixel tips and wider diagonal centers.
ROWS = (
    ((57, 36, 36), (58, 35, 36), (59, 35, 35)),
    ((30, 40, 40), (31, 38, 40), (32, 38, 38)),
    ((60, 38, 38), (61, 37, 38), (62, 37, 37)),
    ((60, 49, 49), (61, 47, 49), (62, 47, 47)),
    ((92, 127, 127), (93, 125, 127), (94, 124, 126),
     (95, 123, 125), (96, 123, 124), (97, 123, 123)),
)
FACE_BOXES = ((13, 42, 44, 72), (17, 15, 47, 42), (17, 45, 47, 74),
              (21, 42, 55, 74), (63, 62, 140, 122))
PHASE2_MUTABLE = (
    'game/art/presentation-rows.h', 'game/tools/selected_rd.py',
    'tools/selected_rd_oracle.py', 'tools/make-story-character.py',
    'tools/verify-story-character.py', 'docs/selected-rd-story-images.md',
    'docs/campaign-expansion.md',
)


def protected_hashes():
    paths = [p for p in character.SOURCE.rglob('*')
             if p.is_file() and OUTPUT not in p.parents]
    paths.append(ROOT / 'game/art/palette.txt')
    return {str(p.relative_to(ROOT)): character.sha(p.read_bytes()) for p in sorted(paths)}


def footprint(rows):
    return {(x, y) for y, left, right in rows for x in range(left, right + 1)}


def assert_shape(mark, rows):
    seen = {min(mark)}
    while True:
        expanded = seen | {p for p in mark if any(
            abs(p[0]-q[0]) + abs(p[1]-q[1]) == 1 for q in seen)}
        if expanded == seen:
            break
        seen = expanded
    assert seen == mark, 'Mark must be four-connected'
    widths = [right-left+1 for _, left, right in rows]
    assert widths[0] == widths[-1] == 1 and 2 <= max(widths) <= 3
    assert all(b[1] <= a[1] and b[2] <= a[2] for a, b in zip(rows, rows[1:]))


def verify_skin(before, after, shown):
    original = Image.open(character.SOURCE / 'victory-identity-master/victory.png').convert('RGB')
    skin = {(x, y) for y in range(88, 104) for x in range(80, 115)
            if original.getpixel((x, y)) == (252, 169, 139)}
    additions = {(80, 88), (80, 89), (81, 88), (82, 88), (83, 88), (113, 88), (114, 88)}
    assert len(skin) == 498 and len(additions) == 7 and not skin & additions
    for p in skin | additions:
        assert before.getpixel(p) == after.getpixel(p) == (252, 169, 139), p
        assert shown.getpixel(p) == (255, 170, 153), p
    return len(skin | additions)


def make_panel(index, spec, palette):
    name = spec['name']
    path = PARENT / f'{name}.png'
    before = Image.open(path).convert('RGB')
    after = before.copy()
    mark = footprint(ROWS[index])
    old = {tuple(p) for p in spec['mark']}
    assert old <= mark
    assert_shape(mark, ROWS[index])
    assert len(mark) == (13 if index == 4 else (4 if index in (0, 2) else 5))
    mask, delta = (Image.new('L', before.size) for _ in range(2))
    for p in mark:
        # No dark liner, hair, eye white or nose shading can be overwritten.
        assert character.nearest(before.getpixel(p), palette) in (11, 13, 14), (name, p)
        mask.putpixel(p, 255)
        after.putpixel(p, palette[13])
    changes, eyes = [], 0
    for y in range(before.height):
        for x in range(before.width):
            p = (x, y)
            a, b = before.getpixel(p), after.getpixel(p)
            if any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in spec['eye_boxes']):
                eyes += 1
                assert a == b and p not in mark, (name, 'eye', p)
            if a != b:
                assert p in mark - old
                delta.putpixel(p, 255)
                changes.append(dict(x=x, y=y, before=a, after=b))
    assert len(changes) == len(mark - old)
    shown = [character.displayed(im, index, palette) for im in (before, after)]
    displayed_changes = sum(a != b for a, b in zip(shown[0].getdata(), shown[1].getdata()))
    assert displayed_changes == len(changes)
    skin_count = verify_skin(before, after, shown[1]) if index == 4 else 0
    record = dict(name=name, parent=str(path.relative_to(ROOT)),
                  parent_sha256=character.sha(path.read_bytes()), dimensions=list(before.size),
                  old_mark_pixels=len(old), mark_pixels=len(mark), changed_pixels=len(changes),
                  displayed_changed=displayed_changes, protected_eye_pixels=eyes,
                  eye_changes=0, outside_footprint_changes=0, protected_skin_samples=skin_count,
                  mark=sorted(mark, key=lambda p: (p[1], p[0])), changes=changes)
    return after, shown, mask, delta, record


def face_review(pair, box, name, scale):
    width, height = (box[2]-box[0])*scale, (box[3]-box[1])*scale
    sheet = Image.new('RGB', (width*2+24, height+32), '#303030')
    draw = ImageDraw.Draw(sheet)
    for i, image in enumerate(pair):
        x = 8+i*(width+8)
        draw.text((x, 6), f'{name}: {"BEFORE" if i == 0 else "AFTER"} / OCS', fill='white')
        sheet.paste(image.crop(box).resize((width, height), Image.Resampling.NEAREST), (x, 26))
    return sheet


def generate(migrate=False):
    protected = protected_hashes()
    baseline = OUTPUT / 'protected-sha256.json'
    if baseline.exists():
        historical = json.loads(baseline.read_text())
        if migrate:
            assert set(historical) - set(protected) == set(PHASE2_MUTABLE)
            for name, expected in historical.items():
                assert character.sha((ROOT/name).read_bytes()) == expected, name
            historical = {name: value for name, value in historical.items() if name not in PHASE2_MUTABLE}
        assert historical == protected, 'Protected parent/assets/palette changed'
    recipe = json.loads((PARENT / 'recipe.json').read_text())
    outputs, records, pairs = {}, [], []
    palette = character.colors()
    assert palette[13] == (170, 68, 51)
    for i, spec in enumerate(recipe['panels']):
        assert spec['name'] == character.NAMES[i]
        after, shown, mask, delta, record = make_panel(i, spec, palette)
        name = spec['name']
        outputs[f'{name}.png'] = character.png(after)
        outputs[f'{name}.rgb.hex'] = (after.tobytes().hex()+'\n').encode()
        outputs[f'{name}.displayed.png'] = character.png(shown[1])
        outputs[f'masks/{name}-footprint.png'] = character.png(mask)
        outputs[f'masks/{name}-additions.png'] = character.png(delta)
        outputs[f'previews/{name}-before-after.png'] = character.png(
            face_review(shown, FACE_BOXES[i], name, 6 if i == 4 else 10))
        records.append(record)
        pairs.append(shown)
    for native in (True, False):
        outputs[f'previews/five-panels-ocs-{"native" if native else "2x"}.png'] = character.png(
            character.montage(pairs, native))
    outputs['previews/ending-closeup.png'] = character.png(
        face_review(pairs[4], (106, 83, 137, 106), 'ending cheek', 14))
    provenance = dict(status='User-approved bold marks; phase-two selected asset layer',
                      cost_usd=0, method='Literal copper ink-13 diagonal runs; no resampling or antialiasing',
                      script_sha256=character.sha(Path(__file__).read_bytes()),
                      parent_recipe_sha256=character.sha((PARENT/'recipe.json').read_bytes()),
                      protected_files=len(protected), panels=records,
                      output_sha256={name: character.sha(data) for name, data in outputs.items()})
    outputs['provenance.json'] = (json.dumps(provenance, indent=2)+'\n').encode()
    outputs['protected-sha256.json'] = (json.dumps(protected, indent=2)+'\n').encode()
    assert protected_hashes() == protected
    return outputs, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Recompute and compare all saved bytes without writes')
    parser.add_argument('--phase2-metadata', action='store_true',
                        help='One-time authorized metadata migration; archive phase-one records; preserve every image byte')
    args = parser.parse_args()
    assert not (args.check and args.phase2_metadata)
    outputs, records = generate(args.phase2_metadata)
    metadata = {'provenance.json', 'protected-sha256.json'}
    if args.phase2_metadata:
        previous = json.loads((OUTPUT/'provenance.json').read_text())
        for name, data in outputs.items():
            if name not in metadata:
                assert character.sha(data) == previous['output_sha256'][name]
                assert (OUTPUT/name).read_bytes() == data
        for name in sorted(metadata):
            character.save(OUTPUT/'phase1-evidence'/name, (OUTPUT/name).read_bytes())
    for name, data in outputs.items():
        path = OUTPUT / name
        if args.check:
            assert path.read_bytes() == data, f'Stale artifact: {path}'
        elif args.phase2_metadata and name in metadata:
            path.write_bytes(data)
        else:
            character.save(path, data)
    for r in records:
        print(f"{r['name']}: {r['old_mark_pixels']} -> {r['mark_pixels']} mark pixels; "
              f"{r['changed_pixels']} RGB / {r['displayed_changed']} OCS changes; "
              f"{r['protected_eye_pixels']} eye pixels unchanged")
    print('PASS: tapered four-connected marks; retained old marks; 505 skin samples; exact deltas; protected hashes')


if __name__ == '__main__':
    main()
