#!/usr/bin/env python3
"""Build the 12-case by 16-duration residual RK2 manual-review bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from build_manual_review import build_review_page  # noqa: E402
from evaluate_latent_projection_against_fys import find_repo_root  # noqa: E402


SCORE_COLUMNS = [
    "local_edit_success_0_2",
    "non_target_preservation_0_2",
]
REVIEW_COLUMNS = [
    "review_uid",
    "case_uid",
    "duration",
    "method",
    "part",
    "edit",
    "part_size",
    "target_prompt",
    "source_image",
    "gt_mask",
    "edited_image",
    *SCORE_COLUMNS,
    "short_note",
]


def normalize_review_value(value: object, *, score: bool) -> str:
    if pd.isna(value) or value == "":
        return ""
    if score:
        numeric = float(value)
        if numeric.is_integer():
            return str(int(numeric))
    return str(value)


def build_review_rows(
    metrics: pd.DataFrame,
    existing_review: pd.DataFrame | None = None,
) -> pd.DataFrame:
    required = {
        "row_uid", "case_uid", "duration", "method", "part", "edit",
        "part_size", "target_prompt", "source_image", "gt_mask", "edited_image",
    }
    missing = sorted(required - set(metrics.columns))
    if missing:
        raise ValueError(f"Metric table is missing review columns: {missing}")
    rows = metrics[metrics["method"] == "residual_rk2"].copy()
    rows["review_uid"] = rows["row_uid"].astype(str)
    rows["method"] = rows["duration"].map(
        lambda value: f"Residual RK2 prefix N={int(value)}"
    )
    for column in [*SCORE_COLUMNS, "short_note"]:
        rows[column] = ""
    if existing_review is not None and "review_uid" in existing_review.columns:
        preserve = [
            column for column in [*SCORE_COLUMNS, "short_note"]
            if column in existing_review.columns
        ]
        old = existing_review[["review_uid", *preserve]].copy()
        old = old.drop_duplicates("review_uid", keep="last")
        rows = rows.merge(old, on="review_uid", how="left", suffixes=("", "_old"))
        for column in preserve:
            old_column = f"{column}_old"
            values = rows[old_column]
            rows[column] = values.where(values.notna(), rows[column]).map(
                lambda value, is_score=column in SCORE_COLUMNS: normalize_review_value(
                    value, score=is_score
                )
            )
            rows = rows.drop(columns=[old_column])
    rows = rows[REVIEW_COLUMNS].sort_values(
        ["case_uid", "duration"]
    ).reset_index(drop=True)
    if rows.empty:
        raise ValueError("No residual_rk2 rows were found for manual review")
    if rows["review_uid"].duplicated().any():
        raise ValueError("Manual review contains duplicate review_uid values")
    return rows


def validate_completed_review(rows: pd.DataFrame, *, expected_count: int = 192) -> None:
    if len(rows) != expected_count or rows["review_uid"].nunique() != expected_count:
        raise ValueError(
            f"Expected {expected_count} unique review rows, found {len(rows)} rows "
            f"and {rows['review_uid'].nunique()} unique IDs"
        )
    invalid = pd.Series(False, index=rows.index)
    for column in SCORE_COLUMNS:
        values = pd.to_numeric(rows[column], errors="coerce")
        invalid |= values.isna() | ~values.isin([0, 1, 2])
    if invalid.any():
        raise ValueError(
            f"Manual review has {int(invalid.sum())} incomplete or invalid rows"
        )


def review_config() -> dict:
    return {
        "title": "Residual RK2 Prefix Sweep Manual Review",
        "storage_key": "residual-rk2-prefix-review-v1",
        "download_filename": "manual_review_scores.csv",
        "id_field": "review_uid",
        "image_fields": [
            {"key": "source_image", "label": "Source"},
            {"key": "gt_mask", "label": "GT part mask"},
            {"key": "edited_image", "label": "Residual RK2 output"},
        ],
        "score_fields": [
            {
                "key": "local_edit_success_0_2",
                "label": "Local edit success",
                "hint": "0 failed; 1 partial/ambiguous; 2 requested part edit is clear.",
                "values": [0, 1, 2],
            },
            {
                "key": "non_target_preservation_0_2",
                "label": "Non-target preservation",
                "hint": "0 poor; 1 partly preserved; 2 source content outside the GT part is preserved.",
                "values": [0, 1, 2],
            },
        ],
        "note_field": "short_note",
        "note_label": "Short note",
        "note_placeholder": "Describe semantic success and non-target preservation separately.",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repo_root = find_repo_root(Path.cwd())
    output_dir = repo_root / "core/results/control_operations_eval/residual_rk2_prefix_sweep"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--metrics", type=Path, default=output_dir / "unified_image_metrics.csv")
    parser.add_argument("--output-dir", type=Path, default=output_dir)
    parser.add_argument("--validate", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.validate is not None:
        completed = pd.read_csv(args.validate, dtype=str, keep_default_na=False)
        validate_completed_review(completed)
        print(f"validated: {args.validate} ({len(completed)} completed rows)")
        return 0

    output_dir = args.output_dir.resolve()
    template_path = output_dir / "manual_review_template.csv"
    existing_path = output_dir / "manual_review_scores.csv"
    existing = (
        pd.read_csv(existing_path, dtype=str, keep_default_na=False)
        if existing_path.exists()
        else (
            pd.read_csv(template_path, dtype=str, keep_default_na=False)
            if template_path.exists()
            else None
        )
    )
    rows = build_review_rows(pd.read_csv(args.metrics), existing)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows.to_csv(template_path, index=False)
    config_path = output_dir / "manual_review_config.json"
    config_path.write_text(
        json.dumps(review_config(), indent=2) + "\n", encoding="utf-8"
    )
    html_path = output_dir / "manual_review.html"
    build_review_page(
        repo_root=args.repo_root.resolve(),
        input_path=template_path,
        config_path=config_path,
        output_path=html_path,
    )
    print(f"saved: {template_path}")
    print(f"saved: {html_path}")
    print(f"review items: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
