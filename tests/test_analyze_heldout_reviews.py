from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "core" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_heldout_reviews import (  # noqa: E402
    add_derived_outcomes,
    evaluate_registered_success,
    paired_stratified_bootstrap,
    weighted_cohen_kappa,
)


class AnalyzeHeldoutReviewsTests(unittest.TestCase):
    def test_weighted_kappa_is_one_for_identical_scores(self):
        scores = np.array([0, 1, 2, 2, 1, 0])
        self.assertAlmostEqual(weighted_cohen_kappa(scores, scores), 1.0)

    def test_derived_joint_outcomes_use_reviewer_level_scores(self):
        frame = pd.DataFrame(
            {
                "local_edit_success_0_2": [1, 2, 2],
                "non_target_preservation_0_2": [1, 1, 2],
            }
        )
        derived = add_derived_outcomes(frame)
        self.assertEqual(derived["joint_success"].tolist(), [1, 1, 1])
        self.assertEqual(derived["strict_joint_success"].tolist(), [0, 0, 1])

    def test_paired_stratified_bootstrap_preserves_case_pairing(self):
        rows = []
        for stratum in ("small", "medium", "large"):
            for index in range(4):
                case_uid = f"{stratum}_{index}"
                for reviewer in ("r1", "r2"):
                    rows.extend(
                        [
                            {
                                "case_uid": case_uid,
                                "part_size": stratum,
                                "reviewer_id": reviewer,
                                "method": "better",
                                "score": 2.0,
                            },
                            {
                                "case_uid": case_uid,
                                "part_size": stratum,
                                "reviewer_id": reviewer,
                                "method": "worse",
                                "score": 1.0,
                            },
                        ]
                    )
        frame = pd.DataFrame(rows)

        result = paired_stratified_bootstrap(
            frame,
            metric="score",
            method_a="better",
            method_b="worse",
            iterations=200,
            seed=7,
        )

        self.assertAlmostEqual(result["difference"], 1.0)
        self.assertAlmostEqual(result["ci_low"], 1.0)
        self.assertAlmostEqual(result["ci_high"], 1.0)

    def test_registered_success_requires_all_three_frozen_criteria(self):
        summary = pd.DataFrame(
            {
                "non_target_preservation_0_2": [0.8, 1.2, 1.6],
                "local_edit_success_0_2": [1.0, 1.2, 1.1],
                "joint_success": [0.50, 0.70, 0.72],
            },
            index=["original_fys_tdm", "endpoint_projection", "residual_rk2"],
        )
        comparisons = pd.DataFrame(
            [
                {"metric": "non_target_preservation_0_2", "method_a": "residual_rk2", "method_b": "original_fys_tdm", "ci_low": 0.5},
                {"metric": "non_target_preservation_0_2", "method_a": "residual_rk2", "method_b": "endpoint_projection", "ci_low": 0.2},
                {"metric": "local_edit_success_0_2", "method_a": "residual_rk2", "method_b": "endpoint_projection", "ci_low": -0.15},
            ]
        )

        result = evaluate_registered_success(summary, comparisons)

        self.assertTrue(result["preservation_superiority"])
        self.assertTrue(result["local_edit_noninferiority"])
        self.assertTrue(result["joint_utility"])
        self.assertTrue(result["all_primary_criteria_met"])
        self.assertEqual(result["stronger_local_edit_baseline"], "endpoint_projection")


if __name__ == "__main__":
    unittest.main()
