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
        self.assertIn("residual_human_by_part_size.png", code)
        self.assertIn("residual_per_case_human_scores.png", code)
        self.assertIn("QUALITATIVE_DURATION_GROUPS", code)
        self.assertIn("list(range(0, 8))", code)
        self.assertIn("list(range(8, 16))", code)
        self.assertIn("Original FYS-TDM", code)
        self.assertNotIn("ENDPOINT_REVIEW_PATH", code)
        self.assertIn("projection duration", markdown.lower())
        self.assertIn("part-size", markdown.lower())
        self.assertIn("N=5", markdown)
        self.assertIn("N=7", markdown)
        self.assertNotIn("remain **pending**", markdown.lower())

    def test_report_contains_complete_internal_duration_analysis(self) -> None:
        report = REPORT.read_text(encoding="utf-8")
        for section in (
            "## Method",
            "## Frozen Evaluation",
            "## Results",
            "## Interpretation",
            "## Result Artifacts",
            "## Reproduction",
        ):
            self.assertIn(section, report)
        self.assertIn("source-referenced residual", report)
        self.assertIn("LPIPS", report)
        self.assertIn("Original FYS-TDM", report)
        self.assertIn("Residual RK2", report)
        self.assertIn("N=0..15", report)
        self.assertIn("N=5", report)
        self.assertIn("N=7", report)
        self.assertIn("head -> dragon", report)
        self.assertIn("residual_image_metric_curves.png", report)
        self.assertIn("residual_human_metric_curves.png", report)
        self.assertIn("residual_human_by_part_size.png", report)
        self.assertIn("residual_per_case_human_scores.png", report)
        self.assertNotIn("empirical conclusions are **pending**", report.lower())

    def test_final_note_appends_frozen_control_method_comparison(self) -> None:
        final_note = (REPO_ROOT / "core/reports/final_note.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Control-Operation Comparison", final_note)
        self.assertIn("Endpoint projection", final_note)
        self.assertIn("Residual RK2", final_note)
        self.assertIn("`N=3`", final_note)
        self.assertIn("`N=15`", final_note)
        self.assertIn("Original FYS-TDM", final_note)
        self.assertIn("91.7%", final_note)
        for expected in (
            "### Background and hypothesis",
            "### Shared experimental setting",
            "### Endpoint latent projection",
            "### Source-referenced Residual RK2",
            "d_{i+\\frac{1}{2}}",
            "d_{i+1}",
            "control_comparison_part1.jpg",
            "control_comparison_part2.jpg",
            "oracle mask",
            "not time-aligned",
            "### Reading the Residual RK2 sweep figures",
            "Automatic preservation curves",
            "Human-score curves",
            "Part-size curves",
            "Per-case heatmaps",
            "`N=9..15` are tied on all four human summary metrics",
            "run_latent_projection_duration_sweep.py",
            "run_residual_rk2_prefix_sweep.py",
            "09_evaluate_latent_projection_duration_sweep.ipynb",
            "10_evaluate_residual_rk2_prefix_sweep.ipynb",
        ):
            self.assertIn(expected, final_note)


if __name__ == "__main__":
    unittest.main()
