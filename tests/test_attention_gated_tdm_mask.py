import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
MASK_UTILS_PATH = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src" / "flux" / "attention_mask_utils.py"
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"


def load_mask_utils_module():
    sys.path.insert(0, str(FYS_SRC))
    spec = importlib.util.spec_from_file_location("flux.attention_mask_utils", MASK_UTILS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AttentionGatedTdmMaskTest(unittest.TestCase):
    def test_original_mode_keeps_original_binary_mask(self):
        mask_utils = load_mask_utils_module()
        smoothed_tdm = np.array([[0.1, 0.8], [0.2, 0.7]], dtype=np.float32)
        original_binary = np.array([[0, 1], [0, 1]], dtype=np.uint8)

        result = mask_utils.build_attention_gated_tdm_mask(
            smoothed_tdm=smoothed_tdm,
            original_binary_tdm=original_binary,
            attention_map=None,
            mask_mode="original",
        )

        np.testing.assert_array_equal(result["binary_mask"], original_binary)
        self.assertEqual(result["selected_mask_source"], "original_tdm")

    def test_attention_gated_mode_intersects_tdm_with_attention(self):
        mask_utils = load_mask_utils_module()
        smoothed_tdm = np.array([[0.9, 0.9], [0.1, 0.1]], dtype=np.float32)
        original_binary = np.array([[1, 1], [0, 0]], dtype=np.uint8)
        attention_map = np.array([[0.0, 1.0], [0.0, 0.0]], dtype=np.float32)

        result = mask_utils.build_attention_gated_tdm_mask(
            smoothed_tdm=smoothed_tdm,
            original_binary_tdm=original_binary,
            attention_map=attention_map,
            mask_mode="attention_gated",
            smoothing_sigma=0.0,
        )

        self.assertEqual(result["selected_mask_source"], "attention_gated_tdm")
        self.assertEqual(result["binary_mask"][0, 1], 1)
        self.assertEqual(int(result["binary_mask"].sum()), 1)

    def test_oracle_mode_uses_gt_mask_without_tdm_or_attention(self):
        mask_utils = load_mask_utils_module()
        smoothed_tdm = np.array([[0.9, 0.9], [0.1, 0.1]], dtype=np.float32)
        original_binary = np.array([[1, 1], [0, 0]], dtype=np.uint8)
        oracle_binary = np.array([[0, 0], [1, 0]], dtype=np.uint8)

        result = mask_utils.build_attention_gated_tdm_mask(
            smoothed_tdm=smoothed_tdm,
            original_binary_tdm=original_binary,
            attention_map=None,
            oracle_binary_mask=oracle_binary,
            mask_mode="oracle",
        )

        np.testing.assert_array_equal(result["binary_mask"], oracle_binary)
        self.assertEqual(result["selected_mask_source"], "oracle_gt_mask")
        self.assertIsNone(result["threshold"])

    def test_oracle_mode_rejects_shape_mismatch(self):
        mask_utils = load_mask_utils_module()

        with self.assertRaisesRegex(ValueError, "oracle_binary_mask shape"):
            mask_utils.build_attention_gated_tdm_mask(
                smoothed_tdm=np.zeros((2, 2), dtype=np.float32),
                original_binary_tdm=np.zeros((2, 2), dtype=np.uint8),
                attention_map=None,
                oracle_binary_mask=np.zeros((3, 2), dtype=np.uint8),
                mask_mode="oracle",
            )


if __name__ == "__main__":
    unittest.main()
