from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"
sys.path.insert(0, str(FYS_SRC))

if importlib.util.find_spec("transformers") is None:
    transformers_stub = types.ModuleType("transformers")
    for name in ("CLIPTextModel", "CLIPTokenizer", "T5EncoderModel", "T5Tokenizer"):
        setattr(transformers_stub, name, type(name, (), {}))
    sys.modules["transformers"] = transformers_stub

if importlib.util.find_spec("skimage") is None:
    skimage_stub = types.ModuleType("skimage")
    filters_stub = types.ModuleType("skimage.filters")
    filters_stub.threshold_otsu = lambda values: float(np.asarray(values).mean())
    skimage_stub.filters = filters_stub
    sys.modules["skimage"] = skimage_stub
    sys.modules["skimage.filters"] = filters_stub

from flux.control_schedule import ControlPlan, load_control_plan  # noqa: E402
from flux.control_runtime import build_step_attention_control, configure_step_control  # noqa: E402
from flux.sampling import denoise_with_TDM  # noqa: E402


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
    class _ConstantVelocityModel:
        def __call__(self, *, img, **_kwargs):
            return torch.ones_like(img), _kwargs["info"]

    @staticmethod
    def _projection_plan(start: int = 0, end: int = 0) -> ControlPlan:
        return ControlPlan.from_dict(
            {
                "name": "projection-test",
                "num_steps": 2,
                "front": 0,
                "inject": 0,
                "tail_pad": 0,
                "mask_source": "oracle",
                "stages": [
                    {
                        "name": "projection",
                        "start": start,
                        "end": end,
                        "latent_projection": "source_outside_mask",
                    }
                ],
            }
        )

    @staticmethod
    def _projection_inputs(vis_path: str | None = None):
        img = torch.zeros(1, 4, 1)
        return {
            "model": ControlPlanSamplingTests._ConstantVelocityModel(),
            "img": img,
            "img_ids": torch.zeros(1, 4, 3),
            "txt": torch.zeros(1, 1, 1),
            "txt_ids": torch.zeros(1, 1, 3),
            "vec": torch.zeros(1, 1),
            "timesteps": [1.0, 0.5, 0.0],
            "inverse": False,
            "width": 32,
            "height": 32,
            "inject_list": [False, False],
            "tail_pad": 0,
            "front_pad": 0,
            "info": {
                "inject_step": 0,
                "inv_noise": {
                    "step0": torch.tensor([[[0.0], [0.1], [0.2], [0.3]]]),
                    "step1": torch.tensor([[[0.0], [0.1], [0.2], [0.3]]]),
                },
                "source_latents": {
                    1: torch.tensor([[[10.0], [20.0], [30.0], [40.0]]]),
                    2: torch.tensor([[[50.0], [60.0], [70.0], [80.0]]]),
                },
                **({"vis_path": vis_path} if vis_path is not None else {}),
            },
            "control_spatial_mask": torch.tensor([1.0, 0.0, 1.0, 0.0]),
        }

    def test_projection_uses_source_endpoint_after_complete_heun_step(self):
        inputs = self._projection_inputs()

        actual, info = denoise_with_TDM(
            **inputs,
            control_plan=self._projection_plan(),
        )

        expected = torch.tensor([[[-1.0], [19.5], [-1.0], [39.5]]])
        torch.testing.assert_close(actual, expected)
        self.assertEqual(len(info["latent_projection_trace"]), 1)
        trace = info["latent_projection_trace"][0]
        self.assertEqual(trace["step"], 0)
        self.assertEqual(trace["source_latent_index"], 1)
        self.assertEqual(trace["timestep"], 1.0)
        self.assertEqual(trace["next_timestep"], 0.5)
        self.assertEqual(trace["mask_area_ratio"], 0.5)
        self.assertGreater(trace["outside_mae_before"], 0.0)
        self.assertEqual(trace["outside_mae_after"], 0.0)

    def test_projection_leaves_disabled_step_as_heun_candidate(self):
        inputs = self._projection_inputs()

        actual, info = denoise_with_TDM(
            **inputs,
            control_plan=self._projection_plan(start=0, end=0),
        )

        self.assertEqual(len(info["latent_projection_trace"]), 1)
        expected_second_step = torch.tensor([[[-1.0], [19.5], [-1.0], [39.5]]])
        torch.testing.assert_close(actual, expected_second_step)

    def test_projection_requires_selected_source_endpoint(self):
        inputs = self._projection_inputs()
        del inputs["info"]["source_latents"][1]

        with self.assertRaisesRegex(RuntimeError, r"source_latents\[1\]"):
            denoise_with_TDM(
                **inputs,
                control_plan=self._projection_plan(),
            )

    def test_projection_validates_mask_before_bfloat16_cast(self):
        inputs = self._projection_inputs()
        inputs["img"] = inputs["img"].to(torch.bfloat16)
        inputs["info"]["source_latents"] = {
            index: latent.to(torch.bfloat16)
            for index, latent in inputs["info"]["source_latents"].items()
        }
        inputs["control_spatial_mask"] = torch.tensor(
            [1.0, 0.0, 1.0, 1.0001], dtype=torch.float32
        )

        with self.assertRaisesRegex(RuntimeError, r"spatial mask values must be in \[0, 1\]"):
            denoise_with_TDM(
                **inputs,
                control_plan=self._projection_plan(),
            )

    def test_projection_trace_is_written_to_control_trace_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            inputs = self._projection_inputs(vis_path=temp_dir)
            _, _ = denoise_with_TDM(
                **inputs,
                control_plan=self._projection_plan(),
            )

            payload = json.loads((Path(temp_dir) / "control_trace.json").read_text())
            self.assertEqual(payload["trace"][0]["latent_projection"], "source_outside_mask")
            self.assertEqual(payload["latent_projection_trace"][0]["source_latent_index"], 1)

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
