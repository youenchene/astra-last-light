#!/usr/bin/env python3.12
"""Read-only diagnosis of a failed complete-frame comparison; never updates goldens."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('baseline', type=Path)
parser.add_argument('candidate', type=Path)
parser.add_argument('--out', required=True, type=Path)
args = parser.parse_args()
spec = importlib.util.spec_from_file_location('cards', ROOT/'tools/verify-precomputed-cards.py')
cards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cards)
a, b = [cards.Image.load_png(p) for p in (args.baseline, args.candidate)]
diff = [{'x':x, 'y':y, 'before':a.pixel(x,y), 'after':b.pixel(x,y)}
        for y in range(256) for x in range(320) if a.pixel(x,y) != b.pixel(x,y)]
report = {'baseline':str(args.baseline), 'candidate':str(args.candidate),
          'differing_pixels':len(diff), 'pixels':diff}
if diff:
    report['bounds'] = [min(p['x'] for p in diff), min(p['y'] for p in diff),
                        max(p['x'] for p in diff), max(p['y'] for p in diff)]
    report['per_row'] = {y:sum(p['y'] == y for p in diff) for y in sorted({p['y'] for p in diff})}
args.out.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k != 'pixels'}, indent=2))
