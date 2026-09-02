from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd
from PIL import Image

from core.scripts.build_control_operation_comparison import (
    build_comparison_rows,
    render_comparison_sheets,
)


class ControlOperationComparisonTest(unittest.TestCase):
    def _metrics(self) -> pd.DataFrame:
        rows = []
        for case_uid in ("case_b", "case_a"):
            common = {
                "case_uid": case_uid,
                "part": "head",
                "edit": "cat",
                "part_size": "small",
                "target_prompt": f"target for {case_uid}",
                "source_image": f"data/{case_uid}/source.png",
                "gt_mask": f"data/{case_uid}/mask.png",
            }
            rows.extend(
                [
                    {
                        **common,
                        "method": "residual_rk2",
                        "duration": 15,
                        "edited_image": f"results/{case_uid}/residual.jpg",
                    },
                    {
                        **common,
                        "method": "latent_projection",
                        "duration": 3,
                        "edited_image": f"results/{case_uid}/endpoint.jpg",
                    },
                    {
                        **common,
                        "method": "original_fys",
                        "duration": None,
                        "edited_image": f"results/{case_uid}/fys.jpg",
                    },
                    {
                        **common,
                        "method": "residual_rk2",
                        "duration": 6,
                        "edited_image": f"results/{case_uid}/unused.jpg",
                    },
                ]
            )
        return pd.DataFrame(rows).sample(frac=1, random_state=4).reset_index(drop=True)

    def test_build_rows_aligns_methods_by_case_uid(self) -> None:
        rows = build_comparison_rows(self._metrics(), ["case_a", "case_b"])

        self.assertEqual(rows["case_uid"].tolist(), ["case_a", "case_b"])
        self.assertEqual(
            rows.loc[0, ["fys_image", "endpoint_image", "residual_image"]].tolist(),
            [
                "results/case_a/fys.jpg",
                "results/case_a/endpoint.jpg",
                "results/case_a/residual.jpg",
            ],
        )

    def test_build_rows_rejects_missing_or_duplicate_method_rows(self) -> None:
        metrics = self._metrics()
        missing = metrics[
            ~(
                metrics["case_uid"].eq("case_a")
                & metrics["method"].eq("residual_rk2")
                & metrics["duration"].eq(15)
            )
        ]
        with self.assertRaisesRegex(ValueError, "case_a.*residual_rk2"):
            build_comparison_rows(missing, ["case_a", "case_b"])

        duplicate = pd.concat(
            [
                metrics,
                metrics[
                    metrics["case_uid"].eq("case_b")
                    & metrics["method"].eq("latent_projection")
                    & metrics["duration"].eq(3)
                ],
            ],
            ignore_index=True,
        )
        with self.assertRaisesRegex(ValueError, "case_b.*latent_projection"):
            build_comparison_rows(duplicate, ["case_a", "case_b"])

    def test_render_writes_two_sheets_with_six_cases_each(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = []
            for index in range(12):
                case_uid = f"case_{index:02d}"
                image_paths = {}
                for field, color in (
                    ("source_image", "white"),
                    ("gt_mask", "black"),
                    ("fys_image", "red"),
                    ("endpoint_image", "blue"),
                    ("residual_image", "green"),
                ):
                    path = root / f"{case_uid}_{field}.png"
                    Image.new("RGB", (32, 24), color).save(path)
                    image_paths[field] = str(path)
                rows.append(
                    {
                        "case_uid": case_uid,
                        "part": "head",
                        "edit": "cat",
                        "part_size": "small",
                        "target_prompt": "a target prompt",
                        **image_paths,
                    }
                )

            outputs = render_comparison_sheets(
                pd.DataFrame(rows), root / "figures", cases_per_sheet=6
            )

            self.assertEqual([path.name for path in outputs], [
                "control_comparison_part1.jpg",
                "control_comparison_part2.jpg",
            ])
            self.assertTrue(all(path.is_file() and path.stat().st_size > 0 for path in outputs))


if __name__ == "__main__":
    unittest.main()
