#!/usr/bin/env python3
"""Verify remapped sprites,2bpp bullets and BOB masks against generated words."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "game/art"
generated = (ROOT / "game/build/art/art.c").read_text()

def palette(name):
    return {int(i): int(c,16) for i,c in re.findall(r"^(\d+)\s+0x([0-9a-fA-F]+)", (ART/name).read_text(), re.M)}

sprite = palette("sprite-palette.txt")
bullet = palette("bullet-palette.txt")
assert [sprite[i] for i in (13,14,15)] == [bullet[i] for i in (1,2,3)], "Bullet colors conflict with attached sprites"
assert sorted(sprite.values()) == sorted(palette("palette.txt").values()), "Original sprite RGB colors changed"

for name, symbol, count, width, height, depth, pal, kind in (
    ("hero32", "Hero32", 2, 32, 24, 4, "sprite-palette.txt", "bitmap"),
    ("sector_enemies", "SectorEnemies", 24, 16, 16, 4, "sprite-palette.txt", "bitmap"),
    ("decor", "Decor", 8, 64, 24, 4, "palette.txt", "bitmap"),
    ("bullets", "Bullets", 4, 16, 10, 2, "bullet-palette.txt", "bitmap"),
    ("bonuses", "Bonuses", 5, 16, 16, 4, "palette.txt", "bob"),
    ("pshot", "Pshot", 1, 16, 4, 4, "palette.txt", "bob"),
    ("lance", "Lance", 2, 16, 10, 4, "palette.txt", "bob"),
):
    text = (ART/f"{name}.txt").read_text()
    inks = {char: int(color,16) for char,color in re.findall(r"^\s+([0-9A-F])\s+0x([0-9a-fA-F]+)", text, re.M)}
    inverse = {color:index for index,color in palette(pal).items()}
    frames = [part.strip().splitlines() for part in text.split("\nframe\n")[1:]]
    assert len(frames) == count
    assert all(len(fr) == height and all(len(row) == width for row in fr) for fr in frames)
    expected = []
    for frame in frames:
        for row in frame:
            pixels = [0 if c == "." else inverse[inks[c]] for c in row]
            for plane in range(depth):
                for start in range(0,width,16):
                    expected.append(sum(((p >> plane)&1) << (15-bit) for bit,p in enumerate(pixels[start:start+16])))
            if kind == "bob":
                for start in range(0,width,16):
                    expected.append(sum((c != ".") << (15-bit) for bit,c in enumerate(row[start:start+16])))
    match = re.search(rf"s_pArt{symbol}\[\] = \{{(.*?)\}};", generated, re.S)
    assert match
    actual = [int(v,16) for v in re.findall(r"0x([0-9a-fA-F]+)", match[1])]
    assert actual == expected, f"Conversion mismatch: {name}"
    if name == "bullets":
        for f,w,h in ((0,8,4),(1,16,10),(2,6,8),(3,16,10)):
            assert all(c == "." for row in frames[f][h:] for c in row)
            assert all(c == "." for row in frames[f] for c in row[w:])
    if name == "decor":
        assert all(row[0] == row[-1] for fr in frames for row in fr)
    print(f"PASS {name}: {count} frames {width}x{height}, {depth}bpp {kind}, exact palette-remapped pixels/masks")
