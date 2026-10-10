#!/usr/bin/env python3.12
"""Record final production identities and immutable evidence references."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'game/build'
flags = ('COMBAT_STRESS','COMBAT_TIMING','CAMPAIGN_PROBE','PRESENTATION_TIMING')
cache = (BUILD/'CMakeCache.txt').read_text()
assert all(f'ASTRA_{flag}:BOOL=OFF' in cache for flag in flags)
report = {'flags':{flag:'OFF' for flag in flags}, 'artifacts':{}, 'production_matches_tested_executable':True}
for name in ('astra','astra.adf'):
    path = BUILD/name
    report['artifacts'][name] = {'bytes':path.stat().st_size,
                                 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
for profile in ('a500','a500-aros'):
    tested = json.loads((BUILD/'perf-prod-final'/profile/'report.json').read_text())
    assert tested['identity']['astra'] == report['artifacts']['astra']
report['evidence'] = {}
for path in sorted(BUILD.glob('perf-fenced-*/report.json')):
    data = json.loads(path.read_text())
    report['evidence'][str(path.relative_to(ROOT))] = {
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'timing':data['timing'],
        'profiles':{p:{k:v for k,v in d['whole_performance'].items() if k != 'windows'}
                    for p,d in data['profiles'].items()}}
for path in [BUILD/'perf-prod-final/comparison.json', BUILD/'perf-campaign-final/report.json']:
    report['evidence'][str(path.relative_to(ROOT))] = {'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
report['source_hashes'] = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
    for p in [ROOT/'game/src'/n for n in ('main.c','render.c','render_bobs.c','render_bullets.c',
                                        'render_world.c','combat_perf.c','combat_perf.h')]}
(BUILD/'perf-prod-final/final-evidence.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
