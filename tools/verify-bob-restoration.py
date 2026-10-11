#!/usr/bin/env python3
"""Check actual 320x256 emulator captures against host BOB restoration evidence.

First run game/build/plan-bonus-flight --write, then run bob_restore.agk in
the emulator. Example (uses AGK's stdlib-only PNG reader):
  python3 tools/verify-bob-restoration.py --drop PATH/bonus_drop.screen.png \
      --restored PATH/bob_restored.screen.png

The restoration ROI is the union of aligned 32x16 ACE backup rectangles
across the first pickup's lifetime, not merely its final 16x16 image. Host
replay excludes visible sprites and the hero over the final three states.
Every restored pixel must match the selected PNG plus exact XOR-star history. The drop check proves
the entire opaque D artwork AND transparent mask against actual pixels.
"""

import argparse
import importlib.util
import json
import os
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
KIT = Path(os.environ.get("AGK_KIT", str(Path.home() / "Code/amiga/amiga-game-kit")))
sys.path.insert(0, str(KIT / "harness"))
_spec = importlib.util.spec_from_file_location("gameover_states", ROOT / "tools/verify-gameover-title.py")
STATE_PARSER = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(STATE_PARSER)
from galaxy_oracle import pixel as background_pixel


def first_bonus():
    """Read source pixels; index 4 is overridden by the gameplay star palette."""
    colors = {}
    rows = []
    collecting = False
    for line in (ROOT / "game/art/bonuses.txt").read_text().splitlines():
        line = line.strip()
        if line == "frame":
            if collecting:
                break
            collecting = True
        elif collecting:
            rows.append(line)
        elif len(line.split()) == 2 and line.split()[1].startswith("0x"):
            symbol, value = line.split()
            rgb = int(value, 16)
            colors[symbol] = tuple(((rgb >> shift) & 15) * 17 for shift in (8, 4, 0))
    colors["4"] = (187, 221, 255)
    if len(rows) != 16 or any(len(row) != 16 for row in rows):
        raise ValueError("expected a 16x16 first bonus frame")
    return colors, rows


def image(path):
    from agk.image import Image
    source = Image.load_png(str(path))
    if (source.width, source.height) != (320, 256):
        raise ValueError(f"{path}: expected 320x256 game-coordinate screenshot")
    return source


def verify_restore(restored, roi, ticks):
    x0, y0, x1, y1 = roi
    if not (0 <= x0 < x1 <= 320 and 56 <= y0 < y1 <= 216):
        raise ValueError(f"invalid gameplay ROI: {roi}")
    bad = [(x, y, restored.pixel(x, y))
           for y in range(y0, y1) for x in range(x0, x1)
           if restored.pixel(x, y) != background_pixel(0, ticks, x, y)]
    if bad:
        raise ValueError(f"restoration: {len(bad)} non-background pixels; first={bad[:8]}")
    print(f"PASS restoration: all {(x1-x0)*(y1-y0)} pixels in {roi} match PNG + exact stars at tick {ticks}")


def verify_drop(drop, bounds, x_adjust, ticks):
    colors, rows = first_bonus()
    x0, y0, x1, y1 = bounds
    x0 += x_adjust
    if (x1 - bounds[0], y1 - y0) != (16, 16) or not (0 <= x0 <= 304 and 56 <= y0 <= 200):
        raise ValueError(f"invalid drop BOB: {bounds}")
    bad = []
    opaque = 0
    for dy, row in enumerate(rows):
        for dx, symbol in enumerate(row):
            actual = drop.pixel(x0 + dx, y0 + dy)
            if symbol == ".":
                correct = actual == background_pixel(0, ticks, x0 + dx, y0 + dy)
            else:
                opaque += 1
                correct = actual == colors[symbol]
            if not correct:
                bad.append((x0 + dx, y0 + dy, symbol, actual))
    if bad:
        raise ValueError(f"drop artwork/mask: {len(bad)} mismatches; first={bad[:8]}")
    print(f"PASS drop: {opaque} opaque artwork pixels and {256-opaque} transparent pixels at ({x0},{y0})")


