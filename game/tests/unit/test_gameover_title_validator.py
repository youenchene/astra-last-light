"""Deterministic parser/lifecycle regressions; no emulator or golden files needed."""
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("gameover_validator", ROOT / "tools/verify-gameover-title.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def state(frame, **changes):
    values = dict(frame=frame, phase=0, level=1, score=0, lives=3, sim=615,
                  enemy_tick=492, enemy_acc=0, pf=0, title_blocked=1, preparing=0)
    values.update(changes)
    return "AGK " + " ".join(f"{key}={value}" for key, value in values.items())


def evidence(wrapped=False):
    lines = ["AGK gameover_ready", state(100, phase=4, lives=0, title_blocked=0),
             "AGK music theme", "AGK gameover_title", state(250, preparing=1),
             state(550), state(753, phase=6, title_blocked=0),
             state(1128, phase=1, title_blocked=0)]
    text = "\n".join(lines)
    return text.replace(" enemy_acc=", "\nAGK enemy_acc=") if wrapped else text


class FrameStateTests(unittest.TestCase):
    def test_paused_continuation_retains_required_fields(self):
        text = state(123, paused=1, pattern=3)
        for split in (" enemy_acc=", " preparing=", " paused="):
            with self.subTest(split=split):
                parsed = validator.frame_states(text.replace(split, "\nAGK " + split.strip()).splitlines())
                self.assertEqual(parsed, validator.frame_states([text]))
                self.assertEqual(parsed[0][1]["paused"], 1)
        first, rest = text.split(" enemy_acc=")
        with self.assertRaisesRegex(ValueError, "incomplete frame state"):
            validator.frame_states([first, "AGK music theme", "AGK enemy_acc=" + rest])

    def test_single_line_and_wrapped_lifecycle(self):
        for wrapped in (False, True):
            with self.subTest(wrapped=wrapped):
                validator.validate(evidence(wrapped))

    def test_multiple_fragments_preserve_start_index(self):
        lines = ["AGK music theme", state(123).replace(" enemy_tick=", "\nAGK enemy_tick=")
                 .replace(" enemy_acc=", "\nAGK enemy_acc=")]
        parsed = validator.frame_states("\n".join(lines).splitlines())
        self.assertEqual(parsed, validator.frame_states(["AGK music theme", state(123)]))
        self.assertEqual(parsed[0][0], 1)

    def test_unrelated_records_do_not_merge(self):
        noise = ["AGK music theme", "AGK perf frames=50 dropped=0 load=19 maxload=29",
                 "AGK event phase=9 score=999", "AGK qa_scene=0 frame=999", "AGK sfx warp"]
        lines = [state(10), *noise, "AGK enemy_acc=4 pf=999", state(20)]
        parsed = validator.frame_states(lines)
        self.assertEqual([i for i, _ in parsed], [0, 7])
        self.assertEqual([s["frame"] for _, s in parsed], [10, 20])
        self.assertTrue(all(s["enemy_acc"] == 0 and s["pf"] == 0 for _, s in parsed))

    def test_truncated_record_does_not_inherit_fields(self):
        for ending in ([], [state(30)], ["AGK music theme", "AGK enemy_acc=0 pf=0"]):
            with self.subTest(ending=ending):
                lines = [state(10), state(20).split(" enemy_acc=")[0], *ending]
                with self.assertRaisesRegex(ValueError, "incomplete frame state at line 2: missing.*pf"):
                    validator.frame_states(lines)

    def test_missing_field_and_malformed_or_duplicate_values(self):
        for line, message in ((state(10).replace(" pf=0", ""), "missing pf"),
                              (state(10) + " pf=1", "duplicate"),
                              (state(10) + " broken=", "malformed")):
            with self.subTest(line=line), self.assertRaisesRegex(ValueError, message):
                validator.frame_states([line])

    def test_marker_cannot_reorder_a_partial_state(self):
        first, continuation = state(100).split(" enemy_acc=")
        with self.assertRaisesRegex(ValueError, "incomplete frame state at line 1"):
            validator.frame_states([first, "AGK gameover_ready", "AGK enemy_acc=" + continuation])


class EvidenceTests(unittest.TestCase):
    def test_missing_evidence_has_clear_errors(self):
        cases = [("", "missing frame state evidence"),
                 (state(1), "expected exactly one marker"),
                 (state(1) + "\nAGK gameover_ready", "missing frame state after"),
                 (evidence().rsplit("\n", 2)[0], "missing fresh-press SECTOR_INTRO"),
                 (evidence().rsplit("\n", 1)[0], "fresh press did not reach PLAY")]
        for text, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                validator.validate(text)

    def test_bad_timing_reset_clocks_and_guard_remain_rejected(self):
        cases = [(state(250, preparing=1), state(249, preparing=1), "150 ready ticks"),
                 (state(250, preparing=1), state(250, preparing=1, score=123), "reset/guard"),
                 (state(250, preparing=1), state(250, preparing=1, lives=0), "reset/guard"),
                 (state(250, preparing=1), state(250, preparing=1, level=2), "default TITLE"),
                 (state(250, preparing=1), state(250, preparing=1, enemy_acc=1), "clock changed"),
                 (state(550), state(550, title_blocked=0), "held fire unblocked"),
                 (state(550), state(550, preparing=1), "never completed composition"),
                 (state(753, phase=6, title_blocked=0), state(749, phase=6, title_blocked=0), "held input restarted")]
        for before, after, message in cases:
            for wrapped in (False, True):
                text = evidence().replace(before, after)
                if wrapped:
                    text = text.replace(" enemy_acc=", "\nAGK enemy_acc=")
                with self.subTest(message=message, wrapped=wrapped), self.assertRaisesRegex(ValueError, message):
                    validator.validate(text)

    def test_native_errors_remain_rejected(self):
        with self.assertRaisesRegex(ValueError, "native error"):
            validator.validate(evidence() + "\nAGK bullet_hidden=1")


if __name__ == "__main__":
    unittest.main()
