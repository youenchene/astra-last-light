#!/usr/bin/env python3.12
"""Check native loading/prompt pixels and complete cross-profile captures."""
import argparse
import ast
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
KIT = Path(os.environ.get("AGK_KIT", str(Path.home() / "Code/amiga/amiga-game-kit")))
sys.path.insert(0, str(KIT / "harness"))
from agk.image import Image
font = (ROOT / "game/src/scene_font.h").read_text().split("=", 1)[1].split(";", 1)[0]
GLYPHS = ast.literal_eval(font.replace("{", "[").replace("}", "]"))


def check_footer(path, text):
    image = Image.load_png(path)
    assert (image.width, image.height) == (320, 256), path
    expected = set()
    x = 112 + (96 - len(text) * 5) // 2
    for letter in text:
        if letter != " ":
            for row, bits in enumerate(GLYPHS[ord(letter) - ord("A")]):
                for col in range(4):
                    if bits & (8 >> col):
                        expected.add((x + col, 249 + row))
        x += 5
    colors = set()
    for y in range(248, 256):
        for x in range(320):
            color = image.pixel(x, y)
            if (x, y) in expected:
                assert color in ((255, 255, 255), (170, 170, 170)), (path, x, y, color)
                colors.add(color)
            else:
                assert color == (0, 17, 17), (path, x, y, color)
    assert len(colors) == 1, (path, "torn pulse/text")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    args = parser.parse_args()
    names = [p.name for p in (args.base / "a500").glob("*.screen.png")]
    assert len(names) == 17, "run loading_feedback.agk on both profiles first"
    for profile in ("a500", "a500-aros"):
        directory = args.base / profile
        text = (directory / "serial.txt").read_text()
        assert "AGK language=1" in text and "allocation failure" not in text
        for name in names:
            label = None
            if "loading" in name or name == "opening_closing.screen.png":
                label = "LOADING"
            elif name == "language_release.screen.png":
                label = "RELEASE FIRE"
            elif name == "ending_wait.screen.png":
                label = "PLEASE WAIT"
            elif name == "ending_continue.screen.png":
                label = "FIRE TO CONTINUE"
            if label:
                check_footer(directory / name, label)
            else:
                # Ready input screens must not retain the loading-strip background.
                pixels = Image.load_png(directory / name)
                if name == "language_default.screen.png":
                    assert all(pixels.pixel(x, y) == (0, 17, 17)
                               for y in range(248, 256) for x in range(320)), name
                else:
                    assert any(pixels.pixel(x, 248) != (0, 17, 17) for x in range(320)), name
        windows = [tuple(map(int, values)) for values in re.findall(
            r"AGK perf frames=(\d+) dropped=(\d+) load=(\d+) maxload=(\d+)", text)]
        assert windows, "missing performance telemetry"
        print(f"PASS {profile}: all status pixels; {len(windows)} emitted windows, "
              f"{sum(w[1] for w in windows)} drops, peak {max(w[3] for w in windows)}%")
    for name in names:
        a = Image.load_png(args.base / "a500" / name)
        b = Image.load_png(args.base / "a500-aros" / name)
        assert a.rgb == b.rgb, f"profile mismatch: {name}"
    print(f"PASS: {len(names)} complete screen pairs identical, no masked regions")


if __name__ == "__main__":
    main()
