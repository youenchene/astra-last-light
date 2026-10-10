import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("bob_check", ROOT / "tools/verify-bob-restoration.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def state(frame, **updates):
    values = dict.fromkeys(CHECK.STATE_PARSER.STATE_FIELDS, 0)
    values.update(frame=frame, phase=1, level=1, lives=3)
    values.update(updates)
    # Exercise the actual enemy_acc continuation boundary, without field carryover.
    second = {key: values.pop(key) for key in ("enemy_acc", "pf", "scene_ready", "preparing", "pattern", "title_blocked")}
    values.pop("frame")
    return "AGK frame=" + str(frame) + " " + " ".join(f"{k}={v}" for k, v in values.items()) + \
        "\nAGK " + " ".join(f"{k}={v}" for k, v in second.items())


EVIDENCE = dict(ready_updates=1, kill1=9, death_tick=19, death_stage=20,
                drop_stage=30, pickup_stage=40)
TRACE = "\n".join((
    state(615, phase=6, scene_ready=1, pf=0),
    state(765, preparing=1),
    "AGK combat_ready", state(976),
    state(986, score=100, wave=1, stage=10, sim=10),
    state(996, phase=9, stage=20, sim=20, score=500, wave=1, lives=2),
    state(1026, phase=9, stage=20, sim=20, score=500, wave=1, lives=2, pf=30),
    state(1036, stage=20, sim=20, score=500, wave=1, lives=2),
    "AGK bonus_drop", state(1046, stage=30, sim=30, score=600, wave=1, lives=2),
    "AGK bonus_pickup", state(1056, stage=40, sim=40, score=600, wave=1, lives=2, weapon=1),
))


class BobLifecycleTests(unittest.TestCase):
    def test_wrapped_state_zero_age_ack_and_ready_update(self):
        CHECK.verify_lifecycle_text(TRACE, EVIDENCE)

    def test_one_tick_old_scene_ack_still_counts_exact_dwell(self):
        CHECK.verify_lifecycle_text(TRACE.replace("frame=615", "frame=616").replace("pf=0 scene_ready=1", "pf=1 scene_ready=1"), EVIDENCE)

    def test_scene_dwell_not_relaxed(self):
        with self.assertRaisesRegex(ValueError, "150 acknowledged"):
            CHECK.verify_lifecycle_text(TRACE.replace("frame=765", "frame=764"), EVIDENCE)

    def test_truncated_state_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete frame state"):
            CHECK.verify_lifecycle_text(TRACE.replace("preparing=0", "", 1), EVIDENCE)

    def test_no_real_drop_rejected(self):
        with self.assertRaisesRegex(ValueError, "genuine six-kill"):
            CHECK.verify_lifecycle_text(TRACE.replace("AGK bonus_drop", "AGK unrelated"), EVIDENCE)

    def test_no_real_collection_rejected(self):
        with self.assertRaisesRegex(ValueError, "genuine pickup"):
            CHECK.verify_lifecycle_text(TRACE.replace("AGK bonus_pickup", "AGK unrelated"), EVIDENCE)

    def test_milestone_offset_rejected(self):
        with self.assertRaisesRegex(ValueError, "first kill"):
            CHECK.verify_lifecycle_text(TRACE.replace("frame=986", "frame=987"), EVIDENCE)

    def test_death_pause_must_remain_40(self):
        with self.assertRaisesRegex(ValueError, "40 ticks"):
            CHECK.verify_lifecycle_text(TRACE.replace("frame=1036", "frame=1035"), EVIDENCE)


if __name__ == "__main__":
    unittest.main()
