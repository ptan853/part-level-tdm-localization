#!/usr/bin/env python3
"""Analyze blinded held-out ratings with case-paired stratified bootstrap CIs."""

from __future__ import annotations

import argparse
from itertools import combinations
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCORE_FIELDS = (
    "local_edit_success_0_2",
    "non_target_preservation_0_2",
    "overall_prompt_adherence_0_2",
    "visual_quality_0_2",
)
METHODS = (
    "original_fys_tdm",
    "endpoint_projection",
    "residual_rk2",
    "endpoint_projection_n3",
)


def weighted_cohen_kappa(a: np.ndarray, b: np.ndarray) -> float:
    """Linearly weighted Cohen's kappa for ordinal scores 0, 1, and 2."""
    a = np.asarray(a, dtype=int)
    b = np.asarray(b, dtype=int)
    if a.shape != b.shape or a.size == 0:
        raise ValueError("kappa inputs must be non-empty and have the same shape")
    if np.any((a < 0) | (a > 2) | (b < 0) | (b > 2)):
        raise ValueError("kappa scores must be integers from 0 through 2")
    observed = np.zeros((3, 3), dtype=float)
    for left, right in zip(a, b):
        observed[left, right] += 1
    observed /= observed.sum()
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0))
    disagreement = np.abs(np.arange(3)[:, None] - np.arange(3)[None, :]) / 2
    observed_cost = float((disagreement * observed).sum())
    expected_cost = float((disagreement * expected).sum())
    if expected_cost == 0:
        return 1.0 if observed_cost == 0 else float("nan")
    return float(1 - observed_cost / expected_cost)


