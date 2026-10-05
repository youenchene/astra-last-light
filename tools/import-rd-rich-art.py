#!/usr/bin/env python3.12
"""Fit preserved Retro Diffusion masters to OCS sprites and decor strips.

Run with Python 3.12. Original PNGs are never modified. No paid API calls.
"""
from collections import Counter, deque
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
KIT = Path(os.environ.get("AGK_KIT", str(Path.home() / "Code/amiga/amiga-game-kit")))
sys.path.insert(0, str(KIT / "harness"))
from agk.art import parse_palette, to_rgb8
from agk.image import load_png_rgba

ART = ROOT / "game/art"
PALETTE = parse_palette(str(ART / "palette.txt"))
RGB = [to_rgb8(PALETTE[i]) for i in range(16)]
CHARS = ".123456789ABCDEF"
SHOT_H, LANCE_H = 4, 10
INPUTS = []

def nearest(pixel, first=0):
    return min(range(first, 16), key=lambda i: sum((RGB[i][c] - pixel[c]) ** 2 for c in range(3)))

def load(name, remove_border=False):
    path = ART / (name + ".png")
    width, height, rgba = load_png_rgba(str(path))
    pixels = [nearest(p) if p[3] >= 128 else None for p in rgba]
    removed = 0
    # Some palette-constrained RD outputs keep an opaque flat background.
    # Remove ONLY a dominant border-connected color, never internal craters.
    if remove_border and sum(p is None for p in pixels) < width * height // 10:
        edge = [x for x in range(width)] + [(height - 1) * width + x for x in range(width)]
        edge += [y * width for y in range(1, height - 1)]
        edge += [y * width + width - 1 for y in range(1, height - 1)]
        color, count = Counter(pixels[i] for i in edge).most_common(1)[0]
        if color is not None and count * 5 >= len(edge) * 3:
            queue = deque(i for i in edge if pixels[i] == color)
            while queue:
                i = queue.popleft()
                if pixels[i] != color:
                    continue
                pixels[i] = None
                removed += 1
                x, y = i % width, i // width
                if x: queue.append(i - 1)
                if x + 1 < width: queue.append(i + 1)
                if y: queue.append(i - width)
                if y + 1 < height: queue.append(i + width)
    INPUTS.append({"source": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "border_pixels_removed": removed})
    print(f"{name}: {width}x{height}, cleaned {removed} border pixels")
    return width, height, pixels, rgba

