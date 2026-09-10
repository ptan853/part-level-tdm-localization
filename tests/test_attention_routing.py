from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core" / "scripts"))
sys.path.insert(0, str(ROOT / "core" / "third_party" / "FollowYourShape" / "src"))


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("attention_routing"),
                             "The read-only routing recorder is not implemented")
        import attention_routing
        self.module = attention_routing

    def test_chunked_statistics_match_full_joint_attention(self):
        torch.manual_seed(4)
        q, k = torch.randn(1, 3, 7, 4), torch.randn(1, 3, 7, 4)
        mask = np.array([1, 0, 1, 0], dtype=np.uint8)
        original = q.clone()
        text, mass, error = self.module.summarize_attention(q, k, 3, mask, chunk_size=1)
        weights = torch.softmax(q.float() @ k.float().transpose(-2, -1) / 2, dim=-1)
        expected = weights[0, :, [3, 5], :].mean(dim=1)
        np.testing.assert_allclose(text, expected[:, :3].numpy(), atol=1e-7)
        expected_mass = torch.stack((expected[:, :3].sum(-1),
                                     expected[:, [3, 5]].sum(-1),
                                     expected[:, [4, 6]].sum(-1)), dim=-1)
        np.testing.assert_allclose(mass, expected_mass.numpy(), atol=1e-7)
        np.testing.assert_allclose(mass.sum(-1), 1, atol=1e-6)
        self.assertLess(error, 1e-6)
        self.assertTrue(torch.equal(q, original))

    def test_uniform_attention_includes_all_text_and_padding_keys(self):
        q = torch.zeros(1, 2, 6, 4)
        text, mass, _ = self.module.summarize_attention(q, q, 2, np.array([1, 0, 0, 0]))
        np.testing.assert_allclose(text, 1 / 6)
        np.testing.assert_allclose(mass, [[2/6, 1/6, 3/6]] * 2)

    def test_invalid_mask_rejected(self):
        q = torch.zeros(1, 1, 6, 4)
        for mask in (np.zeros(4), np.ones(3), np.array([1, .5, 0, 0])):
            with self.assertRaises(ValueError):
                self.module.summarize_attention(q, q, 2, mask)

    def test_select_only_actual_forward_midpoint(self):
        info = {"inverse": False, "second_order": True,
                "inject": False, "control_trace": [{"step": 3}]}
        self.assertEqual(self.module.midpoint_step(info, info), 3)
        self.assertIsNone(self.module.midpoint_step(None, info))
        self.assertIsNone(self.module.midpoint_step(dict(info), info))
        info["second_order"] = False
        self.assertIsNone(self.module.midpoint_step(info, info))
        info.update(second_order=True, inverse=True)
        self.assertIsNone(self.module.midpoint_step(info, info))

    def test_real_flux_observer_preserves_outputs_and_restores_hooks(self):
        from flux.model import Flux, FluxParams
        from flux.modules import layers
        torch.manual_seed(7)
        model = Flux(FluxParams(4, 6, 8, 16, 2, 2, 2, 2, [2, 2, 4], 10000, True, False)).eval()
        info = {"inverse": False, "second_order": True, "inject": False,
                "control_trace": [{"step": 0}]}
        inputs = dict(img=torch.randn(1, 4, 4), img_ids=torch.zeros(1, 4, 3),
                      txt=torch.randn(1, 3, 8), txt_ids=torch.zeros(1, 3, 3),
                      timesteps=torch.tensor([.6]), y=torch.randn(1, 6), info=info)
        original_attention = layers.attention
        with torch.no_grad():
            baseline, _ = model(**inputs)
            recorder = self.module.RoutingRecorder(model, info, np.array([[1, 0], [0, 0]]),
                                                   3, layers={"double": [0], "single": [1]})
            rng = torch.get_rng_state().clone()
            with recorder:
                actual, _ = model(**inputs)
                model(**{**inputs, "info": None})  # Legacy scout must not be recorded.
            self.assertTrue(torch.equal(baseline, actual))
            self.assertTrue(torch.equal(rng, torch.get_rng_state()))
        self.assertIs(layers.attention, original_attention)
        self.assertEqual(len(recorder.records), 2)
        self.assertFalse(model._forward_pre_hooks)
        with tempfile.TemporaryDirectory() as tmp:
            recorder.save(Path(tmp), num_steps=1, tokens={"token_ids": [1, 2, 3]})
            with np.load(Path(tmp) / "attention_statistics.npz") as data:
                self.assertEqual(data["text_attention"].shape, (2, 2, 3))
            with self.assertRaises(ValueError):
                recorder.save(Path(tmp), num_steps=2, tokens={"token_ids": [1, 2, 3]})
        with self.assertRaisesRegex(RuntimeError, "synthetic"):
            with self.module.RoutingRecorder(model, info, np.ones(4), 3,
                                            layers={"double": [0], "single": [1]}):
                raise RuntimeError("synthetic failure")
        self.assertIs(layers.attention, original_attention)
        self.assertFalse(model._forward_pre_hooks)


if __name__ == "__main__":
    unittest.main()
