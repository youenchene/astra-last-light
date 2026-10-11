import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools'))
from hud_bob_breakdown import HUD, BOB, parse, work_area


class HudBobBreakdownTests(unittest.TestCase):
    def fixture(self, detailed=True):
        chain = [(-1,'start')]+HUD+BOB[1:]+[(-2,'end')]
        stamps = {i:n*10 for n,(i,_) in enumerate(chain)}
        stamps[7],stamps[8] = stamps[36]+2,stamps[36]+4
        executed = set(stamps)-{-1,-2} if detailed else {3,4,5}
        total=stamps[-2]
        lines=[f'galaxy_diag=0 frame=751 lines={total}',
               f'split_frame=751 prefix=2 suffix=3 whole={total+5} report=0',
               f'hb_frame=751 faults=0 ops_valid={int(detailed)}']
        lines += [f'stamp_frame=751 index={i} at={stamps.get(i,0) if i in executed else 0} valid={int(i in executed)}' for i in range(49)]
        lines += [f'hud_op_frame=751 index={i} count={int(i==4 and detailed)}' for i in range(16)]
        lines += [f'bob_op_frame=751 category={i} pushes={6 if i==1 and detailed else 0} unaligned=0' for i in range(7)]
        return '\n'.join(lines)

    def test_disjoint_sums_and_nested_format(self):
        row=parse(self.fixture(),[751])[751]
        self.assertEqual(sum(row['hud'].values()),row['outer']['hud'])
        self.assertEqual(sum(row['bobs'].values()),row['outer']['bobs'])
        self.assertEqual(sum(row['outer'].values()),row['lines'])
        self.assertEqual(sum(row['score_format'].values()),row['hud']['score'])

    def test_light_does_not_present_unexecuted_counters_as_zero_work(self):
        row=parse(self.fixture(False),[751],False)[751]
        self.assertIsNone(row['operations'])
        self.assertIsNone(row['hud'])

    def test_rejects_unexecuted_stamp_bad_inventory_and_fault(self):
        text=self.fixture()
        for changed in (text.replace('valid=1','valid=0',1),
                        text.replace('index=48','index=49'),
                        text.replace('faults=0','faults=1'),
                        text+'\nhud_op_frame=751 index=4 count=1',
                        text.replace('category=6','category=7')):
            with self.assertRaises(ValueError): parse(changed,[751])

    def test_source_word_areas_keep_save_and_masked_alignment_distinct(self):
        aligned=work_area(1,6,0)
        shifted=work_area(1,6,6)
        self.assertEqual(aligned['save_word_area'],768)
        self.assertEqual(aligned['masked_word_area'],384)
        self.assertEqual(shifted['masked_word_area'],768)
        with self.assertRaises(ValueError): work_area(1,7,0)
        with self.assertRaises(ValueError): work_area(1,1,2)
