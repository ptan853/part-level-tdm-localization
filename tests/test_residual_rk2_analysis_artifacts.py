from __future__ import annotations

import unittest
from pathlib import Path

import nbformat


REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = REPO_ROOT / "core/notebooks/10_evaluate_residual_rk2_prefix_sweep.ipynb"
REPORT = REPO_ROOT / "core/reports/residual_rk2_prefix_study.md"


class ResidualRk2AnalysisArtifactsTest(unittest.TestCase):
    def test_notebook_has_reader_facing_analysis_sections(self) -> None:
        notebook = nbformat.read(NOTEBOOK, as_version=4)
        markdown = "\n".join(
            cell.source for cell in notebook.cells if cell.cell_type == "markdown"
        )
        code = "\n".join(
            cell.source for cell in notebook.cells if cell.cell_type == "code"
        )
        for section in (
            "## TL;DR",
            "## Context and Methods",
            "## Data Integrity",
            "## Quantitative Results",
            "## Human Evaluation",
            "## Qualitative Results",
            "## Takeaways",
            "## Reproduction",
        ):
            self.assertIn(section, markdown)
        self.assertIn("unified_image_metrics.csv", code)
        self.assertIn("manual_review_scores.csv", code)
        self.assertIn("outside_mask_lpips", code)
        self.assertIn("local_edit_success_0_2", code)
        self.assertIn("projection duration", markdown.lower())

    def test_report_separates_method_metrics_and_pending_evidence(self) -> None:
        report = REPORT.read_text(encoding="utf-8")
        for section in (
            "## Method",
            "## Frozen Evaluation",
            "## Result Artifacts",
            "## Reproduction",
            "## Current Status",
        ):
            self.assertIn(section, report)
        self.assertIn("source-referenced residual", report)
        self.assertIn("LPIPS", report)
        self.assertIn("pending", report.lower())


if __name__ == "__main__":
    unittest.main()
