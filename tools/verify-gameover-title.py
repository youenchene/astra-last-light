#!/usr/bin/env python3
"""Validate ordinary-input gameover_title serial evidence without changing goldens.

Run after tools/agk run -f game/tests/native/gameover_title.agk on each profile.
Pass its serial.txt path; captures still require visual inspection.
"""
import argparse
from pathlib import Path
import re


STATE_FIELDS = set("frame phase level score lives boss x y weapon speed shield wave hostile_bullets "
                   "bullet4 bullet5 bullet6 bullet7 bullet_hidden shot_bobs enemies effects stage sim "
                   "enemy_tick enemy_acc pf title_blocked scene scene_ready preparing paused pattern".split())
REQUIRED_FIELDS = set("frame phase level score lives sim enemy_tick enemy_acc pf title_blocked preparing".split())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def frame_states(lines):
    """Join contiguous AGK state fragments, retaining the frame line's index.

    AGK may flush its bounded line buffer before enemy_acc (or another field).
    Only pure, known state key/value lines can continue a frame record. Events,
    music, perf and marker lines end it; no fields carry across record boundaries.
    """
    states, current, start = [], None, 0

    def finish():
        if current is not None:
            missing = REQUIRED_FIELDS - current.keys()
            require(not missing, f"incomplete frame state at line {start + 1}: missing {', '.join(sorted(missing))}")
            states.append((start, current))

    for index, line in enumerate(lines):
        numeric = re.fullmatch(r"AGK (?:\w+=-?\d+)(?: +\w+=-?\d+)* *", line)
        pairs = re.findall(r"(\w+)=(-?\d+)", line) if numeric else []
        values = {key: int(value) for key, value in pairs}
        is_state = bool(values) and values.keys() <= STATE_FIELDS
        if line.startswith("AGK frame="):
            finish()
            require(is_state, f"malformed frame state at line {index + 1}")
            current, start = {}, index
        elif not (is_state and "frame" not in values and current is not None):
            finish()
            current = None
            continue
        require(len(values) == len(pairs) and not (values.keys() & current.keys()),
                f"duplicate frame state fields at line {index + 1}")
        current.update(values)
    finish()
    require(states, "missing frame state evidence")
    return states


def validate(text):
    lines = text.splitlines()
    states = frame_states(lines)

    def after(marker):
        matches = [i for i, line in enumerate(lines) if line == marker]
        require(len(matches) == 1, f"{marker}: expected exactly one marker, got {len(matches)}")
        following = next(((i, s) for i, s in states if i > matches[0]), None)
        require(following is not None, f"missing frame state after {marker}")
        return following

    _, ready = after("AGK gameover_ready")
    returned_line, returned = after("AGK gameover_title")
    require(ready["phase"] == 4 and ready["lives"] == 0 and ready["pf"] == 0, f"invalid GAMEOVER ready state: {ready}")
    require(returned["frame"] - ready["frame"] == 150, "GAMEOVER dwell is not 150 ready ticks")
    require(returned["phase"] == 0 and returned["level"] == 1, "GAMEOVER did not return to default TITLE")
    require(returned["lives"] == 3 and returned["score"] == 0 and returned["title_blocked"] == 1,
            "returned TITLE reset/guard is invalid")
    for key in ("sim", "enemy_tick", "enemy_acc"):
        require(returned[key] == ready[key], f"clock changed during gameover: {key}")
    later = [s for i, s in states if i > returned_line]
    intro = next((s for s in later if s["phase"] == 6), None)
    require(intro is not None, "missing fresh-press SECTOR_INTRO evidence")
    require(intro["frame"] - returned["frame"] >= 500, "held input restarted title")
    held = [s for s in later if s["frame"] < intro["frame"]]
    require(held and all(s["phase"] == 0 and s["level"] == 1 for s in held), "invalid held TITLE state")
    guarded = [s for s in held if s["frame"] < returned["frame"] + 500]
    require(guarded and all(s["title_blocked"] == 1 for s in guarded), "held fire unblocked title")
    require(any(s["preparing"] == 0 for s in guarded), "title never completed composition")
    require(intro["level"] == 1 and intro["lives"] == 3 and intro["score"] == 0, "fresh-press reset is invalid")
    require(any(s["phase"] == 1 and s["frame"] > intro["frame"] for s in later), "fresh press did not reach PLAY")
    require(not re.search(r"bullet_hidden=[1-9]|ERR|STACK SMASHED|allocation failure", text), "native error in serial evidence")


def check(path):
    validate(path.read_text())
    print(f"PASS {path}: 150 ready ticks, reset, held title guard, fresh-press restart")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("serial", type=Path, nargs="+")
    for path in parser.parse_args().serial:
        try:
            check(path)
        except (ValueError, OSError) as error:
            parser.exit(1, f"FAIL {path}: {error}\n")
