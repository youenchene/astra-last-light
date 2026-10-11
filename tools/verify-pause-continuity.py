#!/usr/bin/env python3.12
"""Source-pixel and clock checks for the production P/M/input-edge replay."""
import importlib.util
from pathlib import Path
import re
import sys

SPEC = importlib.util.spec_from_file_location('campaign', Path(__file__).with_name('check-campaign-native.py'))
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)
from agk.image import Image


def states(text):
    result = []
    for line in text.splitlines():
        fields = dict((k, int(v)) for k, v in re.findall(r'(\w+)=(-?\d+)', line))
        if line.startswith('AGK frame='):
            result.append(fields)
        elif line.startswith('AGK enemy_acc=') and result:
            result[-1].update(fields)
    return result


def check_clocks(text):
    samples = states(text)
    for phase in (6, 1):
        paused = [s for s in samples if s['phase'] == phase and s.get('paused') == 1]
        CHECK.require(len(paused) >= 3, f'phase {phase}: insufficient pause samples')
        CHECK.require(paused[-1]['frame'] - paused[0]['frame'] >= 50, 'video clock stopped')
        for field in ('x', 'y', 'stage', 'sim', 'enemy_tick', 'enemy_acc', 'pf', 'wave',
                      'shot_bobs', 'hostile_bullets', 'enemies', 'lives', 'score'):
            CHECK.require(len({s[field] for s in paused}) == 1, f'phase {phase}: paused {field} changed')
        CHECK.require(any(s['frame'] > paused[-1]['frame'] and s['phase'] == phase and
                          s.get('paused') == 0 for s in samples), f'phase {phase}: missing resume')
    CHECK.require('AGK sfx shot' not in text, 'pause-era charge released a shot')
    first = CHECK.records(text, 'cut_visible=')
    for revision, phase in ((2, 6), (3, 1)):
        cuts = [s for s in first if s['cut_visible'] == revision and s['phase'] == phase]
        CHECK.require([s['both'] for s in cuts] == [0, 1], 'first-visible/both-ready gate')
        CHECK.require(cuts[0]['vblank'] < cuts[1]['vblank'], 'missing second-bitmap repair')
    preparing = [s for s in samples if s['phase'] == 6 and s.get('preparing')]
    CHECK.require(preparing and all(s['sim'] == s['stage'] == s['pf'] == s['wave'] == 0
                                  for s in preparing), 'opening logic ran before readiness')


def check_indicator(image, paused):
    _, glyphs = CHECK.artwork('font')
    message, ink = ('PAUSE', (238, 238, 255)) if paused else ('LANCE', (187, 221, 255))
    # Source palette, not a screenshot-derived expected label.
    colors, _ = CHECK.artwork('campaign_manga')
    ink = colors['E'] if paused else (187, 221, 255)
    lit = {(8 + column * 6 + x, 18 + y) for column, letter in enumerate(message)
           for y, row in enumerate(glyphs[ord(letter) - ord('A')])
           for x, pixel in enumerate(row) if pixel == 'X'}
    CHECK.require(all(image.pixel(x, y) == (ink if (x, y) in lit else colors['1'])
                      for y in range(18, 25) for x in range(8, 40)), 'pause/restore label pixels')


def verify(folder):
    text = (folder / 'serial.txt').read_text()
    check_clocks(text)
    names = ('opening_first', 'opening_paused', 'opening_paused_late', 'opening_resumed',
             'closing_first', 'closing_ready', 'play_paused', 'play_paused_late', 'play_resumed')
    images = {name: Image.load_png(str(folder / f'{name}.screen.png')) for name in names}
    for name, image in images.items():
        CHECK.require((image.width, image.height) == (320, 256), 'capture dimensions')
        CHECK.hero_pixels(image)
        check_indicator(image, 'paused' in name)
    for prefix in ('opening', 'play'):
        a, b = images[f'{prefix}_paused'], images[f'{prefix}_paused_late']
        hero = CHECK.hero_pixels(a) | CHECK.hero_pixels(b)
        CHECK.require(all(a.pixel(x, y) == b.pixel(x, y) for y in range(256) for x in range(320)
                          if (x, y) not in hero), 'paused background changed')
    # Story source and static exterior are validated with the two PAUSE labels equal.
    CHECK.check_scene_pair(images['opening_paused'], images['opening_paused_late'], 0)
    perf = CHECK.performance(text)
    print(f'PASS {folder}: first-visible/closing hero, P clocks/edges, pause/restore pixels; '
          f'drops={perf["dropped"]}, peak={perf["maxload"]}%; '
          f'memory={CHECK.records(text, "chip_free=")}')


if __name__ == '__main__':
    for argument in sys.argv[1:]:
        verify(Path(argument))