def verify_lifecycle(path, evidence):
    """Check native video/stage clocks without assuming frame resets at start."""
    verify_lifecycle_text(path.read_text(), evidence)


def verify_lifecycle_text(text, evidence):
    reports = [state for _, state in STATE_PARSER.frame_states(text.splitlines())]
    ready_tail = text.split("AGK combat_ready\n", 1)[1]
    match = re.search(r"AGK frame=(\d+)", ready_tail)
    if not match:
        raise ValueError("missing combat_ready state report")
    start = int(match[1])
    initial = next(s for s in reports if s["frame"] == start)
    if initial["stage"] or initial["sim"] or initial["preparing"]:
        raise ValueError("combat_ready must precede the first simulation tick")
    scene = next(s for s in reports if s["phase"] == 6 and s["scene_ready"])
    entered = next(s for s in reports if s["phase"] == 1)
    if entered["frame"] - scene["frame"] + scene["pf"] != 150:
        raise ValueError("sector scene did not dwell exactly 150 acknowledged ticks")
    ready_updates = evidence["ready_updates"]
    first_kill = next(s for s in reports if s["score"] == 100)
    if first_kill["frame"] - start != evidence["kill1"] + ready_updates:
        raise ValueError("native first kill differs from host replay")
    drop = next(s for s in reports if s["stage"] == evidence["drop_stage"] and s["score"] == 600)
    if drop["wave"] != 1 or drop["enemies"] or "AGK bonus_drop" not in text:
        raise ValueError("first formation did not produce genuine six-kill bonus")
    pickup = next(s for s in reports if s["stage"] == evidence["pickup_stage"] and s["weapon"] == 1)
    if "AGK bonus_pickup" not in text or pickup["frame"] <= drop["frame"]:
        raise ValueError("missing genuine pickup after clear")
    death_frame = start + evidence["death_tick"] + ready_updates
    death = next(s for s in reports if s["frame"] == death_frame)
    resumed = next(s for s in reports if s["frame"] > death_frame and s["phase"] != 9)
    if death["phase"] != 9 or resumed["frame"] - death_frame != 40:
        raise ValueError("hero death did not pause for exactly 40 ticks")
    frozen = ("stage", "sim", "wave", "score", "lives")
    for state in reports:
        if death_frame <= state["frame"] <= resumed["frame"]:
            if any(state[key] != death[key] for key in frozen):
                raise ValueError(f"simulation advanced during hero death: {state}")
    if death["stage"] != evidence["death_stage"]:
        raise ValueError("native death stage differs from host replay")
    print(f"PASS lifecycle: combat starts at frame {start}, scene dwell150, hero pause40 at stage {death['stage']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=ROOT / "game/tests/bonus-flight.json")
    parser.add_argument("--drop", type=Path, required=True)
    parser.add_argument("--restored", type=Path, required=True)
    parser.add_argument("--lifecycle-serial", type=Path,
                        help="asteroids replay serial log: verify scene dwell and genuine hero death")
    parser.add_argument("--drop-x-adjust", type=int, choices=(-1, 0, 1), default=0,
                        help="explicit one-pixel presentation-latency correction; reported, never auto-fitted")
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text())
    if args.drop_x_adjust:
        print(f"Presentation correction requested: drop x {args.drop_x_adjust:+d}")
    # One ready update precedes input; one 40-tick death freezes world scrolling.
    offset = evidence["ready_updates"] - evidence["death_duration"]
    verify_drop(image(args.drop), evidence["drop_bob"], args.drop_x_adjust, evidence["drop_capture"] + offset)
    verify_restore(image(args.restored), evidence["roi"], evidence["restore_capture"] + offset)
    if args.lifecycle_serial:
        verify_lifecycle(args.lifecycle_serial, evidence)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, IndexError, StopIteration) as error:
        raise SystemExit(f"FAIL: {error}") from error
