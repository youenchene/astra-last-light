#!/usr/bin/env python3
"""Offline 160x96 to 112x64 nearest-neighbor derivative; preserve source inks."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "game/art"


def compact(source):
    header, *frames = source.split("\nframe\n")
    assert len(frames) == 5, "expected five authored panels"
    result = ["# Offline 112x64 derivative of campaign_manga.txt; make-compact-manga.py\n"
              + header[header.index("colors\n"):]]
    for frame in frames:
        rows = frame.strip().splitlines()
        assert len(rows) == 96 and all(len(row) == 160 for row in rows)
        assert all(set(row) <= set(".123456789ABCDEF") for row in rows)
        result.append("frame\n" + "\n".join(
            "".join(rows[y * 96 // 64][x * 160 // 112] for x in range(112)) for y in range(64)))
    return "\n".join(result) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = compact((ART / "campaign_manga.txt").read_text())
    target = ART / "campaign_manga_compact.txt"
    if args.check:
        assert target.read_text() == output, "compact manga derivative is stale"
    else:
        target.write_text(output)
