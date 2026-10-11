#!/usr/bin/env python3.12
"""Injected combat matrix, retained raw timings and guaranteed production rebuild."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
from combat_evidence import MATRIX_CAPTURES, PROFILES, capture_hashes, matrix_event_identity, require_names

ROOT = Path(__file__).resolve().parents[1]
STAGES = ['restore_world', 'logic', 'audio', 'render_inclusive', 'bobs_inclusive',
          'sprite_preparation', 'copper_build', 'publication', 'explicit_wait', 'injection']
FLAGS = ['ASTRA_COMBAT_STRESS', 'ASTRA_COMBAT_TIMING',
         'ASTRA_CAMPAIGN_PROBE', 'ASTRA_PRESENTATION_TIMING']
LOG = None


def command(*args):
    print('agk '+' '.join(args), flush=True)
    with LOG.open('a') as output:
        subprocess.run(['bash', 'tools/agk', *args], cwd=ROOT, check=True,
                       stdout=output, stderr=subprocess.STDOUT)


def identity():
    return {name: {'bytes': (ROOT/'game/build'/name).stat().st_size,
                   'sha256': hashlib.sha256((ROOT/'game/build'/name).read_bytes()).hexdigest()}
            for name in ('astra', 'astra.adf')}


def records(text, tag):
    return [{k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', line)}
            for line in text.splitlines() if line.startswith('AGK '+tag+'=')]


def inspect(folder, timing):
    captures = capture_hashes(folder, MATRIX_CAPTURES)
    text = (folder/'serial.txt').read_text()
    if 'AGK stress_complete' not in text or re.search(r'stress_fail|allocation failure|bullet_hidden=[1-9]', text):
        raise ValueError('matrix completion/visibility failure: '+str(folder))
    cases = records(text, 'stress_case')
    matrix_event_identity(cases)
    spec = importlib.util.spec_from_file_location('campaign', ROOT/'tools/check-campaign-native.py')
    campaign = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(campaign)
    rows = records(text, 'cp')
    windows = records(text, 'cp_window')
    busy = {r['cp_busy']: r['busy'] for r in records(text, 'cp_busy')}
    for window in windows:
        window['busy'] = busy[window['cp_window']]
    if timing and (not rows or len(rows) != len(windows)*len(STAGES)):
        raise ValueError('incomplete stage telemetry: '+str(folder))
    for r in rows:
        r['mean_lines'] = r['lines']/r['calls'] if r['calls'] else None
        r['stage_name'] = STAGES[r['stage']]
    return {'functional_pass': True, 'cases': cases, 'stage_rows': rows,
            'stage_windows': windows, 'whole_performance': campaign.performance(text),
            'memory': campaign.records(text, 'chip_free='),
            'captures': captures}


def main():
    global LOG
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--timing', choices=['ON', 'OFF'], default='ON')
    parser.add_argument('--check-only', action='store_true', help='inspect retained evidence without builds or writes')
    args = parser.parse_args()
    if args.check_only:
        saved = json.loads((args.out/'report.json').read_text())
        require_names(saved['profiles'], PROFILES, 'matrix profiles')
        for profile in PROFILES:
            checked = inspect(args.out/profile, saved['timing'] == 'ON')
            for field in ('captures', 'cases'):
                if checked[field] != saved['profiles'][profile][field]:
                    raise ValueError(f'{profile}: saved {field} differ from actual evidence')
            print(f'PASS {profile}: 48 captures, 96 acknowledged events, retained telemetry')
        return 0
    args.out.mkdir(parents=True, exist_ok=False)
    LOG = args.out/'commands.log'
    report = {'scope': 'injected matrix; not ordinary play', 'timing': args.timing, 'profiles': {}}
    scenario = args.out/'matrix.agk'
    lines = ['wait-serial "AGK language_ready" 600', 'press right 1', 'wait 24', 'press fire 1',
             'wait-serial "AGK title_ready" 600', 'press fire 1',
             'wait-serial "AGK combat_ready" 1000']
    for i in range(48):
        lines += [f'wait-serial "AGK stress_case={i} tick=100 " 1000', f'screenshot case{i:02}',
                  'key 0x59', f'wait-serial "AGK stress_case={i} tick=200 " 1000', 'key 0x59']
    lines += ['wait-serial "AGK stress_complete" 1000', 'wait 60',
              'expect-no-serial "ERR|STACK SMASHED|allocation failure|stress_fail|bullet_hidden=[1-9]"']
    scenario.write_text('\n'.join(lines)+'\n')
    try:
        command('build', '-D', 'ASTRA_COMBAT_STRESS=ON', '-D', 'ASTRA_COMBAT_TIMING='+args.timing,
                '-D', 'ASTRA_CAMPAIGN_PROBE=OFF', '-D', 'ASTRA_PRESENTATION_TIMING=OFF')
        report['identity'] = identity()
        for profile in ('a500', 'a500-aros'):
            folder = args.out/profile
            command('run', '--no-build', '--fresh', '--profile', profile, '-f', str(scenario), '-o', str(folder))
            report['profiles'][profile] = inspect(folder, args.timing == 'ON')
    except (subprocess.CalledProcessError, ValueError, OSError) as error:
        report['error'] = str(error)
    finally:
        try:
            command('build', *[part for flag in FLAGS for part in ('-D', flag+'=OFF')])
            cache = (ROOT/'game/build/CMakeCache.txt').read_text()
            report['production_restored'] = all(flag+':BOOL=OFF' in cache for flag in FLAGS)
            report['production_identity'] = identity()
        except (subprocess.CalledProcessError, OSError) as error:
            report['restore_error'] = str(error)
        (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'profiles'}, indent=2))
    return 0 if len(report['profiles']) == 2 and report.get('production_restored') and not report.get('error') else 1


if __name__ == '__main__':
    raise SystemExit(main())
