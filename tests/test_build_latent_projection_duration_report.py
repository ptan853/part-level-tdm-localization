from __future__ import annotations

import unittest
from pathlib import Path

from core.scripts.build_latent_projection_duration_report import build_report


class LatentProjectionDurationReportTest(unittest.TestCase):
    def test_report_covers_method_metrics_and_reproduction(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        report = build_report(repo_root)

        self.assertIn("Latent-State Projection Duration Study", report)
        self.assertIn("Control Strategy", report)
        self.assertIn("Original FYS-TDM", report)
        self.assertIn("outside LPIPS", report)
        self.assertIn("Human Semantic Evaluation", report)
        self.assertIn("--lpips require", report)
        self.assertIn("09_evaluate_latent_projection_duration_sweep.ipynb", report)


if __name__ == "__main__":
    unittest.main()
