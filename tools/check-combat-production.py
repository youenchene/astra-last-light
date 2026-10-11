#!/usr/bin/env python3.12
"""Profiler/injection-OFF ordinary input, source-pixel and lifecycle evidence."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from perf_boundary import scenario_with_boundary, complete_performance

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT/'tools'/filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--profile', required=True, choices=['a500', 'a500-aros'])
    args = parser.parse_args()
    folder = args.out/args.profile
    folder.mkdir(parents=True, exist_ok=False)
    campaign = load('campaign', 'check-campaign-native.py')
    states = load('states', 'verify-gameover-title.py')
    report = {'profile':args.profile, 'scope':'ordinary input; all diagnostics OFF', 'cases':{}}

    def command(parts):
        print(' '.join(str(p) for p in parts), flush=True)
        with (folder/'commands.log').open('a') as output:
            subprocess.run([str(p) for p in parts], cwd=ROOT, check=True,
                           stdout=output, stderr=subprocess.STDOUT)

    try:
        cache = (ROOT/'game/build/CMakeCache.txt').read_text()
        for flag in ('COMBAT_STRESS', 'COMBAT_TIMING', 'CAMPAIGN_PROBE', 'PRESENTATION_TIMING'):
            if f'ASTRA_{flag}:BOOL=OFF' not in cache:
                raise ValueError('production diagnostic flag not OFF: '+flag)
        report['identity'] = {}
        for name in ('astra', 'astra.adf'):
            source = ROOT/'game/build'/name
            shutil.copyfile(source, folder/name)
            report['identity'][name] = {'bytes':source.stat().st_size,
                                       'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
        for case in ('pause_continuity', 'clean_transitions', 'gameover_title', 'large_manga', 'bob_restore'):
            output = folder/case
            scenario = f'game/tests/{"" if case == "bob_restore" else "native/"}{case}.agk'
            scenario = scenario_with_boundary(ROOT, scenario, folder/'scenarios')
            command(['bash','tools/agk','run','--no-build','--fresh','--profile',args.profile,
                     '-f',scenario,'-o',output])
            if case == 'bob_restore':
                command([sys.executable,'tools/verify-bob-restoration.py','--drop',output/'bonus_drop.screen.png',
                         '--restored',output/'bob_restored.screen.png'])
            elif case == 'large_manga':
                command([sys.executable,'tools/verify-precomputed-cards.py','--scene','0',output])
            else:
                validator = {'pause_continuity':'verify-pause-continuity.py',
                             'clean_transitions':'verify-clean-transitions.py',
                             'gameover_title':'verify-gameover-title.py'}[case]
                command([sys.executable,'tools/'+validator,
                         output/'serial.txt' if case == 'gameover_title' else output])
            text = (output/'serial.txt').read_text()
            report['cases'][case] = {'functional_pass':True, 'performance':complete_performance(text, campaign.performance(text)),
                'memory':campaign.records(text,'chip_free='),
                'captures':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob('*.screen.png')}}
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        report['error'] = str(error)
    finally:
        (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    for name, case in report['cases'].items():
        print(name, {k:v for k,v in case['performance'].items() if k != 'windows'})
    if report.get('error'):
        print('STOP: '+report['error'])
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