def add_derived_outcomes(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    local = pd.to_numeric(output["local_edit_success_0_2"], errors="raise").astype(int)
    preservation = pd.to_numeric(
        output["non_target_preservation_0_2"], errors="raise"
    ).astype(int)
    output["joint_success"] = ((local >= 1) & (preservation >= 1)).astype(int)
    output["strict_joint_success"] = ((local == 2) & (preservation == 2)).astype(int)
    return output


def paired_stratified_bootstrap(
    frame: pd.DataFrame,
    *,
    metric: str,
    method_a: str,
    method_b: str,
    iterations: int = 10_000,
    seed: int = 20260903,
) -> dict[str, float | str | int]:
    selected = frame[frame["method"].isin([method_a, method_b])].copy()
    case_methods = selected.groupby(["case_uid", "method"])[metric].mean().unstack()
    complete = case_methods[[method_a, method_b]].dropna()
    strata = selected.drop_duplicates("case_uid").set_index("case_uid")["part_size"]
    complete = complete.join(strata.rename("part_size"), how="left")
    if complete.empty or complete["part_size"].isna().any():
        raise ValueError(
            "paired bootstrap requires complete paired cases with part_size"
        )
    observed = float((complete[method_a] - complete[method_b]).mean())
    rng = np.random.default_rng(seed)
    samples = np.empty(iterations, dtype=float)
    groups = [group for _, group in complete.groupby("part_size", sort=True)]
    for iteration in range(iterations):
        differences = []
        for group in groups:
            sampled = rng.integers(0, len(group), size=len(group))
            differences.extend(
                (group.iloc[sampled][method_a] - group.iloc[sampled][method_b]).tolist()
            )
        samples[iteration] = float(np.mean(differences))
    return {
        "metric": metric,
        "method_a": method_a,
        "method_b": method_b,
        "difference": observed,
        "ci_low": float(np.quantile(samples, 0.025)),
        "ci_high": float(np.quantile(samples, 0.975)),
        "iterations": iterations,
    }


def load_completed_reviews(pairs: list[tuple[Path, Path]]) -> pd.DataFrame:
    merged = []
    for scores_path, mapping_path in pairs:
        scores = pd.read_csv(scores_path, dtype=str).fillna("")
        mapping = pd.read_csv(mapping_path, dtype=str)
        if (
            scores["review_uid"].duplicated().any()
            or mapping["review_uid"].duplicated().any()
        ):
            raise ValueError("review files contain duplicate review_uid values")
        joined = mapping.merge(
            scores, on="review_uid", how="left", validate="one_to_one"
        )
        for field in SCORE_FIELDS:
            values = pd.to_numeric(joined[field], errors="coerce")
            if values.isna().any() or not values.isin([0, 1, 2]).all():
                raise ValueError(
                    f"incomplete or invalid scores in {scores_path}: {field}"
                )
            joined[field] = values.astype(int)
        merged.append(joined)
    frame = pd.concat(merged, ignore_index=True)
    expected = len(frame["reviewer_id"].unique()) * 240
    if len(frame) != expected:
        raise ValueError(f"expected 240 ratings per reviewer, found {len(frame)} total")
    return add_derived_outcomes(frame)


def interrater_table(frame: pd.DataFrame) -> pd.DataFrame:
    reviewers = sorted(frame["reviewer_id"].unique())
    if len(reviewers) != 2:
        raise ValueError("inter-rater analysis requires exactly two reviewers")
    left = frame[frame["reviewer_id"] == reviewers[0]].set_index("row_uid")
    right = frame[frame["reviewer_id"] == reviewers[1]].set_index("row_uid")
    common = left.index.intersection(right.index)
    if len(common) != 240:
        raise ValueError(
            f"reviewers must share exactly 240 output IDs, found {len(common)}"
        )
    return pd.DataFrame(
        [
            {
                "criterion": field,
                "linear_weighted_cohen_kappa": weighted_cohen_kappa(
                    left.loc[common, field], right.loc[common, field]
                ),
            }
            for field in SCORE_FIELDS
        ]
    )


def evaluate_registered_success(
    summary: pd.DataFrame,
    comparisons: pd.DataFrame,
) -> dict[str, Any]:
    def residual_minus_baseline_ci_low(metric: str, baseline: str) -> float:
        direct = comparisons[
            (comparisons["metric"] == metric)
            & (comparisons["method_a"] == "residual_rk2")
            & (comparisons["method_b"] == baseline)
        ]
        if len(direct) == 1:
            return float(direct.iloc[0]["ci_low"])

        reverse = comparisons[
            (comparisons["metric"] == metric)
            & (comparisons["method_a"] == baseline)
            & (comparisons["method_b"] == "residual_rk2")
        ]
        if len(reverse) == 1:
            # If the stored interval is baseline - residual, reversing the
            # contrast changes [low, high] to [-high, -low].
            return -float(reverse.iloc[0]["ci_high"])

        raise ValueError(
            f"missing unique registered comparison for {metric} versus {baseline}"
        )

    preservation = all(
        residual_minus_baseline_ci_low(
            "non_target_preservation_0_2", baseline
        )
        > 0
        for baseline in ("endpoint_projection", "original_fys_tdm")
    )
    baseline_means = summary.loc[
        ["endpoint_projection", "original_fys_tdm"],
        "local_edit_success_0_2",
    ]
    stronger_baseline = str(baseline_means.idxmax())
    local_edit = (
        residual_minus_baseline_ci_low(
            "local_edit_success_0_2", stronger_baseline
        )
        > -0.20
    )
    joint = bool(
        summary.loc["residual_rk2", "joint_success"]
        - summary.loc["original_fys_tdm", "joint_success"]
        >= 0.10
        and summary.loc["residual_rk2", "joint_success"]
        >= summary.loc["endpoint_projection", "joint_success"]
    )
    return {
        "preservation_superiority": bool(preservation),
        "local_edit_noninferiority": bool(local_edit),
        "stronger_local_edit_baseline": stronger_baseline,
        "joint_utility": joint,
        "all_primary_criteria_met": bool(preservation and local_edit and joint),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--review",
        action="append",
        nargs=2,
        metavar=("SCORES", "MAPPING"),
        required=True,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260903)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    pairs = [(Path(scores), Path(mapping)) for scores, mapping in args.review]
    frame = load_completed_reviews(pairs)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_dir / "reviewer_level_scores.csv", index=False)
    interrater_table(frame).to_csv(output_dir / "interrater_kappa.csv", index=False)

    summary_metrics = [*SCORE_FIELDS, "joint_success", "strict_joint_success"]
    summary = frame.groupby("method")[summary_metrics].mean().reindex(METHODS)
    summary.to_csv(output_dir / "human_method_summary.csv")
    comparisons: list[dict[str, Any]] = []
    for method_a, method_b in combinations(METHODS, 2):
        for metric in summary_metrics:
            comparisons.append(
                paired_stratified_bootstrap(
                    frame,
                    metric=metric,
                    method_a=method_a,
                    method_b=method_b,
                    iterations=args.iterations,
                    seed=args.seed,
                )
            )
    comparisons_frame = pd.DataFrame(comparisons)
    comparisons_frame.to_csv(
        output_dir / "paired_bootstrap_comparisons.csv", index=False
    )
    (output_dir / "registered_success_criteria.json").write_text(
        json.dumps(
            evaluate_registered_success(summary, comparisons_frame), indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "analysis_metadata.json").write_text(
        json.dumps(
            {
                "bootstrap_iterations": args.iterations,
                "bootstrap_seed": args.seed,
                "kappa_weighting": "linear",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"analysis: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
