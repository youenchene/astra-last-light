#!/usr/bin/env python3
"""Assert actual leftward motion of both captured decor bands and rich hero colors."""
import argparse
import os
import re
from pathlib import Path
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
KIT = Path(os.environ.get("AGK_KIT", str(Path.home() / "Code/amiga/amiga-game-kit")))
sys.path.insert(0, str(KIT / "harness"))
from agk.image import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base", default=str(ROOT / "game/build/agk"))
parser.add_argument("--profiles", nargs="+", default=["a500", "a500-aros"])
parser.add_argument("--compare-profiles", action="store_true",
                    help="require byte-identical complete captures for every production scenario")
parser.add_argument("--performance-summary", action="store_true",
                    help="report all emitted perf windows for campaign_waves and bonus; no relaxed gate")
args = parser.parse_args()
if args.compare_profiles:
    reference = Path(args.base) / args.profiles[0]
    for profile in args.profiles[1:]:
        count = 0
        for scenario in sorted((ROOT / "game/tests").glob("*.agk")):
            captures = sorted((reference / scenario.stem).glob("*.screen.png"))
            actual = Path(args.base) / profile / scenario.stem
            assert {p.name for p in captures} == {p.name for p in actual.glob("*.screen.png")}, \
                f"{profile}: capture set differs for {scenario.stem}"
            for capture in captures:
                assert capture.read_bytes() == (actual / capture.name).read_bytes(), \
                    f"{profile}: complete capture differs: {scenario.stem}/{capture.name}"
                count += 1
        assert count, "no production captures compared"
        print(f"PASS {profile}: all {count} complete production captures byte-identical to {args.profiles[0]}")
if args.performance_summary:
    for profile in args.profiles:
        for scenario in ("campaign_waves", "bonus"):
            text = (Path(args.base) / profile / scenario / "serial.txt").read_text()
            windows = [tuple(map(int, row)) for row in re.findall(
                r"AGK perf frames=(\d+) dropped=(\d+) load=(\d+) maxload=(\d+)", text)]
            assert windows, f"{profile}/{scenario}: missing performance telemetry"
            frames = sum(row[0] for row in windows)
            average = sum(row[0] * row[2] for row in windows) / frames
            peak = max(row[3] for row in windows)
            drops = sum(row[1] for row in windows)
            print(f"SUMMARY {profile}/{scenario}: {len(windows)} windows/{frames} ticks, "
                  f"weighted average={average:.2f}% peak={peak}% drops={drops}; "
                  "all emitted windows including intros/preparation/transitions; "
                  "final partial window is not emitted by production telemetry")
for profile in args.profiles:
    tap = (Path(args.base) / profile / "tap_fire/serial.txt").read_text()
    hold = (Path(args.base) / profile / "hold_charge/serial.txt").read_text()
    assert len(re.findall(r"AGK sfx shot\b", tap)) == 1, f"{profile}: tap must emit exactly one normal shot, no idle shots"
    assert len(re.findall(r"AGK sfx charge\b", hold)) == 1, f"{profile}: hold must charge exactly once"
    assert not re.search(r"AGK sfx (shot|lance)\b", hold), f"{profile}: shot during hold"
    nebula = Image.load_png(str(Path(args.base) / profile / "sector2/nebula.screen.png"))
    for top in (29, 220):
        bad = [(x, y) for y in range(top, top + 24) for x in range(320)
               if nebula.pixel(x, y) != (17, 0, 34)]
        assert not bad, f"{profile}: sector2 band at {top}: {len(bad)} non-$102 pixels: {bad[:8]}"
    print(f"PASS {profile}: all 15360 sector2 border pixels are $102")
    folder = Path(args.base) / profile / "scrolling"
    a = Image.load_png(str(folder / "first.screen.png"))
    b = Image.load_png(str(folder / "second.screen.png"))
    assert (a.width, a.height, b.width, b.height) == (320, 256, 320, 256)
    for name, top, shift in (("top", 29, 4), ("bottom", 220, 4)):
        assert any(a.pixel(x,y) != b.pixel(x,y) for y in range(top, top+24) for x in range(320)), f"{profile}: static {name}"
        changed = [(x,y) for y in range(top, top+24) for x in range(320-shift)
            if a.pixel(x+shift,y) != b.pixel(x,y)]
        mismatches = len(changed)
        if changed:
            print(f"{profile} {name} mismatched X/Y bounds:",
                min(x for x,y in changed), max(x for x,y in changed),
                min(y for x,y in changed), max(y for x,y in changed))
            print("Rows:", Counter(y for x,y in changed).most_common())
        assert not mismatches, f"{profile}: {name} is not a clean {shift}px leftward scroll ({mismatches} mismatches)"
    background = a.pixel(250,58)
    nonspace = sum(a.pixel(x,y) != background for y in range(56,122) for x in range(184,312))
    assert nonspace < 200, f"{profile}: static picture remains in gameplay ({nonspace} pixels)"
    star_color = (187, 221, 255)
    colors = {a.pixel(x,y) for y in range(126,150) for x in range(32,64)} - {background, star_color}
    assert len(colors) >= 10, f"{profile}: hero has only {len(colors)} visible colors"
    right_half = sum(a.pixel(x,y) not in (background, star_color) for y in range(126,150) for x in range(48,64))
    assert right_half >= 32, f"{profile}: hero does not extend visibly beyond16px"
    stars = sum(a.pixel(x,y) == star_color for y in range(56,216) for x in range(320)
        if not (32 <= x < 64 and 126 <= y < 150))
    assert 120 <= stars <= 160, f"{profile}: unexpected dense star population: {stars} pixels"
    checked = [0] * 4
    for index in range(96):
        y = 56 + index * 159 // 95
        if 126 <= y < 150: continue  # hero may occlude a star
        positions = [x for x in range(320) if a.pixel(x,y) == star_color]
        width = 1 if (index & 3) < 2 else 2
        assert len(positions) == width, f"{profile}: malformed star at row{y}"
        start = positions[0]
        expected = (start - 16 // (8 >> (index & 3))) % 316
        if start >= 240 or expected >= 240: continue  # new formation enters at right edge
        actual = {x for x in range(240) if b.pixel(x,y) == star_color}
        assert actual == set(range(expected, expected + width)), f"{profile}: wrong parallax on layer{index & 3}, y{y}"
        checked[index & 3] += 1
    assert all(n >= 8 for n in checked), f"{profile}: not enough independent parallax samples: {checked}"
    title = Image.load_png(str(Path(args.base) / profile / "boot/title.screen.png"))
    title_bg = title.pixel(0,60)
    for top in (29,220):
        assert all(title.pixel(x,y) == title_bg for y in range(top,top+24) for x in range(320)), f"{profile}: title still has decor"
    print(f"PASS {profile}: borders both4px left, four slow parallax rates {checked}, 32px hero/{len(colors)} colors, clean title")
