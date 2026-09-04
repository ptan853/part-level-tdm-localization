from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "core" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from prepare_heldout_manual_review import (  # noqa: E402
    SCORE_FIELDS,
    build_blinded_assignments,
    write_review_package,
)
from heldout_review_randomization import build_frozen_randomization  # noqa: E402


class PrepareHeldoutManualReviewTests(unittest.TestCase):
    def fixture(self) -> pd.DataFrame:
        rows = []
        for case_index in range(2):
            for method in ("original_fys_tdm", "endpoint_projection"):
                rows.append(
                    {
                        "row_uid": f"{method}::synth_{case_index:04d}::seed_000",
                        "case_uid": f"synth_{case_index:04d}",
                        "seed": 0,
                        "method": method,
                        "part": "head",
                        "edit": "robot",
                        "part_size": "small",
                        "footprint_change": "comparable",
                        "source_prompt": "an alien",
                        "target_prompt": "an alien with robot head",
                        "source_image": f"source_{case_index}.png",
                        "gt_mask": f"gt_{case_index}.png",
                        "edited_image": f"{method}_{case_index}.jpg",
                    }
                )
        return pd.DataFrame(rows)

    def test_assignments_hide_method_case_and_gt_from_reviewer(self):
        frozen = pd.DataFrame(build_frozen_randomization(self.fixture().to_dict("records")))
        review, mapping = build_blinded_assignments(
            self.fixture(), frozen, reviewer_id="reviewer_1"
        )

        self.assertEqual(len(review), 4)
        self.assertEqual(len(mapping), 4)
        self.assertNotIn("method", review.columns)
        self.assertNotIn("case_uid", review.columns)
        self.assertNotIn("gt_mask", review.columns)
        self.assertTrue({"method", "case_uid", "row_uid"}.issubset(mapping.columns))
        self.assertEqual(review["review_uid"].nunique(), 4)
        for field in SCORE_FIELDS:
            self.assertTrue((review[field] == "").all())

    def test_reviewer_assignments_are_reproducible_but_independently_ordered(self):
        frozen = pd.DataFrame(build_frozen_randomization(self.fixture().to_dict("records")))
        first, _ = build_blinded_assignments(self.fixture(), frozen, "reviewer_1")
        repeated, _ = build_blinded_assignments(self.fixture(), frozen, "reviewer_1")
        second, _ = build_blinded_assignments(self.fixture(), frozen, "reviewer_2")

        self.assertEqual(first["review_uid"].tolist(), repeated["review_uid"].tolist())
        self.assertNotEqual(first["review_uid"].tolist(), second["review_uid"].tolist())

    def test_rejects_randomization_with_unknown_or_missing_rows(self):
        rows = self.fixture()
        frozen = pd.DataFrame(build_frozen_randomization(rows.to_dict("records")))
        frozen.loc[frozen.index[0], "row_uid"] = "unknown"

        with self.assertRaisesRegex(ValueError, "does not match evaluation rows"):
            build_blinded_assignments(rows, frozen, "reviewer_1")

    def test_review_package_uses_frozen_order_and_copies_blinded_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = self.fixture()
            for path in rows["source_image"].tolist() + rows["edited_image"].tolist():
                (root / path).write_bytes(b"image")
            rows["source_image"] = rows["source_image"].map(lambda path: str(root / path))
            rows["edited_image"] = rows["edited_image"].map(lambda path: str(root / path))
            frozen = pd.DataFrame(build_frozen_randomization(rows.to_dict("records")))

            write_review_package(
                rows,
                frozen_randomization=frozen,
                reviewer_id="reviewer_1",
                repo_root=root,
                output_root=root / "review",
            )

            package = root / "review" / "reviewer_1"
            review = pd.read_csv(package / "review_template.csv")
            expected = (
                frozen[frozen["reviewer_id"] == "reviewer_1"]
                .sort_values("review_position")["review_uid"]
                .tolist()
            )
            self.assertEqual(review["review_uid"].tolist(), expected)
            self.assertTrue((package / "review.html").is_file())


if __name__ == "__main__":
    unittest.main()
