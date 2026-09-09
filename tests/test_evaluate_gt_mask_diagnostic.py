import sys
import unittest
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core/scripts'))
from evaluate_gt_mask_diagnostic import comparison_sets, filtered_randomization, METHODS


class DiagnosticEvaluationTests(unittest.TestCase):
    def test_supplement_missing_does_not_shrink_primary(self):
        rows = pd.DataFrame([{'case_uid': c, 'method': m, 'available': not (c == 'b' and m == 'rk2_n15_gt')}
                             for c in ['a', 'b'] for m in METHODS])
        self.assertEqual(comparison_sets(rows), (['a', 'b'], ['a']))

    def test_filter_preserves_ids_and_order(self):
        source = pd.DataFrame([{'reviewer_id': r, 'row_uid': str(i), 'review_uid': r+str(i), 'review_position': i}
                               for r in ['reviewer_1', 'reviewer_2'] for i in [1, 2, 3]])
        result = filtered_randomization(source, {'1', '3'})
        self.assertEqual(result['review_uid'].tolist(), ['reviewer_11', 'reviewer_13', 'reviewer_21', 'reviewer_23'])
        self.assertEqual(result['review_position'].tolist(), [1, 2, 1, 2])
        self.assertEqual(result['frozen_review_position'].tolist(), [1, 3, 1, 3])
