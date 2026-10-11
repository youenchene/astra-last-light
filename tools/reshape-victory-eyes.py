#!/usr/bin/env python3.12
"""Reproduce the approved offline eye reshape selected by the ending importer."""
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(os.environ.get('AGK_KIT', Path.home() / 'Code/amiga/amiga-game-kit')) / 'harness'))
from agk.image import Image, load_png_rgba

ART = ROOT / 'game/art/selected-rd'
PARENT = ART / 'victory-identity-master'
DEST = ART / 'victory-eyes-almond'
MASK_RECORD = ART / 'victory-eyes-refined/request.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path, size):
    w, h, pixels = load_png_rgba(str(path))
    assert (w, h) == size and all(p[3] == 255 for p in pixels)
    return [p[:3] for p in pixels]


def save(name, pixels, w, h):
    rgb = bytes(c for p in pixels for c in p)
    (DEST / name).write_bytes(Image(rgb, w, h).to_png())
    return rgb


def mask_png(name, mask, w, h):
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag+data))
    rows = b''.join(b'\0' + bytes(255 if m else 0 for m in mask[y*w:(y+1)*w]) for y in range(h))
    (DEST / name).write_bytes(b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 0, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def sample(values):
    return [values[((2*y+1)*288//384)*480 + (2*x+1)*480//640] for y in range(192) for x in range(320)]


def reshape(parent, spans):
    result = list(parent)
    mappings = []
    for eye in spans:
        columns = {}
        for y, left, right in eye:
            for x in range(left, right+1):
                columns.setdefault(x, []).append(y)
        left, right = min(columns), max(columns)
        center, radius = (left+right)/2, (right-left)/2
        for x, ys in columns.items():
            top, bottom = min(ys), max(ys)
            taper = max(0, 1 - ((x-center)/radius)**4)
            removed = round((bottom-top+1) * 0.28 * taper)
            new_top = top + round(removed * 0.2)
            new_bottom = bottom - (removed - (new_top-top))
            # Boundary colors are sampled from the same column of the parent.
            # The lower sample is beyond the original eye liner, in peach skin.
            below = parent[(bottom+4)*480+x]
            above = parent[top*480+x]
            for y in ys:
                if y < new_top:
                    result[y*480+x] = above
                elif y > new_bottom:
                    result[y*480+x] = below
                else:
                    source_y = top + round((y-new_top)*(bottom-top)/max(1, new_bottom-new_top))
                    result[y*480+x] = parent[source_y*480+x]
            mappings.append({'x': x, 'source_y': [top, bottom], 'target_y': [new_top, new_bottom],
                             'peach_sample_xy': [x, bottom+4]})
    return result, mappings


def verify(before, after, mask):
    changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    outside = sum(not mask[i] for i in changed)
    assert outside == 0
    return {'changed_pixels': len(changed), 'mask_pixels': sum(mask),
            'outside_mask_changed_pixels': outside, 'outside_mask_equal': True}


def preview(parent, master, mask):
    overlay = [tuple((c+t)//2 for c, t in zip(p, (255, 0, 255))) if m else p
               for p, m in zip(parent, mask)]
    zooms = []
    for name, pixels in [('before', parent), ('after', master), ('mask', overlay)]:
        zoom = [pixels[(90+y//4)*480+90+x//4] for y in range(220) for x in range(460)]
        save(name+'-face-4x.png', zoom, 460, 220)
        zooms.append(zoom)
    comparison = [p for y in range(220) for p in zooms[0][y*460:(y+1)*460]+zooms[1][y*460:(y+1)*460]]
    save('before-after-face-4x.png', comparison, 920, 220)


def main():
    DEST.mkdir(exist_ok=True)
    mask_record = json.loads(MASK_RECORD.read_text())
    assert sha(PARENT / 'master.png') == mask_record['parent_master_sha256']
    assert sha(PARENT / 'victory.png') == mask_record['parent_runtime_sha256']
    spans = mask_record['eye_spans_y_xmin_xmax_inclusive']
    selected = {(x, y) for eye in spans for y, left, right in eye for x in range(left, right+1)}
    mask = [(x, y) in selected for y in range(288) for x in range(480)]
    parent = load(PARENT / 'master.png', (480, 288))
    master, mappings = reshape(parent, spans)
    assert set(master) <= set(parent), 'Offline reshape must not introduce colors'
    for x in (104, 131, 163, 191):
        assert all(master[y*480+x] == parent[y*480+x] for y in range(288)), 'Outer corner changed'
    runtime = sample(master)
    baseline = load(PARENT / 'victory.png', (320, 192))
    assert sample(parent) == baseline
    save('master.png', master, 480, 288)
    rgb = save('runtimevictory.png', runtime, 320, 192)
    save('victory.png', runtime, 320, 192)
    (DEST / 'victory.rgb.hex').write_text(rgb.hex()+'\n')
    mask_png('master-mask.png', mask, 480, 288)
    mask_png('runtime-mask.png', sample(mask), 320, 192)
    preview(parent, master, mask)
    comparison = [p for y in range(192) for p in baseline[y*320:(y+1)*320]+runtime[y*320:(y+1)*320]]
    save('before-after-runtime.png', comparison, 640, 192)
    # Re-decode delivered PNGs and grayscale masks for independent export checks.
    checks = {}
    for label, before, name, mask_name, size in [
        ('master', parent, 'master.png', 'master-mask.png', (480, 288)),
        ('runtime', baseline, 'victory.png', 'runtime-mask.png', (320, 192)),
    ]:
        decoded_mask = load(DEST / mask_name, size)
        assert (DEST / mask_name).read_bytes()[24:26] == bytes((8, 0))
        assert set(decoded_mask) == {(0, 0, 0), (255, 255, 255)}
        checks[label] = verify(before, load(DEST / name, size), [p[0] == 255 for p in decoded_mask])
    assert bytes.fromhex((DEST / 'victory.rgb.hex').read_text()) == rgb
    files = ['master.png', 'victory.png', 'runtimevictory.png', 'victory.rgb.hex', 'master-mask.png',
             'runtime-mask.png', 'before-after-face-4x.png', 'before-after-runtime.png']
    provenance = {
        'method': 'Deterministic offline localized eye reshape of RD identity parent; not RD-generated edit',
        'paid_requests': 0, 'cost_usd': 0, 'balance_cost': 0, 'integrated': True,
        'input_sha256': sha(ART / 'victory-a.png'),
        'master_sha256': sha(DEST / 'master.png'),
        'image_sha256': sha(DEST / 'victory.png'),
        'rgb_sha256': hashlib.sha256(rgb).hexdigest(),
        'original': '../victory-a.png', 'parent_master': '../victory-identity-master/master.png',
        'width': 320, 'height': 192, 'master_width': 480, 'master_height': 288,
        'original_sha256': sha(ART / 'victory-a.png'),
        'parent_master_sha256': sha(PARENT / 'master.png'),
        'parent_runtime_sha256': sha(PARENT / 'victory.png'),
        'mask_spans_source': str(MASK_RECORD.relative_to(ROOT)), 'mask_spans_source_sha256': sha(MASK_RECORD),
        'eye_spans_y_xmin_xmax_inclusive': spans,
        'master_mask_bounding_boxes_xyxy_inclusive': [[104, 110, 131, 134], [163, 110, 191, 134]],
        'runtime_mask_bounding_boxes_xyxy_inclusive': [[69, 73, 87, 89], [109, 73, 127, 89]],
        'transform': '28% vertical compression tapered to zero at outer column boundaries, nearest source pixels; same-column skin fill',
        'column_mappings': mappings,
        'runtime_conversion': 'Unchanged pixel-center nearest sampling; no palette changes',
        'sha256': {name: sha(DEST / name) for name in files},
        'helper_sha256': sha(Path(__file__)), 'verification': checks,
        'palette_verification': 'All output master RGB colors already occur in parent; no quantization or runtime palette files edited',
        'outer_corner_verification': 'Extreme mask columns 104,131,163,191 are byte-for-byte unchanged',
    }
    (DEST / 'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
