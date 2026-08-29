from __future__ import annotations

from pathlib import Path
import sys
import unittest

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"
sys.path.insert(0, str(FYS_SRC))

from flux.control_schedule import ControlPlan, load_control_plan  # noqa: E402
from flux.control_runtime import build_step_attention_control, configure_step_control  # noqa: E402


def make_plan(it_gate: str = "edit") -> ControlPlan:
    value = {
        "name": "test",
        "num_steps": 15,
        "stages": [
            {
                "name": "stage2",
                "start": 2,
                "end": 8,
                "it_gate": it_gate,
                "image_kv": "none",
            },
            {
                "name": "stage3",
                "start": 10,
                "end": 13,
                "it_gate": "none",
                "image_kv": "source_outside_mask",
            },
        ],
        "image_kv_layers": list(range(20, 38)),
        "it_gate_layers": list(range(28, 38)),
    }
    if it_gate == "edit":
        value["mask_source"] = "oracle"
    elif it_gate == "part_to_edit":
        value["mask_source"] = "oracle"
    return ControlPlan.from_dict(value)


class ControlPlanSamplingTests(unittest.TestCase):
    def test_oracle_baseline_preserves_original_injection_schedule(self):
        plan = load_control_plan(
            REPO_ROOT / "core" / "configs" / "control_plans" / "oracle_fys_control.json"
        )
        info = {}
        actual = []
        for step in range(15):
            actual.append(
                configure_step_control(
                    info,
                    plan,
                    step=step,
                    txt_len=4,
                    edit_token_indices=(),
                    part_token_indices=(),
                    spatial_mask=torch.ones(3),
                )
            )

        expected = [True, True] + [False] * 8 + [True] * 4 + [False]
        self.assertEqual(actual, expected)

    def test_oracle_stage_builds_spatial_control_only_in_window(self):
        plan = make_plan("edit")
        mask = torch.tensor([1.0, 0.0, 1.0])

        self.assertIsNone(
            build_step_attention_control(
                plan,
                step=1,
                txt_len=4,
                edit_token_indices=(2, 3),
                part_token_indices=(1,),
                spatial_mask=mask,
            )
        )
        control = build_step_attention_control(
            plan,
            step=2,
            txt_len=4,
            edit_token_indices=(2, 3),
            part_token_indices=(1,),
            spatial_mask=mask,
        )
        self.assertEqual(control.operation, "spatial_logit_bias")
        self.assertEqual(control.edit_token_indices, (2, 3))
        self.assertIs(control.image_mask, mask)
        self.assertIsNone(
            build_step_attention_control(
                plan,
                step=9,
                txt_len=4,
                edit_token_indices=(2, 3),
                part_token_indices=(1,),
                spatial_mask=mask,
            )
        )

    def test_transfer_stage_builds_dynamic_control_without_mask(self):
        plan = make_plan("part_to_edit")

        control = build_step_attention_control(
            plan,
            step=4,
            txt_len=4,
            edit_token_indices=(3,),
            part_token_indices=(1, 2),
            spatial_mask=None,
        )

        self.assertEqual(control.operation, "part_to_edit_logit_transfer")
        self.assertEqual(control.part_token_indices, (1, 2))
        self.assertIsNone(control.image_mask)

    def test_configure_step_sets_gate_and_image_kv_independently(self):
        plan = make_plan("edit")
        info = {"attention_control": object(), "attention_control_layers": (0,)}
        kwargs = {
            "txt_len": 4,
            "edit_token_indices": (3,),
            "part_token_indices": (1,),
            "spatial_mask": torch.ones(3),
        }

        stage2_image_kv = configure_step_control(info, plan, step=2, **kwargs)
        self.assertFalse(stage2_image_kv)
        self.assertEqual(info["image_kv_operation"], "none")
        self.assertEqual(info["attention_control_layers"], tuple(range(28, 38)))
        self.assertEqual(info["attention_control"].operation, "spatial_logit_bias")

        stage3_image_kv = configure_step_control(info, plan, step=10, **kwargs)
        self.assertTrue(stage3_image_kv)
        self.assertEqual(info["image_kv_operation"], "source_outside_mask")
        self.assertNotIn("attention_control", info)
        self.assertNotIn("attention_control_layers", info)

        gap_image_kv = configure_step_control(info, plan, step=9, **kwargs)
        self.assertFalse(gap_image_kv)
        self.assertNotIn("image_kv_operation", info)
        self.assertNotIn("attention_control", info)


if __name__ == "__main__":
    unittest.main()
