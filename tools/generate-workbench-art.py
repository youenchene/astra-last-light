#!/usr/bin/env python3.12
"""Two bounded, durable RD jobs. Default is a free quote; --submit spends <=$0.36."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'assets/workbench'
KIT = Path(os.environ.get('AGK_KIT', Path.home() / 'Code/amiga/amiga-game-kit'))
sys.path.insert(0, str(KIT / 'harness'))
from agk import rd

JOBS = {
    'drawer': (86101, 'An original Amiga Workbench drawer icon shaped like a compact alien orbital hangar, open dark navy steel cargo bay with a folder-like raised back tab, silver armored ribs, cyan luminous entrance, tiny orange warning lamps, strange biomechanical science fiction architecture, broad horizontal silhouette, three quarter view, isolated single object'),
    'interceptor': (86102, 'An original heroic space interceptor, strict side view flying RIGHT, long pointed silver white fuselage, luminous cyan cockpit, broad swept angular wings, dark navy underside, short vivid orange exhaust only at left, unusual elegant science fiction spaceship, broad horizontal silhouette, isolated single object'),
}
SUFFIX = ', 1990s Amiga pixel art desktop icon, crisp chunky pixel clusters, strong dark outline, entire object visible with generous transparent margin, no lettering, no logo, no frame, no cast shadow, on a plain white background'


def atomic(path, data):
    temporary = path.with_suffix(path.suffix + '.pending')
    with temporary.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def save(manifest):
    atomic(ART / 'generation.json', (json.dumps(manifest, indent=2) + '\n').encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--submit', action='store_true')
    args = parser.parse_args()
    ART.mkdir(parents=True, exist_ok=True)
    path = ART / 'generation.json'
    manifest = json.loads(path.read_text()) if path.exists() else {}
    for name in JOBS:
        if (ART / (name + '-master.png')).exists() and name not in manifest:
            raise SystemExit('Existing master lacks provenance; recover metadata instead of regenerating')
    bodies = {name: dict(prompt=prompt + SUFFIX, prompt_style='rd_pro__default',
                        width=64, height=64, num_images=1, seed=seed, remove_bg=True)
              for name, (seed, prompt) in JOBS.items()}
    quotes = {}
    for name, body in bodies.items():
        if manifest.get(name, {}).get('status') == 'complete':
            continue
        quote = rd._request('POST', '/inferences', dict(body, check_cost=True))
        quotes[name] = Decimal(str(quote['balance_cost']))
        print(f'{name}: fresh free quote ${quotes[name]}', flush=True)
    spent = sum(Decimal(str(e.get('cost_usd', e.get('quote_usd', 0))))
                for e in manifest.values())
    fresh = sum(price for name, price in quotes.items() if name not in manifest)
    if spent + fresh > Decimal('0.36') or any(p < 0 for p in quotes.values()):
        raise SystemExit('Bounded $0.36 budget exceeded; no paid request submitted')
    if not args.submit:
        return
    for name, body in bodies.items():
        entry = manifest.get(name)
        if entry and entry['status'] == 'complete':
            assert hashlib.sha256((ART / (name + '-master.png')).read_bytes()).hexdigest() == entry['sha256']
            continue
        if entry is None:
            entry = dict(provider='Retro Diffusion', request=body,
                         request_id=str(uuid.uuid5(uuid.NAMESPACE_URL, 'astra-workbench-v1/' + json.dumps(body, sort_keys=True))),
                         quote_usd=float(quotes[name]), status='pending_submission',
                         reference='Verbal description of rd_hero16 only; no image conditioning')
            manifest[name] = entry
            save(manifest)  # durable intent BEFORE charge-capable POST
            accepted = rd._request('POST', '/inferences', body, {'Idempotency-Key': entry['request_id']})
            entry.update(task_id=accepted['task_id'], status='pending')
            save(manifest)  # persist task BEFORE polling
        if 'task_id' not in entry:
            raise SystemExit('Uncertain submission: recover existing task ID; never automatically resubmit')
        image, cost, _ = rd.wait_task(entry['task_id'])
        if not image or not image.startswith(b'\x89PNG\r\n\x1a\n'):
            raise SystemExit('Task returned no PNG; retain task for recovery')
        atomic(ART / (name + '-master.png'), image)
        entry.update(status='complete', cost_usd=cost, sha256=hashlib.sha256(image).hexdigest())
        save(manifest)
        print(f'{name}: saved master, cost ${cost}', flush=True)


if __name__ == '__main__':
    try:
        main()
    except rd.GenError:
        raise SystemExit('RD request failed; durable metadata retained. No automatic resubmission.')
