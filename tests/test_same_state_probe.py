import importlib.util
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


if __name__ == "__main__":
    unittest.main()
