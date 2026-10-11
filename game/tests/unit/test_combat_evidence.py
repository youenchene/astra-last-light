"""Fail-closed checks at the real retained-evidence inspector/CLI boundaries."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools'))
SPEC = importlib.util.spec_from_file_location('combat_check', ROOT/'tools/check-combat-performance.py')
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)
PROFILES = ('a500', 'a500-aros')
SCENARIOS = ('pause_continuity', 'clean_transitions', 'gameover_title', 'large_manga', 'bob_restore')
PERF = {'dropped':0, 'maxload':10, 'windows':[{'frames':50, 'load':5}]}
STATE = 'AGK frame=1 phase=1 level=1 score=0 lives=3 sim=1 enemy_tick=0 enemy_acc=0 pf=0 title_blocked=0 preparing=0\n'


def captures(folder, names):
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        (folder/name).write_bytes(b'capture fixture: '+name.encode())
    return {name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in names}


def matrix(root):
    report = {'profiles':{}}
    for profile in PROFILES:
        folder = root/profile
        hashes = captures(folder, [f'case{i:02}.screen.png' for i in range(48)])
        events = [dict(stress_case=i, tick=t, phase=1+(i//6)%2, level=i//12,
                       bitmap=0, copper=0, submitted=i*400+t, ack=i*400+t+1, scanout=i*400+t+2)
                  for i in range(48) for t in (100, 200)]
        text = '\n'.join('AGK '+' '.join(f'{k}={v}' for k,v in e.items()) for e in events)
        (folder/'serial.txt').write_text(text+'\nAGK stress_complete\nAGK perf frames=50 dropped=0 load=5 maxload=10\n')
        report['profiles'][profile] = dict(captures=hashes, cases=events, stage_rows=[],
                                           stage_windows=[], whole_performance=PERF)
    (root/'report.json').write_text(json.dumps(report))


def production(root, campaign):
    campaign_report = {'profiles':{}}
    for profile in PROFILES:
        report = {'cases':{}}
        for case in (*SCENARIOS, 'campaign'):
            source = ROOT/f'game/tests/{"" if case == "bob_restore" else "native/"}{case}.agk'
            names = [m+'.screen.png' for m in re.findall(r'^screenshot (\w+)\s*$', source.read_text(), re.M)]
            folder = campaign/profile if case == 'campaign' else root/profile/case
            hashes = captures(folder, names)
            (folder/'serial.txt').write_text(STATE)
            data = {'captures':hashes, 'performance':PERF}
            if case == 'campaign':
                campaign_report['profiles'][profile] = data
            else:
                report['cases'][case] = data
        (root/profile/'report.json').write_text(json.dumps(report))
    (campaign/'report.json').write_text(json.dumps(campaign_report))


class CombatEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_check(self, tool, *args):
        return subprocess.run([sys.executable, str(ROOT/'tools'/tool), *map(str,args)],
                              capture_output=True, text=True)

    def matrix_pair(self):
        a, b = self.root/'a', self.root/'b'
        matrix(a); matrix(b)
        return a, b

    def production_pair(self):
        a,b,ac,bc = [self.root/n for n in ('a','b','ac','bc')]
        production(a,ac); production(b,bc)
        return a,b,ac,bc

    def compare_production(self, paths):
        return self.run_check('compare-combat-production.py', *[
            v for flag, path in zip(('--baseline','--candidate','--baseline-campaign','--candidate-campaign'),paths)
            for v in (flag,path)])

    def test_complete_matrix_passes(self):
        a,b = self.matrix_pair()
        self.assertTrue(CHECK.inspect(a/'a500', False)['functional_pass'])
        result = self.run_check('compare-combat-performance.py', a,b)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_inspector_rejects_missing_or_extra_matrix_capture(self):
        a,_ = self.matrix_pair()
        (a/'a500/case47.screen.png').unlink()
        with self.assertRaises(ValueError): CHECK.inspect(a/'a500',False)
        (a/'a500/case47.screen.png').write_bytes(b'restored')
        (a/'a500/extra.screen.png').write_bytes(b'extra')
        with self.assertRaises(ValueError): CHECK.inspect(a/'a500',False)

    def test_inspector_rejects_all_matrix_captures_missing(self):
        a,_ = self.matrix_pair()
        for p in (a/'a500').glob('*.screen.png'): p.unlink()
        with self.assertRaises(ValueError): CHECK.inspect(a/'a500',False)

    def test_matrix_comparison_rejects_missing_files_on_either_or_both_sides(self):
        for sides, all_files in (((0,),False),((1,),False),((0,1),False),
                                ((0,),True),((1,),True),((0,1),True)):
            with self.subTest(sides=sides, all=all_files):
                paths = self.matrix_pair()
                for side in sides:
                    files = (paths[side]/'a500').glob('*.screen.png') if all_files else [paths[side]/'a500/case00.screen.png']
                    for p in files: p.unlink()
                self.assertNotEqual(self.run_check('compare-combat-performance.py',*paths).returncode,0)

    def test_matrix_comparison_rejects_empty_manifests_and_events(self):
        a,b = self.matrix_pair()
        for path in (a,b):
            report = json.loads((path/'report.json').read_text())
            report['profiles']['a500'].update(captures={}, cases=[])
            (path/'report.json').write_text(json.dumps(report))
        self.assertNotEqual(self.run_check('compare-combat-performance.py',a,b).returncode,0)

    def test_matrix_comparison_rejects_extra_capture(self):
        a,b = self.matrix_pair()
        (b/'a500/extra.screen.png').write_bytes(b'extra')
        self.assertNotEqual(self.run_check('compare-combat-performance.py',a,b).returncode,0)

    def test_matrix_comparison_rejects_mismatched_acknowledged_identity(self):
        a,b = self.matrix_pair()
        report = json.loads((b/'report.json').read_text())
        report['profiles']['a500']['cases'][0]['bitmap'] = 1
        (b/'report.json').write_text(json.dumps(report))
        serial = b/'a500/serial.txt'
        serial.write_text(serial.read_text().replace('bitmap=0','bitmap=1',1))
        self.assertNotEqual(self.run_check('compare-combat-performance.py',a,b).returncode,0)

    def test_matrix_comparison_rejects_empty_events_with_complete_captures(self):
        a,b = self.matrix_pair()
        for root in (a,b):
            report = json.loads((root/'report.json').read_text())
            report['profiles']['a500']['cases'] = []
            (root/'report.json').write_text(json.dumps(report))
            (root/'a500/serial.txt').write_text('AGK stress_complete\n')
        self.assertNotEqual(self.run_check('compare-combat-performance.py',a,b).returncode,0)

    def test_matrix_comparison_rejects_incomplete_manifest_with_complete_files(self):
        a,b = self.matrix_pair()
        for root in (a,b):
            report = json.loads((root/'report.json').read_text())
            report['profiles']['a500']['captures'].pop('case47.screen.png')
            (root/'report.json').write_text(json.dumps(report))
        self.assertNotEqual(self.run_check('compare-combat-performance.py',a,b).returncode,0)

    def test_complete_production_and_campaign_pass(self):
        result = self.compare_production(self.production_pair())
        self.assertEqual(result.returncode,0,result.stderr)

    def test_production_rejects_missing_capture_on_either_or_both_sides(self):
        for sides in ((0,),(1,),(0,1)):
            with self.subTest(sides=sides):
                paths = self.production_pair()
                for side in sides: next((paths[side]/'a500/large_manga').glob('*.screen.png')).unlink()
                self.assertNotEqual(self.compare_production(paths).returncode,0)

    def test_production_rejects_all_captures_missing_in_ordinary_or_campaign(self):
        for case in ('large_manga','campaign'):
            with self.subTest(case=case):
                paths = self.production_pair()
                folders = [p/'a500'/case for p in paths[:2]] if case != 'campaign' else [p/'a500' for p in paths[2:]]
                for folder in folders:
                    for p in folder.glob('*.screen.png'): p.unlink()
                self.assertNotEqual(self.compare_production(paths).returncode,0)

    def test_production_rejects_empty_or_event_only_state_logs_in_every_scenario(self):
        for case in (*SCENARIOS,'campaign'):
            for text in ('','AGK qa_complete=1\nAGK perf frames=50 dropped=0 load=5 maxload=10\n'):
                with self.subTest(case=case,text=text):
                    paths = self.production_pair()
                    folders = [p/'a500'/case for p in paths[:2]] if case != 'campaign' else [p/'a500' for p in paths[2:]]
                    for folder in folders: (folder/'serial.txt').write_text(text)
                    self.assertNotEqual(self.compare_production(paths).returncode,0)

    def test_production_rejects_omitted_or_extra_scenarios(self):
        for change in ('missing','empty','extra'):
            with self.subTest(change=change):
                paths = self.production_pair()
                for root in paths[:2]:
                    p = root/'a500/report.json'; report = json.loads(p.read_text())
                    if change == 'missing': report['cases'].pop('bob_restore')
                    elif change == 'empty': report['cases'] = {}
                    else: report['cases']['unknown'] = report['cases']['bob_restore']
                    p.write_text(json.dumps(report))
                self.assertNotEqual(self.compare_production(paths).returncode,0)

    def test_production_rejects_extra_capture(self):
        paths = self.production_pair()
        (paths[1]/'a500/large_manga/extra.screen.png').write_bytes(b'extra')
        self.assertNotEqual(self.compare_production(paths).returncode,0)


if __name__ == '__main__':
    unittest.main()
