#!/usr/bin/env python3.12
"""Offline original Astra icons: classic planar images + OS3.5 FORM ICON."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'assets/workbench'
KIT = Path(os.environ.get('AGK_KIT', Path.home() / 'Code/amiga/amiga-game-kit'))
sys.path.insert(0, str(KIT / 'harness'))
from agk.image import load_png_rgba

WIDTH, HEIGHT = 64, 48
CLASSIC = [(0, 85, 170), (255, 255, 255), (0, 0, 0), (255, 136, 0)]


def png(width, height, pixels):
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))
    rows = b''.join(b'\0' + bytes(c for p in pixels[y * width:(y + 1) * width] for c in p)
                    for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def fit_master(name):
    width, height, pixels = load_png_rgba(ART / (name + '-master.png'))
    if (width, height) != (64, 64):
        raise ValueError('Expected preserved 64x64 RD master')
    # RD left a flat sage background behind the interceptor. Remove only that
    # exact RGB, not similar silver hull colors, and retain the untouched master.
    removed = sum(p[:3] == (203, 214, 203) and p[3] != 0 for p in pixels) if name == 'interceptor' else 0
    pixels = [(0, 0, 0, 0) if p[3] < 128 or (name == 'interceptor' and p[:3] == (203, 214, 203))
              else (*p[:3], 255) for p in pixels]
    occupied = [(i % width, i // width) for i, p in enumerate(pixels) if p[3]]
    x0, y0 = min(x for x, y in occupied), min(y for x, y in occupied)
    x1, y1 = max(x for x, y in occupied) + 1, max(y for x, y in occupied) + 1
    scale = min(60 / (x1 - x0), 44 / (y1 - y0), 1)
    w, h = round((x1 - x0) * scale), round((y1 - y0) * scale)
    out = [(0, 0, 0, 0)] * (WIDTH * HEIGHT)
    for y in range(h):
        for x in range(w):
            out[(y + (HEIGHT - h) // 2) * WIDTH + x + (WIDTH - w) // 2] = pixels[(y0 + y * (y1 - y0) // h) * width + x0 + x * (x1 - x0) // w]
    return out, dict(source_bbox=[x0, y0, x1, y1], fitted_size=[w, h], cleared_sage_pixels=removed)


def indexed(pixels):
    palette = [(0, 0, 0)]
    indices = []
    for r, g, b, a in pixels:
        rgb = (r, g, b)
        if not a:
            indices.append(0)
            continue
        if rgb not in palette[1:]:
            palette.append(rgb)
        indices.append(palette.index(rgb, 1))
    if len(palette) > 256:
        raise ValueError('Too many colors; explicitly author quantization instead of silently losing art')
    return bytes(indices), palette


def classic_indices(pixels, selected=False):
    result = []
    for r, g, b, a in pixels:
        if not a:
            pen = 0
        elif max(r, g, b) < 125:
            pen = 2
        elif r > g * 1.3 or (g > r * 1.25 and b > r * 1.25):
            pen = 3
        else:
            pen = 1
        if selected and pen in (1, 3):
            pen = 4 - pen
        result.append(pen)
    return bytes(result)


def planar(indices):
    data = bytearray()
    for plane in range(2):
        for y in range(HEIGHT):
            for x in range(0, WIDTH, 8):
                data.append(sum(((indices[y * WIDTH + x + bit] >> plane) & 1) << (7 - bit) for bit in range(8)))
    return struct.pack('>hhhhhIBBI', 0, 0, WIDTH, HEIGHT, 2, 1, 3, 0, 0) + data


def iff_chunk(tag, data):
    return tag + struct.pack('>I', len(data)) + data + (b'\0' if len(data) & 1 else b'')


def glow(states):
    palettes = [indexed(pixels) for pixels in states]
    face = struct.pack('>BBBBH', WIDTH - 1, HEIGHT - 1, 1, 0x11, max(len(p) * 3 for _, p in palettes) - 1)
    chunks = iff_chunk(b'FACE', face)
    for indices, palette in palettes:
        colors = bytes(c for p in palette for c in p)
        header = struct.pack('>BBBBBBHH', 0, len(palette) - 1, 3, 0, 0, 8, len(indices) - 1, len(colors) - 1)
        chunks += iff_chunk(b'IMAG', header + indices + colors)
    return iff_chunk(b'FORM', b'ICON' + chunks)


def icon_string(value):
    raw = value.encode('ascii') + b'\0'
    if len(raw) > 128:
        raise ValueError('Workbench string exceeds 128 bytes')
    return struct.pack('>I', len(raw)) + raw


def diskobject(kind, states, classic):
    header = bytearray(78)
    struct.pack_into('>HH', header, 0, 0xE310, 1)
    struct.pack_into('>HHHHH', header, 12, WIDTH, HEIGHT, 6, 3, 1)
    struct.pack_into('>II', header, 22, 1, 1)
    header[48] = kind
    struct.pack_into('>II', header, 50, int(kind == 4), int(kind == 4))
    struct.pack_into('>II', header, 58, 0x80000000, 0x80000000)
    struct.pack_into('>I', header, 66, int(kind == 2))
    struct.pack_into('>I', header, 74, 65536)
    drawer = bytearray(56) if kind == 2 else bytearray()
    if drawer:
        struct.pack_into('>hhhhBBII', drawer, 0, 20, 20, 300, 160, 0, 1, 0, 0x240027F)
        struct.pack_into('>hhhhH', drawer, 38, 100, 60, -1, -1, 1)
    metadata = b''
    if kind == 4:
        metadata = icon_string('WHDLoad') + struct.pack('>I', 12)
        metadata += icon_string('SLAVE=Astra.slave') + icon_string('PRELOAD')
    return bytes(header) + drawer + b''.join(planar(p) for p in classic) + metadata + glow(states)


def outputs():
    result, provenance = {}, {}
    for name in ('drawer', 'interceptor'):
        normal, details = fit_master(name)
        selected = [(min(255, r + 18), min(255, g + 34), min(255, b + 42), a) if a else (0, 0, 0, 0)
                    for r, g, b, a in normal]
        states = [normal, selected]
        classic = [classic_indices(normal, state == 1) for state in range(2)]
        provenance[name] = dict(details, selected='Offline RGB lift +18/+34/+42; same registered canvas and alpha',
                                classic_selected='Offline exchange pens 1 and 3; same silhouette')
        for state, pixels, pens in zip(('normal', 'selected'), states, classic):
            result[f'{name}-{state}.png'] = png(WIDTH, HEIGHT, pixels)
            result[f'{name}-classic-{state}.png'] = png(WIDTH, HEIGHT, [(*CLASSIC[p], 255) for p in pens])
        kinds = [('drawer', 2)] if name == 'drawer' else [('tool', 3), ('whdload', 4)]
        for target, kind in kinds:
            result[f'Astra-{target}.info'] = diskobject(kind, states, classic)
    provenance['sha256'] = {name: hashlib.sha256(data).hexdigest() for name, data in result.items()}
    result['conversion.json'] = (json.dumps(provenance, indent=2) + '\n').encode()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, data in outputs().items():
        path = ART / name
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit(f'Outdated or missing: {path}')
        else:
            path.write_bytes(data)
    print('Workbench icons: deterministic output verified' if args.check else 'Workbench icons written')


if __name__ == '__main__':
    main()
