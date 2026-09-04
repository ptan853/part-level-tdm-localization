from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "core" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from evaluate_heldout_control_comparison import (  # noqa: E402
    build_evaluation_rows,
    compute_localization_metrics,
    dilate_mask_by_token_radius,
    load_protocol_inputs,
    summarize_automatic_metrics,
)


class EvaluateHeldoutControlComparisonTests(unittest.TestCase):
    def test_build_rows_excludes_scout_and_links_shared_mask(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = [
                {
                    "case_uid": "synth_0000",
                    "source_image": "source.png",
                    "gt_mask": "gt.png",
                    "source_prompt": "source prompt",
                    "target_prompt": "target prompt",
                    "part": "head",
                    "edit": "robot",
                    "part_size": "small",
                    "footprint_change": "comparable",
                }
            ]
            roles = [
                "original_fys_tdm",
                "attention_mask_scout",
                "endpoint_projection",
                "residual_rk2",
                "endpoint_projection_n3",
            ]
            matrix = pd.DataFrame(
                [
                    {
                        "role": role,
                        "evaluated": role != "attention_mask_scout",
                        "case_uid": "synth_0000",
                        "seed": 0,
                        "control_mask_path": str(
                            root / "scout" / "hybrid_binary_tdm_attention.npy"
                        )
                        if role != "original_fys_tdm"
                        else "",
                        "run_config": json.dumps({"output_dir": str(root / role)}),
                    }
                    for role in roles
                ]
            )

            rows = build_evaluation_rows(root, manifest, matrix)

        self.assertEqual(len(rows), 4)
        self.assertNotIn("attention_mask_scout", set(rows["method"]))
        self.assertEqual(set(rows["case_uid"]), {"synth_0000"})
        self.assertTrue(rows["edited_image"].str.endswith("img_0.jpg").all())
        self.assertEqual(rows["scout_binary_mask"].nunique(), 1)
        self.assertTrue(
            rows["scout_soft_mask"]
            .str.endswith("hybrid_smoothed_tdm_attention.npy")
            .all()
        )

    def test_localization_metrics_report_iou_ap_and_area_ratio(self):
        gt = np.array([[1, 1], [0, 0]], dtype=bool)
        binary = np.array([[1, 0], [1, 0]], dtype=bool)
        soft = np.array([[0.9, 0.8], [0.7, 0.1]], dtype=np.float32)

        metrics = compute_localization_metrics(soft, binary, gt)

        self.assertAlmostEqual(metrics["mask_iou"], 1 / 3)
        self.assertAlmostEqual(metrics["mask_ap"], 1.0)
        self.assertAlmostEqual(metrics["mask_area_over_gt"], 1.0)

    def test_buffered_region_dilates_by_two_token_cells(self):
        mask = np.zeros((32, 32), dtype=bool)
        mask[16, 16] = True

        buffered = dilate_mask_by_token_radius(mask, token_radius=2, token_grid_size=32)

        self.assertTrue(buffered[16, 18])
        self.assertFalse(buffered[16, 19])
        self.assertGreater(buffered.sum(), mask.sum())

    def test_protocol_inputs_are_evaluated_at_fixed_512_resolution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            edited = root / "edited.png"
            mask = root / "mask.png"
            Image.new("RGB", (1024, 1024), "white").save(source)
            Image.new("RGB", (512, 512), "black").save(edited)
            Image.new("L", (1024, 1024), 255).save(mask)

            source_array, edited_array, mask_array = load_protocol_inputs(
                source, edited, mask
            )

        self.assertEqual(source_array.shape, (512, 512, 3))
        self.assertEqual(edited_array.shape, (512, 512, 3))
        self.assertEqual(mask_array.shape, (512, 512))

    def test_automatic_summary_uses_case_paired_stratified_bootstrap(self):
        rows = []
        for part_size in ("small", "medium", "large"):
            for index in range(2):
                case_uid = f"{part_size}_{index}"
                rows.extend(
                    [
                        {
                            "case_uid": case_uid,
                            "part_size": part_size,
                            "method": "endpoint_projection",
                            "strict_outside_mask_l1_aux": 0.2,
                        },
                        {
                            "case_uid": case_uid,
                            "part_size": part_size,
                            "method": "residual_rk2",
                            "strict_outside_mask_l1_aux": 0.1,
                        },
                    ]
                )
        summary, comparisons = summarize_automatic_metrics(
            pd.DataFrame(rows),
            metric_columns=["strict_outside_mask_l1_aux"],
            iterations=100,
            seed=11,
        )

        self.assertEqual(len(summary), 2)
        selected = comparisons[
            (comparisons["method_a"] == "residual_rk2")
            & (comparisons["method_b"] == "endpoint_projection")
        ].iloc[0]
        self.assertAlmostEqual(selected["difference"], -0.1)
        self.assertAlmostEqual(selected["ci_low"], -0.1)
        self.assertAlmostEqual(selected["ci_high"], -0.1)


if __name__ == "__main__":
    unittest.main()
