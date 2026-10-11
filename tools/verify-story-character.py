#!/usr/bin/env python3
"""Independent saved-PNG invariance checks for the unintegrated phase-one layer."""
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'game/art/selected-rd/story-character'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_panel(spec, record):
    name = spec['name']
    before = Image.open(ROOT / record['parent']).convert('RGB')
    after = Image.open(LAYER / f'{name}.png').convert('RGB')
    masks = [Image.open(LAYER / 'masks' / f'{name}-{role}.png').convert('L')
             for role in ('armor','cheek','protected-eyes')]
    assert before.size == after.size == ((320,192) if name == 'victory' else (160,96))
    assert all(mask.size == before.size for mask in masks)
    assert bytes.fromhex((LAYER/f'{name}.rgb.hex').read_text()) == after.tobytes()
    expected_changes = {(p['x'],p['y']):(tuple(p['before']),tuple(p['after'])) for p in record['changes']}
    actual_changes = {}
    eye_count = 0
    armor_count = 0
    for y in range(before.height):
        for x in range(before.width):
            p = (x,y)
            a,b = before.getpixel(p),after.getpixel(p)
            armor,cheek,eyes = (mask.getpixel(p) for mask in masks)
            assert all(v in (0,255) for v in (armor,cheek,eyes))
            is_eye = any(x0<=x<x1 and y0<=y<y1 for x0,y0,x1,y1 in spec['eye_boxes'])
            assert bool(eyes) == is_eye
            if is_eye:
                eye_count += 1
                assert a == b and not armor and not cheek, (name,'eye',p)
            if not armor and not cheek:
                assert a == b, (name,'outside masks',p)
            if a != b:
                actual_changes[p] = (a,b)
                armor_count += bool(armor)
                if armor:
                    assert b in ((51,68,102),(136,153,170),(204,238,255),(255,255,255),(68,187,221))
    assert actual_changes == expected_changes
    assert len(actual_changes) == record['changed_pixels']
    assert armor_count == record['armor_changed']
    assert eye_count == record['protected_eye_pixels']
    for x,y in spec['mark']:
        assert after.getpixel((x,y)) == (170,68,51)
    if name == 'victory':
        assert set(actual_changes) == {tuple(p) for p in spec['mark']}
        assert not masks[0].getbbox(), 'Ending armor must be entirely untouched'
    else:
        assert len(spec['mark']) in (2,3)
        assert any(after.getpixel(p)==(68,187,221) for p in actual_changes), 'Missing stable blue trim'
        assert any(after.getpixel(p)==(204,238,255) for p in actual_changes), 'Missing pale plate'
    print(f'{name}: PASS {len(actual_changes)} changes; {eye_count} full-eye pixels immutable; all other unmasked pixels immutable')


def main():
    provenance = json.loads((LAYER/'provenance.json').read_text())
    recipe = json.loads((LAYER/'recipe.json').read_text())
    historical = json.loads((LAYER/'protected-sha256.json').read_text())
    for name,expected in historical.items():
        assert digest(ROOT/name) == expected, f'Historical asset changed: {name}'
    for name,expected in provenance['output_sha256'].items():
        assert digest(LAYER/name) == expected, f'Output changed: {name}'
    assert digest(ROOT/'tools/make-story-character.py') == provenance['script_sha256']
    assert digest(LAYER/'recipe.json') == provenance['recipe_sha256']
    assert len(recipe['panels']) == len(provenance['panels']) == 5
    for spec,record in zip(recipe['panels'],provenance['panels']):
        assert spec['name'] == record['name']
        verify_panel(spec,record)
    print(f'PASS: {len(historical)} historical files, all output hashes, RGB exports, dimensions, mask/eye/ending invariants')


if __name__ == '__main__':
    main()
