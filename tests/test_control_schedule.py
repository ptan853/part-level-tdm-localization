from __future__ import annotations

from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"
sys.path.insert(0, str(FYS_SRC))

from flux.control_schedule import ControlPlan, load_control_plan, resolve_stage  # noqa: E402


VALID_PLAN = {
    "name": "oracle_stage2_edit_gate",
    "num_steps": 15,
    "mask_source": "oracle",
    "stages": [
        {
            "name": "stage2",
            "start": 2,
            "end": 8,
            "prompt": "target",
            "image_kv": "none",
            "it_gate": "edit",
            "it_gate_strength": 1.0,
        },
        {
            "name": "stage3",
            "start": 10,
            "end": 13,
            "prompt": "target",
            "image_kv": "source_outside_mask",
            "it_gate": "none",
        },
    ],
    "image_kv_layers": list(range(20, 38)),
    "it_gate_layers": list(range(28, 38)),
}


class ControlScheduleTests(unittest.TestCase):
    def test_oracle_pair_differs_only_by_stage2_it_gate(self):
        config_dir = REPO_ROOT / "core" / "configs" / "control_plans"
        baseline = load_control_plan(config_dir / "oracle_fys_control.json")
        gated = load_control_plan(config_dir / "oracle_stage2_edit_logit_gate.json")

        self.assertEqual(baseline.num_steps, gated.num_steps)
        self.assertEqual(baseline.front, gated.front)
        self.assertEqual(baseline.inject, gated.inject)
        self.assertEqual(baseline.tail_pad, gated.tail_pad)
        self.assertEqual(baseline.mask_source, gated.mask_source)
        self.assertEqual(baseline.image_kv_layers, gated.image_kv_layers)
        self.assertEqual(baseline.it_gate_layers, gated.it_gate_layers)
        self.assertEqual(
            [(stage.start, stage.end, stage.image_kv) for stage in baseline.stages],
            [(stage.start, stage.end, stage.image_kv) for stage in gated.stages],
        )
        self.assertEqual([stage.it_gate for stage in baseline.stages], ["none"] * 4)
        self.assertEqual(
            [stage.it_gate for stage in gated.stages],
            ["none", "edit", "none", "none"],
        )

    def test_resolve_stage_uses_inclusive_boundaries_and_allows_gaps(self):
        plan = ControlPlan.from_dict(VALID_PLAN)

        self.assertEqual(resolve_stage(plan, 2).name, "stage2")
        self.assertEqual(resolve_stage(plan, 8).name, "stage2")
        self.assertIsNone(resolve_stage(plan, 9))
        self.assertEqual(resolve_stage(plan, 10).name, "stage3")

    def test_plan_rejects_overlapping_stages(self):
        value = dict(VALID_PLAN)
        value["stages"] = [
            dict(VALID_PLAN["stages"][0]),
            {**VALID_PLAN["stages"][1], "start": 8},
        ]

        with self.assertRaisesRegex(ValueError, "overlap"):
            ControlPlan.from_dict(value)

    def test_plan_rejects_out_of_range_stage(self):
        value = dict(VALID_PLAN)
        value["stages"] = [{**VALID_PLAN["stages"][0], "end": 15}]

        with self.assertRaisesRegex(ValueError, "num_steps"):
            ControlPlan.from_dict(value)

    def test_plan_rejects_unknown_gate(self):
        value = dict(VALID_PLAN)
        value["stages"] = [{**VALID_PLAN["stages"][0], "it_gate": "mystery"}]

        with self.assertRaisesRegex(ValueError, "it_gate"):
            ControlPlan.from_dict(value)

    def test_spatial_operation_requires_mask_source(self):
        value = dict(VALID_PLAN)
        value.pop("mask_source")

        with self.assertRaisesRegex(ValueError, "mask_source"):
            ControlPlan.from_dict(value)

    def test_part_to_edit_transfer_does_not_require_mask(self):
        value = dict(VALID_PLAN)
        value.pop("mask_source")
        value["stages"] = [
            {
                **VALID_PLAN["stages"][0],
                "it_gate": "part_to_edit",
                "image_kv": "none",
            }
        ]

        plan = ControlPlan.from_dict(value)

        self.assertEqual(plan.stages[0].it_gate, "part_to_edit")


if __name__ == "__main__":
    unittest.main()
