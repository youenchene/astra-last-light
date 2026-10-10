#!/usr/bin/env python3
"""Retain actual 68000 decoder disassembly and undefined helper symbols."""
import argparse
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    base = ['docker', 'run', '--rm', '-v', f'{ROOT}/game:/project:ro',
            'amigadev/crosstools:m68k-amigaos']
    obj = '/project/build/CMakeFiles/astra.dir/src/presentation_rows.c.obj'
    def tool(name, *flags):
        return subprocess.check_output(base + ['m68k-amigaos-'+name, *flags, obj], text=True)
    symbols = tool('nm', '-n')
    start = min(int(address,16) for address, kind, name in
                re.findall(r'^(\w+) ([Tt]) (\S+)$', symbols, re.M)
                if not name.startswith('_s_'))
    undefined = tool('nm', '-u')
    disassembly = tool('objdump', '-dr', f'--start-address={start}')
    args.out.write_text(symbols + '\nUndefined:\n' + undefined + '\n' + disassembly)
    assert not re.search(r'___(?:mul|div|mod)', undefined), undefined
    print('Undefined helpers: ' + undefined.strip())
    print(f'Actual decoder disassembly retained at {args.out}')
