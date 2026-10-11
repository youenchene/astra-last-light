"""Approved bold layer: independent footprints, historical isolation and corruption guards."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'game/tools'))
sys.path.insert(0, str(ROOT / 'tools'))
import selected_rd
import selected_rd_oracle
from agk.image import load_png_rgba
from test_story_character import EYES, MARKS as OLD_MARKS, NAMES

PARENT = ROOT / 'game/art/selected-rd/story-character'
LAYER = PARENT / 'bold-marks'
MARKS = (
    {(36,57),(35,58),(36,58),(35,59)},
    {(40,30),(38,31),(39,31),(40,31),(38,32)},
    {(38,60),(37,61),(38,61),(37,62)},
    {(49,60),(47,61),(48,61),(49,61),(47,62)},
    {(127,92),(125,93),(126,93),(127,93),(124,94),(125,94),(126,94),
     (123,95),(124,95),(125,95),(123,96),(124,96),(123,97)},
)


class StoryBoldMarksTests(unittest.TestCase):
    def tearDown(self):
        selected_rd_oracle.original_panels.cache_clear()

    def test_exact_sixteen_additions_and_all_unmasked_pixels_unchanged(self):
        total, eye_count = 0, 0
        for index, name in enumerate(NAMES):
            w,h,before = load_png_rgba(PARENT / f'{name}.png')
            width,height,after = load_png_rgba(LAYER / f'{name}.png')
            self.assertEqual((width,height), (w,h))
            masks = [load_png_rgba(LAYER/'masks'/f'{name}-{kind}.png')[2]
                     for kind in ('footprint','additions')]
            changes = set()
            for i,(a,b) in enumerate(zip(before,after)):
                p = (i%w,i//w)
                self.assertEqual(masks[0][i][0], 255 if p in MARKS[index] else 0)
                self.assertEqual(masks[1][i][0], 255 if p in MARKS[index]-set(OLD_MARKS[index]) else 0)
                if p in MARKS[index]:
                    self.assertEqual(b, (170,68,51,255))
                if a != b:
                    changes.add(p)
                if any(x0<=p[0]<x1 and y0<=p[1]<y1 for x0,y0,x1,y1 in EYES[index]):
                    self.assertEqual(a,b)
                    self.assertNotIn(p,MARKS[index])
                    eye_count += 1
            self.assertEqual(changes, MARKS[index]-set(OLD_MARKS[index]))
            self.assertEqual(len(changes), (2,2,2,2,8)[index])
            total += len(changes)
        self.assertEqual(total,16)
        self.assertEqual(eye_count,2571)

    def test_connected_tapered_same_cheek_footprints(self):
        for index, mark in enumerate(MARKS):
            self.assertTrue(set(OLD_MARKS[index]) <= mark)
            reached = {min(mark)}
            while True:
                neighbors = {p for p in mark if any(abs(p[0]-q[0])+abs(p[1]-q[1])==1 for q in reached)}
                if neighbors <= reached:
                    break
                reached |= neighbors
            self.assertEqual(reached,mark)
            rows = [sorted(x for x,y in mark if y==row) for row in sorted({y for _,y in mark})]
            self.assertEqual(tuple(len(row) for row in rows),
                             ((1,2,1),(1,3,1),(1,2,1),(1,3,1),(1,3,3,3,2,1))[index])
            for first, second in zip(rows, rows[1:]):
                self.assertLessEqual(second[0],first[0])
                self.assertLessEqual(second[-1],first[-1])

    def test_defaults_select_bold_with_exact_parent_displayed_deltas(self):
        for reader in (selected_rd.panels, selected_rd_oracle.original_panels):
            parent = reader(layer='story-character')
            current = reader(layer='bold-marks')
            self.assertEqual(reader(),current)
            total = 0
            for index,(before,after) in enumerate(zip(parent,current)):
                changes = {(x,y) for y,row in enumerate(before) for x,ink in enumerate(row)
                           if ink != after[y][x]}
                self.assertEqual(changes,MARKS[index]-set(OLD_MARKS[index]))
                self.assertEqual(len(changes),8 if index==4 else 2)
                total += len(changes)
            self.assertEqual(total,16)

    def test_approved_phase_one_image_bytes_and_immutable_protection_retained(self):
        approved = json.loads((LAYER/'phase1-evidence/provenance.json').read_text())
        for name, digest in approved['output_sha256'].items():
            self.assertEqual(hashlib.sha256((LAYER/name).read_bytes()).hexdigest(),digest,name)
        protected = json.loads((LAYER/'protected-sha256.json').read_text())
        for name, digest in protected.items():
            self.assertTrue(name.startswith('game/art/selected-rd/') or name=='game/art/palette.txt')
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)

    def test_both_readers_reject_bold_provenance_corruption(self):
        path = LAYER/'provenance.json'
        read_text = Path.read_text
        for index,name in enumerate(NAMES):
            for field in ('parent_sha256','parent_recipe_sha256','output','before','after','duplicate','count'):
                data = json.loads(read_text(path))
                entry = data['panels'][index]
                if field == 'output':
                    data['output_sha256'][name+'.png'] = '0'*64
                elif field == 'parent_recipe_sha256':
                    data[field] = '0'*64
                elif field in ('before','after'):
                    entry['changes'][0][field][0] ^= 1
                elif field == 'duplicate':
                    entry['changes'].append(entry['changes'][0])
                elif field == 'count':
                    entry['changed_pixels'] += 1
                else:
                    entry[field] = '0'*64
                def read(candidate,*args,**kwargs):
                    return json.dumps(data) if candidate==path else read_text(candidate,*args,**kwargs)
                for reader in (selected_rd.panels,selected_rd_oracle.original_panels):
                    with self.subTest(index=index,field=field,reader=reader.__module__):
                        selected_rd_oracle.original_panels.cache_clear()
                        with patch.object(Path,'read_text',read),self.assertRaises(AssertionError):
                            reader(layer='bold-marks')

    def test_importer_rejects_bold_rgb_corruption(self):
        read_bytes = Path.read_bytes
        for name in NAMES:
            path = LAYER/f'{name}.rgb.hex'
            data = bytearray.fromhex(read_bytes(path).decode())
            data[0] ^= 1
            def read(candidate):
                return (data.hex()+'\n').encode() if candidate==path else read_bytes(candidate)
            with patch.object(Path,'read_bytes',read),self.assertRaises(AssertionError):
                selected_rd.panels(layer='bold-marks')
