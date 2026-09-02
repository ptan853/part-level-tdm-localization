from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "core" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_control_plan import build_control_command, validate_output_dir, write_run_matrix  # noqa: E402


class RunControlPlanTests(unittest.TestCase):
    def test_builds_isolated_command_with_plan_and_oracle_mask(self):
        record = {
            "case_uid": "real_0006",
            "source_image": "core/data/partedit_subset/cases/real_0006/source.png",
            "gt_mask": "core/data/partedit_subset/cases/real_0006/gt_mask.png",
            "source_prompt": "a man standing in a park",
            "target_prompt": "a man with alien head standing in a park",
            "part": "head",
            "edit": "alien",
        }
        plan = {
            "name": "test_oracle_control",
            "num_steps": 15,
            "mask_source": "oracle",
            "stages": [
                {
                    "name": "projection",
                    "start": 2,
                    "end": 4,
                    "latent_projection": "source_outside_mask",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            command = build_control_command(
                record,
                plan_path=plan_path,
                repo_root=REPO_ROOT,
                python_executable="python",
                seed=0,
                offload=True,
            )

        self.assertTrue(
            command.output_dir.as_posix().endswith(
                "control_operations/test_oracle_control/real_0006/seed_000"
            )
        )
        self.assertIn("--control-plan-resolved", command.args)
        self.assertIn("--tdm_mask_mode", command.args)
        self.assertIn("oracle", command.args)
        self.assertEqual(command.run_config["gt_mask"], record["gt_mask"])

    def test_refuses_nonempty_output_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "occupied.txt").write_text("keep", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                validate_output_dir(output, overwrite=False)
            validate_output_dir(output, overwrite=True)

    def test_run_matrix_uses_lf_line_endings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "matrix.csv"
            command = SimpleNamespace(
                run_config={"case_uid": "case", "resolved_control_plan": {}},
                cwd=REPO_ROOT,
                args=("python", "edit.py"),
            )
            write_run_matrix(path, [command], REPO_ROOT)
            self.assertNotIn(b"\r\n", path.read_bytes())


if __name__ == "__main__":
    unittest.main()
