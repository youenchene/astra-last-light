#!/usr/bin/env python3.12
"""NON-SHIPPING raster cost of each decoder; always restore production OFF."""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    report = {}
    def command(*parts):
        subprocess.run(['bash', 'tools/agk', *parts], cwd=ROOT, check=True)
    try:
        command('build', '-D', 'ASTRA_PRESENTATION_TIMING=ON')
        for profile in ('a500', 'a500-aros'):
            folder = args.out / profile
            command('run', '--no-build', '--profile', profile, '-f',
                    'game/tests/native/title_latency.agk', '-o', str(folder))
            rows = [{k: int(v) for k,v in re.findall(r'(\w+)=(-?\d+)', line)}
                    for line in (folder/'serial.txt').read_text().splitlines()
                    if line.startswith('AGK row_cost=')]
            assert [r['row_cost'] for r in rows] == [1, 0, 2, 1, 0, 2], rows
            report[profile] = rows
    finally:
        try:
            command('build', '-D', 'ASTRA_PRESENTATION_TIMING=OFF')
            report['production_restored'] = 'ASTRA_PRESENTATION_TIMING:BOOL=OFF' in (
                ROOT/'game/build/CMakeCache.txt').read_text()
        except (subprocess.CalledProcessError, OSError) as error:
            report['production_restored'] = False
            report['restore_error'] = str(error)
        (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    if not report['production_restored']:
        raise SystemExit('production restoration failed: see report.json')
    print(json.dumps(report, indent=2))
