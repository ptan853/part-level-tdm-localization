import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "core" / "scripts" / "run_same_state_inversion_probe.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_same_state_inversion_probe", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SameStateProbeRunnerTest(unittest.TestCase):
    def test_builds_two_isolated_probe_commands(self):
        runner = load_runner_module()
        records = runner.load_manifest(
            REPO_ROOT / "core" / "data" / "partedit_subset" / "pilot_12_manifest.json"
        )
        selected = runner.select_records(records, ["real_0006", "real_0010"])

        with tempfile.TemporaryDirectory() as tmpdir:
            commands = runner.build_commands(
                selected,
                repo_root=REPO_ROOT,
                python_executable="python",
                seed=0,
                name="flux-dev",
                guidance=2.0,
                num_steps=15,
                front=2,
                inject=4,
                layers="28,29",
                offload=True,
                output_root=Path(tmpdir),
            )

        self.assertEqual([command.case_uid for command in commands], ["real_0006", "real_0010"])
        self.assertNotEqual(commands[0].run_config["output_dir"], commands[1].run_config["output_dir"])
        for command, record in zip(commands, selected):
            self.assertIn("--same_state_probe_dir", command.args)
            self.assertIn("--probe_part", command.args)
            self.assertIn(str(record["part"]), command.args)
            self.assertIn("--probe_edit", command.args)
            self.assertIn(str(record["edit"]), command.args)
            self.assertIn("--probe_layers", command.args)
            self.assertIn("28,29", command.args)
            self.assertEqual(command.run_config["run_type"], "same_state_inversion_probe")
            self.assertFalse(Path(command.run_config["output_dir"]).exists())

    def test_dry_run_selects_exact_cases_without_writing(self):
        runner = load_runner_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "probe-results"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                returncode = runner.main(
                    [
                        "--case-uid",
                        "real_0006",
                        "--case-uid",
                        "real_0010",
                        "--seed",
                        "0",
                        "--output-root",
                        str(output_root),
                    ]
                )

            output = stdout.getvalue()
            self.assertEqual(returncode, 0)
            self.assertIn("[1/2] real_0006_seed_000", output)
            self.assertIn("[2/2] real_0010_seed_000", output)
            self.assertIn("Dry run only", output)
            self.assertFalse(output_root.exists())

    def test_requires_explicit_case_selection(self):
        runner = load_runner_module()
        with self.assertRaisesRegex(ValueError, "--case-uid"):
            runner.main([])


if __name__ == "__main__":
    unittest.main()
