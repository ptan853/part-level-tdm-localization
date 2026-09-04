from __future__ import annotations

from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "core" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from heldout_review_randomization import (  # noqa: E402
    REVIEWER_SEEDS,
    build_frozen_randomization,
    validate_frozen_randomization,
)


class HeldoutReviewRandomizationTests(unittest.TestCase):
    def fixture(self) -> list[dict]:
        return [
            {
                "row_uid": f"{method}::synth_{case_index:04d}::seed_000",
                "case_uid": f"synth_{case_index:04d}",
                "seed": 0,
                "method": method,
                "part_size": "small",
                "footprint_change": "comparable",
            }
            for case_index in range(3)
            for method in ("original_fys_tdm", "endpoint_projection")
        ]

    def test_frozen_randomization_is_reproducible_and_complete(self):
        first = build_frozen_randomization(self.fixture())
        repeated = build_frozen_randomization(self.fixture())

        self.assertEqual(first, repeated)
        self.assertEqual(len(first), len(self.fixture()) * len(REVIEWER_SEEDS))
        validate_frozen_randomization(
            first,
            expected_row_uids={row["row_uid"] for row in self.fixture()},
        )

    def test_reviewers_receive_independent_orders_and_opaque_ids(self):
        frozen = build_frozen_randomization(self.fixture())
        orders = {
            reviewer: [
                row["row_uid"]
                for row in frozen
                if row["reviewer_id"] == reviewer
            ]
            for reviewer in REVIEWER_SEEDS
        }

        self.assertNotEqual(orders["reviewer_1"], orders["reviewer_2"])
        self.assertTrue(all(row["review_uid"].startswith("item_") for row in frozen))
        self.assertTrue(all(len(row["review_uid"]) == 17 for row in frozen))

    def test_validation_rejects_missing_assignment(self):
        frozen = build_frozen_randomization(self.fixture())

        with self.assertRaisesRegex(ValueError, "assignment count"):
            validate_frozen_randomization(
                frozen[:-1],
                expected_row_uids={row["row_uid"] for row in self.fixture()},
            )


if __name__ == "__main__":
    unittest.main()
