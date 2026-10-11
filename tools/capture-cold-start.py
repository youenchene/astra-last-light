#!/usr/bin/env python3.12
"""Diagnostic only: retain A500 loader pixels/state at the fixed 6000-frame limit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

KIT = Path(os.environ.get('AGK_KIT', str(Path.home() / 'Code/amiga/amiga-game-kit')))
sys.path.insert(0, str(KIT / 'harness'))
from agk import runner
from agk.image import Image

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('adf', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    adf, out = args.adf.resolve(), args.out.resolve()
    (out / 'identity.json').write_text(json.dumps({
        'adf': str(adf), 'sha256': hashlib.sha256(adf.read_bytes()).hexdigest(),
        'frames': 6000, 'profile': 'A500_OCS_1MB'}, indent=2) + '\n')
    lines = [f'regression setup A500_OCS_1MB {KIT}/roms/kick13.rom',
             *runner._display_lines(), f'regression run {adf}', 'wait 6000 frames',
             f'agk screenshot {out}/loader.raw', f'agk serial {out}/serial.txt',
             f'agk snapsave {out}/loader.vasnap']
    code, log, elapsed = runner._run_vamiga(lines, str(out))
    print('\n'.join(log))
    if code:
        raise SystemExit(code)
    Image.from_raw_file(out / 'loader.raw').canonical12().save_png(out / 'loader.png')
