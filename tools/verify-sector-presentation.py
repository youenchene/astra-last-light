#!/usr/bin/env python3.12
"""Check native title/Veil Nebula pixels against preserved PNGs, not goldens.

Uses only AGK's PNG decoder; quantization and fixed-point connectivity are
independent of the production title generator and decor importer's queue walk.
"""
import argparse
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "game/art"
KIT = Path(os.environ.get("AGK_KIT", str(Path.home() / "Code/amiga/amiga-game-kit")))
sys.path.insert(0, str(KIT / "harness"))
from agk.image import Image, load_png_rgba

NAMES = ("graveyard", "nebula", "foundry", "citadel")
SPACE = (0x001, 0x102, 0x101, 0x001)
INKS = ".123456789ABCDEF"


def rgb(color):
    return tuple(((color >> shift) & 15) * 17 for shift in (8, 4, 0))


def palette():
    entries = re.findall(r"^(\d+)\s+0x([0-9a-fA-F]{3})\b",
                         (ART / "palette.txt").read_text(), re.M)
    colors = {int(index): rgb(int(value, 16)) for index, value in entries}
    assert set(colors) == set(range(16)), "expected complete four-plane palette"
    return colors


def source_indices(name, colors, title=False):
    width, height, pixels = load_png_rgba(str(ART / f"{name}.png"))
    result = []
    for pixel in pixels:
        if pixel[3] < 128:
            result.append(0)
            continue
        # Title conversion first rounds to OCS RGB, then uses weighted distance.
        sample = tuple(((c * 15 + 127) // 255) * 17 for c in pixel[:3]) if title else pixel[:3]
        weights = (2, 4, 3) if title else (1, 1, 1)
        result.append(min(colors, key=lambda i: sum(
            weight * (a - b) ** 2 for weight, a, b in zip(weights, sample, colors[i]))))
    return width, height, result


def nebula_bands(colors):
    width, height, source = source_indices("rd_decor1", colors)
    assert (width, height) == (64, 64)
    bands = []
    for crop, edge, counts in ((0, 23, (293, 53)), (40, 0, (251, 105))):
        rows = [source[(crop + y) * 64:(crop + y + 1) * 64] for y in range(24)]
        for row in rows:
            row[63] = row[0]
        for y in ((22, 23) if crop == 0 else (0, 1)):
            rows[y] = [0] * 64
        dark = {(x, y) for y in range(24) for x in range(64) if rows[y][x] in (0, 1)}
        reached = {(x, edge) for x in range(64)} & dark
        while True:
            expanded = reached | {point for point in dark if any(neighbor in reached for neighbor in (
                ((point[0] - 1) % 64, point[1]), ((point[0] + 1) % 64, point[1]),
                (point[0], point[1] - 1), (point[0], point[1] + 1)))}
            if expanded == reached:
                break
            reached = expanded
        changed = sum(rows[y][x] == 1 for x, y in reached)
        retained = sum(rows[y][x] == 1 for x, y in dark - reached)
        assert (changed, retained) == counts, f"crop {crop}: cleanup/shadow counts {(changed, retained)}"
        bands.append([[0 if (x, y) in reached else rows[y][x] for x in range(64)] for y in range(24)])
    frames = []
    for line in (ART / "decor.txt").read_text().splitlines():
        if line == "frame":
            frames.append([])
        elif frames and line and set(line) <= set(INKS):
            frames[-1].append([INKS.index(c) for c in line])
    assert len(frames) == 8
    assert frames[2:4] == bands, "decor derivative differs from original PNG + intended cleanup"
    print("PASS source: only 544 connected ink-1 pixels cleared; 158 disconnected shadows retained")
    return bands


def screen(path):
    image = Image.load_png(str(path))
    assert (image.width, image.height) == (320, 256), f"{path}: wrong screen size"
    return image


def check_titles(folder, colors):
    glyphs = []
    for line in (ART / "font.txt").read_text().splitlines():
        if line == "frame":
            glyphs.append([])
        elif glyphs and line and set(line) <= {".", "X"}:
            glyphs[-1].append(line)
    captions = ("ORBITAL GRAVEYARD", "VEIL NEBULA", "IMPERIAL FOUNDRY", "STELLAR CITADEL")
    visible = [(x, y) for y in range(96) for x in range(128)]
    assert len(visible) == 12288  # Centered original plate is entirely unobscured.
    signatures = []
    exterior = None
    for level, name in enumerate(NAMES):
        width, height, indices = source_indices(name, colors, title=True)
        assert (width, height) == (128, 96)
        live = dict(colors)
        live[0] = rgb(SPACE[level])
        image = screen(folder / f"title{level + 1}.screen.png")
        # Normalize only the sector's ink-zero palette color, not any pixels.
        # Every pixel outside the two dirty regions must retain its ink.
        inverse = {value: ink for ink, value in live.items()}
        static = tuple(inverse[image.pixel(x, y)] for y in range(256) for x in range(320)
                       if not (96 <= x < 224 and 26 <= y < 122) and not (224 <= y < 232))
        if exterior is not None:
            assert static == exterior, f"{name}: title exterior changed during sector refresh"
        exterior = static
        blade = ("....62.....", "...6F3.....", "..6F5666662",
                 ".6F55555542", "6F5544FFF32", ".3543333321",
                 "..343222221", "...321.....", "....21.....")
        prompt_pixels = {}
        for left, mirrored in ((88, False), (122, True)):
            for y, row in enumerate(blade):
                for x, ink in enumerate(row[::-1] if mirrored else row):
                    if ink != ".":
                        prompt_pixels[left + x, 202 + y] = int(ink, 16)
        for left, text in ((105, "OR"), (137, "TO CHANGE SECTOR")):
            for index, letter in enumerate(text):
                if letter == " ":
                    continue
                for y, row in enumerate(glyphs[ord(letter) - ord("A")]):
                    for x, pixel in enumerate(row):
                        if pixel == "X":
                            prompt_pixels[left + index * 6 + x, 203 + y] = 4
        assert all(image.pixel(x, y) == live[prompt_pixels.get((x, y), 1)]
                   for y in range(201, 212) for x in range(24, 296)), f"{name}: metallic navigation prompt pixels"
        signature = tuple(image.pixel(96 + x, 26 + y) for x, y in visible)
        expected = tuple(live[indices[y * 128 + x]] for x, y in visible)
        assert signature == expected, f"{folder}/{name}: original title pixels differ"
        signatures.append(signature)
        caption_x = (320 - len(captions[level]) * 6 + 1) // 2
        caption_pixels = {(caption_x + index * 6 + x, 224 + y)
                          for index, letter in enumerate(captions[level]) if letter != " "
                          for y, row in enumerate(glyphs[ord(letter) - ord("A")])
                          for x, pixel in enumerate(row) if pixel == "X"}
        assert all(image.pixel(x, y) == live[5 if (x, y) in caption_pixels else 0]
                   for top in (29, 220) for y in range(top, top + 24) for x in range(320)
                   if not (96 <= x < 224 and 26 <= y < 122)), \
            f"{name}: expected only source-font sector caption, no decor on title"
        assert all(image.pixel(x, y) == live[0] for y in (*range(26), *range(245, 256))
                   for x in range(320)), f"{name}: gameplay HUD remains on title"
    assert len(set(signatures)) == 4, f"{folder}: title illustrations are not distinct"
    for capture, target in (("wrap_right", "title1"), ("wrap_left", "title4")):
        assert (folder / f"{capture}.screen.png").read_bytes() == (folder / f"{target}.screen.png").read_bytes(), \
            f"{folder}: {capture} differs from {target}"
    print(f"PASS {folder}: 12288 exact pixels/title, four distinct originals, both full-screen wraps")


def check_nebula(path, colors, bands):
    image = screen(path)
    live = dict(colors)
    live[0], live[4] = rgb(0x102), rgb(0xBDF)
    phases = []
    for top, rows in zip((29, 220), bands):
        matches = [phase for phase in range(64) if all(
            image.pixel(x, top + y) == live[rows[y][(x + phase) % 64]]
            for y in range(24) for x in range(320))]
        assert len(matches) == 1, f"{path}: band y{top} must have one exact source phase, got {matches}"
        phases.append(matches[0])
    distance = (phases[0] - phases[1]) % 64
    assert min(distance, 64 - distance) <= 1, f"{path}: top/bottom phase divergence {phases}"
    print(f"PASS {path}: all 15360 crystal/background pixels exact; phases {phases}; PLAY ink4 #BDF")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=ROOT / "game/build/agk")
    parser.add_argument("--profiles", nargs="+", default=["a500", "a500-aros"])
    args = parser.parse_args()
    colors = palette()
    bands = nebula_bands(colors)
    for profile in args.profiles:
        check_titles(args.base / profile / "title_sectors", colors)
        check_nebula(args.base / profile / "sector2/nebula.screen.png", colors, bands)


if __name__ == "__main__":
    main()
