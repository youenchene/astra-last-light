#!/usr/bin/env python3.12
"""Verify current native character pixels and exact deltas from eye-only captures."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw
from selected_rd_oracle import scene_rgb

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'game/art/selected-rd/story-character'
NAMES = ('graveyard-b','nebula-b','foundry-b','citadel-b','victory')
EYE_SAMPLES = (((23,53),(36,54)),((25,24),(39,24)),
               ((25,55),(39,56)),((29,53),(46,54)))
ENDING = ('ending_first','ending_next_buffer','ending_held','ending_released')


def scene_for(stem):
    if stem.startswith('scene'):
        return int(stem[5:7])
    if stem in ENDING:
        return 12
    return 0 if stem == 'restarted_opening' else None


def check_capture(path, baseline, scene):
    image = Image.open(path).convert('RGB')
    prior = Image.open(baseline / path.name).convert('RGB')
    assert image.size == prior.size == (320,256)
    allowed,expected_deltas,eye_count = set(),set(),0
    if scene is not None:
        index = 4 if scene == 12 else scene//3
        x0,y0 = (0,32) if scene == 12 else (144,68)
        expected = scene_rgb(scene,layer='story-character')
        historical = scene_rgb(scene,layer='story-eyes')
        armor,cheek,eyes = [Image.open(LAYER/'masks'/f'{NAMES[index]}-{kind}.png').convert('L')
                            for kind in ('armor','cheek','protected-eyes')]
        for y,row in enumerate(expected):
            for x,pixel in enumerate(row):
                p = (x0+x,y0+y)
                assert image.getpixel(p) == pixel, (path,'current source',p)
                assert prior.getpixel(p) == historical[y][x], (path,'historical source',p)
                if armor.getpixel((x,y)) or cheek.getpixel((x,y)):
                    allowed.add(p)
                if historical[y][x] != pixel:
                    expected_deltas.add(p)
                if eyes.getpixel((x,y)):
                    assert image.getpixel(p) == prior.getpixel(p), (path,'complete eye',p)
                    eye_count += 1
        if index < 4:
            for x,y in EYE_SAMPLES[index]:
                assert image.getpixel((x+x0,y+y0)) == (68,187,221)
        if index == 4:
            assert len(expected_deltas) == 5
    actual = {(x,y) for y in range(256) for x in range(320)
              if image.getpixel((x,y)) != prior.getpixel((x,y))}
    assert actual == expected_deltas, (path,'unexpected complete-screen differences',len(actual),len(expected_deltas))
    assert actual <= allowed, (path,'outside armor/cheek masks')
    return dict(changed_pixels=len(actual),protected_eye_pixels=eye_count,
                exterior_changed_pixels=0,png_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def review_sheet(folder):
    sheet = Image.new('RGB',(1600,552),'#303030')
    draw = ImageDraw.Draw(sheet)
    for row,profile in enumerate(('a500','a500-aros')):
        for col,scene in enumerate((0,3,6,9,12)):
            draw.text((col*320+4,row*276+4),f'{profile} scene{scene:02}',fill='white')
            sheet.paste(Image.open(folder/profile/f'scene{scene:02}.screen.png'),(col*320,row*276+20))
    sheet.save(folder/'character-native-review.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('--baseline',type=Path,default=ROOT/'game/build/story-eyes-campaign')
    args = parser.parse_args()
    report = json.loads((args.folder/'report.json').read_text())
    assert report['production_restored'] and not report.get('error')
    evidence = {'baseline':str(args.baseline),'profiles':{}}
    for profile in ('a500','a500-aros'):
        assert report['profiles'][profile]['functional_pass']
        paths = sorted((args.folder/profile).glob('*.screen.png'))
        assert len(paths) == 32
        captures = {}
        for path in paths:
            stem = path.name.removesuffix('.screen.png')
            captures[stem] = check_capture(path,args.baseline/profile,scene_for(stem))
            assert path.read_bytes() == (args.folder/'a500'/path.name).read_bytes(), ('cross-profile',path)
        evidence['profiles'][profile] = dict(captures=captures,**report['profiles'][profile])
    cache = (ROOT/'game/build/CMakeCache.txt').read_text()
    for flag in ('ASTRA_CAMPAIGN_PROBE','ASTRA_PRESENTATION_TIMING'):
        assert f'{flag}:BOOL=OFF' in cache
    evidence['production_flags'] = 'probe OFF; timing OFF'
    evidence['production_executable_bytes'] = (ROOT/'game/build/astra').stat().st_size
    review_sheet(args.folder)
    (args.folder/'character-integration-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS: 32 byte-identical cross-profile pairs; 64 exact full-screen historical delta/mask comparisons; all eight ordinary eyes and ending complete eyes; production OFF')


if __name__ == '__main__':
    main()
