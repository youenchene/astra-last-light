"""Independent .info reader and byte/pixel contracts; no native build required."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / 'assets/workbench'
spec = importlib.util.spec_from_file_location('workbench_writer', ROOT / 'tools/make-workbench-icons.py')
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)


def unpack_rle(data, bits, count):
    """Read OS3.5 bit-oriented PackBits, including Rugby's compressed images."""
    position = 0

    def take(n):
        nonlocal position
        value = 0
        for _ in range(n):
            value = value * 2 + ((data[position // 8] >> (7 - position % 8)) & 1)
            position += 1
        return value

    out = []
    while len(out) < count:
        control = take(8)
        if control < 128:
            out.extend(take(bits) for _ in range(control + 1))
        elif control > 128:
            out.extend([take(bits)] * (257 - control))
    if len(out) != count:
        raise ValueError('RLE overrun')
    return bytes(out)


def read_icon(path):
    data = path.read_bytes()
    if data[:4] != bytes.fromhex('e3100001'):
        raise ValueError('Invalid DiskObject header')
    long = lambda offset: int.from_bytes(data[offset:offset + 4], 'big')
    pos = 78
    drawer = None
    if long(66):
        drawer = data[pos:pos + 56]
        pos += 56
    classic = []
    image_headers = []
    for pointer in (22, 26):
        if not long(pointer):
            continue
        header = data[pos:pos + 20]
        x, y, w, h, depth, imageptr, pick, onoff, nextptr = struct.unpack('>hhhhhIBBI', header)
        if nextptr or not 0 < w <= 256 or not 0 < h <= 256 or not 0 < depth <= 8:
            raise ValueError('Unsupported image')
        pos += 20
        stride = ((w + 15) // 16) * 2
        planes = data[pos:pos + stride * h * depth]
        if len(planes) != stride * h * depth:
            raise ValueError('Short image')
        pos += len(planes)
        pixels = []
        for row in range(h):
            for col in range(w):
                value, source_plane = onoff & ~pick, 0
                for plane in range(8):
                    if pick & (1 << plane):
                        value |= ((planes[source_plane * stride * h + row * stride + col // 8] >> (7 - col % 8)) & 1) << plane
                        source_plane += 1
                pixels.append(value)
        classic.append((w, h, bytes(pixels)))
        image_headers.append((x, y, depth, imageptr, pick, onoff, nextptr))

    def string():
        nonlocal pos
        n = long(pos)
        pos += 4
        raw = data[pos:pos + n]
        pos += n
        if not 1 <= n <= 128 or len(raw) != n or raw[-1] != 0:
            raise ValueError('Malformed Workbench string')
        return raw[:-1].decode('ascii')

    default = string() if long(50) else None
    tooltypes = []
    if long(54):
        count = long(pos)
        if count < 4 or count % 4:
            raise ValueError('Invalid tooltype array size')
        pos += 4
        tooltypes = [string() for _ in range(count // 4 - 1)]
    window = string() if long(70) else None
    if drawer and 0 < long(44) & 255 <= 1:
        pos += 6
    form_offset = pos
    if data[pos:pos + 4] != b'FORM' or data[pos + 8:pos + 12] != b'ICON':
        raise ValueError('Missing genuine GlowIcon FORM ICON')
    end = pos + 8 + long(pos + 4)
    if end != len(data):
        raise ValueError('Wrong FORM size or trailing bytes')
    pos += 12
    rich, palette = [], None
    while pos < end:
        tag, n = struct.unpack_from('>4sI', data, pos)
        chunk = data[pos + 8:pos + 8 + n]
        if len(chunk) != n:
            raise ValueError('Truncated IFF chunk')
        pos += 8 + n + (n & 1)
        if tag == b'FACE':
            w, h = chunk[0] + 1, chunk[1] + 1
        elif tag == b'IMAG':
            transparent, colors, flags, packing, palpacking, depth, size, palsize = struct.unpack('>BBBBBBHH', chunk[:10])
            image = chunk[10:11 + size]
            image = unpack_rle(image, depth, w * h) if packing else image
            if flags & 2:
                raw = chunk[11 + size:12 + size + palsize]
                raw = unpack_rle(raw, 8, (colors + 1) * 3) if palpacking else raw
                if len(raw) != (colors + 1) * 3:
                    raise ValueError('Incorrect palette length')
                palette = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]
            if len(image) != w * h or max(image) >= len(palette):
                raise ValueError('Incorrect chunky image')
            rich.append((w, h, [(*palette[i], 0 if flags & 1 and i == transparent else 255) for i in image]))
    if pos != end:
        raise ValueError('Invalid IFF padding')
    return dict(header=data[:78], drawer=drawer, classic=classic, image_headers=image_headers,
                default=default, tooltypes=tooltypes, window=window, rich=rich, form_offset=form_offset)


class WorkbenchIcons(unittest.TestCase):
    def test_diskobject_contracts_and_exact_exported_pixels(self):
        for name, kind, source in [('drawer', 2, 'drawer'), ('tool', 3, 'interceptor'), ('whdload', 4, 'interceptor')]:
            with self.subTest(icon=name):
                icon = read_icon(ART / f'Astra-{name}.info')
                header = icon['header']
                self.assertEqual(header[48:50], bytes([kind, 0]))
                self.assertEqual(struct.unpack_from('>HHHHH', header, 12), (64, 48, 6, 3, 1))
                self.assertEqual(struct.unpack_from('>II', header, 58), (0x80000000, 0x80000000))
                self.assertEqual(struct.unpack_from('>I', header, 74)[0], 65536)
                self.assertEqual(icon['default'], 'WHDLoad' if kind == 4 else None)
                self.assertEqual(icon['tooltypes'], ['SLAVE=Astra.slave', 'PRELOAD'] if kind == 4 else [])
                self.assertIsNone(icon['window'])
                self.assertEqual(icon['drawer'] is not None, kind == 2)
                if kind == 2:
                    self.assertEqual(len(icon['drawer']), 56)
                    self.assertEqual(struct.unpack_from('>hhhh', icon['drawer']), (20, 20, 300, 160))
                    self.assertEqual(icon['drawer'][18:38], bytes(20))
                    self.assertEqual(struct.unpack_from('>H', icon['drawer'], 46)[0], 1)
                self.assertEqual(len(icon['classic']), 2)
                self.assertEqual(len(icon['rich']), 2)
                self.assertNotEqual(icon['classic'][0], icon['classic'][1])
                self.assertNotEqual(icon['rich'][0], icon['rich'][1])
                for i, state in enumerate(('normal', 'selected')):
                    self.assertEqual(icon['image_headers'][i], (0, 0, 2, 1, 3, 0, 0))
                    w, h, pens = icon['classic'][i]
                    self.assertEqual((w, h), (64, 48))
                    exported = writer.load_png_rgba(ART / f'{source}-classic-{state}.png')
                    self.assertEqual(exported, (w, h, [(*writer.CLASSIC[p], 255) for p in pens]))
                    self.assertEqual(writer.load_png_rgba(ART / f'{source}-{state}.png'), icon['rich'][i])
                self.assertEqual([p[3] for p in icon['rich'][0][2]], [p[3] for p in icon['rich'][1][2]])

    def test_reproduction_and_provenance(self):
        for name, data in writer.outputs().items():
            self.assertEqual((ART / name).read_bytes(), data, name)
        manifest = json.loads((ART / 'generation.json').read_text())
        self.assertAlmostEqual(sum(e['cost_usd'] for e in manifest.values()), 0.36)
        for name, entry in manifest.items():
            self.assertEqual(entry['status'], 'complete')
            self.assertTrue(entry['task_id'])
            self.assertTrue(entry['request_id'])
            self.assertEqual(entry['request']['num_images'], 1)
            self.assertEqual(entry['request']['prompt_style'], 'rd_pro__default')
            self.assertTrue(entry['request']['remove_bg'])
            self.assertEqual(hashlib.sha256((ART / f'{name}-master.png').read_bytes()).hexdigest(), entry['sha256'])

    def test_string_limit(self):
        self.assertEqual(len(writer.icon_string('A' * 127)), 132)
        with self.assertRaises(ValueError):
            writer.icon_string('A' * 128)


def previews():
    """Compile previews by decoding actual .info bytes, including read-only Rugby."""
    out = ROOT / '.tmp/workbench-icons'
    out.mkdir(parents=True, exist_ok=True)
    sources = [(f'Astra-{name}', ART / f'Astra-{name}.info') for name in ('drawer', 'tool', 'whdload')]
    reference = ROOT / '.tmp/SuperRugbyV/assets/workbench/source'
    sources += [(f'Rugby-reference-{name}', reference / f'Retromiga-{name}.info') for name in ('drawer', 'launch')]
    html = ['<!doctype html><meta charset="utf-8"><title>Astra Workbench decoded icon previews</title>',
            '<style>body{background:#182234;color:white;font:16px sans-serif}img{image-rendering:pixelated;width:256px}figure{display:inline-block;background:#aaa;padding:16px;color:black}</style>',
            '<h1>Decoded .info previews</h1><p>Classic: Workbench 1.3 default pens. Rich: embedded GlowIcon palette. Rugby references are read-only comparisons, not Astra source art.</p>']
    for name, path in sources:
        if not path.exists():
            continue
        icon = read_icon(path)
        html.append(f'<h2>{name}</h2>')
        for format in ('classic', 'rich'):
            for state, (w, h, pixels) in zip(('normal', 'selected'), icon[format]):
                if format == 'classic':
                    pixels = [(*writer.CLASSIC[p], 255) for p in pixels]
                filename = f'{name}-{format}-{state}.png'
                (out / filename).write_bytes(writer.png(w, h, pixels))
                html.append(f'<figure><img src="{filename}"><figcaption>{format} {state} ({w}×{h})</figcaption></figure>')
    (out / 'index.html').write_text('\n'.join(html))
    print(out / 'index.html')


if __name__ == '__main__':
    import sys
    if '--previews' in sys.argv:
        previews()
    else:
        unittest.main()
