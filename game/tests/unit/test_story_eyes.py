"""Approved eight-eye coordinates, immutable surrounds and independent readers."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'game/tools'))
sys.path.insert(0, str(ROOT / 'tools'))
import selected_rd
import selected_rd_oracle
from agk.image import load_png_rgba

ART = ROOT / 'game/art/selected-rd'
DERIVATIVE = ART / 'story-eyes'
# Independent approval fixture: (iris pixels, pupil, highlight), viewer L then R.
EYES = (
    ((((23, 53), (24, 53), (24, 54)), (23, 54), (23, 52)),
     (((36, 54),), (35, 54), (35, 53))),
    ((((25, 24), (25, 25), (27, 25)), (26, 25), (26, 24)),
     (((39, 24), (39, 25), (38, 26)), (38, 25), (38, 24))),
    ((((25, 55), (26, 56), (26, 57), (25, 57)), (25, 56), (26, 55)),
     (((39, 56), (39, 57), (38, 57)), (38, 56), (38, 55))),
    ((((29, 53), (29, 54), (30, 54), (31, 53), (32, 54)), (31, 54), (30, 53)),
     (((46, 54), (48, 54), (48, 55), (46, 55)), (47, 55), (47, 54))),
)
NAMES = ('graveyard-b', 'nebula-b', 'foundry-b', 'citadel-b')


class StoryEyesTests(unittest.TestCase):
    def tearDown(self):
        selected_rd_oracle.original_panels.cache_clear()

    def test_all_eight_eyes_in_both_quantizers_and_displayed_palette(self):
        for reader in (selected_rd.panels, selected_rd_oracle.original_panels):
            panels = reader()
            for index, eyes in enumerate(EYES):
                shown = selected_rd_oracle.scene_rgb(index * 3)
                for eye in eyes:
                    for points, ink, rgb in ((eye[0], 15, (68, 187, 221)),
                                             ((eye[1],), 1, (17, 17, 34)),
                                             ((eye[2],), 7, (255, 255, 255))):
                        for x, y in points:
                            self.assertEqual(panels[index][y][x], ink, (index, x, y))
                            self.assertEqual(shown[y][x], rgb)

    def test_exact_masks_and_unchanged_surrounds(self):
        provenance = json.loads((DERIVATIVE / 'provenance.json').read_text())
        for index, name in enumerate(NAMES):
            original = load_png_rgba(ART / f'{name}.png')
            edited = load_png_rgba(DERIVATIVE / f'{name}.png')
            mask = load_png_rgba(DERIVATIVE / f'{name}.mask.png')
            expected = {p for blue, pupil, glint in EYES[index] for p in (*blue, pupil, glint)}
            self.assertEqual(original[:2], (160, 96))
            self.assertEqual(edited[:2], original[:2])
            self.assertEqual(mask[:2], original[:2])
            changed = set()
            for i, (before, after, mask_pixel) in enumerate(zip(original[2], edited[2], mask[2])):
                point = (i % 160, i // 160)
                self.assertEqual(mask_pixel, (255, 255, 255, 255) if point in expected else (0, 0, 0, 255))
                if before != after:
                    changed.add(point)
                    self.assertIn(point, expected)
            self.assertEqual(len(changed), (4, 5, 7, 12)[index])
            self.assertEqual(changed, {tuple(p) for p in provenance['panels'][index]['changed_coordinates']})

    def test_preserved_inputs_and_ending_hashes(self):
        provenance = json.loads((DERIVATIVE / 'provenance.json').read_text())
        self.assertFalse(any('game/build/' in p for p in provenance['protected_sha256']))
        for path, expected in provenance['protected_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected, path)

    def test_entire_ending_remains_almond_source_with_existing_palette_and_border(self):
        source = selected_rd_oracle.Image.load_png(ART / 'victory-eyes-almond/victory.png')
        # Existing ending palette, independent from the ordinary derivative recipe.
        words = (0x000, 0x112, 0x224, 0x346, 0xBDF, 0x89A, 0xCEF, 0xFFF,
                 0x214, 0x536, 0xA58, 0xFA9, 0x521, 0xA43, 0xFA6, 0x4BD)
        colors = [tuple((word >> shift & 15) * 17 for shift in (8, 4, 0)) for word in words]
        mapping = {}
        actual = selected_rd.panels()[4]
        for y in range(192):
            for x in range(320):
                rgb = source.pixel(x, y)
                if rgb not in mapping:
                    mapping[rgb] = min(range(16), key=lambda i: sum((a-b)**2 for a, b in zip(rgb, colors[i])))
                expected = 7 if x < 2 or x >= 318 or y < 2 or y >= 190 else mapping[rgb]
                self.assertEqual(actual[y][x], expected)

    def test_both_readers_reject_corrupted_story_provenance(self):
        path = DERIVATIVE / 'provenance.json'
        read_text = Path.read_text
        for index in range(4):
            for field in ('original_sha256', 'output_sha256', 'rgb_sha256'):
                data = json.loads(read_text(path))
                data['panels'][index][field] = '0' * 64
                def read(candidate, *args, **kwargs):
                    return json.dumps(data) if candidate == path else read_text(candidate, *args, **kwargs)
                for reader in (selected_rd.panels, selected_rd_oracle.original_panels):
                    with self.subTest(index=index, field=field, reader=reader.__module__):
                        selected_rd_oracle.original_panels.cache_clear()
                        with patch.object(Path, 'read_text', read), self.assertRaises(AssertionError):
                            reader()

    def test_importer_rejects_corrupted_story_rgb(self):
        read_text = Path.read_text
        for name in NAMES:
            path = DERIVATIVE / f'{name}.rgb.hex'
            data = bytearray.fromhex(read_text(path))
            data[0] ^= 1
            def read(candidate, *args, **kwargs):
                return data.hex() if candidate == path else read_text(candidate, *args, **kwargs)
            with patch.object(Path, 'read_text', read), self.assertRaises(AssertionError):
                selected_rd.panels()
