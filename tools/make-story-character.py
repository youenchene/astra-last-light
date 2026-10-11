#!/usr/bin/env python3
"""Phase-one offline character retouch and pixel-exact review evidence."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any, cast

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'game/art/selected-rd'
OUTPUT = SOURCE / 'story-character'
NAMES = ('graveyard-b', 'nebula-b', 'foundry-b', 'citadel-b', 'victory')
CROPS = ((0, 30, 56, 96), (0, 0, 56, 70), (0, 28, 57, 96),
         (0, 28, 67, 96), (45, 55, 153, 192))


def parent(name):
    return SOURCE / ('victory-eyes-almond' if name == 'victory' else 'story-eyes') / f'{name}.png'


def png(image):
    stream = io.BytesIO()
    image.save(stream, format='PNG')
    return stream.getvalue()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == data, f'Refusing differing overwrite: {path}'
    else:
        path.write_bytes(data)


def inspect():
    for name, box in zip(NAMES, CROPS):
        image = Image.open(parent(name)).convert('RGB')
        scale = 10 if name != 'victory' else 5
        crop = image.crop(box).resize(((box[2]-box[0])*scale, (box[3]-box[1])*scale), Image.Resampling.NEAREST)
        sheet = Image.new('RGB', (crop.width+40, crop.height+40), '#303030')
        sheet.paste(crop, (40, 40))
        draw = ImageDraw.Draw(sheet)
        for x in range(box[0], box[2], 5):
            draw.text((40+(x-box[0])*scale, 24), str(x), fill='white')
        for y in range(box[1], box[3], 5):
            draw.text((5, 40+(y-box[1])*scale), str(y), fill='white')
        draw.text((4, 4), name + ' CURRENT PARENT / source coordinates', fill='white')
        save(OUTPUT / 'inspection' / f'{name}-parent.png', png(sheet))
        ranges = {'graveyard-b':(16,56,41,64), 'nebula-b':(19,29,45,35),
                  'foundry-b':(19,60,45,68), 'citadel-b':(22,58,52,66)}
        if name in ranges:
            x0,y0,x1,y1 = ranges[name]
            text = 'Parent nearest-base ink grid (hex index); x=' + ','.join(str(x) for x in range(x0,x1))+'\n'
            text += '\n'.join(f'{y}: ' + ' '.join(f'{nearest(image.getpixel((x,y)),colors()):X}' for x in range(x0,x1)) for y in range(y0,y1))
            save(OUTPUT/'inspection'/f'{name}-cheek-inks.txt', (text+'\n').encode())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def colors():
    words = re.findall(r'^\d+\s+0x([0-9A-Fa-f]{3})\b',
                       (ROOT / 'game/art/palette.txt').read_text(), re.M)
    return [tuple(int(c, 16)*17 for c in word) for word in words]


def nearest(rgb, palette):
    return min(range(16), key=lambda i: sum((a-b)**2 for a, b in zip(rgb, palette[i])))


def displayed(image, index, palette):
    live = list(palette)
    live[0] = ((0,0,17), (17,0,34), (17,0,17), (0,0,17), (0,0,0))[index]
    live[4] = (187,221,255)
    if index == 4:
        live[11] = (255,170,153)
    quantize = live if index == 4 else palette
    mapping = {rgb: live[nearest(rgb, quantize)] for rgb in set(image.getdata())}
    result = Image.new('RGB', image.size)
    result.putdata([mapping[rgb] for rgb in image.getdata()])
    return result


def shape_mask(size, shape):
    mask = Image.new('L', size)
    draw = ImageDraw.Draw(mask)
    if 'polygon' in shape:
        draw.polygon([tuple(p) for p in shape['polygon']], fill=255)
    else:
        draw.line([tuple(p) for p in shape['line']], fill=255)
    return mask


def points(mask):
    return [(x,y) for y in range(mask.height) for x in range(mask.width) if mask.getpixel((x,y))]


def edit(before, spec, palette):
    after = before.copy()
    armor, cheek, eyes = (Image.new('L', before.size) for _ in range(3))
    for x0,y0,x1,y1 in spec['eye_boxes']:
        ImageDraw.Draw(eyes).rectangle((x0,y0,x1-1,y1-1), fill=255)
    for polygon in spec['armor']:
        mask = shape_mask(before.size, {'polygon':polygon})
        for p in points(mask):
            armor.putpixel(p, 255)
            ink = str(nearest(before.getpixel(p), palette))
            if ink in spec['recolor']:
                after.putpixel(p, palette[spec['recolor'][ink]])
    for detail in spec['details']:
        for p in points(shape_mask(before.size, detail)):
            armor.putpixel(p, 255)
            after.putpixel(p, palette[detail['ink']])
    for cleanup in spec['cleanup']:
        for p in points(shape_mask(before.size, cleanup)):
            cheek.putpixel(p, 255)
            if nearest(before.getpixel(p), palette) in cleanup['inks']:
                after.putpixel(p, before.getpixel(tuple(cleanup['sample'])))
    for point in spec['mark']:
        p = tuple(point)
        cheek.putpixel(p, 255)
        after.putpixel(p, palette[13])
    return after, armor, cheek, eyes


def verify(before, after, spec, masks, palette, index) -> tuple[dict[str, Any], list]:
    armor, cheek, eyes = masks
    assert before.size == after.size == ((320,192) if index == 4 else (160,96))
    changes = []
    for y in range(before.height):
        for x in range(before.width):
            p = (x,y)
            a,b = before.getpixel(p), after.getpixel(p)
            assert not (eyes.getpixel(p) and (armor.getpixel(p) or cheek.getpixel(p))), (spec['name'], p)
            if a != b:
                assert armor.getpixel(p) or cheek.getpixel(p), p
                changes.append(dict(x=x,y=y,before=a,after=b,region='armor' if armor.getpixel(p) else 'cheek'))
    x0,y0,x1,y1 = spec['cheek_box']
    for x,y in spec['mark']:
        assert x0 <= x < x1 and y0 <= y < y1
        assert after.getpixel((x,y)) == palette[13]
        assert nearest(before.getpixel((x,y)), palette) in (11,13,14,15), 'Mark must stay on skin/old cheek paint'
    assert all((b[0]-a[0],b[1]-a[1]) == (-1,1) for a,b in zip(spec['mark'],spec['mark'][1:]))
    if index == 4:
        assert not points(armor)
        assert len(changes) == 5
    else:
        for detail in spec['details']:
            assert any(after.getpixel(p) == palette[detail['ink']]
                       for p in points(shape_mask(before.size,detail))), detail['role']
    shown = [displayed(im,index,palette) for im in (before,after)]
    return dict(name=spec['name'], changed_pixels=len(changes),
                armor_changed=sum(c['region']=='armor' for c in changes),
                cheek_changed=sum(c['region']=='cheek' for c in changes),
                displayed_changed=sum(a!=b for a,b in zip(shown[0].getdata(),shown[1].getdata())),
                protected_eye_pixels=len(points(eyes)), eye_changes=0, outside_mask_changes=0,
                changes=changes), shown


def detail_preview(pair, box, name, mode):
    scale = 8 if name != 'victory' else 4
    w,h = (box[2]-box[0])*scale, (box[3]-box[1])*scale
    sheet = Image.new('RGB',(2*w+24,h+28),'#303030')
    draw = ImageDraw.Draw(sheet)
    for i,image in enumerate(pair):
        draw.text((8+i*(w+8),5), f'{name} {mode} / {"BEFORE" if i==0 else "AFTER"}', fill='white')
        sheet.paste(image.crop(box).resize((w,h),Image.Resampling.NEAREST),(8+i*(w+8),24))
    return sheet


def montage(pairs, native):
    widths = [160]*4+[320] if native else [320]*5
    height = 192
    sheet = Image.new('RGB',(sum(widths)+8*6,2*(height+32)),'#303030')
    draw = ImageDraw.Draw(sheet)
    x=8
    for name,pair,w in zip(NAMES,pairs,widths):
        for row,image in enumerate(pair):
            y=row*(height+32)
            draw.text((x,y+4),name+' / '+('BEFORE' if row==0 else 'AFTER'),fill='white')
            size=(w, image.height*w//image.width)
            sheet.paste(image.resize(size,Image.Resampling.NEAREST),(x,y+24))
        x+=w+8
    return sheet


def protected_hashes():
    files = [p for p in SOURCE.rglob('*') if p.is_file() and OUTPUT not in p.parents]
    files.append(ROOT/'game/art/palette.txt')
    return {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(files)}


def generate():
    protected = protected_hashes()
    baseline_path = OUTPUT/'protected-sha256.json'
    if baseline_path.exists():
        assert json.loads(baseline_path.read_text()) == protected, 'Historical asset hashes changed'
    recipe_bytes = (OUTPUT/'recipe.json').read_bytes()
    recipe = json.loads(recipe_bytes)
    palette = colors()
    outputs, records, source_pairs, shown_pairs = {}, [], [], []
    for index,spec in enumerate(recipe['panels']):
        name = spec['name']
        assert name == NAMES[index]
        before = Image.open(parent(name)).convert('RGB')
        after,*masks = edit(before,spec,palette)
        record,shown = verify(before,after,spec,masks,palette,index)
        record.update(parent=str(parent(name).relative_to(ROOT)), parent_sha256=sha(parent(name).read_bytes()))
        records.append(record)
        source_pairs.append((before,after))
        shown_pairs.append(shown)
        outputs[f'{name}.png'] = png(after)
        outputs[f'{name}.rgb.hex'] = (after.tobytes().hex()+'\n').encode()
        outputs[f'{name}.displayed.png'] = png(shown[1])
        for kind,mask in zip(('armor','cheek','protected-eyes'),masks):
            outputs[f'masks/{name}-{kind}.png'] = png(mask)
        for mode,pair in (('source',(before,after)),('ocs',shown)):
            outputs[f'previews/{name}-{mode}-detail.png'] = png(detail_preview(pair,CROPS[index],name,mode))
        overlay = after.copy()
        for mask,color in zip(masks,((0,255,128),(255,128,0),(255,0,255))):
            for p in points(mask):
                rgb = cast(tuple[int, int, int], after.getpixel(p))
                overlay.putpixel(p,tuple((a+b)//2 for a,b in zip(rgb,color)))
        outputs[f'previews/{name}-masks.png'] = png(detail_preview((before,overlay),CROPS[index],name,'MASKS'))
    for mode,pairs in (('source',source_pairs),('ocs',shown_pairs)):
        for native in (True,False):
            outputs[f'previews/five-panels-{mode}-{"native" if native else "2x"}.png'] = png(montage(pairs,native))
    provenance = dict(status='phase1 candidate; pending parent visual approval; not integrated',cost_usd=0,
                      method='Offline palette-aware localized armor retouch, hand-authored collar segments and literal cheek pixels',
                      recipe_sha256=sha(recipe_bytes),script_sha256=sha(Path(__file__).read_bytes()),
                      historical_files_verified=len(protected),panels=records,
                      output_sha256={name:sha(data) for name,data in outputs.items()})
    outputs['provenance.json'] = (json.dumps(provenance,indent=2)+'\n').encode()
    outputs['protected-sha256.json'] = (json.dumps(protected,indent=2)+'\n').encode()
    assert protected_hashes() == protected
    return outputs,records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--check', action='store_true', help='Recompute every output and verify frozen historical hashes without writes')
    parser.add_argument('--draft', metavar='DIRECTORY', help='Write a separately named review iteration')
    args = parser.parse_args()
    if args.inspect:
        inspect()
    else:
        outputs,records = generate()
        for name,data in outputs.items():
            path = OUTPUT / (args.draft or '') / name
            if args.check:
                assert path.read_bytes() == data, f'Stale artifact: {path}'
            else:
                save(path,data)
        for r in records:
            print(f"{r['name']}: {r['changed_pixels']} RGB / {r['displayed_changed']} OCS; armor {r['armor_changed']}, cheek {r['cheek_changed']}; eye/outside changes 0")
        print('PASS: complete eye boxes, explicit masks, cheek side/diagonal, ending armor, historical hashes and reproducibility')
