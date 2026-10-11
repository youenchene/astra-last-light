"""Approved character layer: exact parent deltas, complete eyes and provenance."""
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

ART = ROOT / 'game/art/selected-rd'
LAYER = ART / 'story-character'
NAMES = ('graveyard-b', 'nebula-b', 'foundry-b', 'citadel-b', 'victory')
EYES = (((17,46,31,57),(32,48,41,57)), ((19,17,35,29),(35,19,45,29)),
        ((19,48,34,60),(34,50,44,60)), ((24,43,42,58),(42,48,52,58)),
        ((64,63,94,88),(106,65,134,88)))
MARKS = (((36,57),(35,58)), ((40,30),(39,31),(38,32)), ((38,60),(37,61)),
         ((49,60),(48,61),(47,62)), ((127,92),(126,93),(125,94),(124,95),(123,96)))


class StoryCharacterTests(unittest.TestCase):
    def tearDown(self):
        selected_rd_oracle.original_panels.cache_clear()

    def test_exact_masks_deltas_complete_eyes_and_ending_only_five_pixels(self):
        for index,name in enumerate(NAMES):
            parent = ART / ('story-eyes' if index < 4 else 'victory-eyes-almond') / f'{name}.png'
            width,height,before = load_png_rgba(parent)
            w,h,after = load_png_rgba(LAYER / f'{name}.png')
            self.assertEqual((w,h),(width,height))
            armor,cheek,eyes = [load_png_rgba(LAYER / 'masks' / f'{name}-{kind}.png')[2]
                                for kind in ('armor','cheek','protected-eyes')]
            changes,armor_changes = set(),set()
            for i,(a,b) in enumerate(zip(before,after)):
                x,y = i%width,i//width
                protected = any(x0<=x<x1 and y0<=y<y1 for x0,y0,x1,y1 in EYES[index])
                self.assertEqual(bool(eyes[i][0]),protected)
                if protected:
                    self.assertEqual(a,b,(name,x,y))
                    self.assertEqual((armor[i][0],cheek[i][0]),(0,0))
                if a != b:
                    changes.add((x,y))
                    self.assertTrue(armor[i][0] or cheek[i][0],(name,x,y))
                    if armor[i][0]:
                        armor_changes.add((x,y))
            self.assertEqual(len(changes),(441,560,586,685,5)[index])
            self.assertEqual(len(armor_changes),(429,551,562,655,0)[index])
            for x,y in MARKS[index]:
                self.assertEqual(after[y*width+x],(170,68,51,255))
            if index == 4:
                self.assertEqual(changes,set(MARKS[4]))

    def test_historical_character_quantizers_have_only_approved_displayed_deltas(self):
        for reader in (selected_rd.panels,selected_rd_oracle.original_panels):
            historical,current = reader(layer='story-eyes'),reader(layer='story-character')
            for index,(before,after) in enumerate(zip(historical,current)):
                changes = {(x,y) for y,row in enumerate(before) for x,ink in enumerate(row) if ink != after[y][x]}
                self.assertEqual(len(changes),(441,560,585,685,5)[index])
                for x0,y0,x1,y1 in EYES[index]:
                    self.assertFalse(any((x,y) in changes for y in range(y0,y1) for x in range(x0,x1)))
                if index == 4:
                    self.assertEqual(changes,set(MARKS[4]))
                    for y,row in enumerate(after):
                        for x,ink in enumerate(row):
                            if x<2 or x>=318 or y<2 or y>=190:
                                self.assertEqual(ink,7)

    def test_both_readers_reject_new_layer_provenance_corruption(self):
        path = LAYER / 'provenance.json'
        read_text = Path.read_text
        for index,name in enumerate(NAMES):
            for field in ('parent_sha256','output','delta'):
                data = json.loads(read_text(path))
                if field == 'output':
                    data['output_sha256'][name+'.png'] = '0'*64
                elif field == 'delta':
                    data['panels'][index]['changes'][0]['before'][0] ^= 1
                else:
                    data['panels'][index][field] = '0'*64
                def read(candidate,*args,**kwargs):
                    return json.dumps(data) if candidate == path else read_text(candidate,*args,**kwargs)
                for reader in (selected_rd.panels,selected_rd_oracle.original_panels):
                    with self.subTest(index=index,field=field,reader=reader.__module__):
                        selected_rd_oracle.original_panels.cache_clear()
                        with patch.object(Path,'read_text',read),self.assertRaises(AssertionError):
                            reader(layer='story-character')

    def test_importer_rejects_new_layer_rgb_corruption(self):
        read_bytes = Path.read_bytes
        for name in NAMES:
            path = LAYER / f'{name}.rgb.hex'
            changed = bytearray.fromhex(read_bytes(path).decode())
            changed[0] ^= 1
            def read(candidate):
                return (changed.hex()+'\n').encode() if candidate == path else read_bytes(candidate)
            with patch.object(Path,'read_bytes',read),self.assertRaises(AssertionError):
                selected_rd.panels(layer='story-character')
