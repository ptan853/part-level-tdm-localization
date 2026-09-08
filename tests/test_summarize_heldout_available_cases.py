from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core/scripts'))
from analyze_heldout_reviews import paired_stratified_bootstrap
from summarize_heldout_available_cases import bootstrap_table


class AvailableCaseBootstrapTests(unittest.TestCase):
    def test_matches_frozen_sampling_with_unequal_strata_and_reviewers(self):
        rng = np.random.default_rng(42)
        rows = []
        for stratum, n in [('small', 4), ('medium', 3), ('large', 4)]:
            for i in range(n):
                for method in ['a', 'b']:
                    for reviewer in ['r1', 'r2']:
                        rows.append(dict(case_uid=f'{stratum}_{i}', part_size=stratum,
                                         method=method, reviewer_id=reviewer,
                                         score=int(rng.integers(0, 3))))
        frame = pd.DataFrame(rows)
        for a, b in [('a', 'b'), ('b', 'a')]:
            actual = bootstrap_table(frame, ['score'], [a, b], iterations=300, seed=9).iloc[0]
            expected = paired_stratified_bootstrap(frame, metric='score', method_a=a,
                                                  method_b=b, iterations=300, seed=9)
            for field in ['difference', 'ci_low', 'ci_high']:
                self.assertAlmostEqual(actual[field], expected[field], places=12)
            self.assertEqual(actual.paired_cases, 11)

    def test_constant_difference_and_invalid_iterations(self):
        frame = pd.DataFrame([dict(case_uid='c', part_size='small', method=m, score=s)
                              for m, s in [('a', 2), ('b', 1)]])
        result = bootstrap_table(frame, ['score'], ['a', 'b'], iterations=20).iloc[0]
        self.assertEqual(result.ci_low, 1)
        self.assertEqual(result.ci_high, 1)
        with self.assertRaises(ValueError):
            bootstrap_table(frame, ['score'], ['a', 'b'], iterations=0)
