import importlib.util
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "core" / "scripts" / "run_flux_attention_baseline.py"
FYS_RUNNER_PATH = REPO_ROOT / "core" / "scripts" / "run_fys_pilot.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_flux_attention_baseline", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_fys_runner_module():
    spec = importlib.util.spec_from_file_location("run_fys_pilot", FYS_RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PromptValidationTest(unittest.TestCase):
    def test_part_mode_accepts_prompt_containing_part(self):
        runner = load_runner_module()
        records = [
            {
                "case_uid": "case_ok",
                "part": "curly_hair",
                "edit": "curly",
                "target_prompt": "a man with curly hair smiling",
            }
        ]

        runner.validate_prompt_terms(records, token_mode="part")

    def test_part_mode_rejects_prompt_missing_part(self):
        runner = load_runner_module()
        records = [
            {
                "case_uid": "case_bad",
                "part": "head",
                "edit": "alien",
                "target_prompt": "an alien standing in a park",
            }
        ]

        with self.assertRaisesRegex(ValueError, "case_bad"):
            runner.validate_prompt_terms(records, token_mode="part")

    def test_attention_gated_fys_command_uses_separate_output_and_part_edit_args(self):
        runner = load_fys_runner_module()
        record = {
            "case_uid": "case_0001",
            "source_image": "core/data/case/source.png",
            "source_prompt": "a man standing",
            "target_prompt": "a man with alien head standing",
            "follow_your_shape_output_dir": "core/results/follow_your_shape/case_0001",
            "part": "head",
            "edit": "alien",
        }

        command = runner.build_fys_command(
            record,
            repo_root=REPO_ROOT,
            python_executable="python",
            seed=0,
            seed_subdirs=True,
            use_oracle_mask=False,
            name="flux-dev",
            guidance=2.0,
            num_steps=15,
            front=2,
            inject=4,
            offload=True,
            controlnet_type="none",
            tdm_mask_mode="attention_gated",
            attention_token_mode="part_edit",
            attention_layers="28,29",
            output_root=REPO_ROOT / "core" / "results" / "fys_mask_ablation" / "attention_gated_tdm",
        )

        self.assertIn("--tdm_mask_mode", command.args)
        self.assertIn("attention_gated", command.args)
        self.assertIn("--attention_part", command.args)
        self.assertIn("head", command.args)
        self.assertIn("--attention_edit", command.args)
        self.assertIn("alien", command.args)
        self.assertIn("fys_mask_ablation/attention_gated_tdm/case_0001/seed_000", command.run_config["output_dir"])


if __name__ == "__main__":
    unittest.main()
