#!/usr/bin/env python3.12
"""Compare identical matrix workloads, raw elapsed counters and complete pixels."""
import argparse
import importlib.util
import json
from pathlib import Path
from combat_evidence import PROFILES, require_names, validate_matrix

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('baseline', type=Path)
parser.add_argument('candidate', type=Path)
args = parser.parse_args()
reports = [json.loads((p/'report.json').read_text()) for p in (args.baseline, args.candidate)]
for report in reports:
    require_names(report['profiles'], PROFILES, 'matrix profiles')
result = {}
for profile in ('a500', 'a500-aros'):
    a, b = [r['profiles'][profile] for r in reports]
    matched_identity = [validate_matrix(root/profile, data)
                        for root,data in zip((args.baseline,args.candidate),(a,b))]
    if matched_identity[0] != matched_identity[1]:
        raise SystemExit('STOP: submitted case/tick/bitmap/copper identities differ')
    changed = [n for n, digest in a['captures'].items() if b['captures'].get(n) != digest]
    stats = []
    for data in (a, b):
        windows = {r['cp_window']:r for r in data['stage_windows']}
        table = {}
        for stage in range(10):
            for dense in (0, 1):
                rows = [r for r in data['stage_rows'] if r['stage'] == stage and
                        windows[r['cp']]['case'] < 48 and
                        windows[r['cp']]['first_case'] == windows[r['cp']]['case'] and
                        not windows[r['cp']]['busy'] and windows[r['cp']]['case']//3%2 == dense]
                count = sum(r['calls'] for r in rows)
                if not count:
                    continue
                table[f'{stage}:{dense}'] = {'mean':sum(r['lines'] for r in rows)/count,
                                            'max':max(r['peak'] for r in rows), 'samples':count}
        stats.append(table)
    result[profile] = {'changed_complete_captures':changed, 'stages':stats,
                       'whole':[ {k:v for k,v in d['whole_performance'].items() if k != 'windows'} for d in (a,b)]}
    print(profile, 'changed captures', changed, 'whole', result[profile]['whole'])
    for key in stats[0]:
        av, bv = stats[0][key]['mean'], stats[1][key]['mean']
        print(key, f'{av:.3f} -> {bv:.3f} lines ({(bv/av-1)*100:+.2f}%)')
(args.candidate/'comparison.json').write_text(json.dumps(result, indent=2)+'\n')
if any(r['changed_complete_captures'] for r in result.values()):
    raise SystemExit('STOP: complete pixel identities differ; inspect before proceeding')
