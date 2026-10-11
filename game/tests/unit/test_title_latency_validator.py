import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("latency", ROOT / "tools/verify-title-latency.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)

TRACE = """AGK title_input=2 phase=0 level=2 vblank=100
AGK cut_submit=2 phase=0 level=2 bitmap=0 copper=1 both=0 vblank=123
AGK cut_visible=2 phase=0 level=2 bitmap=0 copper=1 both=0 vblank=124
AGK cut_submit=2 phase=0 level=2 bitmap=1 copper=0 both=1 vblank=147
AGK cut_visible=2 phase=0 level=2 bitmap=1 copper=0 both=1 vblank=148
"""


class TitleLatencyTests(unittest.TestCase):
    def launch_trace(self):
        lines = ["AGK title_confirm_input=1 vblank=100", "AGK sfx confirm"]
        for step in range(1, 7):
            lines += [f"AGK title_confirm_submit={step} vblank={120 + step}",
                      f"AGK title_confirm_visible={step} level=1 vblank={121 + step}"]
        lines += ["AGK title_input=12 phase=6 level=1 vblank=127",
                  "AGK cut_visible=12 phase=6 level=1 both=1 vblank=300",
                  "AGK publication_ready=12 phase=6 level=1 scene_ready=1 preparing=0 vblank=300",
                  "AGK cut_visible=13 phase=1 level=1 both=1 vblank=500",
                  "AGK publication_ready=13 phase=1 level=1 scene_ready=0 preparing=0 vblank=500"]
        return "\n".join(lines) + "\n"

    def test_launch_origin_is_accepted_fire_not_scene_transition(self):
        self.assertEqual(CHECK.launch_timing(self.launch_trace()),
                         dict(chime_request=21, first_feedback=22, playable_opening=200, combat=400))

    def test_launch_rejects_duplicate_chime(self):
        with self.assertRaises(ValueError):
            CHECK.launch_timing(self.launch_trace() + "AGK sfx confirm\n")

    def test_launch_rejects_early_weapon_and_warp(self):
        for sound in ("shot", "lance", "warp"):
            with self.assertRaisesRegex(ValueError, "weapon/warp during launch"):
                CHECK.launch_timing(self.launch_trace().replace(
                    "AGK publication_ready=12", f"AGK sfx {sound}\nAGK publication_ready=12"))

    def test_launch_allows_live_opening_fire_and_later_warp(self):
        trace = self.launch_trace().replace(
            "AGK cut_visible=13", "AGK sfx shot\nAGK sfx lance\nAGK sfx warp\nAGK cut_visible=13")
        self.assertEqual(CHECK.launch_timing(trace), CHECK.launch_timing(self.launch_trace()))

    def test_launch_rejects_hidden_or_unacknowledged_opening(self):
        for before, after in (("scene_ready=1", "scene_ready=0"),
                              ("preparing=0", "preparing=1"),
                              ("both=1", "both=0")):
            with self.assertRaises(ValueError):
                CHECK.launch_timing(self.launch_trace().replace(before, after))

    def test_launch_requires_six_published_frames(self):
        with self.assertRaisesRegex(ValueError, "six confirmation"):
            CHECK.launch_timing(self.launch_trace().replace("title_confirm_visible=6", "unpublished=6"))

    def test_elapsed_vblanks(self):
        self.assertEqual(CHECK.validate(TRACE, False), [(2, 0, 2, 24, 48)])

    def test_late_first_visible(self):
        with self.assertRaisesRegex(ValueError, "first-visible"):
            CHECK.validate(TRACE.replace("vblank=124", "vblank=141"), False)

    def test_late_both_ready(self):
        with self.assertRaisesRegex(ValueError, "both-ready"):
            CHECK.validate(TRACE.replace("vblank=148", "vblank=181"), False)

    def test_no_repair(self):
        with self.assertRaisesRegex(ValueError, "never ready"):
            CHECK.validate(TRACE[:TRACE.index("AGK cut_submit=2 phase=0 level=2 bitmap=1")], False)

    def test_wrong_sector(self):
        with self.assertRaisesRegex(ValueError, "wrong selection"):
            CHECK.validate(TRACE.replace("title_input=2 phase=0 level=2", "title_input=2 phase=0 level=3"), False)

    def test_reused_physical_bitmap(self):
        with self.assertRaisesRegex(ValueError, "hidden repair"):
            CHECK.validate(TRACE.replace("bitmap=1", "bitmap=0"), False)

    def test_no_vblank_acknowledgement(self):
        with self.assertRaisesRegex(ValueError, "after vblank"):
            CHECK.validate(TRACE.replace("vblank=124", "vblank=123"), False)

    def test_stale_target_after_retap(self):
        text = TRACE.replace("AGK cut_submit=2", "AGK title_input=3 phase=0 level=3 vblank=102\nAGK cut_submit=2", 1)
        with self.assertRaisesRegex(ValueError, "stale selection"):
            CHECK.validate(text, False)

    def test_missing_coverage(self):
        with self.assertRaisesRegex(ValueError, "sectors/wraps"):
            CHECK.validate(TRACE)


if __name__ == "__main__":
    unittest.main()
