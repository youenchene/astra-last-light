"""Independent source PNG/palette and original-48-seed moving-star oracle."""
import os
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(os.environ.get("AGK_KIT", Path.home()/"Code/amiga/amiga-game-kit"))/"harness"))
from agk.image import Image


def palette(level):
    values = [int(line.split()[1], 16) for line in (ROOT/"game/art/palette.txt").read_text().splitlines() if line and not line.startswith("#")]
    values[0] = (1, 0x102, 0x101, 1)[level]
    values[4] = 0xbdf
    return [tuple(17*((value >> shift) & 15) for shift in (8,4,0)) for value in values]


@lru_cache(maxsize=4)
def background(level):
    name = ("s1-graveyard-c", "s2-nebula-b", "s3-foundry-b", "s4-citadel-a")[level]
    source = Image.load_png(str(ROOT/"game/art/galaxy"/(name+".png")))
    colors = palette(level)
    result = []
    for y in range(160):
        row = []
        for x in range(320):
            rgb = source.pixel(x*256//320, y*128//160)
            rgb = [channel*(2 if level == 1 else 3)//4 for channel in rgb]
            distances = [sum((rgb[c]-colors[i][c])**2 for c in range(3)) for i in range(4)]
            row.append(distances.index(min(distances)))
        result.append(row)
    return result


def stars(ticks):
    result = []
    seed = 0xace1
    for i in range(48):
        seed = (seed >> 1) ^ (0xb400 if seed & 1 else 0)
        layer, stagger = i % 4, i // 4
        if not layer:
            continue
        period = (16,8,4,2)[layer]
        moves = (ticks + stagger) // period - stagger // period
        x = (seed % 316 - 2*moves) % 316
        result.append((x, 56+i*159//47, 1 if layer == 1 else 2))
    return result


def indices(level, ticks):
    rows = [row[:] for row in background(level)]
    for x, y, width in stars(ticks):
        for dx in range(width):
            rows[y-56][x+dx] ^= 4
    return rows


def pixel(level, ticks, x, y):
    ink = background(level)[y-56][x]
    for sx, sy, width in stars(ticks):
        if y == sy and sx <= x < sx+width:
            ink ^= 4
    return palette(level)[ink]
