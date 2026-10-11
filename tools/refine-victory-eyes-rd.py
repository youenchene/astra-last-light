#!/usr/bin/env python3.12
"""Prepare, quote and resume one eyes-only RD candidate; never integrate it."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import time
import urllib.request
import uuid
import zlib

ROOT = Path(__file__).resolve().parents[1]
KIT = Path(os.environ.get('AGK_KIT', Path.home() / 'Code/amiga/amiga-game-kit'))
sys.path.insert(0, str(KIT / 'harness'))
from agk import rd
from agk.image import Image, load_png_rgba

ART = ROOT / 'game/art/selected-rd'
PARENT = ART / 'victory-identity-master'
DEST = ART / 'victory-eyes-refined'
# Inclusive horizontal spans by row: shaped to avoid glove, brows and hair.
EYES = (
    [(110, 106, 121), (111, 105, 125), (112, 105, 127),
     (113, 105, 129), (114, 104, 130)]
    + [(y, 104, 131) for y in range(115, 129)]
    + [(129, 105, 131), (130, 106, 130), (131, 107, 129),
       (132, 108, 128), (133, 110, 126), (134, 112, 124)],
    [(110, 169, 178), (111, 166, 182), (112, 165, 185),
     (113, 164, 187), (114, 163, 189)]
    + [(y, 163, 191) for y in range(115, 129)]
    + [(129, 164, 190), (130, 165, 190), (131, 166, 189),
       (132, 168, 188), (133, 170, 186), (134, 172, 183)],
)
PROMPT = (
    'Edit only the two masked eyes of this same adult woman space pilot. '
    'Replace the large round doll-like eyes with slightly smaller, horizontally '
    'almond-shaped adult anime eyes. Relaxed upper eyelids partially cover the '
    'smaller blue-grey irises, subtly narrower vertical eye opening, calm confident '
    'gentle expression. Natural peach skin fills the removed rounded eye edges. '
    'Keep both eyes looking forward consistently, fine crisp pixel-art outlines '
    'and small restrained catchlights. Preserve the exact existing peach skin '
    'tone, eyebrows, nose, gentle smile, rounded side-part purple bob, salute, '
    'suit and background. Only refine the eyes, no other changes.'
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(name, value):
    target = DEST / name
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(target)


def load_rgb(path, size):
    width, height, pixels = load_png_rgba(str(path))
    assert (width, height) == size, (path, width, height)
    assert all(p[3] == 255 for p in pixels), 'Unexpected transparency'
    return [tuple(p[:3]) for p in pixels]


def save_rgb(name, pixels, width, height):
    data = bytes(c for p in pixels for c in p)
    (DEST / name).write_bytes(Image(data, width, height).to_png())
    return data


def save_mask(name, mask, width, height):
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))
    rows = b''.join(b'\0' + bytes(255 if v else 0 for v in mask[y*width:(y+1)*width])
                    for y in range(height))
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))
    (DEST / name).write_bytes(png)


def eye_mask(width, height):
    selected = {(x, y) for eye in EYES for y, left, right in eye for x in range(left, right+1)}
    return [(x, y) in selected for y in range(height) for x in range(width)]


def face_preview(name, pixels, width):
    # 4x nearest-neighbor inspection, source rectangle [90,90,205,145).
    zoom = [pixels[(90+y//4)*width + 90+x//4] for y in range(220) for x in range(460)]
    save_rgb(name, zoom, 460, 220)


def prepare():
    DEST.mkdir(exist_ok=True)
    parent = load_rgb(PARENT / 'master.png', (480, 288))
    crop = [parent[y*480+x] for y in range(256) for x in range(256)]
    save_rgb('input-crop.png', crop, 256, 256)
    mask = eye_mask(256, 256)
    save_mask('mask.png', mask, 256, 256)
    overlay = [tuple((c+t)//2 for c, t in zip(p, (255, 0, 255))) if m else p
               for p, m in zip(crop, mask)]
    face_preview('before-face-4x.png', crop, 256)
    face_preview('mask-overlay-face-4x.png', overlay, 256)
    save_rgb('mask-overlay.png', overlay, 256, 256)
    record = {
        'original_sha256': digest(ART / 'victory-a.png'),
        'parent_master_sha256': digest(PARENT / 'master.png'),
        'parent_runtime_sha256': digest(PARENT / 'victory.png'),
        'input_crop_sha256': digest(DEST / 'input-crop.png'),
        'mask_sha256': digest(DEST / 'mask.png'),
        'crop_xywh': [0, 0, 256, 256], 'eye_spans_y_xmin_xmax_inclusive': EYES,
        'mask_format': '8-bit grayscale PNG: 0 protected, 255 editable',
        'parameters': {'prompt': PROMPT, 'seed': 861015, 'soft_inpaint': False},
    }
    if (DEST / 'request.json').exists():
        previous = json.loads((DEST / 'request.json').read_text())
        assert json.loads(json.dumps(record)) == {k: v for k, v in previous.items() if k != 'custom_id'}
    else:
        save_json('request.json', dict(record, custom_id=str(uuid.uuid4())))
    print(f'Prepared crop (0,0,256,256); {sum(mask)} editable pixels.')


def request_body(record):
    for name, key in [('input-crop.png', 'input_crop_sha256'), ('mask.png', 'mask_sha256')]:
        assert digest(DEST / name) == record[key], f'{name} changed since preparation'
    assert digest(PARENT / 'master.png') == record['parent_master_sha256']
    assert digest(PARENT / 'victory.png') == record['parent_runtime_sha256']
    return dict(record['parameters'], custom_id=record['custom_id'],
                input_image=base64.b64encode((DEST / 'input-crop.png').read_bytes()).decode(),
                mask_image=base64.b64encode((DEST / 'mask.png').read_bytes()).decode())


def quote(record):
    catalog = rd._request('GET', '/edit/tools')
    save_json('catalog.json', catalog)
    result = rd._request('POST', '/edit/tools/inpainting/estimate', request_body(record))
    save_json('quote.json', result)
    print(json.dumps(result, indent=2))


def get_result(body):
    if (DEST / 'task.json').exists():
        task = json.loads((DEST / 'task.json').read_text())
        if task['status'] == 'succeeded':
            return task
    if (DEST / 'accepted.json').exists():
        accepted = json.loads((DEST / 'accepted.json').read_text())
    else:
        if (DEST / 'submission.json').exists():
            raise RuntimeError('Submission already attempted: recover via API Activity; never auto-resubmit.')
        save_json('submission.json', {'custom_id': body['custom_id'], 'attempted_at': time.time()})
        accepted = rd._request('POST', '/edit/tools/inpainting/tasks', body)
        save_json('accepted.json', accepted)
    print('Resumable task:', accepted['task_id'], flush=True)
    for _ in range(100):
        task = rd._request('GET', '/edit/tasks/' + accepted['task_id'])
        save_json('task.json', task)
        if task['status'] == 'succeeded':
            return task
        if task['status'] not in ('pending', 'running'):
            raise RuntimeError(f"Task stopped: {task['status']}; saved task.json, no resubmission")
        time.sleep(3)
    raise TimeoutError('Resume with action generate; accepted.json retains the task ID')


def sample_runtime(values):
    return [values[((2*y+1)*288//384)*480 + (2*x+1)*480//640]
            for y in range(192) for x in range(320)]


def invariance(before, after, mask):
    changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    outside = sum(not mask[i] for i in changed)
    assert outside == 0, f'{outside} changed pixels outside mask'
    return {'changed_pixels': len(changed), 'editable_pixels': sum(mask),
            'outside_mask_changed_pixels': outside, 'outside_mask_equal': True}


def verify_exports():
    """Independently decode saved PNGs and masks, then compare every pixel."""
    reports = {}
    for label, source, output, mask_name, size in [
        ('master', 'master.png', 'master.png', 'master-mask.png', (480, 288)),
        ('runtime', 'victory.png', 'runtimevictory.png', 'runtime-mask.png', (320, 192)),
    ]:
        mask_path = DEST / mask_name
        assert mask_path.read_bytes()[24:26] == bytes((8, 0)), 'Mask must be 8-bit grayscale'
        mask_pixels = load_rgb(mask_path, size)
        assert set(mask_pixels) == {(0, 0, 0), (255, 255, 255)}
        reports[label] = invariance(load_rgb(PARENT / source, size),
                                   load_rgb(DEST / output, size),
                                   [p[0] == 255 for p in mask_pixels])
    runtime = load_rgb(DEST / 'runtimevictory.png', (320, 192))
    assert bytes.fromhex((DEST / 'victory.rgb.hex').read_text()) == bytes(c for p in runtime for c in p)
    assert (DEST / 'mask.png').read_bytes()[24:26] == bytes((8, 0))
    provenance = json.loads((DEST / 'provenance.json').read_text())
    assert all(digest(DEST / name) == expected for name, expected in provenance['sha256'].items())
    request_body(provenance)
    assert digest(ART / 'victory-a.png') == provenance['original_sha256']
    save_json('export-verification.json', reports)
    print(json.dumps(reports, indent=2))


def composite(record, task):
    result = task['result']
    output = DEST / 'provider-output-crop.png'
    if not output.exists():
        if result.get('base64_images'):
            data = base64.b64decode(result['base64_images'][0])
        else:
            with urllib.request.urlopen(result['output_urls'][0], timeout=60) as response:
                data = response.read()
        output.write_bytes(data)
    edited = load_rgb(output, (256, 256))
    parent = load_rgb(PARENT / 'master.png', (480, 288))
    mask = eye_mask(480, 288)
    master = [edited[(i//480)*256+i%480] if m else p for i, (p, m) in enumerate(zip(parent, mask))]
    runtime = sample_runtime(master)
    baseline = load_rgb(PARENT / 'victory.png', (320, 192))
    assert sample_runtime(parent) == baseline, 'Parent runtime sampling differs'
    runtime_mask = sample_runtime(mask)
    verification: dict = {'master': invariance(parent, master, mask),
                          'runtime': invariance(baseline, runtime, runtime_mask)}
    original_crop = load_rgb(DEST / 'input-crop.png', (256, 256))
    crop_mask = eye_mask(256, 256)
    verification['provider_outside_mask_changed_pixels'] = sum(
        a != b and not m for a, b, m in zip(original_crop, edited, crop_mask))
    save_rgb('master.png', master, 480, 288)
    rgb = save_rgb('runtimevictory.png', runtime, 320, 192)
    (DEST / 'victory.rgb.hex').write_text(rgb.hex() + '\n')
    save_mask('master-mask.png', mask, 480, 288)
    save_mask('runtime-mask.png', runtime_mask, 320, 192)
    face_preview('after-face-4x.png', master, 480)
    before_zoom = load_rgb(DEST / 'before-face-4x.png', (460, 220))
    after_zoom = load_rgb(DEST / 'after-face-4x.png', (460, 220))
    comparison = [p for y in range(220)
                  for p in before_zoom[y*460:(y+1)*460] + after_zoom[y*460:(y+1)*460]]
    save_rgb('before-after-face-4x.png', comparison, 920, 220)
    save_json('verification.json', verification)
    names = ['provider-output-crop.png', 'master.png', 'runtimevictory.png',
             'victory.rgb.hex', 'master-mask.png', 'runtime-mask.png']
    save_json('provenance.json', dict(record, task_id=task['task_id'],
        balance_cost=result.get('balance_cost'), charged=result.get('charged'),
        method='RD localized inpainting; hard-mask composite over exact parent pixels',
        runtime_conversion='pixel-center nearest sampling, identical to parent conversion',
        api_base=rd.API, api_docs='https://github.com/Retro-Diffusion/api-examples/blob/main/EDIT_TOOLS.md',
        sha256={name: digest(DEST / name) for name in names}, verification=verification))
    print(json.dumps(verification, indent=2))
    print('Actual cost:', result.get('balance_cost'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'quote', 'generate', 'verify'])
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
        return
    if args.action == 'verify':
        verify_exports()
        return
    record = json.loads((DEST / 'request.json').read_text())
    if args.action == 'quote':
        quote(record)
        return
    body = request_body(record)
    quoted = json.loads((DEST / 'quote.json').read_text())
    assert float(quoted['balance_cost']) <= 0.18, 'Exceeds the authorized single-job quote'
    composite(record, get_result(body))


if __name__ == '__main__':
    main()
