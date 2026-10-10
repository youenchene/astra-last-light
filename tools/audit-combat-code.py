#!/usr/bin/env python3.12
"""Retain actual compiled hot-path instructions and helper references."""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', required=True, type=Path)
args = parser.parse_args()
base = ['docker', 'run', '--rm', '-v', f'{ROOT}/game:/project:ro', 'amigadev/crosstools:m68k-amigaos']
with args.out.open('w') as output:
    for module in ('logic', 'render_bullets', 'render_bobs', 'render_world'):
        obj = f'/project/build/CMakeFiles/astra.dir/src/{module}.c.obj'
        output.write('\nMODULE '+module+'\n')
        for tool, flags in [('nm', ['-S', '-n']), ('objdump', ['-dr'])]:
            text = subprocess.check_output(base+['m68k-amigaos-'+tool, *flags, obj], text=True)
            output.write(text)
        print('Audited '+module)
