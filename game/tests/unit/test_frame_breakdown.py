import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
from frame_breakdown import CHAIN, LOGIC, partition, parse


class FrameBreakdownTests(unittest.TestCase):
    def fixture(self):
        stamps = {i: n * 10 for n, (i, _) in enumerate(CHAIN)}
        for n, (i, _) in enumerate(LOGIC[1:-1], 1):
            stamps[i] = stamps[14] + n
        stamps[7], stamps[8] = stamps[3] + 1, stamps[3] + 2
        total = stamps[-2]
        text = f'galaxy_diag=0 frame=751 lines={total}\n'
        text += f'split_frame=751 prefix=7 suffix=11 whole={total+18} report=0\n'
        text += '\n'.join(f'stamp_frame=751 index={i} at={v}' for i,v in stamps.items() if i >= 0)
        return text

    def test_exact_sum_with_nested_intervals_and_external_meter(self):
        row = parse(self.fixture(), [751])[751]
        self.assertEqual(sum(row['segments'].values()), row['lines'])
        self.assertEqual(sum(row['nested_logic'].values()), row['segments']['logic'])

    def test_rejects_duplicate_and_backward_boundaries(self):
        with self.assertRaises(ValueError):
            partition({1: 0, 2: 1}, [(1,'a'), (2,'b'), (1,'c')])
        with self.assertRaises(ValueError):
            partition({1: 2, 2: 1}, [(1,'a'), (2,'b')])

    def test_rejects_missing_frame_duplicate_stamp_and_wrong_meter(self):
        for text, frames in [(self.fixture(), [751,2817]),
                             (self.fixture()+'\nstamp_frame=751 index=9 at=10', [751]),
                             (self.fixture().replace('prefix=7', 'prefix=8'), [751])]:
            with self.assertRaises(ValueError):
                parse(text, frames)
