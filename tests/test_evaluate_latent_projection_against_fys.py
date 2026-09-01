from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from core.scripts.evaluate_latent_projection_against_fys import (
    build_evaluation_rows,
    compute_image_metrics,
    masked_global_ssim,
)


class UnifiedImageMetricsTest(unittest.TestCase):
    def test_masked_metrics_separate_inside_and_outside(self) -> None:
        source = np.zeros((2, 2, 3), dtype=np.float32)
        edited = source.copy()
        edited[0, 0] = 1.0
        gt = np.array([[True, False], [False, False]])

        metrics = compute_image_metrics(source, edited, gt)

        self.assertAlmostEqual(metrics["inside_mask_l1_aux"], 1.0)
        self.assertAlmostEqual(metrics["inside_mask_mse"], 1.0)
        self.assertAlmostEqual(metrics["outside_mask_l1_aux"], 0.0)
        self.assertAlmostEqual(metrics["outside_mask_mse"], 0.0)
        self.assertTrue(np.isinf(metrics["outside_mask_psnr"]))

    def test_identical_selected_pixels_have_unit_global_ssim(self) -> None:
        image = np.array(
            [
                [[0.0, 0.1, 0.2], [0.3, 0.4, 0.5]],
                [[0.6, 0.7, 0.8], [0.9, 1.0, 0.2]],
            ],
            dtype=np.float32,
        )
        mask = np.ones((2, 2), dtype=bool)
        self.assertAlmostEqual(masked_global_ssim(image, image, mask), 1.0, places=6)

    def test_build_rows_collapses_fys_to_seed_zero_and_keeps_all_durations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case_dir = root / "core/data/cases/case_a"
            case_dir.mkdir(parents=True)
            image = np.zeros((4, 4, 3), dtype=np.uint8)
            mask = np.zeros((4, 4), dtype=np.uint8)
            mask[:2, :2] = 255
            Image.fromarray(image).save(case_dir / "source.png")
            Image.fromarray(mask).save(case_dir / "gt.png")

            fys_dir = root / "core/results/fys/case_a/seed_000"
            fys_dir.mkdir(parents=True)
            Image.fromarray(image).save(fys_dir / "img.jpg")

            projection_rows = []
            for duration in (0, 1):
                out = root / f"core/results/projection/duration_{duration:02d}/case_a/img.jpg"
                out.parent.mkdir(parents=True)
                Image.fromarray(image).save(out)
                projection_rows.append(
                    {
                        "case_uid": "case_a",
                        "duration": duration,
                        "generated_image": str(out.relative_to(root)),
                    }
                )

            manifest = [
                {
                    "case_uid": "case_a",
                    "part": "head",
                    "edit": "cat",
                    "part_size": "small",
                    "source_image": str((case_dir / "source.png").relative_to(root)),
                    "gt_mask": str((case_dir / "gt.png").relative_to(root)),
                }
            ]
            fys = pd.DataFrame(
                [
                    {
                        "case_uid": "case_a",
                        "seed": seed,
                        "fys_image": str((fys_dir / "img.jpg").relative_to(root)),
                        "outside_mask_lpips": 0.25,
                    }
                    for seed in (0, 1, 2)
                ]
            )
            projection = pd.DataFrame(projection_rows)

            rows = build_evaluation_rows(root, manifest, fys, projection)

            self.assertEqual(len(rows), 3)
            self.assertEqual((rows["method"] == "original_fys").sum(), 1)
            self.assertEqual(rows.loc[rows["method"] == "latent_projection", "duration"].tolist(), [0, 1])
            self.assertEqual(rows["row_uid"].nunique(), 3)


if __name__ == "__main__":
    unittest.main()
