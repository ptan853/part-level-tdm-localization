import unittest

import pandas as pd

from core.scripts.analyze_gt_diagnostic_single_reviewer import METHODS, paired_intervals


class SingleReviewerBootstrapTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame([
            dict(case_uid=str(i), part_size=size, method=method,
                 score=int(method.endswith('gt')))
            for i, size in enumerate(['small', 'medium', 'large'])
            for method in METHODS
        ])

    def test_constant_difference_and_identical_controllers(self):
        result = paired_intervals(self.frame(), ['score'], draws=100).set_index('contrast')
        for column in ['difference', 'ci_low', 'ci_high']:
            self.assertEqual(result.loc['Endpoint GT - auto', column], 1)
            self.assertEqual(result.loc['RK2 - Endpoint (GT)', column], 0)
            self.assertEqual(result.loc['Mask-by-controller interaction', column], 0)

    def test_seed_is_reproducible(self):
        frame = self.frame()
        frame.loc[0, 'score'] = 2
        pd.testing.assert_frame_equal(
            paired_intervals(frame, ['score'], draws=100),
            paired_intervals(frame, ['score'], draws=100),
        )

    def test_missing_paired_condition_is_rejected(self):
        with self.assertRaises(AssertionError):
            paired_intervals(self.frame().iloc[1:], ['score'], draws=100)


if __name__ == '__main__':
    unittest.main()
