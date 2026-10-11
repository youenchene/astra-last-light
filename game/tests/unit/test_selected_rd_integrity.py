"""Provenance guards reject changed assets independently of packed-row checks."""
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
ALMOND = ART / 'victory-eyes-almond'
PEACH_ADDITIONS = {(80, 88), (80, 89), (81, 88), (82, 88),
                   (83, 88), (113, 88), (114, 88)}


class SelectedRDIntegrityTests(unittest.TestCase):
    def tearDown(self):
        selected_rd_oracle.original_panels.cache_clear()

    def test_importer_matches_independent_png_oracle(self):
        self.assertEqual(selected_rd.panels(), selected_rd_oracle.original_panels())

    def test_ending_face_is_peach_and_sky_stays_orange(self):
        source = selected_rd_oracle.Image.load_png(
            ROOT / 'game/art/selected-rd/victory-identity-master/victory.png')
        inks = selected_rd.panels()[4]
        displayed = selected_rd_oracle.scene_rgb(12)
        skin = [(x, y) for y in range(88, 104) for x in range(80, 115)
                if source.pixel(x, y) == (252, 169, 139)]
        self.assertEqual(len(skin), 498)
        for x, y in skin:
            self.assertEqual(inks[y][x], 11)
            self.assertEqual(displayed[y][x], (255, 170, 153))
        self.assertEqual(inks[10][10], 14)
        self.assertEqual(displayed[10][10], (255, 170, 102))

    def test_almond_preserves_original_skin_with_exact_seven_additions(self):
        parent = selected_rd_oracle.Image.load_png(ART / 'victory-identity-master/victory.png')
        candidate = selected_rd_oracle.Image.load_png(ALMOND / 'victory.png')
        def skin(image):
            return {(x, y) for y in range(88, 104) for x in range(80, 115)
                    if image.pixel(x, y) == (252, 169, 139)}
        original, current = skin(parent), skin(candidate)
        self.assertEqual(len(original), 498)
        self.assertEqual(original - current, set())
        self.assertEqual(current - original, PEACH_ADDITIONS)
        inks = selected_rd.panels()[4]
        displayed = selected_rd_oracle.scene_rgb(12)
        for x, y in PEACH_ADDITIONS:
            self.assertEqual(inks[y][x], 11)
            self.assertEqual(displayed[y][x], (255, 170, 153))

    def test_almond_changes_only_original_eye_masks_at_both_resolutions(self):
        record = json.loads((ART / 'victory-eyes-refined/request.json').read_text())
        spans = record['eye_spans_y_xmin_xmax_inclusive']
        master_mask = {(x, y) for eye in spans for y, left, right in eye for x in range(left, right+1)}
        for filename, mask_file, size, expected_changes in (
            ('master.png', 'master-mask.png', (480, 288), 671),
            ('victory.png', 'runtime-mask.png', (320, 192), 299),
        ):
            with self.subTest(resolution=size):
                width, height = size
                parent = load_png_rgba(ART / 'victory-identity-master' / filename)
                candidate = load_png_rgba(ALMOND / filename)
                mask = load_png_rgba(ALMOND / mask_file)
                self.assertEqual(parent[:2], size)
                self.assertEqual(candidate[:2], size)
                self.assertEqual(mask[:2], size)
                changed = 0
                for y in range(height):
                    for x in range(width):
                        source_xy = (x, y) if width == 480 else ((2*x+1)*480//640, (2*y+1)*288//384)
                        editable = source_xy in master_mask
                        i = y*width+x
                        self.assertEqual(mask[2][i], (255, 255, 255, 255) if editable else (0, 0, 0, 255))
                        if parent[2][i] != candidate[2][i]:
                            changed += 1
                            self.assertTrue(editable, (filename, x, y))
                self.assertEqual(changed, expected_changes)

    def test_both_readers_reject_wrong_provenance_hashes(self):
        path = ALMOND / 'provenance.json'
        provenance = json.loads(path.read_text())
        read_text = Path.read_text
        for field in ('input_sha256', 'master_sha256', 'image_sha256', 'rgb_sha256'):
            altered = dict(provenance, **{field: '0' * 64})
            def read(candidate, *args, **kwargs):
                return json.dumps(altered) if candidate == path else read_text(candidate, *args, **kwargs)
            for reader in (selected_rd.panels, selected_rd_oracle.original_panels):
                with self.subTest(field=field, reader=reader.__module__):
                    selected_rd_oracle.original_panels.cache_clear()
                    with patch.object(Path, 'read_text', read), self.assertRaises(AssertionError):
                        reader()

    def test_importer_rejects_changed_rgb_export(self):
        path = ALMOND / 'victory.rgb.hex'
        rgb = bytearray.fromhex(path.read_text())
        rgb[0] ^= 1
        read_text = Path.read_text
        def read(candidate, *args, **kwargs):
            return rgb.hex() if candidate == path else read_text(candidate, *args, **kwargs)
        with patch.object(Path, 'read_text', read), self.assertRaises(AssertionError):
            selected_rd.panels()
