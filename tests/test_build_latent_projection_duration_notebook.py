from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = REPO_ROOT / "core/notebooks/09_evaluate_latent_projection_duration_sweep.ipynb"


class LatentProjectionNotebookTest(unittest.TestCase):
    def test_notebook_uses_unified_metrics_and_separates_metric_families(self) -> None:
        notebook = json.loads(NOTEBOOK_PATH.read_text())
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])

        self.assertIn("unified_image_metrics.csv", source)
        self.assertIn("outside_mask_lpips", source)
        self.assertIn("outside_mask_global_ssim", source)
        self.assertIn("inside_mask_psnr", source)
        self.assertIn("Localization Metrics", source)
        self.assertIn("Human Semantic Evaluation", source)
        self.assertIn("Original FYS-TDM", source)
        self.assertIn("Oracle latent projection", source)

    def test_all_code_cells_compile(self) -> None:
        notebook = json.loads(NOTEBOOK_PATH.read_text())
        for index, cell in enumerate(notebook["cells"]):
            if cell.get("cell_type") != "code":
                continue
            compile("".join(cell.get("source", [])), f"cell_{index}", "exec")


if __name__ == "__main__":
    unittest.main()
