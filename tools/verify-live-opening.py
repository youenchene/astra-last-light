#!/usr/bin/env python3.12
"""Validate ordinary opening input and intact overlay using exact artwork pixels."""
import importlib.util
import sys
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("campaign", Path(__file__).with_name("check-campaign-native.py"))
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)
from agk.image import Image


def verify(folder):
    names = ("idle", "moved", "shot", "shot_later", "settled", "closed")
    images = {name: Image.load_png(str(folder / f"opening_{name}.screen.png")) for name in names}
    CHECK.require(all((im.width, im.height) == (320, 256) for im in images.values()), "dimensions")
    CHECK.hero_pixels(images["idle"])
    # Input is six half-speed updates: nine pixels, then a stationary release.
    for name in ("shot", "shot_later", "settled"):
        CHECK.hero_pixels(images[name], 41, 126)
    colors, frames = CHECK.artwork("pshot")
    shape = {(dx, dy): colors[ink] for dy, row in enumerate(frames[0])
             for dx, ink in enumerate(row) if ink not in (".", "0")}
    positions = []
    for name in ("shot", "shot_later"):
        matches = [x for x in range(73, 137) if all(
            images[name].pixel(x + dx, 136 + dy) == color for (dx, dy), color in shape.items())]
        CHECK.require(len(matches) == 1, f"{name}: expected exactly one source-matching shot, got {matches}")
        positions.append(matches[0])
    CHECK.require(positions[1] - positions[0] == 24, "shot did not move six pixels over four ticks")
    for name in ("moved", "shot", "shot_later", "settled"):
        CHECK.require(all(images["idle"].pixel(x, y) == images[name].pixel(x, y)
                          for y in range(56, 208) for x in range(136, 312)),
                      f"{name}: opaque window corrupted")
    # The settled bitmap must restore the entire aligned shot save corridor;
    # it is outside both hero positions and contains the former shot positions.
    CHECK.require(all(images["idle"].pixel(x, y) == images["settled"].pixel(x, y)
                      for y in range(136, 140) for x in range(80, 152)),
                  "shot BOB restore left a trail before the panel")
    print(f"PASS {folder}: visible nine-pixel hero move, source-exact moving shot, intact window and BOB restoration")


if __name__ == "__main__":
    for argument in sys.argv[1:]:
        verify(Path(argument))
