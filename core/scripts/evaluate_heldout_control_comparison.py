#!/usr/bin/env python3
"""Evaluate the frozen held-out control comparison under one metric contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import binary_dilation


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_latent_projection_against_fys import (  # noqa: E402
    OutsideLpips,
    compute_image_metrics,
    load_mask,
    load_rgb,
)
from analyze_heldout_reviews import paired_stratified_bootstrap  # noqa: E402


EVALUATED_METHODS = {
    "original_fys_tdm",
    "endpoint_projection",
    "residual_rk2",
    "endpoint_projection_n3",
}
PROTOCOL_IMAGE_SIZE = (512, 512)


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def build_evaluation_rows(
    repo_root: Path,
    manifest: list[dict[str, Any]],
    run_matrix: pd.DataFrame,
) -> pd.DataFrame:
    records = {str(record["case_uid"]): record for record in manifest}
    scouts: dict[tuple[str, int], Path] = {}
    for row in run_matrix.to_dict("records"):
        if row["role"] != "attention_mask_scout":
            continue
        config = json.loads(row["run_config"])
        scout_dir = _resolve(repo_root, config["output_dir"]) / "tdm"
        scouts[(str(row["case_uid"]), int(row["seed"]))] = scout_dir

    rows = []
    for row in run_matrix.to_dict("records"):
        method = str(row["role"])
        if method not in EVALUATED_METHODS:
            continue
        case_uid = str(row["case_uid"])
        seed = int(row["seed"])
        if case_uid not in records:
            raise KeyError(f"run matrix case is absent from manifest: {case_uid}")
        if (case_uid, seed) not in scouts:
            raise ValueError(f"missing shared scout row for {case_uid}, seed {seed}")
        record = records[case_uid]
        config = json.loads(row["run_config"])
        scout_dir = scouts[(case_uid, seed)]
        rows.append(
            {
                "row_uid": f"{method}::{case_uid}::seed_{seed:03d}",
                "case_uid": case_uid,
                "seed": seed,
                "method": method,
                "part": record["part"],
                "edit": record["edit"],
                "part_size": record["part_size"],
                "footprint_change": record["footprint_change"],
                "source_prompt": record["source_prompt"],
                "target_prompt": record["target_prompt"],
                "source_image": str(_resolve(repo_root, record["source_image"])),
                "gt_mask": str(_resolve(repo_root, record["gt_mask"])),
                "edited_image": str(
                    _resolve(repo_root, config["output_dir"]) / "img_0.jpg"
                ),
                "scout_binary_mask": str(scout_dir / "hybrid_binary_tdm_attention.npy"),
                "scout_soft_mask": str(scout_dir / "hybrid_smoothed_tdm_attention.npy"),
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("run matrix contains no evaluated outputs")
    if frame["row_uid"].duplicated().any():
        raise ValueError("evaluation rows contain duplicate row_uid values")
    return frame.sort_values(["method", "case_uid", "seed"]).reset_index(drop=True)


def _average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = labels.astype(bool).ravel()
    scores = scores.astype(float).ravel()
    positives = int(labels.sum())
    if positives == 0:
        return float("nan")
    order = np.argsort(-scores, kind="stable")
    ranked = labels[order]
    precision = np.cumsum(ranked) / np.arange(1, ranked.size + 1)
    return float(precision[ranked].sum() / positives)


def compute_localization_metrics(
    soft_mask: np.ndarray,
    binary_mask: np.ndarray,
    gt_mask: np.ndarray,
) -> dict[str, float]:
    soft = np.asarray(soft_mask, dtype=np.float32).squeeze()
    binary = np.asarray(binary_mask).squeeze() > 0
    gt = np.asarray(gt_mask).squeeze() > 0
    if soft.shape != binary.shape or soft.shape != gt.shape:
        raise ValueError(
            f"localization maps must share a shape: {soft.shape}, {binary.shape}, {gt.shape}"
        )
    intersection = int(np.logical_and(binary, gt).sum())
    union = int(np.logical_or(binary, gt).sum())
    gt_area = int(gt.sum())
    return {
        "mask_iou": float(intersection / union) if union else float("nan"),
        "mask_ap": _average_precision(gt, soft),
        "mask_area_over_gt": float(binary.sum() / gt_area) if gt_area else float("nan"),
    }


def dilate_mask_by_token_radius(
    mask: np.ndarray,
    *,
    token_radius: int = 2,
    token_grid_size: int = 32,
) -> np.ndarray:
    mask = np.asarray(mask).astype(bool)
    pixel_radius = max(1, int(round(min(mask.shape) * token_radius / token_grid_size)))
    yy, xx = np.ogrid[
        -pixel_radius : pixel_radius + 1, -pixel_radius : pixel_radius + 1
    ]
    disk = xx * xx + yy * yy <= pixel_radius * pixel_radius
    return binary_dilation(mask, structure=disk)


def _resize_mask_array(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    image = Image.fromarray((np.asarray(mask).squeeze() > 0).astype(np.uint8) * 255)
    return np.asarray(image.resize(size, Image.Resampling.NEAREST)) > 0


def load_protocol_inputs(
    source_path: Path,
    edited_path: Path,
    gt_mask_path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (
        load_rgb(source_path, size=PROTOCOL_IMAGE_SIZE),
        load_rgb(edited_path, size=PROTOCOL_IMAGE_SIZE),
        load_mask(gt_mask_path, size=PROTOCOL_IMAGE_SIZE),
    )


def evaluate_rows(rows: pd.DataFrame, lpips_policy: str = "auto") -> pd.DataFrame:
    lpips_metric = OutsideLpips(lpips_policy)
    output = []
    localization_cache: dict[tuple[str, int], dict[str, float]] = {}
    for row in rows.to_dict("records"):
        paths = {
            key: Path(row[key])
            for key in (
                "source_image",
                "gt_mask",
                "edited_image",
                "scout_binary_mask",
                "scout_soft_mask",
            )
        }
        missing = [str(path) for path in paths.values() if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                f"missing held-out evaluation artifacts for {row['row_uid']}: {missing}"
            )
        source, edited, gt = load_protocol_inputs(
            paths["source_image"], paths["edited_image"], paths["gt_mask"]
        )
        buffered_gt = dilate_mask_by_token_radius(gt)
        strict = compute_image_metrics(source, edited, gt)
        buffered = compute_image_metrics(source, edited, buffered_gt)
        strict_lpips = lpips_metric(source, edited, gt)
        buffered_lpips = lpips_metric(source, edited, buffered_gt)

        key = (str(row["case_uid"]), int(row["seed"]))
        if key not in localization_cache:
            soft = np.load(paths["scout_soft_mask"])
            binary = np.load(paths["scout_binary_mask"])
            map_shape = np.asarray(soft).squeeze().shape
            gt_grid = _resize_mask_array(gt, (map_shape[1], map_shape[0]))
            localization_cache[key] = compute_localization_metrics(
                soft, binary, gt_grid
            )

        metrics = dict(localization_cache[key])
        metrics.update({f"strict_{name}": value for name, value in strict.items()})
        metrics.update({f"buffered_{name}": value for name, value in buffered.items()})
        metrics["strict_outside_mask_lpips"] = strict_lpips
        metrics["buffered_outside_mask_lpips"] = buffered_lpips
        output.append({**row, **metrics})
    return pd.DataFrame(output)


def summarize_automatic_metrics(
    evaluated: pd.DataFrame,
    *,
    metric_columns: list[str],
    iterations: int = 10_000,
    seed: int = 20260903,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = sorted(set(metric_columns) - set(evaluated.columns))
    if missing:
        raise ValueError(f"automatic metric table is missing columns: {missing}")
    methods = sorted(evaluated["method"].unique())
    summary = evaluated.groupby("method")[metric_columns].mean().reset_index()
    comparisons = []
    for method_a in methods:
        for method_b in methods:
            if method_a == method_b:
                continue
            for metric in metric_columns:
                comparisons.append(
                    paired_stratified_bootstrap(
                        evaluated,
                        metric=metric,
                        method_a=method_a,
                        method_b=method_b,
                        iterations=iterations,
                        seed=seed,
                    )
                )
    return summary, pd.DataFrame(comparisons)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lpips", choices=("off", "auto", "require"), default="auto")
    parser.add_argument("--bootstrap-iterations", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260903)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    manifest = json.loads(
        _resolve(repo_root, args.manifest).read_text(encoding="utf-8")
    )
    matrix = pd.read_csv(_resolve(repo_root, args.run_matrix))
    rows = build_evaluation_rows(repo_root, manifest, matrix)
    evaluated = evaluate_rows(rows, lpips_policy=args.lpips)
    output = _resolve(repo_root, args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    evaluated.to_csv(output, index=False)
    automatic_columns = [
        column
        for column in evaluated.columns
        if column.startswith(("strict_", "buffered_"))
    ]
    summary, comparisons = summarize_automatic_metrics(
        evaluated,
        metric_columns=automatic_columns,
        iterations=args.bootstrap_iterations,
        seed=args.bootstrap_seed,
    )
    summary.to_csv(output.with_name(f"{output.stem}_method_summary.csv"), index=False)
    comparisons.to_csv(
        output.with_name(f"{output.stem}_paired_bootstrap.csv"), index=False
    )
    print(f"saved: {output}")
    print(f"evaluated rows: {len(evaluated)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
