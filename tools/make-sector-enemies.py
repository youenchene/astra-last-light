#!/usr/bin/env python3
"""Offline RD-derived sector sprites and authored F badge; no build or API calls."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "game/art"
CHARS = ".123456789ABCDEF"
# Preserve the existing fifteen opaque RGBs, including the hero's shared inks.
PALETTE = (0x102, 0x112, 0x224, 0x346, 0x568, 0x89A, 0xCEF, 0xFFF,
           0x214, 0x536, 0xA58, 0xF9B, 0x521, 0xA43, 0xFA6, 0x4BD)
RAMPS = {
    1: ".1234F6789AB89AF",
    2: ".123456789ACDDEF",
    3: ".134567789A5DE6F",
}


def read_actors(path):
    frames, colors = [], {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line == "colors":
            continue
        if line == "frame":
            frames.append([])
        elif not frames:
            ink, value = line.split()
            colors[ink] = value
        elif len(line) == 16 and set(line) <= set(CHARS):
            frames[-1].append(line)
        else:
            raise ValueError(f"Invalid actor row: {raw!r}")
    expected = {CHARS[i]: f"0x{PALETTE[i]:03X}" for i in range(1, 16)}
    expected["."] = "transparent"
    if colors != expected:
        raise ValueError("Actor palette differs from preserved fifteen-color palette")
    if len(frames) != 14 or any(len(frame) != 16 for frame in frames):
        raise ValueError("Expected fourteen 16x16 actor masters")
    return frames


def stamp(rows, x, y, pattern):
    """Overlay explicit pixel strokes, with spaces leaving the master intact."""
    for dy, row in enumerate(pattern):
        for dx, ink in enumerate(row):
            if ink != " ":
                rows[y + dy][x + dx] = ink


def ship_variant(master, sector, kind):
    rows = [list(row.translate(str.maketrans(CHARS, RAMPS[sector]))) for row in master]
    # Different attachment points retain the four original hull identities.
    root = (8, 9, 6, 7)[kind]
    if sector == 1:
        # Swept organic fins and a branching cyan vein; no rectangular plating.
        fin = ["    A", "   AB", "  9BF", " 9AF ", "89F  "]
        stamp(rows, root, 0, fin)
        stamp(rows, root, 11, list(reversed(fin)))
        stamp(rows, 6, 6, ["  F  ", " F9F ", "F9A9F", "  F  "])
    elif sector == 2:
        # Blunt stepped armor shoulders, rivets and a dark horizontal vent.
        plate = ["1DDD1", "DE5ED", "DCCCD"]
        stamp(rows, root, 2, plate)
        stamp(rows, root, 11, list(reversed(plate)))
        stamp(rows, 5, 7, ["DEDED", "1C1C1", "DDCDD"])
    else:
        # Long silver/gold crown fins, with a bright central shield spine.
        fin = ["  7 7", "  676", "  6E5", " 6ED ", "5ED  "]
        stamp(rows, root, 0, fin)
        stamp(rows, root, 11, list(reversed(fin)))
        stamp(rows, 5, 6, ["  7  ", " 6E6 ", "6E7E6", "  6  "])
    return ["".join(row) for row in rows]


def asteroid_variant(master, sector):
    rows = [list(row.translate(str.maketrans(CHARS, RAMPS[sector]))) for row in master]
    if sector == 1:
        # Mineral growths, not engines/guns: retain an irregular passive rock.
        stamp(rows, 1, 0, ["  A  ", " 9BF ", "89FA ", " 9A  "])
        stamp(rows, 9, 11, [" 9F  ", "9FA  ", " AF9 ", "  A9 ", "   A "])
        stamp(rows, 7, 5, [" F  ", "9AF ", " 9AF", "  F "])
    elif sector == 2:
        # Sheared slag edges and embedded copper chunks, asymmetrical and unlit.
        stamp(rows, 2, 0, ["1DD1 ", "D5ED1", "DCCD "])
        stamp(rows, 11, 9, ["DCC1 ", "DE51 ", "DD1..", "11..."])
        stamp(rows, 5, 6, ["1CC1", "C33D", "1DD1"])
    else:
        # Faceted silver/gold ore; no ship-like paired fins or exhaust.
        stamp(rows, 3, 0, ["  6  ", " 675 ", "67E5 ", " 5D  "])
        stamp(rows, 11, 8, [" 65  ", "67E5 ", " 5D1.", " 11.."])
        stamp(rows, 5, 8, [" 6E ", "65D5", " 5D "])
    return ["".join(row) for row in rows]


def fire_badge():
    # Familiar badge bezel, but a new violet/cyan face and open white F glyph.
    return [
        "................", ".....455554.....", "...457FFFF754...",
        "..45F999999F54..", "..5F97777729F5..", ".4F9272222229F4.",
        ".5F9272222229F5.", ".5F9277772229F5.", ".5F9272222229F5.",
        ".5F9272222229F5.", ".4F9272222229F4.", "..5F92222229F5..",
        "..45F999999F54..", "...445FFFF544...", ".....444444.....",
        "................",
    ]


def make_assets(actors):
    enemies = list(actors[:6])
    for sector in range(1, 4):
        enemies.extend(ship_variant(actors[kind], sector, kind) for kind in range(4))
        enemies.append(actors[4])  # Unused legacy boss slot keeps enum stride six.
        enemies.append(asteroid_variant(actors[5], sector))
    return enemies, actors[10:14] + [fire_badge()]


def validate(enemies, bonuses, actors):
    if len(enemies) != 24 or len(bonuses) != 5:
        raise ValueError("Expected 24 enemies and five badges")
    for frame in enemies + bonuses:
        if len(frame) != 16 or any(len(row) != 16 or not set(row) <= set(CHARS) for row in frame):
            raise ValueError("Frames must be 16x16 in the existing palette")
    if enemies[:6] != actors[:6] or bonuses[:4] != actors[10:14]:
        raise ValueError("Legacy enemy/badge preservation failed")
    for kind in (0, 1, 2, 3, 5):
        masks = {tuple(c != "." for row in enemies[s * 6 + kind] for c in row) for s in range(4)}
        if len(masks) != 4:
            raise ValueError(f"Kind {kind}: sectors must have distinct silhouettes")
    if bonuses[4] in bonuses[:4]:
        raise ValueError("F badge duplicates an existing badge")


def serialize(frames, note):
    lines = ["# " + note, "colors", "  . transparent"]
    lines += [f"  {CHARS[i]} 0x{PALETTE[i]:03X}" for i in range(1, 16)]
    for frame in frames:
        lines.extend(["frame", *frame])
    return "\n".join(lines) + "\n"


def save_preview(path, enemies, bonuses):
    kit = Path(os.environ.get("AGK_KIT", str(Path.home() / "Code/amiga/amiga-game-kit")))
    sys.path.insert(0, str(kit / "harness"))
    from agk.image import Image as AGKImage

    # Four enemy rows in enum order; badge row P/S/R/L/F. Fourfold nearest scale.
    scale, cell, width, height = 4, 24, 144, 120
    pixels = bytearray()
    frames = enemies + bonuses + [["." * 16] * 16]
    for y in range(height * scale):
        for x in range(width * scale):
            sx, sy = x // scale, y // scale
            fx, fy = sx % cell - 4, sy % cell - 4
            ink = frames[(sy // cell) * 6 + sx // cell][fy][fx] if 0 <= fx < 16 and 0 <= fy < 16 else "."
            rgb = PALETTE[CHARS.index(ink)]
            pixels.extend(((rgb >> 8) * 17, ((rgb >> 4) & 15) * 17, (rgb & 15) * 17))
    AGKImage(bytes(pixels), width * scale, height * scale).save_png(str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare exact output bytes without writing assets")
    parser.add_argument("--preview", type=Path, help="Optional local contact-sheet PNG (existing parent directory)")
    args = parser.parse_args()
    actors = read_actors(ART / "actors16.txt")
    enemies, bonuses = make_assets(actors)
    validate(enemies, bonuses, actors)
    outputs = {
        "sector_enemies.txt": serialize(enemies, "RD-derived sector enemies; level*6+kind; boss slots unused; see SECTOR-ENEMIES.md"),
        "bonuses.txt": serialize(bonuses, "Masked BOB pickups P/S/R/L/F; original four retained, authored F; see SECTOR-ENEMIES.md"),
    }
    stale = []
    for name, content in outputs.items():
        path = ART / name
        if args.check:
            if not path.exists() or path.read_bytes() != content.encode("utf-8"):
                stale.append(name)
        else:
            path.write_bytes(content.encode("utf-8"))
    if stale:
        parser.exit(1, "Stale/missing assets: " + ", ".join(stale) + "\n")
    if args.preview:
        save_preview(args.preview, enemies, bonuses)
    print(f"{'Checked' if args.check else 'Wrote'} 24 enemy + 5 badge frames, all 16x16; legacy pixels/palette preserved")


if __name__ == "__main__":
    main()
