#!/usr/bin/env python3
"""Sustained public-logic replay; host-only spawn counters, never pool deltas.

PLAY runs the complete sector quota without shooting. BOSS runs 20,000 ticks.
Hero sweeps vertically with invulnerability to avoid death clearing the pool.
No actor/trajectory/countdown is reset after initialization. This is a density
fixture, not an ordinary no-hit playthrough or a native performance measurement.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def instrument(source):
    admission = ('admitVolleyHostile(s, e, cache)' if 'static uint8_t admitVolleyHostile(' in source else
                 'admitReserved(s, e, cache)' if 'static uint8_t admitReserved(' in source else 'admitHostile(s, e)')
    replacements = [
        ('#include "logic.h"', '#include "logic.h"\nstatic unsigned long opportunities, eligible, accepted, full, conflicts;'),
        (f'\tif(e) {admission};',
         f'\t++eligible;\n\tif(!e) ++full;\n\telse if({admission}) ++accepted;\n\telse ++conflicts;'),
        ('\tint8_t ray, radius = rays / 2;', '\t++opportunities;\n\tint8_t ray, radius = rays / 2;'),
        ('\t\telse {\n\t\t\t/* 32px lanes', '\t\telse {\n\t\t\t++opportunities;\n\t\t\t/* 32px lanes'),
    ]
    for old, new in replacements:
        if source.count(old) != 1:
            raise ValueError(f"Instrumentation anchor changed: {old!r}")
        source = source.replace(old, new)
    return source


HARNESS = r'''
#include <stdio.h>
int main(void) {
    for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
        for(unsigned boss = 0; boss < 2; ++boss) {
            tGameState s;
            logicInit(&s);
            s.level = level; s.phase = boss ? BOSS : PLAY;
            s.waveTimer = 25;
            s.boss = (tBoss){.x=240, .y=104, .hp=480, .maxHp=480,
                .active=1, .visible=1, .cooldown=50};
            opportunities = eligible = accepted = full = conflicts = 0;
            unsigned ticks = 0, peak = 0;
            unsigned long activeTicks = 0;
            while(s.phase == (boss ? BOSS : PLAY) && ticks < 20000) {
                tInput input = {0, (ticks / 100) % 2 ? -1 : 1, 0};
                s.invulnerable = 60000;
                logicUpdate(&s, &input);
                unsigned active = 0;
                for(unsigned i = 0; i < HOSTILE_COUNT; ++i)
                    active += s.hostile[i].active != 0;
                activeTicks += active;
                if(active > peak) peak = active;
                ++ticks;
            }
            if(!boss && s.phase != BOSS_INTRO) return 2;
            printf("%u %s %u %lu %lu %lu %lu %lu %lu %u\n", level + 1,
                boss ? "BOSS" : "PLAY", ticks, opportunities, eligible,
                accepted, full, conflicts, activeTicks, peak);
        }
    }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source = instrument((ROOT / 'game/src/logic.c').read_text())
    with tempfile.TemporaryDirectory(prefix='admission-') as folder:
        path = Path(folder)
        (path / 'replay.c').write_text(source + HARNESS)
        subprocess.run(['cc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-I', str(ROOT / 'game/src'), str(path / 'replay.c'),
                        '-o', str(path / 'replay')], check=True)
        output = subprocess.check_output([str(path / 'replay')], text=True)
    keys = ('sector', 'phase', 'ticks', 'opportunities', 'eligible', 'accepted',
            'full', 'conflicts', 'active_bullet_ticks', 'peak_active')
    rows = []
    for line in output.splitlines():
        values = line.split()
        row = dict(zip(keys, [v if i == 1 else int(v) for i, v in enumerate(values)], strict=True))
        assert row['eligible'] == row['accepted'] + row['full'] + row['conflicts']
        row['mean_active'] = row['active_bullet_ticks'] / row['ticks']
        rows.append(row)
    args.out.write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
