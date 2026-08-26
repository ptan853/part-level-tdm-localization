import importlib.util
import json
import importlib
import tempfile
from pathlib import Path
import sys
import unittest

import numpy as np
import torch
from torch import nn


REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = (
    REPO_ROOT
    / "core"
    / "third_party"
    / "FollowYourShape"
    / "src"
    / "flux"
    / "same_state_probe.py"
)
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"


def load_probe_module():
    sys.path.insert(0, str(FYS_SRC))
    spec = importlib.util.spec_from_file_location("flux.same_state_probe", PROBE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_flux_model_module():
    sys.path.insert(0, str(FYS_SRC))
    return importlib.import_module("flux.model")


def build_tiny_flux():
    flux_model = load_flux_model_module()
    params = flux_model.FluxParams(
        in_channels=2,
        vec_in_dim=4,
        context_in_dim=3,
        hidden_size=4,
        mlp_ratio=1.0,
        num_heads=1,
        depth=0,
        depth_single_blocks=1,
        axes_dim=[2, 2],
        theta=10000,
        qkv_bias=False,
        guidance_embed=False,
    )
    return flux_model.Flux(params)


def build_tiny_flux_inputs():
    return {
        "img": torch.tensor([[[0.1, -0.2], [0.3, 0.4]]], dtype=torch.float32),
        "img_ids": torch.zeros(1, 2, 2, dtype=torch.float32),
        "txt": torch.tensor([[[0.0, 0.1, 0.2], [0.3, 0.4, 0.5]]], dtype=torch.float32),
        "txt_ids": torch.zeros(1, 2, 2, dtype=torch.float32),
        "y": torch.tensor([[0.2, -0.1, 0.4, 0.0]], dtype=torch.float32),
        "timesteps": torch.tensor([0.75], dtype=torch.float32),
        "guidance": torch.tensor([1.5], dtype=torch.float32),
    }


class ZeroModulation(nn.Module):
    def __init__(self, hidden_size: int):
        super().__init__()
        self.hidden_size = hidden_size

    def forward(self, vec):
        zeros = torch.zeros(vec.shape[0], 1, self.hidden_size, dtype=vec.dtype, device=vec.device)
        return type("ModOut", (), {"shift": zeros, "scale": zeros, "gate": zeros}), None


class IdentityNorm(nn.Module):
    def forward(self, q, k, v):
        return q, k


class DummySingleBlock(nn.Module):
    def __init__(self, hidden_size: int = 4, num_heads: int = 1):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.mlp_hidden_dim = 0
        self.modulation = ZeroModulation(hidden_size)
        self.pre_norm = nn.Identity()
        self.linear1 = nn.Linear(hidden_size, hidden_size * 3, bias=True)
        self.norm = IdentityNorm()
        with torch.no_grad():
            self.linear1.weight.zero_()
            self.linear1.bias[: hidden_size * 2].fill_(1.0)
            self.linear1.bias[hidden_size * 2 :].zero_()

    def forward(self, x, *, vec, pe, info):
        return x, info


class DummyModel:
    def __init__(self):
        self.single_blocks = nn.ModuleList([DummySingleBlock()])


class RecordingModel:
    def __init__(self, target_pred: torch.Tensor):
        self.target_pred = target_pred
        self.calls = []

    def __call__(
        self,
        *,
        img,
        img_ids,
        txt,
        txt_ids,
        y,
        timesteps,
        guidance,
        info,
        controlnet_block_samples=None,
        controlnet_single_block_samples=None,
    ):
        self.calls.append(
            {
                "img": img,
                "img_ids": img_ids,
                "txt": txt,
                "txt_ids": txt_ids,
                "y": y,
                "timesteps": timesteps,
                "guidance": guidance,
                "info": info,
            }
        )
        return self.target_pred, info


class RecordingFluxWrapper:
    def __init__(self, flux_model):
        self.flux_model = flux_model
        self.calls = []

    def __call__(
        self,
        *,
        img,
        img_ids,
        txt,
        txt_ids,
        y,
        timesteps,
        guidance,
        info,
        controlnet_block_samples=None,
        controlnet_single_block_samples=None,
    ):
        self.calls.append({"info_before": dict(info) if info is not None else None})
        pred, returned_info = self.flux_model(
            img=img,
            img_ids=img_ids,
            txt=txt,
            txt_ids=txt_ids,
            y=y,
            timesteps=timesteps,
            guidance=guidance,
            info=info,
            controlnet_block_samples=controlnet_block_samples,
            controlnet_single_block_samples=controlnet_single_block_samples,
        )
        self.calls[-1]["info_after"] = dict(returned_info) if returned_info is not None else None
        return pred, returned_info


class DummyAttentionProbe:
    def __init__(self):
        self.finish_calls = 0

    def finish_step(self):
        self.finish_calls += 1


class SameStateProbeTest(unittest.TestCase):
    def test_compute_velocity_delta_and_aggregate_step_maps(self):
        probe = load_probe_module()
        source = torch.tensor([[[0.0, 0.0], [1.0, 1.0]]])
        target = torch.tensor([[[3.0, 4.0], [1.0, 1.0]]])

        np.testing.assert_allclose(
            probe.compute_velocity_delta(source, target),
            np.array([5.0, 0.0], dtype=np.float32),
        )

        aggregate = probe.aggregate_step_maps(
            [
                np.array([[0.0, 2.0]], dtype=np.float32),
                np.array([[3.0, 0.0]], dtype=np.float32),
            ]
        )
        np.testing.assert_allclose(aggregate, np.array([[0.5, 0.5]], dtype=np.float32))

    def test_process_signal_map_rejects_empty_step_sequence(self):
        probe = load_probe_module()

        with self.assertRaisesRegex(ValueError, "step_maps"):
            probe.process_signal_map([])

    def test_process_signal_map_preserves_shape_and_returns_finite_outputs(self):
        probe = load_probe_module()
        result = probe.process_signal_map(
            [
                np.array([[0.0, 2.0], [1.0, 3.0]], dtype=np.float32),
                np.array([[4.0, 1.0], [0.0, 2.0]], dtype=np.float32),
            ],
            sigma=0.0,
        )

        self.assertEqual(result["raw"].shape, (2, 2))
        self.assertEqual(result["smoothed"].shape, (2, 2))
        self.assertEqual(result["binary"].shape, (2, 2))
        self.assertTrue(np.isfinite(result["raw"]).all())
        self.assertTrue(np.isfinite(result["smoothed"]).all())
        self.assertIsInstance(result["threshold"], float)

    def test_named_attention_probe_keeps_part_and_edit_groups_separate(self):
        probe = load_probe_module()
        model = DummyModel()
        attention_probe = probe.NamedSingleBlockAttentionProbe(
            model=model,
            token_groups={"part": [0], "edit": [1]},
            txt_len=2,
            layer_ids=[0],
        )

        x = torch.zeros(1, 4, 4)
        vec = torch.zeros(1, 4)
        pe = torch.zeros(1, 1, 4, 2, 2, 2)
        info = {"record_attention": True}

        try:
            model.single_blocks[0](x, vec=vec, pe=pe, info=info)
            attention_probe.finish_step()
        finally:
            attention_probe.close()

        self.assertEqual(len(attention_probe.step_records["part"]), 1)
        self.assertEqual(len(attention_probe.step_records["edit"]), 1)
        np.testing.assert_allclose(
            attention_probe.step_records["part"][0].numpy(),
            np.array([0.25, 0.25], dtype=np.float32),
        )
        np.testing.assert_allclose(
            attention_probe.step_records["edit"][0].numpy(),
            np.array([0.25, 0.25], dtype=np.float32),
        )

    def test_named_attention_probe_rejects_empty_token_group(self):
        probe = load_probe_module()

        with self.assertRaisesRegex(ValueError, "token_groups\\['part'\\]"):
            probe.NamedSingleBlockAttentionProbe(
                model=DummyModel(),
                token_groups={"part": [], "edit": [1]},
                txt_len=2,
                layer_ids=[0],
            )

    def test_named_attention_probe_rejects_empty_step_records(self):
        probe = load_probe_module()
        attention_probe = probe.NamedSingleBlockAttentionProbe(
            model=DummyModel(),
            token_groups={"part": [0], "edit": [1]},
            txt_len=2,
            layer_ids=[0],
        )

        try:
            with self.assertRaisesRegex(RuntimeError, "token group 'part'"):
                attention_probe.finish_step()
        finally:
            attention_probe.close()

    def test_actual_flux_single_block_requires_noninjecting_contract_keys(self):
        model = build_tiny_flux()
        inputs = build_tiny_flux_inputs()

        with self.assertRaisesRegex(KeyError, "inject"):
            model(info={"record_attention": False}, **inputs)

    def test_same_state_inversion_probe_uses_same_state_and_guidance(self):
        probe = load_probe_module()
        target_pred = torch.tensor([[[3.0, 4.0], [1.0, 1.0]]])
        model = RecordingModel(target_pred=target_pred)
        attention_probe = DummyAttentionProbe()
        observer = probe.SameStateInversionProbe(
            model=model,
            target_txt=torch.ones(1, 2, 4),
            target_txt_ids=torch.ones(1, 2, 3),
            target_vec=torch.ones(1, 4),
            attention_probe=attention_probe,
        )

        img = torch.zeros(1, 2, 2)
        img_ids = torch.zeros(1, 2, 3)
        timestep = torch.tensor([0.75])
        source_pred = torch.tensor([[[0.0, 0.0], [1.0, 1.0]]])
        guidance_vec = torch.tensor([2.0])

        result = observer(
            step_index=3,
            img=img,
            img_ids=img_ids,
            timestep=timestep,
            source_pred=source_pred,
            guidance_vec=guidance_vec,
        )

        self.assertIsNone(result)
        self.assertEqual(attention_probe.finish_calls, 1)
        self.assertEqual(observer.step_indices, [3])
        np.testing.assert_allclose(
            observer.velocity_step_maps[0],
            np.array([5.0, 0.0], dtype=np.float32),
        )

        self.assertEqual(len(model.calls), 1)
        model_call = model.calls[0]
        self.assertIs(model_call["img"], img)
        self.assertIs(model_call["img_ids"], img_ids)
        self.assertIs(model_call["timesteps"], timestep)
        self.assertIs(model_call["guidance"], guidance_vec)
        self.assertTrue(model_call["info"]["record_attention"])

    def test_same_state_inversion_probe_supplies_full_noninjecting_flux_payload(self):
        probe = load_probe_module()
        model = RecordingFluxWrapper(build_tiny_flux())
        inputs = build_tiny_flux_inputs()
        observer = probe.SameStateInversionProbe(
            model=model,
            target_txt=inputs["txt"],
            target_txt_ids=inputs["txt_ids"],
            target_vec=inputs["y"],
        )
        source_pred = torch.zeros_like(inputs["img"])

        observer(
            step_index=2,
            img=inputs["img"],
            img_ids=inputs["img_ids"],
            timestep=inputs["timesteps"],
            source_pred=source_pred,
            guidance_vec=inputs["guidance"],
        )

        self.assertEqual(observer.step_indices, [2])
        self.assertEqual(len(observer.velocity_step_maps), 1)
        self.assertEqual(observer.velocity_step_maps[0].shape, (inputs["img"].shape[1],))
        self.assertTrue(np.isfinite(observer.velocity_step_maps[0]).all())

        self.assertEqual(len(model.calls), 1)
        info_before = model.calls[0]["info_before"]
        self.assertEqual(
            info_before,
            {
                "feature": {},
                "map": {},
                "edit_map": None,
                "inject": False,
                "inverse": False,
                "second_order": False,
                "record_attention": False,
                "t": float(inputs["timesteps"][0].item()),
            },
        )

        info_after = model.calls[0]["info_after"]
        self.assertFalse(info_after["inject"])
        self.assertFalse(info_after["inverse"])
        self.assertFalse(info_after["second_order"])
        self.assertEqual(info_after["feature"], {})
        self.assertEqual(info_after["map"], {})
        self.assertIsNone(info_after["edit_map"])
        self.assertEqual(info_after["type"], "single")
        self.assertEqual(info_after["id"], 0)

    def test_same_state_inversion_probe_serializes_step_and_aggregate_artifacts(self):
        probe = load_probe_module()
        attention_probe = DummyAttentionProbe()
        attention_probe.token_groups = {"part": [0], "edit": [1]}
        attention_probe.layer_ids = [0]
        attention_probe.step_records = {
            "part": [
                torch.tensor([0.20, 0.80], dtype=torch.float32),
                torch.tensor([0.60, 0.40], dtype=torch.float32),
            ],
            "edit": [
                torch.tensor([0.55, 0.45], dtype=torch.float32),
                torch.tensor([0.15, 0.85], dtype=torch.float32),
            ],
        }
        observer = probe.SameStateInversionProbe(
            model=RecordingModel(target_pred=torch.zeros(1, 2, 2)),
            target_txt=torch.ones(1, 2, 4),
            target_txt_ids=torch.ones(1, 2, 3),
            target_vec=torch.ones(1, 4),
            attention_probe=attention_probe,
        )
        observer.step_indices = [0, 1]
        observer.step_timesteps = [0.75, 0.50]
        observer.velocity_step_maps = [
            np.array([1.0, 2.0], dtype=np.float32),
            np.array([3.0, 4.0], dtype=np.float32),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            observer.finalize(output_dir, {"case_uid": "case_test"})

            expected_paths = [
                "steps/step_00_velocity_delta.npy",
                "steps/step_00_velocity_delta.png",
                "steps/step_00_part_attention.npy",
                "steps/step_00_part_attention.png",
                "steps/step_00_edit_attention.npy",
                "steps/step_00_edit_attention.png",
                "steps/step_01_velocity_delta.npy",
                "steps/step_01_velocity_delta.png",
                "steps/step_01_part_attention.npy",
                "steps/step_01_part_attention.png",
                "steps/step_01_edit_attention.npy",
                "steps/step_01_edit_attention.png",
                "aggregate/velocity_delta_raw.npy",
                "aggregate/velocity_delta_smoothed.npy",
                "aggregate/velocity_delta_binary.npy",
                "aggregate/part_attention_raw.npy",
                "aggregate/part_attention_smoothed.npy",
                "aggregate/part_attention_binary.npy",
                "aggregate/edit_attention_raw.npy",
                "aggregate/edit_attention_smoothed.npy",
                "aggregate/edit_attention_binary.npy",
                "aggregate/velocity_delta_raw.png",
                "aggregate/velocity_delta_smoothed.png",
                "aggregate/velocity_delta_binary.png",
                "aggregate/part_attention_raw.png",
                "aggregate/part_attention_smoothed.png",
                "aggregate/part_attention_binary.png",
                "aggregate/edit_attention_raw.png",
                "aggregate/edit_attention_smoothed.png",
                "aggregate/edit_attention_binary.png",
                "probe_metadata.json",
            ]
            for relative_path in expected_paths:
                self.assertTrue((output_dir / relative_path).exists(), relative_path)

            metadata = json.loads((output_dir / "probe_metadata.json").read_text())
            self.assertEqual(metadata["recorded_step_indices"], [0, 1])
            self.assertEqual(metadata["case_uid"], "case_test")
            self.assertEqual(metadata["part_token_indices"], [0])
            self.assertEqual(metadata["edit_token_indices"], [1])


if __name__ == "__main__":
    unittest.main()
