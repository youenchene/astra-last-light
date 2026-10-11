"""Disjoint selected-frame accounting. Nested logic/HUD cuts are never added twice."""
import re

# A chain of shared endpoints, not independent inclusive stopwatch intervals.
CHAIN = [(-1, 'start'), (9, 'bookkeeping'), (10, 'restore'), (0, 'world'),
         (12, 'music'), (13, 'input'), (14, 'injection'), (1, 'logic'),
         (2, 'sound_events'), (3, 'render_setup'), (4, 'hud'), (5, 'bobs'),
         (15, 'display_gate'), (16, 'copper'), (17, 'pause'), (18, 'hero'),
         (19, 'enemies'), (20, 'hostiles'), (6, 'render_return'),
         (21, 'post_render'), (22, 'qa'), (23, 'state_report'),
         (24, 'final_wait'), (25, 'publish'), (-2, 'trace_tail')]
LOGIC = [(14, 'start'), (26, 'logic_setup_hero'), (27, 'enemy_spawn_move_fire_admission'),
         (28, 'projectile_movement'), (29, 'pickups'), (30, 'collisions'),
         (31, 'visibility_schedule'), (32, 'boss_gate'), (1, 'logic_return')]


def partition(stamps, chain):
    indices = [i for i, _ in chain]
    if len(indices) != len(set(indices)):
        raise ValueError('duplicate boundary')
    result = {}
    for (a, _), (b, name) in zip(chain, chain[1:]):
        delta = stamps[b] - stamps[a]
        if delta < 0:
            raise ValueError(f'nonmonotonic boundary {a}->{b}')
        result[name] = delta
    if sum(result.values()) != stamps[indices[-1]] - stamps[indices[0]]:
        raise ValueError('partition identity failed')
    return result


def parse(text, expected, detailed=True):
    rows = {}
    for line in text.splitlines():
        d = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', line)}
        if 'galaxy_diag' in d:
            frame = d['frame']
            if frame in rows:
                raise ValueError('duplicate frame')
            rows[frame] = dict(d, stamps={-1: 0, -2: d['lines']})
        elif 'split_frame' in d:
            row = rows[d.pop('split_frame')]
            row.update(d)
        elif 'stamp_frame' in d:
            row = rows[d['stamp_frame']]
            if d['index'] in row['stamps']:
                raise ValueError('duplicate timestamp')
            row['stamps'][d['index']] = d['at']
    if set(rows) != set(expected):
        raise ValueError(f'frame inventory {set(rows)} != {set(expected)}')
    for row in rows.values():
        if row['whole'] != row['prefix'] + row['lines'] + row['suffix']:
            raise ValueError('AGK identity failed')
        if detailed:
            row['segments'] = partition(row['stamps'], CHAIN)
            row['nested_logic'] = partition(row['stamps'], LOGIC)
            if sum(row['nested_logic'].values()) != row['segments']['logic']:
                raise ValueError('nested logic identity failed')
            if not row['stamps'][3] <= row['stamps'][7] <= row['stamps'][8] <= row['stamps'][4]:
                # No formatter call on pickup frame.
                if row['stamps'][7] or row['stamps'][8]:
                    raise ValueError('formatter outside HUD')
    return rows
