from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"
sys.path.insert(0, str(FYS_SRC))

from flux.attention_control import AttentionControl, apply_attention_control  # noqa: E402


class AttentionControlTests(unittest.TestCase):
    def test_spatial_bias_changes_only_image_query_edit_columns(self):
        logits = torch.zeros(1, 2, 6, 6)
        control = AttentionControl(
            operation="spatial_logit_bias",
            txt_len=2,
            edit_token_indices=(1,),
            image_mask=torch.tensor([1.0, 0.0, 1.0, 0.0]),
            strength=1.0,
            epsilon=0.01,
        )

        actual = apply_attention_control(logits, control)

        self.assertEqual(actual[0, 0, 2, 1].item(), 0.0)
        self.assertTrue(torch.isclose(actual[0, 0, 3, 1], torch.tensor(math.log(0.01))))
        self.assertEqual(actual[0, 0, 4, 1].item(), 0.0)
        self.assertTrue(torch.isclose(actual[0, 0, 5, 1], torch.tensor(math.log(0.01))))
        torch.testing.assert_close(actual[:, :, :2, :], logits[:, :, :2, :])
        torch.testing.assert_close(actual[:, :, 2:, 0], logits[:, :, 2:, 0])
        torch.testing.assert_close(actual[:, :, 2:, 2:], logits[:, :, 2:, 2:])

    def test_spatial_bias_applies_to_every_edit_subtoken(self):
        logits = torch.zeros(1, 1, 5, 5)
        control = AttentionControl(
            operation="spatial_logit_bias",
            txt_len=3,
            edit_token_indices=(1, 2),
            image_mask=torch.tensor([0.0, 1.0]),
            epsilon=0.1,
        )

        actual = apply_attention_control(logits, control)

        expected_bias = torch.tensor(math.log(0.1))
        torch.testing.assert_close(actual[0, 0, 3, [1, 2]], expected_bias.expand(2))
        torch.testing.assert_close(actual[0, 0, 4, [1, 2]], torch.zeros(2))

    def test_full_transfer_copies_mean_part_logits_to_each_edit_column(self):
        logits = torch.arange(36, dtype=torch.float32).reshape(1, 1, 6, 6)
        control = AttentionControl(
            operation="part_to_edit_logit_transfer",
            txt_len=3,
            part_token_indices=(0, 1),
            edit_token_indices=(2,),
            strength=1.0,
        )

        actual = apply_attention_control(logits, control)

        expected = logits[:, :, 3:, [0, 1]].mean(dim=-1)
        torch.testing.assert_close(actual[:, :, 3:, 2], expected)
        torch.testing.assert_close(actual[:, :, :3, :], logits[:, :, :3, :])
        torch.testing.assert_close(actual[:, :, 3:, 3:], logits[:, :, 3:, 3:])

    def test_zero_transfer_strength_is_exact_noop(self):
        logits = torch.randn(2, 3, 7, 7)
        control = AttentionControl(
            operation="part_to_edit_logit_transfer",
            txt_len=3,
            part_token_indices=(0,),
            edit_token_indices=(2,),
            strength=0.0,
        )

        actual = apply_attention_control(logits, control)

        self.assertIs(actual, logits)

    def test_rejects_mask_length_mismatch(self):
        control = AttentionControl(
            operation="spatial_logit_bias",
            txt_len=2,
            edit_token_indices=(1,),
            image_mask=torch.ones(3),
        )

        with self.assertRaisesRegex(ValueError, "image_mask length"):
            apply_attention_control(torch.zeros(1, 1, 6, 6), control)

    def test_rejects_missing_part_tokens_for_transfer(self):
        control = AttentionControl(
            operation="part_to_edit_logit_transfer",
            txt_len=2,
            edit_token_indices=(1,),
            part_token_indices=(),
        )

        with self.assertRaisesRegex(ValueError, "part_token_indices"):
            apply_attention_control(torch.zeros(1, 1, 6, 6), control)


if __name__ == "__main__":
    unittest.main()
