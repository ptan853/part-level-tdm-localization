from __future__ import annotations

from collections import Counter
import json
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
    build_review_randomization_inputs,
    build_supplemental_endpoint_plan,
    capture_runtime_environment,
    execute_comparison_runs,
    validate_execution_commit,
    validate_frozen_preflight,
    write_comparison_matrix,
    write_preflight_evidence,
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
        "dataset_revision": "v1.1",
        "dataset_split": "synth",
        "dataset_index": int(case_uid.rsplit("_", 1)[-1]),
        "gt_area_ratio": 0.01,
        "footprint_change": "comparable",
    }


class HeldoutControlComparisonTests(unittest.TestCase):
    def test_supplemental_endpoint_plan_preserves_historical_n3_schedule(self):
        plan = build_supplemental_endpoint_plan()

        self.assertEqual(plan["mask_source"], "precomputed")
        self.assertEqual(plan["image_kv_layers"], list(range(20, 38)))
        self.assertEqual(plan["it_gate_layers"], [])
        self.assertEqual(
            [
                (
                    stage["start"],
                    stage["end"],
                    stage["image_kv"],
                    stage["latent_projection"],
                )
                for stage in plan["stages"]
            ],
            [
                (0, 1, "source_all", "none"),
                (2, 4, "none", "source_outside_mask"),
            ],
        )

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
            (
                "original_fys_tdm",
                "endpoint_projection",
                "residual_rk2",
                "endpoint_projection_n3",
            ),
        )

    def test_optional_n3_adds_one_evaluated_run_per_case_and_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs = build_comparison_runs(
                records=[_record("synth_0000"), _record("synth_0001")],
                seeds=[0],
                repo_root=REPO_ROOT,
                python_executable="python",
                offload=True,
                output_root=root / "outputs",
                plan_dir=root / "plans",
                attention_token_mode="part",
                include_endpoint_n3=True,
            )

        self.assertEqual(len(runs), 10)
        self.assertEqual(Counter(run.role for run in runs)["endpoint_projection_n3"], 2)
        n3 = next(run for run in runs if run.role == "endpoint_projection_n3")
        self.assertEqual(n3.command.run_config["num_steps"], 15)
        self.assertEqual(
            n3.command.run_config["resolved_control_plan"]["stages"][1]["end"], 4
        )

    def test_builds_pre_generation_randomization_inputs_for_evaluated_rows_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = [_record("synth_0000"), _record("synth_0001")]
            runs = build_comparison_runs(
                records=records,
                seeds=[0],
                repo_root=REPO_ROOT,
                python_executable="python",
                offload=True,
                output_root=root / "outputs",
                plan_dir=root / "plans",
                attention_token_mode="part",
                include_endpoint_n3=True,
            )

            rows = build_review_randomization_inputs(records, runs)

        self.assertEqual(len(rows), 8)
        self.assertEqual({row["method"] for row in rows}, set(EVALUATED_METHODS))
        self.assertTrue(
            all(row["row_uid"].endswith("::seed_000") for row in rows)
        )

    def test_portable_command_matrix_contains_no_local_repository_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            matrix = root / "portable.csv"
            runs = build_comparison_runs(
                records=[_record("synth_0000")],
                seeds=[0],
                repo_root=REPO_ROOT,
                python_executable="python",
                offload=True,
                output_root=REPO_ROOT / "core" / "results" / "heldout",
                plan_dir=root / "plans",
                attention_token_mode="part",
                include_endpoint_n3=True,
            )

            write_comparison_matrix(
                matrix, runs, repo_root=REPO_ROOT, portable=True
            )
            content = matrix.read_text(encoding="utf-8")

        self.assertNotIn(str(REPO_ROOT), content)
        self.assertIn("${REPO_ROOT}", content)

    def test_runtime_environment_is_archived_before_execution(self):
        completed = [
            mock.Mock(returncode=0, stdout="Python 3.11.9\n", stderr=""),
            mock.Mock(returncode=0, stdout="torch==2.4.0\n", stderr=""),
            mock.Mock(returncode=0, stdout="GPU,CUDA\n", stderr=""),
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "runtime_environment.json"
            with mock.patch.object(
                comparison_runner.subprocess, "run", side_effect=completed
            ):
                payload = capture_runtime_environment(output, "python")

            archived = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload, archived)
        self.assertEqual(archived["python_version"]["returncode"], 0)
        self.assertIn("torch==2.4.0", archived["pip_freeze"]["stdout"])

    def test_execution_commit_must_match_current_head(self):
        with mock.patch.object(comparison_runner, "_git_head", return_value="abc123"):
            validate_execution_commit(REPO_ROOT, "abc123")
            with self.assertRaisesRegex(ValueError, "does not match"):
                validate_execution_commit(REPO_ROOT, "different")

    def test_frozen_preflight_accepts_exact_60_case_300_run_matrix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = []
            for index in range(60):
                case_dir = root / "cases" / f"synth_{index:04d}"
                case_dir.mkdir(parents=True)
                (case_dir / "source.png").write_bytes(b"source")
                (case_dir / "gt_mask.png").write_bytes(b"mask")
                record = _record(f"synth_{index:04d}")
                record["source_image"] = str(case_dir / "source.png")
                record["gt_mask"] = str(case_dir / "gt_mask.png")
                record["part_size"] = ("small", "medium", "large")[index // 20]
                records.append(record)
            runs = build_comparison_runs(
                records=records,
                seeds=[0],
                repo_root=REPO_ROOT,
                python_executable="python",
                offload=True,
                output_root=root / "outputs",
                plan_dir=root / "plans",
                attention_token_mode="part",
                include_endpoint_n3=True,
            )

            summary = validate_frozen_preflight(records, [0], runs, REPO_ROOT)

        self.assertEqual(summary["manifest_records"], 60)
        self.assertEqual(summary["command_rows"], 300)
        self.assertEqual(summary["evaluated_outputs"], 240)

    def test_preflight_evidence_archives_matrix_randomization_and_locks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = []
            for index in range(60):
                case_dir = root / "cases" / f"synth_{index:04d}"
                case_dir.mkdir(parents=True)
                (case_dir / "source.png").write_bytes(b"source")
                (case_dir / "gt_mask.png").write_bytes(b"mask")
                record = _record(f"synth_{index:04d}")
                record["source_image"] = str(case_dir / "source.png")
                record["gt_mask"] = str(case_dir / "gt_mask.png")
                record["part_size"] = ("small", "medium", "large")[index // 20]
                records.append(record)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(records), encoding="utf-8")
            runs = build_comparison_runs(
                records=records,
                seeds=[0],
                repo_root=REPO_ROOT,
                python_executable="python",
                offload=True,
                output_root=root / "outputs",
                plan_dir=root / "plans",
                attention_token_mode="part",
                include_endpoint_n3=True,
            )
            summary = validate_frozen_preflight(records, [0], runs, REPO_ROOT)
            evidence = root / "evidence"

            frozen = write_preflight_evidence(
                evidence,
                records=records,
                runs=runs,
                repo_root=REPO_ROOT,
                manifest_path=manifest,
                preflight=summary,
                submodule_commit="b096e8f",
                execution_commit="abc123",
            )

            self.assertEqual(frozen["command_rows"], 300)
            self.assertEqual(frozen["review_assignments"], 480)
            self.assertEqual(frozen["execution_commit"], "abc123")
            self.assertTrue((evidence / "command_matrix.csv").is_file())
            self.assertTrue((evidence / "reviewer_randomization.csv").is_file())
            self.assertTrue((evidence / "environment_lock.json").is_file())
            self.assertTrue((evidence / "preflight_summary.json").is_file())

    def test_frozen_preflight_rejects_incomplete_manifest(self):
        with self.assertRaisesRegex(ValueError, "exactly 60"):
            validate_frozen_preflight([_record("synth_0000")], [0], [], REPO_ROOT)

    def test_frozen_preflight_rejects_any_nonempty_output_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = []
            for index in range(60):
                case_dir = root / "cases" / f"synth_{index:04d}"
                case_dir.mkdir(parents=True)
                (case_dir / "source.png").write_bytes(b"source")
                (case_dir / "gt_mask.png").write_bytes(b"mask")
                record = _record(f"synth_{index:04d}")
                record["source_image"] = str(case_dir / "source.png")
                record["gt_mask"] = str(case_dir / "gt_mask.png")
                record["part_size"] = ("small", "medium", "large")[index // 20]
                records.append(record)
            runs = build_comparison_runs(
                records=records,
                seeds=[0],
                repo_root=REPO_ROOT,
                python_executable="python",
                offload=True,
                output_root=root / "outputs",
                plan_dir=root / "plans",
                attention_token_mode="part",
                include_endpoint_n3=True,
            )
            occupied = runs[0].command.run_config["output_dir"]
            occupied = (
                Path(occupied) if Path(occupied).is_absolute() else REPO_ROOT / occupied
            )
            occupied.mkdir(parents=True)
            (occupied / "partial.txt").write_text("partial", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "not empty"):
                validate_frozen_preflight(records, [0], runs, REPO_ROOT)

            validate_frozen_preflight(
                records, [0], runs, REPO_ROOT, allow_full_rerun=True
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
                self.assertEqual(
                    run.command.run_config["gt_mask"],
                    _record("heldout_0000")["gt_mask"],
                )

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

            with (
                mock.patch.object(comparison_runner, "run_command", return_value=0),
                mock.patch.object(comparison_runner, "execute_command") as execute,
            ):
                with self.assertRaisesRegex(FileNotFoundError, "did not produce"):
                    execute_comparison_runs(
                        runs,
                        repo_root=REPO_ROOT,
                        overwrite=False,
                    )

        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
