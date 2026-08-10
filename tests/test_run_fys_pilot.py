import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "core" / "scripts" / "run_fys_pilot.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_fys_pilot", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sample_record(case_uid="case_a"):
    return {
        "case_uid": case_uid,
        "source_image": "core/data/partedit_subset/cases/case_a/source.png",
        "gt_mask": "core/data/partedit_subset/cases/case_a/gt_mask.png",
        "source_prompt": "a dog standing in a field",
        "target_prompt": "a dog with bear head standing in a field",
        "follow_your_shape_output_dir": "core/results/follow_your_shape/case_a",
        "follow_your_shape_vis_path": "core/results/follow_your_shape/case_a/tdm",
    }


class RunFysPilotTests(unittest.TestCase):
    def test_build_command_uses_manifest_paths_and_prompts(self):
        runner = load_runner_module()
        command = runner.build_fys_command(
            sample_record(),
            repo_root=REPO_ROOT,
            python_executable="python",
            use_oracle_mask=False,
            name="flux-dev",
            guidance=2.0,
            num_steps=15,
            front=2,
            inject=4,
            offload=True,
            controlnet_type="none",
        )

        self.assertEqual(command.cwd, REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src")
        self.assertEqual(command.args[:2], ["python", "edit.py"])
        self.assertIn("--source_img_dir", command.args)
        self.assertIn(str(REPO_ROOT / "core/data/partedit_subset/cases/case_a/source.png"), command.args)
        self.assertIn("--source_prompt", command.args)
        self.assertIn("a dog standing in a field", command.args)
        self.assertIn("--target_prompt", command.args)
        self.assertIn("a dog with bear head standing in a field", command.args)
        self.assertIn("--vis_path", command.args)
        self.assertNotIn("--mask_path", command.args)

    def test_select_records_filters_by_case_uid_then_limit(self):
        runner = load_runner_module()
        records = [sample_record("case_a"), sample_record("case_b"), sample_record("case_c")]

        selected = runner.select_records(records, case_uids=["case_c", "case_a"], limit=1)

        self.assertEqual([record["case_uid"] for record in selected], ["case_a"])

    def test_build_command_can_add_oracle_mask(self):
        runner = load_runner_module()
        command = runner.build_fys_command(
            sample_record(),
            repo_root=REPO_ROOT,
            python_executable="python",
            use_oracle_mask=True,
            name="flux-dev",
            guidance=2.0,
            num_steps=15,
            front=2,
            inject=4,
            offload=False,
            controlnet_type="none",
        )

        self.assertIn("--mask_path", command.args)
        self.assertIn(str(REPO_ROOT / "core/data/partedit_subset/cases/case_a/gt_mask.png"), command.args)
        self.assertNotIn("--offload", command.args)


if __name__ == "__main__":
    unittest.main()
