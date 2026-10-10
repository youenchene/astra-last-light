#!/usr/bin/env python3.12
"""Bounded diagnostic campaign trace; always restore diagnostic flags OFF."""
import argparse
from pathlib import Path
import subprocess
from perf_boundary import scenario_with_boundary

ROOT=Path(__file__).resolve().parents[1]
FLAGS=('CAMPAIGN_PROBE','PRESENTATION_TIMING','COMBAT_TIMING','COMBAT_STRESS')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--profile',choices=('a500','a500-aros'),default='a500')
    parser.add_argument('--ordinary-bob',action='store_true')
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    scenario=scenario_with_boundary(ROOT,
        'game/tests/bob_restore.agk' if args.ordinary_bob else 'game/tests/native/campaign.agk',
        args.out.resolve()/'scenarios')

    def run(*parts):
        with (args.out/'commands.log').open('a') as log:
            subprocess.run(['bash','tools/agk',*parts],cwd=ROOT,
                           stdout=log,stderr=subprocess.STDOUT,check=True)
    try:
        run('build','-D','ASTRA_CAMPAIGN_PROBE='+('OFF' if args.ordinary_bob else 'ON'),
            '-D','ASTRA_PRESENTATION_TIMING=ON',
            '-D','ASTRA_COMBAT_TIMING=OFF','-D','ASTRA_COMBAT_STRESS=OFF')
        run('run','--no-build','--fresh','--profile',args.profile,
            '-f',str(scenario),
            '-o',str(args.out/args.profile))
    finally:
        run('build',*[part for flag in FLAGS for part in ('-D','ASTRA_'+flag+'=OFF')])
        cache=(ROOT/'game/build/CMakeCache.txt').read_text()
        assert all('ASTRA_'+flag+':BOOL=OFF' in cache for flag in FLAGS)
    text=(args.out/args.profile/'serial.txt').read_text()
    assert 'AGK galaxy_diag_omitted=0' in text, 'trace missing or truncated'
    for line in text.splitlines():
        if line.startswith(('AGK galaxy_diag','AGK galaxy_memory')):print(line)


if __name__=='__main__':main()
