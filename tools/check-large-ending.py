#!/usr/bin/env python3.12
"""Focused native story/WIN acceptance; restore probe OFF even after a failure."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


campaign = load('campaign', 'check-campaign-native.py')
cards = load('cards', 'verify-precomputed-cards.py')


def inspect(folder):
    text = (folder / 'serial.txt').read_text()
    campaign.check_lifecycle(text)
    checked = 0
    for scene in range(13):
        early, late = [folder / f'scene{scene:02}{suffix}.screen.png' for suffix in ('', '_late')]
        checked += cards.check_scene(early, scene) + cards.check_scene(late, scene)
        campaign.check_scene_pair(cards.Image.load_png(early), cards.Image.load_png(late), scene)
    for name in ('ending_first', 'ending_next_buffer', 'ending_held', 'ending_released'):
        checked += cards.check_scene(folder / f'{name}.screen.png', 12)
    checked += cards.check_scene(folder / 'restarted_opening.screen.png', 0)
    transitions = campaign.records(text, 'qa_transition=')
    restarts = [r for r in transitions if r['qa_transition'] == 5]
    complete = campaign.records(text, 'qa_complete=')[0]
    campaign.require(len(restarts) == 1 and restarts[0]['phase'] == 6 and
                     restarts[0]['level'] == 1 and restarts[0]['frame'] > complete['frame'] + 100,
                     'WIN restarted early or did not restart on fresh fire')
    campaign.require('AGK escape_title' in text, 'missing ESC cleanup')
    # The returned title must match the exact same title from production startup.
    title = cards.Image.load_png(folder / 'returned_title.screen.png')
    campaign.require(all(title.pixel(x, y) == (0, 0, 17)
                         for y in range(256) for x in range(320)
                         if x < 24 or x >= 296), 'stale ending/HUD/decor at title exterior')
    memory = campaign.records(text, 'chip_free=')
    campaign.require(memory, 'missing startup memory')
    return {'functional_pass': True, 'native_pixels': checked, 'memory': memory,
            'performance_observation_only': campaign.performance(text)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    report = {'profiles': {}, 'scope': 'injected quotas/collisions, real phase/input/publication'}

    def command(*parts):
        subprocess.run(['bash', 'tools/agk', *parts], cwd=ROOT, check=True)

    try:
        command('build', '-D', 'ASTRA_CAMPAIGN_PROBE=ON')
        report['probe_identity'] = campaign.preserve_probe(args.out)
        for profile in campaign.PROFILES:
            folder = args.out / profile
            command('run', '--no-build', '--fresh', '-p', profile,
                    '-f', 'game/tests/native/large_ending.agk', '-o', str(folder))
            report['profiles'][profile] = inspect(folder)
            print(f'PASS {profile}: all thirteen scenes, held ending/release/restart/ESC', flush=True)
    except (subprocess.CalledProcessError, AssertionError, ValueError, OSError, IndexError, StopIteration) as error:
        report['error'] = str(error)
        print(f'STOP: {error}', file=sys.stderr)
    finally:
        try:
            command('build', '-D', 'ASTRA_CAMPAIGN_PROBE=OFF')
            cache = (ROOT / 'game/build/CMakeCache.txt').read_text()
            campaign.require('ASTRA_CAMPAIGN_PROBE:BOOL=OFF' in cache and
                             'ASTRA_PRESENTATION_TIMING:BOOL=OFF' in cache, 'diagnostic flags not OFF')
            report['production_restored'] = True
        except (subprocess.CalledProcessError, OSError, ValueError) as error:
            report['restore_error'] = str(error)
        (args.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if len(report['profiles']) == 2 and not report.get('error') and report.get('production_restored') else 1


if __name__ == '__main__':
    sys.exit(main())
