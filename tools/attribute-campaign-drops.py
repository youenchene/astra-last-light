#!/usr/bin/env python3.12
"""Fail-closed OFF campaign comparison; retain phase context around drop windows.

Window context is not exact attribution of individual missed frames. A mixed
window remains mixed even if its final state is ready PLAY.
"""
import argparse
import json
from pathlib import Path
import re


def fields(line):
    return {k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}


def windows(path):
    state={}; contexts=[]; events=[]; result=[]; elapsed=0
    for number,line in enumerate(path.read_text().splitlines(),1):
        if line.startswith('AGK frame='):
            state=fields(line)
        elif line.startswith('AGK enemy_acc='):
            state.update(fields(line)); contexts.append(dict(state))
        elif line.startswith(('AGK cut_','AGK publication_ready=','AGK qa_','AGK combat_ready','AGK scene_ready')):
            events.append(dict(line=number,text=line))
        if not line.startswith('AGK perf '):continue
        perf=fields(line); elapsed+=perf['frames']
        ready={ (s.get('level'),s.get('phase'),s.get('preparing')) for s in contexts }
        result.append(dict(line=number,end_frame=elapsed,**perf,contexts=contexts,
                           classes=sorted(ready),events=events))
        contexts=[dict(state)] if state else []; events=[]
    assert result, f'missing perf: {path}'
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path)
    parser.add_argument('candidate',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(); report={}; passes=True
    for profile in ('a500','a500-aros'):
        pair={}
        for label,base in [('baseline',args.baseline),('candidate',args.candidate)]:
            ws=windows(base/profile/'serial.txt')
            pair[label]=dict(drops=sum(w['dropped'] for w in ws),peak=max(w['maxload'] for w in ws),
                             dropped_windows=[w for w in ws if w['dropped']])
            print(profile,label,pair[label]['drops'],pair[label]['peak'])
            for w in pair[label]['dropped_windows']:
                first=w['contexts'][0] if w['contexts'] else {}
                last=w['contexts'][-1] if w['contexts'] else {}
                print(' ',w['line'],w['dropped'],w['maxload'],w['classes'],
                      'stage',first.get('stage'),last.get('stage'),
                      'pf',first.get('pf'),last.get('pf'))
        passed=pair['candidate']['drops']<=pair['baseline']['drops'] and pair['candidate']['peak']<=pair['baseline']['peak']
        pair['no_regression']=passed;passes &= passed;report[profile]=pair
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print('PASS no campaign regression' if passes else 'FAIL campaign regression')
    return 0 if passes else 1


if __name__=='__main__':raise SystemExit(main())
