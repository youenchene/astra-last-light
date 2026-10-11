#!/usr/bin/env python3.12
"""Gate second-target preparation using actual publication vblank clocks."""
import argparse
from pathlib import Path
import re


def timings(path):
    first = {}
    result = []
    for revision, phase, both, tick in re.findall(
            r"AGK cut_visible=(\d+) phase=(\d+).*?both=(\d+) vblank=(\d+)",
            path.read_text()):
        revision, phase, both, tick = map(int, (revision, phase, both, tick))
        if not both:
            first[revision] = tick
        elif revision in first:
            result.append((revision, phase, tick - first[revision]))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("serial", type=Path)
    args = parser.parse_args()
    samples = timings(args.serial)
    assert samples, "no complete two-target publications"
    for revision, phase, ticks in samples:
        print(f"revision {revision}, phase {phase}: second target {ticks} frames ({ticks / 50:.2f}s)")
        assert ticks <= 32, f"revision {revision}: second target rebuilt instead of bounded copy"


if __name__ == "__main__":
    main()
