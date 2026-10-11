#!/usr/bin/env python3
"""Record exact cross-profile and prior-ending comparisons after the focused run."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ENDING_NAMES = ('scene12', 'scene12_late', 'ending_first', 'ending_next_buffer',
                'ending_held', 'ending_released')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compare_endings(folder, reference):
    baseline = reference.read_bytes()
    baseline_rgb = Image.open(reference).convert('RGB').tobytes()
    result = {}
    for name in ENDING_NAMES:
        path = folder / f'{name}.screen.png'
        data = path.read_bytes()
        rgb = Image.open(path).convert('RGB').tobytes()
        assert data == baseline, f'Ending PNG bytes differ: {path} vs {reference}'
        assert rgb == baseline_rgb, f'Ending RGB bytes differ: {path}'
        result[name] = dict(png_sha256=sha(data), rgb_sha256=sha(rgb),
                            png_bytes=len(data), rgb_bytes=len(rgb), differing_bytes=0)
    return dict(reference=str(reference.relative_to(ROOT)), captures=result)


def montage(folder):
    image = Image.new('RGB', (5 * 320, 2 * 276), '#303030')
    draw = ImageDraw.Draw(image)
    for row, profile in enumerate(('a500', 'a500-aros')):
        for column, scene in enumerate((0, 3, 6, 9, 12)):
            draw.text((column * 320 + 4, row * 276 + 4), f'{profile} scene{scene:02}', fill='white')
            capture = Image.open(folder / profile / f'scene{scene:02}.screen.png').convert('RGB')
            assert capture.size == (320, 256)
            image.paste(capture, (column * 320, row * 276 + 20))
    image.save(folder / 'native-review.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    folder = parser.parse_args().folder.resolve()
    report = json.loads((folder / 'report.json').read_text())
    assert report['production_restored'] and not report.get('error')
    evidence = {'profiles': {}, 'cross_profile_png_sha256': {}}
    for profile, prior in (('a500', 'a500'), ('a500-aros', 'aros')):
        reference = ROOT / f'game/build/ending-eyes-preview-{prior}/ending_preview_ready.screen.png'
        data = report['profiles'][profile]
        assert data['functional_pass']
        perf = data['performance_observation_only']
        evidence['profiles'][profile] = dict(
            ending_comparison=compare_endings(folder / profile, reference),
            native_pixels=data['native_pixels'], injected_startup_memory=data['memory'],
            dropped=perf['dropped'], maxload=perf['maxload'])
    files = sorted((folder / 'a500').glob('*.screen.png'))
    assert len(files) == 32
    for path in files:
        data = path.read_bytes()
        assert data == (folder / 'a500-aros' / path.name).read_bytes(), path.name
        evidence['cross_profile_png_sha256'][path.name] = sha(data)
    cache = (ROOT / 'game/build/CMakeCache.txt').read_text()
    for flag in ('ASTRA_CAMPAIGN_PROBE', 'ASTRA_PRESENTATION_TIMING'):
        assert f'{flag}:BOOL=OFF' in cache
    evidence['production_flags'] = 'probe OFF; presentation timing OFF'
    evidence['production_executable_bytes'] = (ROOT / 'game/build/astra').stat().st_size
    montage(folder)
    (folder / 'eye-integration-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({p: {k: v for k, v in d.items() if k != 'ending_comparison'}
                      for p, d in evidence['profiles'].items()}, indent=2))
    print(f'PASS: {len(files)} cross-profile PNG pairs; 12 exact prior-ending PNG/RGB comparisons; flags OFF')


if __name__ == '__main__':
    main()
