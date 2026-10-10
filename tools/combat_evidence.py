"""Required evidence inventories shared by combat inspectors and comparisons."""
import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ('a500', 'a500-aros')
SCENARIOS = ('pause_continuity', 'clean_transitions', 'gameover_title', 'large_manga', 'bob_restore')
MATRIX_CAPTURES = {f'case{i:02}.screen.png' for i in range(48)}
EVENT_FIELDS = ('stress_case', 'tick', 'phase', 'level', 'bitmap', 'copper')


def require_names(actual, expected, label):
    actual, expected = set(actual), set(expected)
    if not expected or actual != expected:
        raise ValueError(f'{label}: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}')


def capture_hashes(folder, expected):
    files = {p.name:p for p in folder.glob('*.screen.png') if p.is_file()}
    require_names(files, expected, f'{folder}: capture inventory')
    hashes = {}
    for name, path in sorted(files.items()):
        content = path.read_bytes()
        if not content:
            raise ValueError(f'{path}: empty capture')
        hashes[name] = hashlib.sha256(content).hexdigest()
    return hashes


def matrix_event_identity(events):
    expected = [(i,t) for i in range(48) for t in (100,200)]
    if [(r.get('stress_case'),r.get('tick')) for r in events] != expected:
        raise ValueError('matrix case coverage: require all 96 ordered capture events')
    for row in events:
        case = row['stress_case']
        if (row.get('phase') != 1+(case//6)%2 or row.get('level') != case//12 or
                row.get('bitmap') not in (0,1) or row.get('copper') not in (0,1)):
            raise ValueError('matrix event identity invalid')
        clocks = [row.get(key) for key in ('submitted','ack','scanout')]
        if not all(isinstance(clock,int) for clock in clocks) or not clocks[0] < clocks[1] < clocks[2]:
            raise ValueError('matrix publication acknowledgement failure')
    # Absolute vblank clocks can differ with elapsed work; submission identities cannot.
    return [tuple(row[key] for key in EVENT_FIELDS) for row in events]


def validate_matrix(folder, data):
    hashes = capture_hashes(folder, MATRIX_CAPTURES)
    require_names(data['captures'], MATRIX_CAPTURES, f'{folder}: capture manifest')
    if data['captures'] != hashes:
        raise ValueError(f'{folder}: capture manifest differs from actual files')
    events = [{k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)', line)}
              for line in (folder/'serial.txt').read_text().splitlines()
              if line.startswith('AGK stress_case=')]
    if data['cases'] != events:
        raise ValueError(f'{folder}: event manifest differs from actual serial evidence')
    return matrix_event_identity(data['cases'])


def scenario_captures(case):
    if case not in (*SCENARIOS, 'campaign'):
        raise ValueError('unknown evidence scenario: '+case)
    path = ROOT/f'game/tests/{"" if case == "bob_restore" else "native/"}{case}.agk'
    names = re.findall(r'^screenshot (\w+)\s*$', path.read_text(), re.M)
    if not names or len(names) != len(set(names)):
        raise ValueError(f'{path}: missing or duplicate screenshot declarations')
    return {name+'.screen.png' for name in names}


def validate_production_report(folder, report):
    require_names(report['cases'], SCENARIOS, f'{folder}: scenario manifest')
    require_names((p.name for p in folder.iterdir() if p.is_dir()), SCENARIOS,
                  f'{folder}: scenario directories')
    for case in SCENARIOS:
        actual = capture_hashes(folder/case, scenario_captures(case))
        if report['cases'][case]['captures'] != actual:
            raise ValueError(f'{folder}/{case}: capture manifest differs from actual files')