def sprite(name, draw_height=16, frame_width=16, frame_height=16):
    width, height, pixels, rgba = load(name, True)
    occupied = [i for i, p in enumerate(pixels) if p is not None]
    if not occupied:
        raise ValueError(f"Empty sprite: {name}")
    left, right = min(i % width for i in occupied), max(i % width for i in occupied)
    top, bottom = min(i // width for i in occupied), max(i // width for i in occupied)
    rows = [[0] * frame_width for _ in range(frame_height)]
    for y in range(draw_height):
        sy = top + min(bottom - top, ((2 * y + 1) * (bottom - top + 1)) // (2 * draw_height))
        for x in range(frame_width):
            sx = left + min(right - left, ((2 * x + 1) * (right - left + 1)) // (2 * frame_width))
            index = sy * width + sx
            if pixels[index] is not None:
                # Attached sprite index zero is transparent, not an opaque black.
                rows[y + (frame_height - draw_height) // 2][x] = nearest(rgba[index], 1)
    return rows

def parse_frames(path):
    frames = []
    for line in path.read_text().splitlines():
        if line == "frame": frames.append([])
        elif frames and line and set(line) <= set(CHARS):
            frames[-1].append([CHARS.index(c) for c in line])
    return frames

def write(name, frames, note, palette=None):
    palette = PALETTE if palette is None else palette
    header = ["# " + note, "colors", "  . transparent"]
    header += [f"  {CHARS[i]} 0x{palette[i]:03X}" for i in sorted(palette) if i]
    for frame in frames:
        header.append("frame")
        header.extend("".join(CHARS[p] for p in row) for row in frame)
    (ART / name).write_text("\n".join(header) + "\n")

def main():
    hero = sprite("rd_hero16", 22, frame_width=32, frame_height=24)
    pulse = [[{12: 13, 13: 14, 14: 13}.get(p, p) for p in row] for row in hero]
    write("hero32.txt", [hero, pulse], "Retro Diffusion32px master; 32x24 vessel + warm engine animation")
    old = parse_frames(ART / "actors16.txt")
    if len(old) != 14:
        raise ValueError("Expected fourteen actor frames")
    # One independently simulated 6x8 enemy bullet per DMA element: the former
    # 3x4 rose/white/gold orb at twice the size, rounded instead of blocky.
    bullet = [".BBBB.", "BB77BB", "B7777B", "B7EE7B", "B7EE7B", "B7777B", "BB77BB", ".BBBB."]
    old[8] = [[CHARS.index(c) for c in row.ljust(16, ".")] for row in bullet] + [[0] * 16 for _ in range(16 - len(bullet))]
    bullet_palette = parse_palette(str(ART / "bullet-palette.txt"))
    bullet_rgb = {i: to_rgb8(c) for i, c in bullet_palette.items() if i}
    def bullet_ink(p):
        if not p: return 0
        return min(bullet_rgb, key=lambda i: sum((RGB[p][c] - bullet_rgb[i][c]) ** 2 for c in range(3)))
    bullet_frames = [[[bullet_ink(p) for p in row] for row in old[index][:10]] for index in (6,7,8,9)]
    write("bullets.txt", bullet_frames, "Independent2bpp bullet streams; normal,charge,hostile,chargeAlt", bullet_palette)
    write("bonuses.txt", old[10:14], "Masked BOB pickups P/S/R/L in the playfield palette")
    # Player fire is drawn by the blitter, leaving sprite channels 6/7 to enemy bullets.
    write("pshot.txt", [old[6][:SHOT_H]], "Masked BOB player shot 16x4 (8x4 bolt) in the playfield palette")
    write("lance.txt", [old[7][:LANCE_H], old[9][:LANCE_H]], "Masked BOB charged lance 16x10, two flash frames")
    enemies = [sprite(name, h) for name, h in (
        ("rd_scout16", 14), ("rd_weaver16", 16), ("rd_gunner16", 14),
        ("rd_dart16", 10), ("rd_boss16", 16), ("rd_asteroid16", 16))]
    write("actors16.txt", enemies + old[6:], "Frames0-5 from Retro Diffusion masters; readable shots/UI badges retained; see RD-RICH.md")
    bands = []
    for level in range(4):
        width, height, pixels, _ = load(f"rd_decor{level}")
        if width != 64 or height != 64:
            raise ValueError("Decor masters must be64x64")
        for top in (0, 40):
            band = [[pixels[(top + y) * width + x] or 0 for x in range(64)] for y in range(24)]
            for row in band: row[-1] = row[0]
            if top == 0: band[22] = [0] * 64; band[23] = [0] * 64
            else: band[0] = [0] * 64; band[1] = [0] * 64
            bands.append(band)
    write("decor.txt", bands, "Retro Diffusion rd_decor0..3.png; top/bottom crops, seam and corridor-edge cleanup")
    (ART / "rd-rich-import.json").write_text(json.dumps({"sources": INPUTS,
        "processing": "Border-connected cleanup; nearest-neighbor fit; palette quantization; 2-row corridor clearance; seam endpoint match"}, indent=2) + "\n")
    print("Wrote hero32, actors16, bullets, masked bonuses/shots/lance and decor")
    subprocess.run([sys.executable, str(ROOT / "tools/make-sector-enemies.py")], check=True)

if __name__ == "__main__":
    main()
