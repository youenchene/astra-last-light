#!/usr/bin/env python3
"""Compile static presentation pixels into shared, byte-run encoded planar rows.

Source text remains authored in render_scenes.c / logic.c; the two source fonts
are inputs only. Five shared selected manga row tables avoid thirteen art copies.
"""
import argparse
from collections import Counter
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from selected_rd import panels

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
        if index == 12:
            image = [[0] * 320 for _ in range(256)]
            text(image, (320 - len(title) * 6 + 1) // 2, 12, title, 14, font, 5)
            prompt = 'FIRE TO RESTART'
            text(image, (320 - len(prompt) * 6 + 1) // 2, 237, prompt, 6, font, 5)
            cards.append(image[:32] + image[224:])
            continue
        image = [[0] * 176 for _ in range(152)]
        accent = [5, 11, 7, 14][int(style)]
        rect(image, 6, 10, 164, 100, accent)
        if index % 3:
            wrapped(image, 4, title, accent, small)
        wrapped(image, 112, caption, 6, small)
        wrapped(image, 130, reply, 14, small)
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


def encode(row, previous=None, dictionary=None, literals=()):
    # Offline shortest encoding: repeat / prior-framebuffer reference / literal /
    # packed-literal (two arbitrary dictionary bytes per input byte). Token zero
    # escapes to a previous-row copy. No command crosses a plane or references
    # uninitialized pixels. This is byte compression, never runtime resizing.
    best = [(0, 0, b'')] * (len(row) + 1)
    for start in range(len(row) - 1, -1, -1):
        choices = []
        matches = {}
        if dictionary is not None:
            for source, address in dictionary.get(row[start:start+4], {}).items():
                count = 4
                while count < min(len(source), len(row) - start) and source[count] == row[start+count]:
                    count += 1
                for length in range(4, count + 1):
                    matches[length] = address
        for count in range(1, len(row) - start + 1):
            stop = start + count
            commands = [bytes([128 | count]) + row[start:stop]]
            if all(value in literals for value in row[start:stop]):
                codes = [literals.index(value) for value in row[start:stop]]
                if len(codes) & 1:
                    codes.append(0)
                commands.append(bytes([192 | count]) + bytes(
                    codes[i] << 4 | codes[i+1] for i in range(0, len(codes), 2)))
            if row[start:stop] == bytes([row[start]]) * count:
                commands.append(bytes([count, row[start]]))
            if previous is not None and row[start:stop] == previous[start:stop]:
                commands.append(bytes([0, count]))
            if count in matches:
                address = matches[count]
                commands.append(bytes([64 | count, address >> 8, address & 255]))
            size, operations, suffix = best[stop]
            choices.extend((len(command) + size, operations + 1, command + suffix)
                           for command in commands)
        best[start] = min(choices)
    _, operations, data = best[0]
    assert 0 < operations <= 64
    return bytes([operations]) + data


def generate():
    cards, hud = layers()
    manga = panels()
    literal_tables = []
    for images in (cards + hud, *([image] for image in manga)):
        frequencies = Counter(value for image in images for pixels in image for value in planar(pixels))
        literal_tables.append(tuple(value for value, _ in sorted(
            frequencies.items(), key=lambda pair: (-pair[1], pair[0]))[:16]))
    pool, offsets = bytearray(), {}
    rows, row_ids, costs = [], {}, []
    tables = []
    for group in (cards, hud, manga):
        table = []
        for image_index, image in enumerate(group):
            literals = literal_tables[image_index + 1 if group is manga else 0]
            indices = []
            previous = None
            dictionary = {}
            for row_index, pixels in enumerate(image):
                raw = planar(pixels)
                if group is cards:
                    y, x = (row_index + (192 if row_index >= 32 else 0), 0) if image_index == 12 else (56 + row_index, 17)
                elif group is hud:
                    y, x = row_index + (216 if row_index >= 29 else 0), 0
                else:
                    y, x = (32 + row_index, 0) if image_index == 4 else (68 + row_index, 18)
                # The two margin/HUD bands are not adjacent in the framebuffer.
                if (group is hud and row_index == 29) or (group is cards and len(image) == 64 and row_index == 32):
                    previous = None
                span = len(raw) // 4
                planes, cost = [], 0
                for start in range(0, len(raw), span):
                    plane = raw[start:start+span]
                    encoded = encode(plane, None if previous is None else previous[start:start+span], dictionary, literals)
                    cost += encoded[0]
                    stream = encoded[1:]
                    if stream not in offsets:
                        offsets[stream] = len(pool)
                        pool.extend(stream)
                    planes.append(offsets[stream])
                    for column in range(span - 3):
                        address = (y << 8) | ((start // span) * 40 + x + column)
                        dictionary.setdefault(plane[column:column+4], {}).setdefault(plane[column:], address)
                assert 0 < cost <= 64
                key = tuple(planes)
                if key not in row_ids:
                    row_ids[key] = len(rows)
                    rows.append(key)
                    costs.append(cost)
                indices.append(row_ids[key])
                previous = raw
            table.append(indices)
        tables.append(table)
    assert len(pool) < 65536
    assert len(rows) < 65536
    lines = ['/* Generated by tools/make-presentation.py; do not edit. */',
             '#ifndef ASTRA_PRESENTATION_ROWS_H', '#define ASTRA_PRESENTATION_ROWS_H',
             '/* Keep this read-only payload out of the monolithic code hunk.',
             ' * AmigaDOS must fit each hunk into one physical memory bank. */',
             '#ifdef AMIGA', '#define PRESENTATION_DATA __attribute__((section(".data")))',
             '#else', '#define PRESENTATION_DATA', '#endif',
             f'static const unsigned char s_presentationBytes[{len(pool)}] PRESENTATION_DATA = {{']
    for i in range(0, len(pool), 24):
        lines.append('\t' + ','.join(str(v) for v in pool[i:i+24]) + ',')
    lines.append('};')
    lines.append('static const unsigned char s_presentationLiterals[6][16] PRESENTATION_DATA = {')
    lines.extend('\t{' + ','.join(map(str, literals)) + '},' for literals in literal_tables)
    lines.append('};')
    lines.append(f'static const unsigned short s_presentationPlanes[{len(rows)}][4] PRESENTATION_DATA = {{')
    lines.extend('\t{' + ','.join(map(str, row)) + '},' for row in rows)
    lines.append('};')
    lines.append(f'static const unsigned char s_presentationCosts[{len(costs)}] PRESENTATION_DATA = {{')
    for start in range(0, len(costs), 24):
        lines.append('\t' + ','.join(map(str, costs[start:start+24])) + ',')
    lines.append('};')
    lines.extend(('typedef struct {',
                  '\tunsigned short first, height, y;',
                  '\tunsigned char x, span;',
                  '\tunsigned short split, gap, literals;',
                  '} tPresentationLayout;'))
    for name, table in zip(('s_card', 's_hud', 's_manga'), tables):
        flat = [offset for image in table for offset in image]
        assert len(flat) < 65536
        lines.append(f'static const unsigned short {name}Rows[{len(flat)}] PRESENTATION_DATA = {{')
        for start in range(0, len(flat), 24):
            lines.append('\t' + ','.join(map(str, flat[start:start+24])) + ',')
        lines.append('};')
        if name == 's_hud':
            continue
        lines.append(f'static const tPresentationLayout {name}Layouts[{len(table)}] PRESENTATION_DATA = {{')
        first = 0
        for index, image in enumerate(table):
            if name == 's_card':
                y, x, span, split, gap = (0, 0, 40, 32, 192) if index == 12 else (56, 17, 22, 152, 0)
            else:
                y, x, span, split, gap = (32, 0, 40, 192, 0) if index == 4 else (68, 18, 20, 96, 0)
            assert span * 4 <= 320 and x + span <= 40
            assert y + len(image) + gap <= 256
            literals = index + 1 if name == 's_manga' else 0
            lines.append('\t{' + ','.join(map(str, (first, len(image), y, x, span, split, gap, literals))) + '},')
            first += len(image)
        lines.append('};')
    lines.extend(('#undef PRESENTATION_DATA', '#endif', ''))
    size = len(pool) + len(rows) * 9 + sum(len(row) * 2 for table in tables for row in table) + 18 * 14 + 96
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
    print(f'presentation rows: {size} resident bytes; 13 cards, 8 HUD variants, 5 shared RD images')
