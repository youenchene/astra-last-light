#!/usr/bin/env python3
"""Pillow native comparison against preserved character captures and independent PNG oracle."""
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from selected_rd_oracle import scene_rgb

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT/'game/art/selected-rd/story-character'
LAYER = PARENT/'bold-marks'
NAMES = ('graveyard-b','nebula-b','foundry-b','citadel-b','victory')
ENDING = ('ending_first','ending_next_buffer','ending_held','ending_released')


def scene_for(stem):
    if stem.startswith('scene'):
        return int(stem[5:7])
    if stem in ENDING:
        return 12
    return 0 if stem == 'restarted_opening' else None


def skin_samples():
    original = Image.open(PARENT.parent/'victory-identity-master/victory.png').convert('RGB')
    skin = {(x,y) for y in range(88,104) for x in range(80,115)
            if original.getpixel((x,y)) == (252,169,139)}
    assert len(skin) == 498
    return skin | {(80,88),(80,89),(81,88),(82,88),(83,88),(113,88),(114,88)}


def check_capture(path, baseline, scene, skin):
    image = Image.open(path).convert('RGB')
    prior = Image.open(baseline/path.name).convert('RGB')
    assert image.size == prior.size == (320,256)
    expected_deltas, allowed, eye_count, skin_count = set(), set(), 0, 0
    if scene is not None:
        index = 4 if scene==12 else scene//3
        x0,y0 = (0,32) if scene==12 else (144,68)
        expected = scene_rgb(scene,layer='bold-marks')
        historical = scene_rgb(scene,layer='story-character')
        mask = Image.open(LAYER/'masks'/f'{NAMES[index]}-additions.png').convert('L')
        eyes = Image.open(PARENT/'masks'/f'{NAMES[index]}-protected-eyes.png').convert('L')
        for y,row in enumerate(expected):
            for x,pixel in enumerate(row):
                p = (x0+x,y0+y)
                assert image.getpixel(p) == pixel, (path,'current source',p)
                assert prior.getpixel(p) == historical[y][x], (path,'historical source',p)
                if mask.getpixel((x,y)):
                    allowed.add(p)
                if historical[y][x] != pixel:
                    expected_deltas.add(p)
                if eyes.getpixel((x,y)):
                    assert image.getpixel(p) == prior.getpixel(p), (path,'eye',p)
                    eye_count += 1
        assert len(expected_deltas) == (8 if index==4 else 2)
        if index==4:
            for x,y in skin:
                assert image.getpixel((x,y+32)) == prior.getpixel((x,y+32)) == (255,170,153)
            skin_count = len(skin)
    actual = {(x,y) for y in range(256) for x in range(320)
              if image.getpixel((x,y)) != prior.getpixel((x,y))}
    assert actual == expected_deltas == allowed, (path,'full-screen deltas',len(actual),len(expected_deltas))
    return dict(changed_pixels=len(actual), protected_eye_pixels=eye_count,
                protected_skin_samples=skin_count, outside_additions_changes=0,
                png_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def review_sheet(folder, baseline):
    sheet = Image.new('RGB',(1600,828),'#303030')
    draw = ImageDraw.Draw(sheet)
    for row,(source,profile,label) in enumerate(((baseline,'a500','BEFORE'),
                                               (folder,'a500','AFTER A500'),
                                               (folder,'a500-aros','AFTER AROS'))):
        for col,scene in enumerate((0,3,6,9,12)):
            draw.text((col*320+4,row*276+4),f'{label} scene{scene:02}',fill='white')
            sheet.paste(Image.open(source/profile/f'scene{scene:02}.screen.png'),(col*320,row*276+20))
    sheet.save(folder/'bold-marks-native-review.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('--baseline',type=Path,default=ROOT/'game/build/story-character-campaign')
    args = parser.parse_args()
    report = json.loads((args.folder/'report.json').read_text())
    assert report['production_restored'] and not report.get('error')
    evidence: dict[str, Any] = dict(baseline=str(args.baseline),profiles={})
    skin = skin_samples()
    for profile in ('a500','a500-aros'):
        assert report['profiles'][profile]['functional_pass']
        assert report['profiles'][profile]['native_pixels'] == 1160320
        paths = sorted((args.folder/profile).glob('*.screen.png'))
        assert len(paths) == 32
        captures = {}
        for path in paths:
            stem = path.name.removesuffix('.screen.png')
            captures[stem] = check_capture(path,args.baseline/profile,scene_for(stem),skin)
            assert path.read_bytes() == (args.folder/'a500'/path.name).read_bytes(), ('cross-profile',path)
        evidence['profiles'][profile] = dict(captures=captures,**report['profiles'][profile])
    cache = (ROOT/'game/build/CMakeCache.txt').read_text()
    for flag in ('ASTRA_CAMPAIGN_PROBE','ASTRA_PRESENTATION_TIMING'):
        assert f'{flag}:BOOL=OFF' in cache
    evidence['production_flags'] = 'probe OFF; timing OFF'
    evidence['production_executable_bytes'] = (ROOT/'game/build/astra').stat().st_size
    review_sheet(args.folder,args.baseline)
    (args.folder/'bold-marks-integration-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS: all 13 source scenes; 32 identical cross-profile pairs; 64 exact full-screen parent deltas; '
          'complete eyes and 505 ending skin samples preserved; production OFF')


if __name__ == '__main__':
    main()
