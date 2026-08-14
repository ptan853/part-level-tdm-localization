import importlib.util
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "core" / "scripts" / "run_flux_attention_baseline.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_flux_attention_baseline", RUNNER_PATH)
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


if __name__ == "__main__":
    unittest.main()
