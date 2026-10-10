import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("transitions", ROOT / "tools/verify-clean-transitions.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)

TRACE = """AGK intro_released
AGK cut_hold=1 bitmap=0 copper=1
AGK cut_target_ready=1
AGK cut_submit=1 phase=0 level=1 bitmap=0 copper=1 both=0 vblank=300
AGK cut_visible=1 phase=0 level=1 bitmap=0 copper=1 both=0 vblank=301
AGK music theme
AGK music_visible=1 vblank=301
AGK cut_hold=1 bitmap=1 copper=0
AGK cut_target_ready=1
AGK cut_submit=1 phase=0 level=1 bitmap=1 copper=0 both=1 vblank=400
AGK cut_visible=1 phase=0 level=1 bitmap=1 copper=0 both=1 vblank=401
AGK title_ready
"""


class PublicationEvidenceTests(unittest.TestCase):
    def test_complete_cut_then_hidden_repair(self):
        self.assertEqual(CHECK.validate(TRACE), 1)

    def test_partial_publication(self):
        with self.assertRaisesRegex(ValueError, "partial target"):
            CHECK.validate(TRACE.replace("cut_target_ready=1", "cut_target_ready=0", 1))

    def test_no_vblank_acknowledgement(self):
        with self.assertRaisesRegex(ValueError, "before vblank"):
            CHECK.validate(TRACE.replace("vblank=301", "vblank=300"))

    def test_dma_identity_mismatch(self):
        with self.assertRaisesRegex(ValueError, "identity changed"):
            CHECK.validate(TRACE.replace("cut_visible=1 phase=0 level=1 bitmap=0", "cut_visible=1 phase=0 level=1 bitmap=1"))

    def test_hold_swapped_the_hidden_buffer(self):
        with self.assertRaisesRegex(ValueError, "swapped during hold"):
            CHECK.validate(TRACE.replace("cut_hold=1 bitmap=0", "cut_hold=1 bitmap=1"))

    def test_music_started_on_old_intro(self):
        with self.assertRaisesRegex(ValueError, "theme started before"):
            CHECK.validate("AGK music theme\n" + TRACE.replace("AGK music theme\n", ""))

    def test_music_delayed_after_title(self):
        with self.assertRaisesRegex(ValueError, "not aligned"):
            CHECK.validate(TRACE.replace("music_visible=1 vblank=301", "music_visible=1 vblank=302"))

    def test_ready_before_repair(self):
        with self.assertRaisesRegex(ValueError, "before repair"):
            CHECK.validate(TRACE.replace("AGK title_ready\n", "").replace("AGK cut_hold=1 bitmap=1", "AGK title_ready\nAGK cut_hold=1 bitmap=1"))

    def test_missing_second_buffer(self):
        with self.assertRaisesRegex(ValueError, "missing hidden-buffer repair"):
            CHECK.validate(TRACE[:TRACE.index("AGK cut_hold=1 bitmap=1")])


if __name__ == "__main__":
    unittest.main()
