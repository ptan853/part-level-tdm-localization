from __future__ import annotations

from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"
sys.path.insert(0, str(FYS_SRC))

from flux.control_schedule import (  # noqa: E402
    ControlPlan,
    plan_requires_source_latents,
    resolve_stage,
)


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

    def test_latent_projection_defaults_to_none(self):
        plan = ControlPlan.from_dict(VALID_PLAN)

        self.assertEqual(plan.stages[0].latent_projection, "none")

    def test_residual_control_defaults_to_none(self):
        plan = ControlPlan.from_dict(VALID_PLAN)

        self.assertEqual(plan.stages[0].residual_control, "none")

    def test_residual_control_accepts_source_referenced_rk2_and_serializes(self):
        value = {
            "name": "residual",
            "num_steps": 15,
            "mask_source": "oracle",
            "stages": [{
                "name": "residual",
                "start": 0,
                "end": 2,
                "residual_control": "source_referenced_rk2",
            }],
        }

        plan = ControlPlan.from_dict(value)

        self.assertEqual(plan.stages[0].residual_control, "source_referenced_rk2")
        self.assertEqual(
            plan.to_dict()["stages"][0]["residual_control"],
            "source_referenced_rk2",
        )

    def test_plan_rejects_unknown_residual_control(self):
        value = dict(VALID_PLAN)
        value["stages"] = [
            {**VALID_PLAN["stages"][0], "residual_control": "mystery"}
        ]

        with self.assertRaisesRegex(ValueError, "residual_control"):
            ControlPlan.from_dict(value)

    def test_residual_control_requires_mask_source(self):
        value = {
            "name": "residual",
            "num_steps": 15,
            "stages": [{
                "name": "residual",
                "start": 0,
                "end": 2,
                "residual_control": "source_referenced_rk2",
            }],
        }

        with self.assertRaisesRegex(ValueError, "mask_source"):
            ControlPlan.from_dict(value)

    def test_residual_control_requires_source_latents(self):
        value = {
            "name": "residual",
            "num_steps": 15,
            "mask_source": "oracle",
            "stages": [{
                "name": "residual",
                "start": 0,
                "end": 2,
                "residual_control": "source_referenced_rk2",
            }],
        }

        self.assertTrue(plan_requires_source_latents(ControlPlan.from_dict(value)))

    def test_latent_projection_accepts_source_outside_mask(self):
        value = {
            "name": "projection",
            "num_steps": 15,
            "mask_source": "oracle",
            "stages": [{
                "name": "stage2",
                "start": 2,
                "end": 8,
                "latent_projection": "source_outside_mask",
            }],
        }

        stage = ControlPlan.from_dict(value).stages[0]

        self.assertEqual(stage.latent_projection, "source_outside_mask")

    def test_plan_rejects_unknown_latent_projection(self):
        value = dict(VALID_PLAN)
        value["stages"] = [
            {**VALID_PLAN["stages"][0], "latent_projection": "mystery"}
        ]

        with self.assertRaisesRegex(ValueError, "latent_projection"):
            ControlPlan.from_dict(value)

    def test_latent_projection_requires_mask_source(self):
        value = dict(VALID_PLAN)
        value.pop("mask_source")
        value["stages"] = [
            {**VALID_PLAN["stages"][0], "latent_projection": "source_outside_mask"}
        ]

        with self.assertRaisesRegex(ValueError, "mask_source"):
            ControlPlan.from_dict(value)

    def test_plan_requires_source_latents_only_for_projection(self):
        self.assertFalse(plan_requires_source_latents(None))
        self.assertFalse(plan_requires_source_latents(ControlPlan.from_dict(VALID_PLAN)))

        value = dict(VALID_PLAN)
        value["stages"] = [
            {**VALID_PLAN["stages"][0], "latent_projection": "source_outside_mask"}
        ]

        self.assertTrue(plan_requires_source_latents(ControlPlan.from_dict(value)))

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
