#!/usr/bin/env python3
"""Compile static presentation pixels into shared, byte-run encoded planar rows.

Source text remains authored in render_scenes.c / logic.c; the two source fonts
are inputs only. No font atlas, manga copy, or framebuffer is emitted.
"""
import argparse
from pathlib import Path
import re

GAME_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = GAME_ROOT / "art/presentation-rows.h"


def inputs():
    scenes = re.findall(r'\{"([^"]+)", "([^"]+)", "([^"]+)", (\d), (\d)\}',
                        (GAME_ROOT / "src/render_scenes.c").read_text())
    names = re.search(r'g_stageNames[^=]*=\s*\{([^}]+)',
                      (GAME_ROOT / "src/logic.c").read_text()).group(1)
    names = re.findall(r'"([^"]+)"', names)
    small = re.findall(r'\{([0-9, ]+)\}', (GAME_ROOT / "src/scene_font.h").read_text())
    small = [[int(n) for n in row.split(',')] for row in small]
    font = re.findall(r'^frame\n((?:[.X]{5}\n){7})',
                      (GAME_ROOT / "art/font.txt").read_text(), re.M)
    font = [[int(row.replace('.', '0').replace('X', '1'), 2)
             for row in glyph.splitlines()] for glyph in font]
    assert len(scenes) == 13 and len(names) == 4 and len(small) == 26 and len(font) == 36
    return scenes, names, small, font


def rect(image, x, y, w, h, ink):
    for row in image[y:y+h]:
        row[x:x+w] = [ink] * w


def text(image, x, y, message, ink, font, width):
    for letter in message.upper():
        index = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".find(letter)
        if index >= 0:
            for dy, mask in enumerate(font[index]):
                for dx in range(width):
                    if mask & (1 << (width - dx - 1)):
                        image[y+dy][x+dx] = ink
        x += width + 1


def wrapped(image, y, message, ink, font):
    while message:
        length = min(len(message), 28)
        if length < len(message):
            while message[length] != ' ':
                length -= 1
        text(image, 8, y, message[:length], ink, font, 4)
        message = message[length:].lstrip()
        y += 8


def layers():
    scenes, names, small, font = inputs()
    cards, hud = [], []
    for index, (title, caption, reply, panel, style) in enumerate(scenes):
        image = [[0] * 160 for _ in range(136)]
        accent = [5, 11, 7, 14][int(style)]
        rect(image, 20, 12, 120, 72, accent)
        if index == 12 or index % 3:
            wrapped(image, 4, title, accent, small)
        wrapped(image, 88, caption, 6, small)
        wrapped(image, 108, reply, 14, small)
        cards.append(image)
    for name in names:
        for ready in range(2):
            image = [[0] * 320 for _ in range(256)]
            rect(image, 0, 0, 320, 28, 1)
            rect(image, 0, 28, 320, 1, 15)
            rect(image, 0, 245, 320, 1, 3)
            for x, y, message, ink in (
                (8, 6, name, 5), (126, 6, 'SCORE', 5),
                (218, 6, 'LIVES', 5), (266, 6, 'SECTOR', 5),
                (8, 18, 'READY' if ready else 'LANCE', 7 if ready else 4),
                (8, 249, 'DAMAGE', 4), (62, 249, 'SPEED', 4),
                (116, 249, 'SHIELD', 4), (176, 249, 'FIRE', 4),
                (224, 249, 'RELEASE FIRE' if ready else 'HOLD TO CHARGE', 14 if ready else 4)):
                text(image, x, y, message, ink, font, 5)
            hud.append(image[:29] + image[245:])
    return cards, hud


def planar(row):
    return bytes(sum(((ink >> plane) & 1) << (7 - bit)
                     for bit, ink in enumerate(row[x:x+8]))
                 for plane in range(4) for x in range(0, len(row), 8))


def encode(row):
    # Literal blocks avoid two-byte runs for dense glyph data. Commands never
    # cross plane boundaries; prefix their exact count for bounded scheduling.
    data, operations = [], 0
    span = len(row) // 4
    for start in range(0, len(row), span):
        end = start + span
        while start < end:
            stop = start + 1
            while stop < end and row[stop] == row[start]:
                stop += 1
            if stop - start >= 3:
                data.extend((stop - start, row[start]))
                start = stop
            else:
                stop = start + 1
                while stop < end:
                    if stop + 2 < end and row[stop] == row[stop+1] == row[stop+2]:
                        break
                    stop += 1
                data.append(128 | (stop - start))
                data.extend(row[start:stop])
                start = stop
            operations += 1
    assert 0 < operations <= 64
    return bytes([operations] + data)


def generate():
    cards, hud = layers()
    pool, offsets = bytearray(), {}
    tables = []
    for group in (cards, hud):
        table = []
        for image in group:
            indices = []
            for pixels in image:
                row = encode(planar(pixels))
                if row not in offsets:
                    offsets[row] = len(pool)
                    pool.extend(row)
                indices.append(offsets[row])
            table.append(indices)
        tables.append(table)
    assert len(pool) < 65536
    lines = ['/* Generated by tools/make-presentation.py; do not edit. */',
             '#ifndef ASTRA_PRESENTATION_ROWS_H', '#define ASTRA_PRESENTATION_ROWS_H',
             f'static const unsigned char s_presentationBytes[{len(pool)}] = {{']
    for i in range(0, len(pool), 24):
        lines.append('\t' + ','.join(str(v) for v in pool[i:i+24]) + ',')
    lines.append('};')
    for name, table in zip(('s_cardRows', 's_hudRows'), tables):
        lines.append(f'static const unsigned short {name}[{len(table)}][{len(table[0])}] = {{')
        lines.extend('\t{' + ','.join(map(str, row)) + '},' for row in table)
        lines.append('};')
    lines.extend(('#endif', ''))
    size = len(pool) + sum(len(row) * 2 for table in tables for row in table)
    return '\n'.join(lines), size


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    generated, size = generate()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != generated:
            raise SystemExit('stale presentation rows: run python3 tools/make-presentation.py')
    else:
        OUTPUT.write_text(generated)
    print(f'presentation rows: {size} resident bytes; 13 cards, 8 shared HUD variants')
