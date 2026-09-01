from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from core.scripts.evaluate_latent_projection_against_fys import evaluate_rows
from core.scripts.evaluate_residual_rk2_prefix_sweep import (
    build_residual_evaluation_rows,
    build_unified_evaluation_rows,
)


def write_rgb(path: Path, value: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.full((4, 4, 3), value, dtype=np.uint8)).save(path)


def write_complete_run(root: Path, duration: int, case_uid: str, value: int) -> None:
    run_dir = root / f"duration_{duration:02d}" / case_uid / "seed_000"
    write_rgb(run_dir / "img_0.jpg", value)
    (run_dir / "run_config.json").write_text("{}\n", encoding="utf-8")
    (run_dir / "resolved_control_plan.json").write_text("{}\n", encoding="utf-8")
    tdm = run_dir / "tdm"
    tdm.mkdir()
    (tdm / "control_trace.json").write_text(
        json.dumps({"residual_control_trace": list(range(duration))}) + "\n",
        encoding="utf-8",
    )


class ResidualRk2EvaluationTest(unittest.TestCase):
    def test_script_entrypoint_can_show_help(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable,
                str(repo_root / "core/scripts/evaluate_residual_rk2_prefix_sweep.py"),
                "--help",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def make_fixture(self, root: Path) -> tuple[list[dict], Path]:
        case_dir = root / "core/data/cases/case_a"
        write_rgb(case_dir / "source.png")
        mask = np.zeros((4, 4), dtype=np.uint8)
        mask[:2, :2] = 255
        Image.fromarray(mask).save(case_dir / "gt.png")
        manifest = [{
            "case_uid": "case_a",
            "part": "head",
            "edit": "alien",
            "part_size": "small",
            "source_image": str((case_dir / "source.png").relative_to(root)),
            "gt_mask": str((case_dir / "gt.png").relative_to(root)),
            "target_prompt": "a person with an alien head",
        }]
        output_root = root / "core/results/residual"
        write_complete_run(output_root, 0, "case_a", 64)
        write_complete_run(output_root, 1, "case_a", 128)
        return manifest, output_root

    def test_builds_one_complete_row_per_case_and_duration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, output_root = self.make_fixture(root)

            rows = build_residual_evaluation_rows(
                root, manifest, output_root, durations=[0, 1], seed=0
            )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows["row_uid"].tolist(), [
            "residual_rk2::case_a::N00",
            "residual_rk2::case_a::N01",
        ])
        self.assertEqual(rows["method"].unique().tolist(), ["residual_rk2"])
        self.assertEqual(rows["duration"].tolist(), [0, 1])

    def test_rejects_an_incomplete_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, output_root = self.make_fixture(root)
            (output_root / "duration_01/case_a/seed_000/tdm/control_trace.json").unlink()

            with self.assertRaisesRegex(FileNotFoundError, "control_trace.json"):
                build_residual_evaluation_rows(
                    root, manifest, output_root, durations=[0, 1], seed=0
                )

    def test_unified_rows_keep_fys_projection_and_residual_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, output_root = self.make_fixture(root)
            fys_image = root / "core/results/fys/case_a/img.jpg"
            projection_image = root / "core/results/projection/case_a/img.jpg"
            write_rgb(fys_image, 32)
            write_rgb(projection_image, 48)
            fys = pd.DataFrame([{
                "case_uid": "case_a", "seed": 0,
                "fys_image": str(fys_image.relative_to(root)),
                "outside_mask_lpips": 0.25,
            }])
            projection = pd.DataFrame([{
                "case_uid": "case_a", "duration": 0,
                "generated_image": str(projection_image.relative_to(root)),
            }])
            residual = build_residual_evaluation_rows(
                root, manifest, output_root, durations=[0, 1], seed=0
            )

            rows = build_unified_evaluation_rows(
                root, manifest, fys, projection, residual
            )

        self.assertEqual(len(rows), 4)
        self.assertEqual(
            set(rows["method"]),
            {"original_fys", "latent_projection", "residual_rk2"},
        )
        self.assertEqual(rows["row_uid"].nunique(), 4)

    def test_existing_lpips_is_preserved_when_lpips_is_off(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, output_root = self.make_fixture(root)
            rows = build_residual_evaluation_rows(
                root, manifest, output_root, durations=[0], seed=0
            )
            existing = pd.DataFrame([{
                "row_uid": "residual_rk2::case_a::N00",
                "outside_mask_lpips": 0.123,
            }])

            evaluated = evaluate_rows(root, rows, "off", existing_output=existing)

        self.assertAlmostEqual(evaluated.loc[0, "outside_mask_lpips"], 0.123)
        self.assertIn("outside_mask_global_ssim", evaluated.columns)


if __name__ == "__main__":
    unittest.main()
