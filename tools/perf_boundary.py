"""Append a debug F8 boundary after all original replay commands/assertions."""
import re

BOUNDARY_SUFFIX = ('\n# Flush actual final partial window; no padding frames.\n'
                   'key 0x57\nwait-serial "AGK perf_complete=" 100\n'
                   'expect-serial "AGK perf_complete="\n')


def scenario_with_boundary(root, scenario, folder):
    source = root / scenario
    target = folder.resolve() / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text() + BOUNDARY_SUFFIX)
    return target


def complete_performance(text, performance):
    lines = text.splitlines()
    ends = [i for i, line in enumerate(lines) if line.startswith('AGK perf_complete=')]
    if len(ends) != 1:
        raise ValueError('expected exactly one completed performance boundary')
    end = ends[0]
    if any(line.startswith('AGK perf ') for line in lines[end + 1:]):
        raise ValueError('performance window after completed boundary')
    marker = {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', lines[end])}
    if set(marker) != {'perf_complete', 'dropped', 'boundary_frame'}:
        raise ValueError('malformed performance completion header')
    windows = performance['windows']
    fields = ('frames', 'dropped', 'load', 'maxload')
    raw = [{k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', line)}
           for line in lines[:end] if line.startswith('AGK perf ')]
    if any(set(row) != set(fields) for row in raw) or raw != [
            {key: row[key] for key in fields} for row in windows]:
        raise ValueError('performance manifest differs from actual serial windows')
    if not windows or any(w['frames'] != 50 for w in windows[:-1]):
        raise ValueError('nonfinal performance window does not contain 50 frames')
    if not 1 <= windows[-1]['frames'] <= 50:
        raise ValueError('invalid final partial-window count')
    count = sum(w['frames'] for w in windows)
    if marker['perf_complete'] != count or marker['dropped'] != performance['dropped']:
        raise ValueError('completed-window totals do not match boundary')
    return {**performance, 'complete': True, 'measured_frames': count,
            'final_window_frames': windows[-1]['frames'],
            'boundary_frame': marker['boundary_frame'],
            'boundary_overhead': 'final report/marker/hold excluded; reports followed by gameplay included'}
