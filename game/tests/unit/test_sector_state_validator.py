import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("sector_state", ROOT / "tools/verify-sector-state.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def state(frame, level=2, **changes):
    values = dict(frame=frame, phase=6, level=level, score=0, lives=3, stage=0, sim=0,
                  enemy_tick=0, enemy_acc=0, pf=0, title_blocked=0, scene=3 * (level - 1),
                  scene_ready=1, preparing=0, wave=0, enemies=0, hostile_bullets=0)
    values.update(changes)
    return "AGK " + " ".join(f"{key}={value}" for key, value in values.items())


def trace(level=2):
    return "\n".join((state(100, level), state(300, level, phase=1, scene_ready=0,
        stage=50, sim=50, wave=1, enemies=6, hostile_bullets=5)))


class SectorStateTests(unittest.TestCase):
    def test_all_scenarios_accept_wrapping_and_intervening_clock_fields(self):
        for scenario, level in CHECK.SCENARIOS.items():
            for split in (None, " enemy_acc=", " scene=", " sim="):
                text = trace(level)
                if split:
                    text = text.replace(split, "\nAGK " + split.strip())
                with self.subTest(scenario=scenario, split=split):
                    CHECK.validate(text, scenario)

    def test_wrong_scene_rejected(self):
        with self.assertRaisesRegex(ValueError, "same-record ready sector opening"):
            CHECK.validate(trace().replace("scene=3", "scene=6"), "sector2")

    def test_scene_and_readiness_cannot_come_from_other_records(self):
        for bad in (dict(scene=6), dict(scene_ready=0), dict(preparing=1)):
            text = "\n".join((state(90, **bad), state(95, phase=0), trace().splitlines()[1]))
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "same-record ready sector opening"):
                CHECK.validate(text, "sector2")

    def test_missing_fields_never_borrowed_from_next_state(self):
        for field in ("scene=3", "scene_ready=1", "stage=0", "sim=0", "preparing=0"):
            text = trace().replace(" " + field, "", 1)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "incomplete.*missing"):
                CHECK.validate(text, "sector2")

    def test_marker_between_fragments_rejected(self):
        text = trace().replace(" enemy_acc=", "\nAGK music sector2\nAGK enemy_acc=", 1)
        with self.assertRaisesRegex(ValueError, "incomplete frame state"):
            CHECK.validate(text, "sector2")

    def test_campaign_fresh_combat_clocks_and_barrage_remain_required(self):
        for before, after, message in (("stage=0", "stage=1", "zero stage/sim"),
                                       ("sim=0", "sim=1", "zero stage/sim"),
                                       ("hostile_bullets=5", "hostile_bullets=0", "barrage")):
            with self.subTest(before=before), self.assertRaisesRegex(ValueError, message):
                CHECK.validate(trace(1).replace(before, after), "campaign_waves")

    def test_play_formation_must_be_same_record_and_after_opening(self):
        for text in ("\n".join(reversed(trace().splitlines())),
                     trace().replace("enemies=6", "enemies=5"),
                     trace().replace("phase=1", "phase=2"),
                     trace().replace("scene_ready=0", "scene_ready=1")):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "six-member PLAY"):
                CHECK.validate(text, "sector2")

    def test_launcher_result_rejects_bad_evidence_before_goldens(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "serial.txt"
            path.write_text(trace().replace("scene=3", "scene=6"))
            result = CHECK.check_result({"ok": True, "failures": []}, "sector2", folder)
            self.assertFalse(result["ok"])
            self.assertIn("same-record", result["failures"][0])
            path.write_text(trace())
            self.assertTrue(CHECK.check_result({"ok": True, "failures": []}, "sector2", folder)["ok"])


if __name__ == "__main__":
    unittest.main()
