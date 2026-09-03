from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "core" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_heldout_control_comparison import (  # noqa: E402
    EVALUATED_METHODS,
    build_comparison_runs,
    build_matched_control_plan,
    execute_comparison_runs,
)
import run_heldout_control_comparison as comparison_runner  # noqa: E402


def _record(case_uid: str) -> dict:
    return {
        "case_uid": case_uid,
        "source_image": f"core/data/heldout/{case_uid}/source.png",
        "gt_mask": f"core/data/heldout/{case_uid}/gt_mask.png",
        "source_prompt": "a person standing in a park",
        "target_prompt": "a person with alien head standing in a park",
        "part": "head",
        "edit": "alien",
        "part_size": "small",
    }


class HeldoutControlComparisonTests(unittest.TestCase):
    def test_matched_controls_use_same_n7_prefix(self):
        endpoint = build_matched_control_plan("endpoint_projection")
        residual = build_matched_control_plan("residual_rk2")

        for plan in (endpoint, residual):
            self.assertEqual(plan["mask_source"], "precomputed")
            self.assertEqual(plan["stages"][0]["start"], 0)
            self.assertEqual(plan["stages"][0]["end"], 6)
            self.assertEqual(plan["image_kv_layers"], [])
            self.assertEqual(plan["it_gate_layers"], [])
        self.assertEqual(
            endpoint["stages"][0]["latent_projection"], "source_outside_mask"
        )
        self.assertEqual(
            residual["stages"][0]["residual_control"], "source_referenced_rk2"
        )

    def test_builds_one_shared_scout_and_three_evaluated_methods(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs = build_comparison_runs(
                records=[_record("heldout_0000"), _record("heldout_0001")],
                seeds=[0, 1],
                repo_root=REPO_ROOT,
                python_executable="python",
                offload=True,
                output_root=root / "outputs",
                plan_dir=root / "plans",
                attention_token_mode="part",
            )

        self.assertEqual(len(runs), 16)
        self.assertEqual(
            Counter(run.role for run in runs),
            {
                "original_fys_tdm": 4,
                "attention_mask_scout": 4,
                "endpoint_projection": 4,
                "residual_rk2": 4,
            },
        )
        self.assertEqual(
            EVALUATED_METHODS,
            ("original_fys_tdm", "endpoint_projection", "residual_rk2"),
        )

    def test_endpoint_and_residual_share_scout_mask_without_gt_leakage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs = build_comparison_runs(
                records=[_record("heldout_0000")],
                seeds=[3],
                repo_root=REPO_ROOT,
                python_executable="python",
                offload=True,
                output_root=root / "outputs",
                plan_dir=root / "plans",
                attention_token_mode="part",
            )

            scout = next(run for run in runs if run.role == "attention_mask_scout")
            controls = [
                run
                for run in runs
                if run.role in {"endpoint_projection", "residual_rk2"}
            ]

            expected_mask = (
                Path(scout.command.run_config["vis_path"])
                / "hybrid_binary_tdm_attention.npy"
            )
            self.assertEqual(len(controls), 2)
            for run in controls:
                self.assertEqual(run.control_mask_path, expected_mask)
                self.assertIn("--control-mask-path", run.command.args)
                self.assertIn(str(expected_mask), run.command.args)
                self.assertNotIn("--mask_path", run.command.args)
                self.assertNotIn("oracle", run.command.args)
                self.assertEqual(run.command.run_config["gt_mask"], _record("heldout_0000")["gt_mask"])

    def test_rejects_edit_only_scout_mask(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "part or part_edit"):
                build_comparison_runs(
                    records=[_record("heldout_0000")],
                    seeds=[0],
                    repo_root=REPO_ROOT,
                    python_executable="python",
                    offload=True,
                    output_root=root / "outputs",
                    plan_dir=root / "plans",
                    attention_token_mode="edit",
                )

    def test_execution_stops_when_scout_does_not_write_mask(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs = build_comparison_runs(
                records=[_record("heldout_0000")],
                seeds=[0],
                repo_root=REPO_ROOT,
                python_executable="python",
                offload=True,
                output_root=root / "outputs",
                plan_dir=root / "plans",
                attention_token_mode="part",
            )

            with mock.patch.object(comparison_runner, "run_command", return_value=0), \
                mock.patch.object(comparison_runner, "execute_command") as execute:
                with self.assertRaisesRegex(FileNotFoundError, "did not produce"):
                    execute_comparison_runs(
                        runs,
                        repo_root=REPO_ROOT,
                        overwrite=False,
                    )

        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
