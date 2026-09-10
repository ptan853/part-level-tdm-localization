from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core" / "scripts"))


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("run_attention_routing_diagnostic"),
                             "The dedicated diagnostic runner is not implemented")
        import run_attention_routing_diagnostic
        self.runner = run_attention_routing_diagnostic

    def test_two_conditions_keep_existing_sampling_settings(self):
        from flux.control_schedule import ControlPlan
        for duration in (0, 7):
            plan = ControlPlan.from_dict(self.runner.make_plan(duration))
            self.assertEqual((plan.num_steps, plan.front, plan.inject, plan.tail_pad), (15, 2, 4, 1))
            self.assertFalse(plan.image_kv_layers)
            self.assertFalse(plan.it_gate_layers)
            if duration:
                self.assertEqual((plan.stages[0].start, plan.stages[0].end), (0, 6))
            else:
                self.assertFalse(plan.stages)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "not_created"
            self.assertEqual(self.runner.main(["--output-root", str(root), "--case-uid", "synth_0032"]), 0)
            self.assertFalse(root.exists())

    def test_unknown_case_rejected(self):
        with self.assertRaises(ValueError):
            self.runner.main(["--case-uid", "synth_9999"])

    def test_prepared_plans_match_prior_rk2_and_do_not_create_runs(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            self.runner.main(["--output-root", tmp, "--case-uid", "synth_0032", "--prepare"])
            plan = json.loads((Path(tmp) / "plans/rk2_gt_n07.json").read_text())
            old = json.loads((ROOT / "core/protocols/gt_mask_diagnostic_v2/resolved_plans/residual_rk2_n07.json").read_text())
            plan.pop("name")
            old.pop("name")
            self.assertEqual(plan, old)
            self.assertFalse((Path(tmp) / "recording_on").exists())


if __name__ == "__main__":
    unittest.main()
