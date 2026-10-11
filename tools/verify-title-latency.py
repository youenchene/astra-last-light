#!/usr/bin/env python3.12
"""Measure accepted title input to acknowledged publication in elapsed PAL vblanks."""
import argparse
import importlib.util
from pathlib import Path
import re


def require(ok, message):
    if not ok:
        raise ValueError(message)


def records(text, tag):
    return [{k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", line)}
            for line in text.splitlines() if line.startswith(f"AGK {tag}=")]


def validate(text, coverage=True):
    inputs = records(text, "title_input")
    visible = records(text, "cut_visible")
    submits = records(text, "cut_submit")
    require(inputs and visible and len(submits) == len(visible), "missing timing/publication evidence")
    for s, v in zip(submits, visible):
        require(s["cut_submit"] == v["cut_visible"] and
                all(s[k] == v[k] for k in ("phase", "level", "bitmap", "copper", "both")),
                "publication identity mismatch")
        require(v["vblank"] > s["vblank"], "publication not acknowledged after vblank")
    results = []
    for index, event in enumerate(inputs):
        revision = event["title_input"]
        cuts = [v for v in visible if v["cut_visible"] == revision]
        following = inputs[index + 1] if index + 1 < len(inputs) else None
        for cut in cuts:
            require(cut["phase"] == event["phase"] and cut["level"] == event["level"],
                    "published wrong selection")
            require(cut["vblank"] > event["vblank"], "nonpositive input latency")
            require(not following or cut["vblank"] <= following["vblank"], "stale selection published")
        first = next((v for v in cuts if v["both"] == 0), None)
        both = next((v for v in cuts if v["both"] == 1), None)
        require(first is not None or following is not None, "final selection never visible")
        require(both is not None or following is not None, "final selection never ready")
        if both:
            require(first and first["vblank"] < both["vblank"] and
                    first["bitmap"] != both["bitmap"] and first["copper"] != both["copper"],
                    "missing independent hidden repair")
        elapsed = tuple(v["vblank"] - event["vblank"] if v else None for v in (first, both))
        if event["phase"] == 0:
            require(elapsed[0] is None or elapsed[0] <= 40, "first-visible title latency exceeds 40 vblanks")
            require(elapsed[1] is None or elapsed[1] <= 80, "both-ready title latency exceeds 80 vblanks")
        results.append((revision, event["phase"], event["level"], *elapsed))
    if coverage:
        require([e["level"] for e in inputs[:5]] == [2, 3, 4, 1, 4], "missing sectors/wraps")
        require([e["title_input"] for e in inputs] == list(range(2, 13)), "missing rapid/repair/fire inputs")
        require(all(r[3] is None for r in results if r[0] in (7, 8)), "canceled target unexpectedly visible")
        require(any(r[0] == 11 and r[4] is not None for r in results), "fire bypassed complete selected title")
        require(any(r[0] == 9 and r[3] is not None and r[4] is None for r in results), "no repair retap")
        require(results[-1][1] == 6 and results[-1][2] == 1 and results[-1][4] is not None,
                "fire did not reach selected opening")
        cold = [v for v in visible if v["cut_visible"] == 1]
        require([v["both"] for v in cold] == [0, 1], "missing cold title repair")
    require(not re.search(r"ERR|STACK SMASHED|allocation failure|bullet_hidden=[1-9]", text), "native error")
    return results


def check_images(folder):
    spec = importlib.util.spec_from_file_location("sectors", Path(__file__).with_name("verify-sector-presentation.py"))
    sectors = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sectors)
    sectors.check_titles(folder, sectors.palette())
    for name, target in (("rapid_first", "title1"), ("repair_retap", "title4")):
        require((folder / f"{name}.screen.png").read_bytes() ==
                (folder / f"{target}.screen.png").read_bytes(), f"{name}: incomplete/stale title")


def launch_timing(text):
    inputs = records(text, "title_confirm_input")
    submits = records(text, "title_confirm_submit")
    visible = records(text, "title_confirm_visible")
    require(len(inputs) == 1, "expected one accepted fire origin")
    require([r["title_confirm_submit"] for r in submits] == list(range(1, 7)) and
            [r["title_confirm_visible"] for r in visible] == list(range(1, 7)),
            "expected exactly six confirmation publications")
    origin = inputs[0]["vblank"]
    require(all(s["vblank"] < v["vblank"] for s, v in zip(submits, visible)),
            "confirmation lacks vblank acknowledgement")
    require(all(a["vblank"] < b["vblank"] for a, b in zip(visible, visible[1:])),
            "confirmation clock did not advance")
    require(text.count("AGK sfx confirm\n") == 1, "confirmation sound not requested exactly once")
    start = text.index("AGK title_confirm_input=")
    ready = records(text, "publication_ready")
    opening = next((r for r in ready if r["phase"] == 6 and r["vblank"] > origin), None)
    combat = next((r for r in ready if r["phase"] == 1 and r["vblank"] > origin), None)
    require(opening and opening["scene_ready"] == 1 and opening["preparing"] == 0,
            "missing acknowledged playable opening")
    # After this acknowledgement the opening is live: firing is legal, and its
    # later transition to PLAY legitimately requests warp.
    lines = text[start:].splitlines(keepends=True)
    end = next(i for i, line in enumerate(lines)
               if line.startswith("AGK publication_ready=") and
               records(line, "publication_ready")[0] == opening)
    require(not re.search(r"AGK sfx (shot|lance|warp)\b", "".join(lines[:end + 1])),
            "weapon/warp during launch")
    require(combat and combat["preparing"] == 0, "missing combat readiness")
    require(all(v["level"] == opening["level"] == combat["level"] for v in visible),
            "selected sector changed during confirmation")
    for record in (opening, combat):
        require(any(v["cut_visible"] == record["publication_ready"] and v["both"] == 1
                    and v["phase"] == record["phase"] and v["vblank"] == record["vblank"]
                    for v in records(text, "cut_visible")), "readiness not tied to repaired publication")
    clocks = (submits[0]["vblank"], visible[0]["vblank"], opening["vblank"], combat["vblank"])
    require(origin <= clocks[0] < clocks[1] < clocks[2] < clocks[3], "launch milestone ordering")
    return dict(zip(("chime_request", "first_feedback", "playable_opening", "combat"),
                    (clock - origin for clock in clocks)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+", type=Path)
    args = parser.parse_args()
    for folder in args.directories:
        results = validate((folder / "serial.txt").read_text())
        launch = launch_timing((folder / "serial.txt").read_text())
        check_images(folder)
        for revision, phase, level, first, both in results:
            def timing(value):
                return "superseded" if value is None else f"{value} vblanks ({value / 50:.2f}s)"
            print(f"{folder.name}: revision {revision} phase {phase} sector {level}: "
                  f"first {timing(first)}, both {timing(both)}")
        for milestone, elapsed in launch.items():
            print(f"accepted fire -> {milestone}: {elapsed} vblanks ({elapsed * 20} ms)")
