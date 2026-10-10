#!/usr/bin/env python3.12
"""Ordinary all-sector fixed-background/parallax captures, without injection."""
import argparse
import json
from pathlib import Path
import subprocess
from galaxy_oracle import ROOT, Image, indices, palette


def check(folder, level):
    colors = palette(level)
    count = 0
    # Screenshots capture completed scanout, one iteration behind ready telemetry.
    for name, ticks in (("first",10),("second",26)):
        image = Image.load_png(str(folder/(name+".screen.png")))
        expected = indices(level,ticks)
        assert (image.width,image.height) == (320,256)
        bad = []
        for y in range(56,216):
            for x in range(320 if name == "first" else 240):
                # First flight has only hero; second has six enemies at right.
                if 32 <= x <64 and 126 <= y <150:
                    continue
                if image.pixel(x,y) != colors[expected[y-56][x]]:
                    bad.append((x,y))
                count += 1
        assert not bad, f"{folder}/{name}: {len(bad)} wrong pixels, first={bad[:10]}"
    a = Image.load_png(str(folder/"paused.screen.png"))
    b = Image.load_png(str(folder/"paused_late.screen.png"))
    assert all(a.pixel(x,y)==b.pixel(x,y) for y in range(56,216) for x in range(240)
               if not (32<=x<64 and 126<=y<150)), "paused background changed"
    return count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--profile",choices=("a500","a500-aros"),required=True)
    parser.add_argument("--check-only",action="store_true")
    args=parser.parse_args()
    root=args.out/args.profile
    if not args.check_only:
        root.mkdir(parents=True,exist_ok=False)
    results=[]
    for level in range(4):
        folder=root/f"sector{level+1}"
        if not args.check_only:
            fixture=root/f"sector{level+1}.agk"
            lines=['wait-serial "AGK title_ready" 600']
            for _ in range(level):
                lines += ['press right 1','wait 400']
            lines += ['press fire 1','wait-serial "AGK combat_ready" 1000',
                      'wait 10','screenshot first','wait 16','screenshot second',
                      'key 0x19','wait 4','screenshot paused','wait 20',
                      'screenshot paused_late',
                      'expect-no-serial "ERR|STACK SMASHED|allocation failure|bullet_hidden=[1-9]"']
            fixture.write_text('\n'.join(lines)+'\n')
            subprocess.run(['bash','tools/agk','run','--no-build','--fresh','--profile',args.profile,
                            '-f',str(fixture),'-o',str(folder)],cwd=ROOT,check=True)
        results.append({"sector":level+1,"exact_pixels":check(folder,level)})
        print("PASS",args.profile,results[-1])
    if not args.check_only:
        (root/'report.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__ == '__main__':
    main()
