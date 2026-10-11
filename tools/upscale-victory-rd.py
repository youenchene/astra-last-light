#!/usr/bin/env python3.12
"""One resumable RD img2img enlargement; never overwrite the original master."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
KIT = Path(os.environ.get('AGK_KIT', Path.home() / 'Code/amiga/amiga-game-kit'))
sys.path.insert(0, str(KIT / 'harness'))
from agk import rd
from agk.image import Image, load_png_rgba

DEST = ROOT / 'game/art/selected-rd/victory-upscaled'


def save(name, value):
    (DEST / name).write_text(json.dumps(value, indent=2) + '\n')


def main():
    global DEST
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true', help='Submit the quoted paid job or resume it')
    parser.add_argument('--variant', choices=('original', 'detail-native', 'detail-master', 'identity-master'), default='original')
    args = parser.parse_args()
    if args.variant != 'original':
        DEST = ROOT / 'game/art/selected-rd' / ('victory-' + args.variant)
    source = ROOT / 'game/art/selected-rd/victory-a.png'
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    assert digest == '35db36fca78bd8ff308dc8250b82ea2658bb28e55071110931a9f6cb9662b7f5'
    DEST.mkdir(exist_ok=True)
    request_file = DEST / 'request.json'
    if request_file.exists():
        record = json.loads(request_file.read_text())
        assert record['input_sha256'] == digest
    else:
        record = {
            'input_sha256': digest,
            'idempotency_key': str(uuid.uuid4()),
            'request': {
                'prompt_style': 'rd_plus__default', 'width': 320, 'height': 192,
                'num_images': 1, 'seed': 861013, 'strength': 0.3,
                'remove_bg': False, 'bypass_prompt_expansion': True,
                'prompt': 'Faithfully enlarge this exact victory scene. Preserve the same composition, '
                          'purple-haired female space pilot smiling in the left foreground, white and '
                          'blue space suit, small spacecraft flying across the orange dawn sky on the '
                          'right, and dark mountain silhouettes. Refine edges and small details at '
                          'the higher resolution while preserving her face, pose, colors and all '
                          'objects. Clean crisp pixel art, no text, no added objects or border.',
            },
        }
        if args.variant != 'original':
            record['request'].update({
                'strength': 0.72, 'seed': 861014,
                'prompt': 'A beautifully detailed science fiction anime victory illustration. '
                          'Preserve the reference composition: the same young adult woman pilot with '
                          'short purple hair smiling and saluting at her temple in the left foreground, '
                          'wearing a white and blue armored flight suit. A squadron of small white '
                          'space fighters flies home across an orange sunrise on the right above '
                          'a dark mountain horizon. Redraw with substantially finer detail: clearly '
                          'defined expressive eyes and irises, fine individual hair strands and '
                          'highlights, articulated glove fingers, precise suit seams and layered '
                          'collar hardware, detailed spacecraft wings and engines, layered distant '
                          'mountains and delicate illuminated clouds. Fine single-pixel outlines and '
                          'elegant small pixel clusters at the requested resolution, polished cinematic '
                          'game ending artwork, warm hopeful lighting. Retain character identity and '
                          'pose. No lettering, logos, panels or border. Do not reproduce enlarged '
                          'low-resolution pixel blocks; resolve fresh detail throughout the scene.',
            })
            if args.variant == 'detail-master':
                record['request'].update(prompt_style='rd_plus__environment', width=480, height=288)
            if args.variant == 'identity-master':
                record['request'].update({
                    'prompt_style': 'rd_plus__environment', 'width': 480, 'height': 288,
                    'strength': 0.55, 'seed': 861013,
                    'prompt': 'Faithful high-definition redraw of this exact reference illustration. '
                              'The adult female space pilot must look like the SAME woman as the reference: '
                              'a short smooth rounded purple bob ending at the jaw, an off-center side '
                              'part and long diagonal side-swept fringe crossing her forehead. Preserve '
                              'the asymmetric sweep and clean rounded bob silhouette exactly; do not '
                              'give her straight chopped bangs, spiky hair, shaggy nape strands, a pixie '
                              'cut or a younger face. Restore the reference natural peach and warm rosy '
                              'skin tone, with subtle rose cheek shading, softly defined nose, blue-grey '
                              'eyes and her gentle confident smile. Skin is lit neutrally: no yellow cast, '
                              'no golden yellow skin, no bright pink or magenta face. The orange sunset '
                              'belongs to the sky, not the skin. Preserve the same salute, white and blue '
                              'armored pilot suit, left foreground portrait, small white fighter squadron '
                              'in the right sky and dark distant mountain horizon. Add fine individual '
                              'hair strands inside the original haircut, precise eye details, glove '
                              'joints, suit seams and small spacecraft details at the new resolution. '
                              'Elegant high-definition pixel art with thin outlines and small pixel '
                              'clusters, keeping the original character design and composition. '
                              'No text, logos, frame or border.',
                })
        save('request.json', record)
    body = dict(record['request'], input_image=base64.b64encode(original).decode())
    if not args.generate:
        quote = rd._request('POST', '/inferences', dict(body, check_cost=True))
        save('quote.json', {'balance_cost': quote['balance_cost'], 'model': quote.get('model')})
        print(f"Quoted cost: ${quote['balance_cost']}")
        return
    if (DEST / 'provenance.json').exists():
        print('Completed derivative exists; no new charge.')
        return
    assert (DEST / 'quote.json').exists(), 'Run the free quote first'
    accepted_file = DEST / 'accepted.json'
    if accepted_file.exists():
        accepted = json.loads(accepted_file.read_text())
    else:
        accepted = rd._request('POST', '/inferences', body,
                               {'Idempotency-Key': record['idempotency_key']})
        save('accepted.json', accepted)
    task_id = accepted['task_id']
    print(f'RD task: {task_id}', flush=True)
    for _ in range(120):
        task = rd._request('GET', f'/inferences/tasks/{task_id}')
        if task['status'] in ('accepted', 'pending', 'running'):
            time.sleep(3)
            continue
        if task['status'] != 'succeeded':
            save('failure.json', task)
            raise RuntimeError(f"RD task failed; resume by task ID, do not resubmit: {task_id}")
        result = task['result']
        png = base64.b64decode(result['base64_images'][0])
        (DEST / 'master.png').write_bytes(png)
        width, height, pixels = load_png_rgba(str(DEST / 'master.png'))
        assert (width, height) == (body['width'], body['height'])
        assert all(a == 255 for r, g, b, a in pixels), 'Unexpected transparency'
        # Sample pixel centers only when a larger archival master is requested.
        # The runtime PNG remains320x192; never enlarge a small result locally.
        rgb = bytes(channel for y in range(192) for x in range(320)
                    for channel in pixels[min(height - 1, (2*y+1)*height//384)*width
                                          + min(width - 1, (2*x+1)*width//640)][:3])
        runtime_png = Image(rgb, 320, 192).to_png()
        (DEST / 'victory.png').write_bytes(runtime_png)
        (DEST / 'victory.rgb.hex').write_text(rgb.hex() + '\n')
        save('provenance.json', {
            'method': 'Retro Diffusion image-to-image enlargement (not nearest-neighbor)',
            'original': '../victory-a.png', 'input_sha256': digest,
            'task_id': task_id, 'balance_cost': result['balance_cost'],
            'model': result.get('model'), 'width': 320, 'height': 192,
            'master_width': width, 'master_height': height,
            'master_sha256': hashlib.sha256(png).hexdigest(),
            'runtime_conversion': 'pixel-center nearest sampling to320x192; no enlargement',
            'image_sha256': hashlib.sha256(runtime_png).hexdigest(),
            'rgb_sha256': hashlib.sha256(rgb).hexdigest(),
            'request_file': 'request.json',
            'api_docs': 'https://github.com/Retro-Diffusion/api-examples',
        })
        print(f"Saved {width}x{height}; actual cost ${result['balance_cost']}")
        return
    raise TimeoutError(f'Resume task {task_id} with --generate; do not submit a new request')


if __name__ == '__main__':
    main()
