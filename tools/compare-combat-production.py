#!/usr/bin/env python3.12
"""Compare ordinary OFF/campaign evidence without masking pixels or state fields."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from combat_evidence import PROFILES, SCENARIOS, capture_hashes, require_names, scenario_captures, validate_production_report

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('states', ROOT/'tools/verify-gameover-title.py')
states = importlib.util.module_from_spec(spec)
spec.loader.exec_module(states)


def metrics(perf):
    windows = perf['windows']
    return {'dropped':perf['dropped'], 'peak_percent':perf['maxload'],
            'emitted_frames':sum(w['frames'] for w in windows),
            'mean_load_percent':sum(w['load']*w['frames'] for w in windows)/sum(w['frames'] for w in windows)}


def compare(a, b, case):
    expected = scenario_captures(case)
    ah, bh = [capture_hashes(folder, expected) for folder in (a,b)]
    changed = [name for name in sorted(expected) if ah[name] != bh[name]]
    # Both ordinary and injected campaign evidence use complete AGK frame=
    # records (including wrapped continuation lines), not qa/perf/event markers.
    aa, bb = [[r for _,r in states.frame_states((p/'serial.txt').read_text().splitlines())] for p in (a,b)]
    if not aa or not bb:
        raise ValueError(f'{case}: nonempty gameplay-state evidence required on both sides')
    return {'captures':len(expected), 'changed_captures':changed,
            'baseline_states':len(aa), 'candidate_states':len(bb), 'states_identical':aa == bb}


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline', required=True, type=Path)
parser.add_argument('--candidate', required=True, type=Path)
parser.add_argument('--baseline-campaign', required=True, type=Path)
parser.add_argument('--candidate-campaign', required=True, type=Path)
args = parser.parse_args()
campaign_reports = [json.loads((p/'report.json').read_text()) for p in (args.baseline_campaign,args.candidate_campaign)]
for data in campaign_reports:
    require_names(data['profiles'], PROFILES, 'campaign profiles')
report = {}
for profile in ('a500','a500-aros'):
    report[profile] = {}
    ar, br = [json.loads((p/profile/'report.json').read_text()) for p in (args.baseline,args.candidate)]
    for root,data in zip((args.baseline,args.candidate),(ar,br)):
        validate_production_report(root/profile, data)
    for case in SCENARIOS:
        row = compare(args.baseline/profile/case,args.candidate/profile/case,case)
        row['performance'] = [metrics(r['cases'][case]['performance']) for r in (ar,br)]
        report[profile][case] = row
        print(profile,case,row)
    ar,br = [data['profiles'][profile] for data in campaign_reports]
    row = compare(args.baseline_campaign/profile,args.candidate_campaign/profile,'campaign')
    row['performance'] = [metrics(r['performance']) for r in (ar,br)]
    report[profile]['campaign'] = row
    print(profile,'campaign',row)
(args.candidate/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
if any(r['changed_captures'] or not r['states_identical'] for p in report.values() for r in p.values()):
    raise SystemExit('Comparison differences: see comparison.json')
