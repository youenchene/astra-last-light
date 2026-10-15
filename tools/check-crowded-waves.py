#!/usr/bin/env python3.12
"""Replay ordinary no-fire formations in all sectors; enforce the PAL50 gate."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess

from perf_boundary import BOUNDARY_SUFFIX, complete_performance

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--profiles', nargs='+', default=['a500', 'a500-aros'])
    parser.add_argument('--sectors', nargs='+', type=int, default=[1, 2, 3, 4])
    parser.add_argument('--fire', action='store_true', help='fire normal volleys from the bottom lane')
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('campaign', ROOT/'tools/check-campaign-native.py')
    campaign = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(campaign)
    report = {}
    for sector in args.sectors:
        lines = ['wait-serial "AGK language_ready" 600', 'press right 1', 'wait 24',
                 'press fire 1', 'wait-serial "AGK title_ready" 600']
        for _ in range(sector-1):
            lines += ['press right 1', 'wait-serial "AGK title_ready" 600']
        lines += ['press fire 1', 'wait-serial "AGK combat_ready" 1000', 'press left 24']
        if args.fire:
            lines += ['press down 44']
        def advance(ticks):
            if args.fire:
                while ticks >= 8:
                    lines.extend(['press fire 1', 'wait 7'])
                    ticks -= 8
            if ticks:
                lines.append(f'wait {ticks}')
        for ticks, capture in ((12 if args.fire else 56, 'crowded_right'),
                               (100, 'crowded_middle'), (160, 'crowded_left'),
                               (160, 'crowded_tail'), (200, 'next_wave')):
            advance(ticks)
            lines.append('screenshot '+capture)
        lines += [
                  f'expect-serial "AGK music sector{sector}"',
                  'expect-serial "wave=1 .*enemies=6"',
                  'expect-no-serial "bullet_hidden=[1-9]|ERR|STACK SMASHED|allocation failure"']
        if args.fire:
            lines += ['expect-serial "AGK sfx shot"', 'expect-serial "shot_bobs=[3-9]"']
        else:
            lines += ['expect-no-serial "AGK sfx shot|AGK bonus_drop"',
                      'expect-serial "score=0 .*wave=1 .*shot_bobs=0 enemies=6"']
        scenario = args.out/f'sector{sector}.agk'
        scenario.write_text('\n'.join(lines)+'\n'+BOUNDARY_SUFFIX)
        for profile in args.profiles:
            folder = args.out/f'{profile}-sector{sector}'
            result = subprocess.run(['bash', str(ROOT/'tools/agk'), 'run', '--no-build', '--fresh',
                                     '--profile', profile, '-f', str(scenario), '-o', str(folder)],
                                    cwd=ROOT, capture_output=True, text=True)
            print(result.stdout, end='', flush=True)
            (args.out/f'{profile}-sector{sector}.runner.txt').write_text(result.stdout+result.stderr)
            if not (folder/'serial.txt').exists():
                print(result.stderr, end='', flush=True)
                raise RuntimeError(f'replay failed before serial capture: {folder}')
            text = (folder/'serial.txt').read_text()
            perf = complete_performance(text, campaign.performance(text))
            row = {'functional_pass':result.returncode == 0, 'performance':perf,
                   'memory':campaign.records(text, 'chip_free=')}
            report[f'{profile}-sector{sector}'] = row
            print(f'{profile} sector{sector}: functional={row["functional_pass"]} '
                  f'drops={perf["dropped"]} peak={perf["maxload"]}%', flush=True)
            (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    return 0 if all(r['functional_pass'] and r['performance']['pass'] for r in report.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
