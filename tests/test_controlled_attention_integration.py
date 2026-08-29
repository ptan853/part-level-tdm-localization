from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest import mock

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"
sys.path.insert(0, str(FYS_SRC))

from flux.attention_control import AttentionControl, apply_attention_control  # noqa: E402
from flux.math import attention  # noqa: E402
from flux.modules.layers import (  # noqa: E402
    apply_image_kv_control,
    resolve_block_attention_control,
    resolve_image_kv_injection,
)


class ControlledAttentionIntegrationTests(unittest.TestCase):
    def test_block_control_is_enabled_only_for_selected_layers(self):
        control = object()
        info = {
            "id": 27,
            "attention_control": control,
            "attention_control_layers": (28, 29),
        }

        self.assertIsNone(resolve_block_attention_control(info))
        info["id"] = 28
        self.assertIs(resolve_block_attention_control(info), control)
        self.assertIsNone(resolve_block_attention_control(None))

    def test_image_kv_injection_preserves_legacy_and_supports_plan_layers(self):
        self.assertFalse(resolve_image_kv_injection({"inject": False, "id": 37}))
        self.assertFalse(resolve_image_kv_injection({"inject": True, "id": 19}))
        self.assertTrue(resolve_image_kv_injection({"inject": True, "id": 20}))
        self.assertFalse(
            resolve_image_kv_injection(
                {"inject": True, "id": 20, "image_kv_layers": (28, 29)}
            )
        )
        self.assertTrue(
            resolve_image_kv_injection(
                {"inject": True, "id": 28, "image_kv_layers": (28, 29)}
            )
        )

    def test_attention_without_control_uses_fused_sdpa(self):
        q = torch.randn(1, 1, 3, 2)
        k = torch.randn(1, 1, 3, 2)
        v = torch.randn(1, 1, 3, 2)
        sentinel = torch.randn_like(v)

        with mock.patch("flux.math.apply_rope", return_value=(q, k)):
            with mock.patch(
                "torch.nn.functional.scaled_dot_product_attention",
                return_value=sentinel,
            ) as fused:
                actual = attention(q, k, v, pe=None, control=None)

        fused.assert_called_once_with(q, k, v)
        torch.testing.assert_close(actual, sentinel.transpose(1, 2).reshape(1, 3, 2))

    def test_source_all_ignores_an_existing_edit_map(self):
        source_k = torch.full((1, 1, 3, 1), 2.0)
        source_v = torch.full((1, 1, 3, 1), 3.0)
        current_k = torch.full((1, 1, 3, 1), 7.0)
        current_v = torch.full((1, 1, 3, 1), 11.0)
        info = {
            "t": 1.0,
            "second_order": False,
            "id": 20,
            "type": "src",
            "inverse": False,
            "image_kv_operation": "source_all",
            "edit_map": torch.tensor([1]),
            "feature": {
                "1.0_False_20_src_K": source_k,
                "1.0_False_20_src_V": source_v,
            },
        }

        actual_k, actual_v = apply_image_kv_control(
            info, current_k, current_v, torch.zeros(1)
        )

        torch.testing.assert_close(actual_k, source_k)
        torch.testing.assert_close(actual_v, source_v)

    def test_source_outside_mask_keeps_target_values_only_inside_edit_map(self):
        source_k = torch.zeros(1, 1, 3, 1)
        source_v = torch.zeros(1, 1, 3, 1)
        current_k = torch.tensor([[[[4.0], [5.0], [6.0]]]])
        current_v = torch.tensor([[[[7.0], [8.0], [9.0]]]])
        info = {
            "t": 1.0,
            "second_order": False,
            "id": 20,
            "type": "src",
            "inverse": False,
            "image_kv_operation": "source_outside_mask",
            "edit_map": torch.tensor([1]),
            "feature": {
                "1.0_False_20_src_K": source_k,
                "1.0_False_20_src_V": source_v,
            },
        }

        actual_k, actual_v = apply_image_kv_control(
            info, current_k, current_v, torch.zeros(1)
        )

        torch.testing.assert_close(actual_k.flatten(), torch.tensor([0.0, 5.0, 0.0]))
        torch.testing.assert_close(actual_v.flatten(), torch.tensor([0.0, 8.0, 0.0]))

    def test_controlled_attention_matches_explicit_softmax(self):
        q = torch.tensor([[[[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]]])
        k = torch.tensor([[[[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]]])
        v = torch.tensor([[[[1.0, 0.0], [0.0, 2.0], [3.0, 3.0]]]])
        control = AttentionControl(
            operation="spatial_logit_bias",
            txt_len=1,
            edit_token_indices=(0,),
            image_mask=torch.tensor([1.0, 0.0]),
            epsilon=0.01,
        )

        logits = torch.matmul(q, k.transpose(-2, -1)) * (q.shape[-1] ** -0.5)
        expected_logits = apply_attention_control(logits, control)
        expected = torch.matmul(torch.softmax(expected_logits.float(), dim=-1), v)
        expected = expected.transpose(1, 2).reshape(1, 3, 2)

        with mock.patch("flux.math.apply_rope", return_value=(q, k)):
            with mock.patch(
                "torch.nn.functional.scaled_dot_product_attention"
            ) as fused:
                actual = attention(q, k, v, pe=None, control=control)

        fused.assert_not_called()
        torch.testing.assert_close(actual, expected)


if __name__ == "__main__":
    unittest.main()
