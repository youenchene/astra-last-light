import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("campaign", ROOT / "tools/check-campaign-native.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def trace(flashes=(6, 4, 2, 6)):
    return "\n".join(
        f"AGK qa_flash={level} x=240 y=88 hp={hp - 6} maxhp={hp} flash={flash} tick={80 + level}"
        for level, hp, flash in zip(range(1, 5), (216, 336, 432, 480), flashes))


class FlashEvidenceTests(unittest.TestCase):
    def test_even_snapshot_independent_of_motion_tick(self):
        self.assertEqual(len(CHECK.check_flashes(trace())), 4)

    def test_old_tick82_odd_snapshot_rejected(self):
        old = trace((5, 4, 2, 6)).replace("tick=81", "tick=82")
        with self.assertRaisesRegex(ValueError, "not a white half"):
            CHECK.check_flashes(old)

    def test_zero_odd_and_out_of_range_flash_rejected(self):
        for flash in (0, 1, 3, 5, 8):
            with self.subTest(flash=flash), self.assertRaisesRegex(ValueError, "not a white half"):
                CHECK.check_flashes(trace((flash, 4, 2, 6)))

    def test_missing_sector_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly one flash"):
            CHECK.check_flashes("\n".join(trace().splitlines()[:-1]))

    def test_duplicate_sector_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly one flash"):
            CHECK.check_flashes(trace() + "\n" + trace().splitlines()[0])

    def test_changed_maxhp_rejected(self):
        with self.assertRaisesRegex(ValueError, "changed maxHp"):
            CHECK.check_flashes(trace().replace("maxhp=336", "maxhp=168"))

    def test_wrong_damage_rejected(self):
        with self.assertRaisesRegex(ValueError, "six damage"):
            CHECK.check_flashes(trace().replace("hp=210 ", "hp=211 "))


if __name__ == "__main__":
    unittest.main()
