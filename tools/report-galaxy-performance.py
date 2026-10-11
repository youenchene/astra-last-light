#!/usr/bin/env python3.12
"""Report retained it7/it9 raw timing, preparation and resident-memory evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'game/build'


def records(text, tag):
    return [dict((k,int(v)) for k,v in re.findall(r'(\w+)=(-?\d+)',line))
            for line in text.splitlines() if line.startswith('AGK '+tag+'=')]


def stable_play(text):
    # Both endpoints and every intervening emitted state must be ready PLAY.
    valid=False; all_play=False; frames=weighted=peak=drops=0
    for line in text.splitlines():
        if line.startswith('AGK frame='):
            valid=' phase=1 ' in line
            if not valid: all_play=False
        if ' preparing=' in line:
            valid=valid and 'preparing=0' in line and 'paused=0' in line
            if not valid: all_play=False
        if line.startswith('AGK perf '):
            r=dict((k,int(v)) for k,v in re.findall(r'(\w+)=(\d+)',line))
            if all_play and valid:
                frames+=r['frames']; weighted+=r['frames']*r['load']
                peak=max(peak,r['maxload']); drops+=r['dropped']
            all_play=valid
    return dict(frames=frames,mean_load=weighted/frames if frames else None,peak=peak,drops=drops)


def measure(prod, campaign, matrix, galaxy=None):
    result={}
    raw=json.loads((matrix/'report.json').read_text())
    for profile in ('a500','a500-aros'):
        data=raw['profiles'][profile]
        windows={r['cp_window']:r for r in data['stage_windows']}
        phases={}
        for phase,cases in [('PLAY',range(3,6)),('BOSS',range(9,12))]:
            stages=[]
            for stage in range(10):
                rows=[r for r in data['stage_rows'] if r['stage']==stage
                      and windows[r['cp']]['case'] in cases
                      and windows[r['cp']]['first_case']==windows[r['cp']]['case']
                      and not windows[r['cp']]['busy']]
                factor=2 if stage==2 else 3 if stage==8 else 1
                mean=sum(r['lines'] for r in rows)*factor/sum(r['calls'] for r in rows)
                peak=max(r['peak'] for r in rows)
                stages.append(dict(stage=rows[0]['stage_name'],mean=mean,max=peak,
                                   mean_percent=mean/313*100,max_percent=peak/313*100))
            phases[phase]=stages
        ordinary=json.loads((prod/profile/'report.json').read_text())
        text=(prod/profile/'large_manga/serial.txt').read_text()
        cuts=records(text,'cut_submit')
        works=records(text,'cut_work')
        latency=[dict(cut,work=work['cut_work']) for cut,work in zip(cuts,works)]
        p={name:{k:v for k,v in case['performance'].items() if k!='windows'}
           for name,case in ordinary['cases'].items()}
        p['memory']=ordinary['cases']['large_manga']['memory']
        p['stages_s1_dense']=phases
        p['latency']=latency
        p['steady_play_bob']=stable_play((prod/profile/'bob_restore/serial.txt').read_text())
        p['steady_play_campaign']=stable_play((campaign/profile/'serial.txt').read_text())
        p['matrix_whole']={k:v for k,v in data['whole_performance'].items() if k!='windows'}
        if galaxy:
            p['sector_preparation']={}
            for sector in range(1,5):
                t=(galaxy/profile/f'sector{sector}/serial.txt').read_text()
                p['sector_preparation'][sector]=[dict(c,work=w['cut_work']) for c,w in
                    zip(records(t,'cut_submit'),records(t,'cut_work')) if c['phase']==6]
        result[profile]=p
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',default='it9j')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    report={}
    for tag in ('it7',args.candidate):
        base=BUILD/f'perf-loop5-{tag}'
        report[tag]=measure(Path(str(base)+'-prod'),Path(str(base)+'-campaign'),Path(str(base)+'-on'),
                            Path(str(base)+'-galaxy') if tag!='it7' else None)
    report['production']={n:dict(bytes=(BUILD/n).stat().st_size,sha256=hashlib.sha256((BUILD/n).read_bytes()).hexdigest()) for n in ('astra','astra.adf')}
    data=(ROOT/'game/src/galaxy_data.c').read_text()
    report['asset_bytes']={name:len(re.findall(r'\d+',body))*(2 if kind=='short' else 1)
                           for kind,name,body in re.findall(r'const unsigned (short|char) (\w+)\[\] GALAXY_DATA = \{([^}]+)\}',data)}
    report['flags_off']=all('ASTRA_'+f+':BOOL=OFF' in (BUILD/'CMakeCache.txt').read_text()
                           for f in ('COMBAT_STRESS','COMBAT_TIMING','CAMPAIGN_PROBE','PRESENTATION_TIMING'))
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print('asset bytes',report['asset_bytes'])
    for tag in ('it7',args.candidate):
        for profile,p in report[tag].items():
            print(tag,profile,{k:v for k,v in p.items() if k!='stages_s1_dense'})
            for phase,rows in p['stages_s1_dense'].items():
                print(phase,[(r['stage'],round(r['mean'],2),r['max']) for r in rows])
            if 'sector_preparation' in p:
                print('preparation ticks/bitmap', {sector:[r['work']+1 for r in cuts]
                      for sector,cuts in p['sector_preparation'].items()})


if __name__=='__main__':main()
