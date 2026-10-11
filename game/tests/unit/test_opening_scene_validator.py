import importlib.util
from pathlib import Path
import unittest
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from selected_rd_oracle import scene_rgb
SPEC = importlib.util.spec_from_file_location("campaign", ROOT / "tools/check-campaign-native.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class Image:
    def __init__(self, scene, hero=None):
        self.pixels = {}
        panel = scene_rgb(scene)
        x0, y0 = (0, 32) if scene == 12 else (144, 68)
        for y, row in enumerate(panel):
            for x, color in enumerate(row):
                self.pixels[x0 + x, y0 + y] = color
        if hero is not None:
            colors, frames = CHECK.artwork("hero32")
            colors["4"] = (85, 102, 136)
            for y, row in enumerate(frames[hero]):
                for x, ink in enumerate(row):
                    if ink not in (".", "0"):
                        self.pixels[32 + x, 126 + y] = colors[ink]

    def pixel(self, x, y):
        return self.pixels.get((x, y), (0, 0, 17))


class OpeningSceneTests(unittest.TestCase):
    def test_opening_allows_exact_hero_animation(self):
        CHECK.check_scene_pair(Image(0, 0), Image(0, 1), 0)

    def test_opening_requires_visible_hero(self):
        with self.assertRaisesRegex(ValueError, "hero artwork missing"):
            CHECK.check_scene_pair(Image(0), Image(0, 1), 0)

    def test_all_stories_require_stationary_source_exact_ship(self):
        for scene in range(12):
            CHECK.check_scene_pair(Image(scene, 0), Image(scene, 1), scene)
            with self.assertRaisesRegex(ValueError, "hero artwork missing"):
                CHECK.check_scene_pair(Image(scene), Image(scene, 1), scene)

    def test_opening_exterior_and_window_never_masked(self):
        for point in ((0, 56), (152, 56), (192, 72), (31, 126)):
            with self.subTest(point=point):
                late = Image(0, 1)
                late.pixels[point] = (1, 2, 3)
                with self.assertRaisesRegex(ValueError, "frozen exterior"):
                    CHECK.check_scene_pair(Image(0, 0), late, 0)

    def test_identically_corrupt_panel_is_rejected_against_master(self):
        early, late = Image(0, 0), Image(0, 1)
        early.pixels[192, 72] = late.pixels[192, 72] = (1, 2, 3)
        with self.assertRaisesRegex(ValueError, "selected RD source"):
            CHECK.check_scene_pair(early, late, 0)

    def test_ending_has_no_hero_exception(self):
        CHECK.check_scene_pair(Image(12), Image(12), 12)
        with self.assertRaisesRegex(ValueError, "selected RD source"):
            CHECK.check_scene_pair(Image(12, 0), Image(12, 0), 12)

    def test_later_frozen_scene_accepted(self):
        CHECK.check_scene_pair(Image(1, 0), Image(1, 0), 1)


if __name__ == "__main__":
    unittest.main()
