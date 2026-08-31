from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import unittest

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"
sys.path.insert(0, str(FYS_SRC))

from flux.latent_control import (  # noqa: E402
    LatentProjectionMetrics,
    project_source_outside,
)


class LatentControlTests(unittest.TestCase):
    def test_all_zero_mask_returns_source_and_reports_outside_error(self):
        target = torch.tensor([[[1.0, 2.0], [3.0, 4.0]]])
        source = torch.tensor([[[10.0, 20.0], [30.0, 40.0]]])

        actual, metrics = project_source_outside(target, source, np.zeros(2, dtype=np.float32))

        torch.testing.assert_close(actual, source)
        self.assertEqual(metrics.mask_area_ratio, 0.0)
        self.assertEqual(metrics.outside_mae_before, 22.5)
        self.assertEqual(metrics.outside_mae_after, 0.0)

    def test_all_one_mask_returns_target_and_has_no_outside_error(self):
        target = torch.tensor([[[1.0, 2.0], [3.0, 4.0]]])
        source = torch.tensor([[[10.0, 20.0], [30.0, 40.0]]])

        actual, metrics = project_source_outside(target, source, torch.ones(2))

        torch.testing.assert_close(actual, target)
        self.assertEqual(metrics.mask_area_ratio, 1.0)
        self.assertEqual(metrics.outside_mae_before, 0.0)
        self.assertEqual(metrics.outside_mae_after, 0.0)

    def test_mixed_mask_projects_only_masked_tokens(self):
        target = torch.tensor([[[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]])
        source = torch.tensor([[[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]]])
        mask = torch.tensor([1.0, 0.0, 1.0])

        actual, metrics = project_source_outside(target, source, mask)

        expected = torch.tensor([[[1.0, 2.0], [30.0, 40.0], [5.0, 6.0]]])
        torch.testing.assert_close(actual, expected)
        self.assertAlmostEqual(metrics.mask_area_ratio, 2.0 / 3.0)
        self.assertEqual(metrics.outside_mae_before, 31.5)
        self.assertEqual(metrics.outside_mae_after, 0.0)

    def test_projection_does_not_mutate_inputs(self):
        target = torch.tensor([[[1.0, 2.0], [3.0, 4.0]]])
        source = torch.tensor([[[10.0, 20.0], [30.0, 40.0]]])
        target_before = target.clone()
        source_before = source.clone()

        actual, _ = project_source_outside(target, source, torch.tensor([1.0, 0.0]))

        torch.testing.assert_close(target, target_before)
        torch.testing.assert_close(source, source_before)
        self.assertIsNot(actual, target)
        self.assertIsNot(actual, source)

    def test_metrics_are_immutable(self):
        _, metrics = project_source_outside(
            torch.zeros(1, 1, 1), torch.ones(1, 1, 1), torch.zeros(1)
        )

        with self.assertRaises(FrozenInstanceError):
            metrics.mask_area_ratio = 1.0

    def test_shape_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "target and source latent shapes must match"):
            project_source_outside(
                torch.zeros(1, 2, 3), torch.zeros(1, 2, 4), torch.zeros(2)
            )

    def test_non_three_dimensional_latents_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "latents must have shape"):
            project_source_outside(torch.zeros(2, 3), torch.zeros(2, 3), torch.zeros(3))

    def test_mask_length_must_match_image_token_count(self):
        with self.assertRaisesRegex(ValueError, "spatial mask length must match image token count"):
            project_source_outside(
                torch.zeros(1, 2, 3), torch.zeros(1, 2, 3), torch.zeros(3)
            )

    def test_mask_values_must_be_between_zero_and_one(self):
        with self.assertRaisesRegex(ValueError, "spatial mask values must be in \[0, 1\]"):
            project_source_outside(
                torch.zeros(1, 2, 3), torch.zeros(1, 2, 3), torch.tensor([0.0, 1.1])
            )


if __name__ == "__main__":
    unittest.main()
