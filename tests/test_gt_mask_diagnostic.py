import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core/scripts'))
from prepare_gt_mask_diagnostic import gt_to_token_grid, common_case_ids, diagnostic_assignments, full_duration_rk2_plan


class DiagnosticTests(unittest.TestCase):
    def test_gt_conversion_is_nearest_then_max_pool(self):
        gt = np.zeros((32, 32), dtype=np.uint8)
        gt[8, 8] = 255
        result = gt_to_token_grid(gt, (32, 32))
        np.testing.assert_array_equal(result, [[1, 0], [0, 0]])
        gt[:] = 0
        gt[24, 24] = 255
        np.testing.assert_array_equal(gt_to_token_grid(gt, (32, 32)), [[0, 0], [0, 1]])

    def test_empty_or_bad_grid_rejected(self):
        with self.assertRaises(ValueError):
            gt_to_token_grid(np.zeros((32, 32)), (32, 32))
        with self.assertRaises(ValueError):
            gt_to_token_grid(np.ones((31, 32)), (31, 32))

    def test_common_cases_require_all_four(self):
        rows = [{'case_uid': case, 'method': method, 'available': not (case == 'b' and method == 'rk2_gt')}
                for case in ['a', 'b'] for method in ['endpoint_auto', 'rk2_auto', 'endpoint_gt', 'rk2_gt']]
        self.assertEqual(common_case_ids(rows), ['a'])
        with self.assertRaises(ValueError):
            common_case_ids(rows + [rows[0]])

    def test_randomization_is_new_and_reproducible(self):
        records = [{'case_uid': 'synth_0000', 'part_size': 'small', 'footprint_change': 'comparable'}]
        a = diagnostic_assignments(records)
        self.assertEqual(a, diagnostic_assignments(records))
        self.assertEqual(len(a), 12)
        self.assertEqual(len({r['review_uid'] for r in a}), 12)
        self.assertTrue(all('gt-diagnostic-v2' in r['row_uid'] for r in a))

    def test_full_duration_changes_only_name_and_interval(self):
        from run_heldout_control_comparison import build_matched_control_plan
        base = build_matched_control_plan('residual_rk2')
        plan = full_duration_rk2_plan()
        self.assertEqual(plan['stages'][0]['start'], 0)
        self.assertEqual(plan['stages'][0]['end'], 14)
        plan['name'] = base['name']
        plan['stages'][0]['end'] = 6
        self.assertEqual(plan, base)


if __name__ == '__main__':
    unittest.main()
