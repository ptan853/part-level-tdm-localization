from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"
sys.path.insert(0, str(FYS_SRC))

from flux.spatial_mask_io import load_precomputed_spatial_mask  # noqa: E402


class SpatialMaskIoTests(unittest.TestCase):
    def test_loads_precomputed_patch_grid_mask(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mask.npy"
            np.save(path, np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float32))

            actual = load_precomputed_spatial_mask(path, expected_shape=(2, 2))

        np.testing.assert_array_equal(
            actual, np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float32)
        )

    def test_rejects_wrong_grid_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mask.npy"
            np.save(path, np.ones((4, 4), dtype=np.float32))

            with self.assertRaisesRegex(ValueError, "expected patch-grid shape"):
                load_precomputed_spatial_mask(path, expected_shape=(2, 2))

    def test_rejects_non_binary_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mask.npy"
            np.save(path, np.array([[0.0, 0.5], [1.0, 0.0]], dtype=np.float32))

            with self.assertRaisesRegex(ValueError, "binary"):
                load_precomputed_spatial_mask(path, expected_shape=(2, 2))

    def test_rejects_non_finite_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mask.npy"
            np.save(path, np.array([[0.0, np.nan], [1.0, 0.0]], dtype=np.float32))

            with self.assertRaisesRegex(ValueError, "finite"):
                load_precomputed_spatial_mask(path, expected_shape=(2, 2))


if __name__ == "__main__":
    unittest.main()
