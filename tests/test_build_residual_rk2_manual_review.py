from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import subprocess
import sys

import pandas as pd

from core.scripts.build_residual_rk2_manual_review import (
    build_review_rows,
    validate_completed_review,
)


class ResidualRk2ManualReviewTest(unittest.TestCase):
    def test_script_entrypoint_can_show_help(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable,
                str(repo_root / "core/scripts/build_residual_rk2_manual_review.py"),
                "--help",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def metric_rows(self) -> pd.DataFrame:
        rows = []
        for case_uid in ("case_a", "case_b"):
            for duration in range(16):
                rows.append({
                    "row_uid": f"residual_rk2::{case_uid}::N{duration:02d}",
                    "case_uid": case_uid,
                    "duration": duration,
                    "method": "residual_rk2",
                    "part": "head",
                    "edit": "alien",
                    "part_size": "small",
                    "target_prompt": "an alien head",
                    "source_image": "source.png",
                    "gt_mask": "gt.png",
                    "edited_image": f"duration_{duration:02d}.jpg",
                })
        return pd.DataFrame(rows)

    def test_builds_all_unique_case_duration_review_rows(self) -> None:
        rows = build_review_rows(self.metric_rows())

        self.assertEqual(len(rows), 32)
        self.assertEqual(rows["review_uid"].nunique(), 32)
        self.assertEqual(set(rows["duration"]), set(range(16)))
        self.assertTrue((rows["local_edit_success_0_2"] == "").all())
        self.assertTrue((rows["non_target_preservation_0_2"] == "").all())

    def test_preserves_existing_scores_by_review_uid(self) -> None:
        existing = pd.DataFrame([{
            "review_uid": "residual_rk2::case_a::N02",
            "local_edit_success_0_2": 2,
            "non_target_preservation_0_2": 1,
            "short_note": "keep this",
        }])

        rows = build_review_rows(self.metric_rows(), existing)
        selected = rows[rows["review_uid"] == "residual_rk2::case_a::N02"].iloc[0]

        self.assertEqual(str(selected["local_edit_success_0_2"]), "2")
        self.assertEqual(str(selected["non_target_preservation_0_2"]), "1")
        self.assertEqual(selected["short_note"], "keep this")

    def test_completed_review_requires_every_score_to_be_integer_zero_to_two(self) -> None:
        rows = build_review_rows(self.metric_rows())
        rows["local_edit_success_0_2"] = "2"
        rows["non_target_preservation_0_2"] = "1"
        validate_completed_review(rows, expected_count=32)

        rows.loc[0, "local_edit_success_0_2"] = ""
        with self.assertRaisesRegex(ValueError, "incomplete or invalid"):
            validate_completed_review(rows, expected_count=32)


if __name__ == "__main__":
    unittest.main()
