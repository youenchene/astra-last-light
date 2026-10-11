#!/usr/bin/env python3
"""Independently verify saved phase-one bold-mark PNGs, deltas and protected files."""
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'game/art/selected-rd/story-character'
LAYER = PARENT / 'bold-marks'
# Independently enumerated accepted footprints, not imported from the generator.
MARKS = (
    {(36,57), (35,58), (36,58), (35,59)},
    {(40,30), (38,31), (39,31), (40,31), (38,32)},
    {(38,60), (37,61), (38,61), (37,62)},
    {(49,60), (47,61), (48,61), (49,61), (47,62)},
    {(127,92), (125,93), (126,93), (127,93), (124,94), (125,94), (126,94),
     (123,95), (124,95), (125,95), (123,96), (124,96), (123,97)},
)
NOSES = ((29,56,34,65), (30,29,36,36), (29,58,36,67),
         (35,58,45,65), (95,88,115,110))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_panel(index, spec, record):
    name = spec['name']
    before = Image.open(PARENT / f'{name}.png').convert('RGB')
    after = Image.open(LAYER / f'{name}.png').convert('RGB')
    assert before.size == after.size == ((320,192) if index == 4 else (160,96))
    assert digest(PARENT / f'{name}.png') == record['parent_sha256']
    assert bytes.fromhex((LAYER / f'{name}.rgb.hex').read_text()) == after.tobytes()
    masks = [Image.open(LAYER / 'masks' / f'{name}-{kind}.png')
             for kind in ('footprint', 'additions')]
    assert all(mask.size == before.size and mask.mode == 'L' for mask in masks)
    old = {tuple(p) for p in spec['mark']}
    mark = MARKS[index]
    assert old <= mark
    assert {tuple(p) for p in record['mark']} == mark
    changes, eyes, nose = [], 0, 0
    for y in range(before.height):
        for x in range(before.width):
            p = (x,y)
            a, b = before.getpixel(p), after.getpixel(p)
            assert masks[0].getpixel(p) == (255 if p in mark else 0)
            assert masks[1].getpixel(p) == (255 if p in mark-old else 0)
            if p in mark:
                assert b == (170,68,51)
            else:
                assert a == b, (name, 'outside footprint', p)
            if any(x0 <= x < x1 and y0 <= y < y1 for x0,y0,x1,y1 in spec['eye_boxes']):
                assert a == b and p not in mark
                eyes += 1
            x0,y0,x1,y1 = NOSES[index]
            if x0 <= x < x1 and y0 <= y < y1:
                assert a == b and p not in mark
                nose += 1
            if a != b:
                assert isinstance(a, tuple) and isinstance(b, tuple)
                changes.append(dict(x=x, y=y, before=list(a), after=list(b)))
    assert {(c['x'],c['y']) for c in changes} == mark-old
    assert changes == record['changes']
    assert len(changes) == record['changed_pixels'] == (8 if index == 4 else 2)
    assert eyes == record['protected_eye_pixels']
    if index == 4:
        original = Image.open(ROOT / 'game/art/selected-rd/victory-identity-master/victory.png').convert('RGB')
        skin = {(x,y) for y in range(88,104) for x in range(80,115)
                if original.getpixel((x,y)) == (252,169,139)}
        assert len(skin) == 498
        extra = {(80,88),(80,89),(81,88),(82,88),(83,88),(113,88),(114,88)}
        displayed = Image.open(LAYER / 'victory.displayed.png').convert('RGB')
        for p in skin | extra:
            assert after.getpixel(p) == before.getpixel(p) == (252,169,139)
            assert displayed.getpixel(p) == (255,170,153)
    print(f'{name}: PASS {len(changes)} exact changes, {eyes} eye / {nose} nose pixels unchanged')


def main():
    provenance = json.loads((LAYER / 'provenance.json').read_text())
    historical = json.loads((LAYER / 'protected-sha256.json').read_text())
    recipe = json.loads((PARENT / 'recipe.json').read_text())
    for name, expected in historical.items():
        assert digest(ROOT / name) == expected, f'Protected file changed: {name}'
    for name, expected in provenance['output_sha256'].items():
        assert digest(LAYER / name) == expected, f'Output changed: {name}'
    assert digest(ROOT / 'tools/make-story-bold-marks.py') == provenance['script_sha256']
    assert digest(PARENT / 'recipe.json') == provenance['parent_recipe_sha256']
    assert len(recipe['panels']) == len(provenance['panels']) == len(MARKS) == 5
    for i, (spec, record) in enumerate(zip(recipe['panels'], provenance['panels'])):
        assert spec['name'] == record['name']
        verify_panel(i, spec, record)
    print(f'PASS: {len(historical)} protected files; 16 exact RGB changes; 2571 eye pixels; 498+7 skin samples')


if __name__ == '__main__':
    main()
