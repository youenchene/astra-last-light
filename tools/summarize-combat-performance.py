#!/usr/bin/env python3.12
"""Derive reproducible tables from retained raw counters, never percent estimates."""
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path


def summarize(path):
    report = json.loads((path/'report.json').read_text())
    print('\n## '+path.name+'\n')
    print('Executable: `'+str(report.get('identity', {}).get('astra'))+'`\n')
    for profile, data in report['profiles'].items():
        perf = data.get('whole_performance', data.get('performance', {}))
        print('\n### '+profile+'\n')
        print('Whole metrics: `'+str({k:v for k,v in perf.items() if k != 'windows'})+'`; memory: `'+str(data.get('memory'))+'`\n')
        windows = {r['cp_window']: r for r in data.get('stage_windows', [])}
        result = []
        for case in range(48):
            for stage in range(10):
                rows = [r for r in data.get('stage_rows', []) if r['stage'] == stage and
                        windows[r['cp']]['first_case'] == windows[r['cp']]['case'] == case and
                        not windows[r['cp']].get('busy', 0)]
                samples = sum(r['calls'] for r in rows)
                if not samples:
                    continue
                result.append({'case':case, 'sector':case//12+1,
                               'phase':'BOSS' if case//6%2 else 'PLAY',
                               'density':'dense' if case//3%2 else 'sparse',
                               'band':['left','center','right'][case%3],
                               'stage':rows[0]['stage_name'], 'samples':samples,
                               'mean_lines':sum(r['lines'] for r in rows)/samples,
                               'max_lines':max(r['peak'] for r in rows)})
        (path/(profile+'-stages.json')).write_text(json.dumps(result, indent=2)+'\n')
        print('|Case|Phase|Density|X|restore|logic|audio|render inclusive|BOBs|sprites|copper|publish|wait|inject|')
        print('|---|'+'---:|'*13)
        for case in range(48):
            rows = [r for r in result if r['case'] == case]
            if rows:
                r = rows[0]
                print(f'|{case}|{r["phase"]}|{r["density"]}|{r["band"]}|'+
                      '|'.join(f'{r["mean_lines"]:.2f}/{r["max_lines"]} ({r["samples"]})' for r in rows)+'|')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.out:
        with args.out.open('w') as output, redirect_stdout(output):
            print('# Combat performance raw-counter tables\n')
            print('Each cell is mean/max elapsed PAL raster lines per stage call (sample count).\n')
            print('Inclusive stages overlap. Mixed/preparing windows remain in source JSON.\n')
            for path in args.paths:
                summarize(path)
    else:
        for path in args.paths:
            summarize(path)
