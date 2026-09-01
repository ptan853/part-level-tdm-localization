#!/usr/bin/env python3
"""Evaluate residual RK2 prefix outputs with the frozen image-metric contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_latent_projection_against_fys import (  # noqa: E402
    build_evaluation_rows,
    evaluate_rows,
    find_repo_root,
)


DEFAULT_DURATIONS = tuple(range(16))


def repo_relative(repo_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo_root.resolve()))


def build_residual_evaluation_rows(
    repo_root: Path,
    manifest: list[dict[str, Any]],
    output_root: Path,
    *,
    durations: list[int] | tuple[int, ...] = DEFAULT_DURATIONS,
    seed: int = 0,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in manifest:
        case_uid = str(record["case_uid"])
        for duration in durations:
            run_dir = (
                output_root
                / f"duration_{int(duration):02d}"
                / case_uid
                / f"seed_{seed:03d}"
            )
            artifacts = [
                run_dir / "img_0.jpg",
                run_dir / "run_config.json",
                run_dir / "resolved_control_plan.json",
                run_dir / "tdm" / "control_trace.json",
            ]
            missing = [path for path in artifacts if not path.is_file()]
            if missing:
                raise FileNotFoundError(
                    f"Incomplete residual RK2 run {case_uid}/N{duration:02d}: "
                    + ", ".join(str(path) for path in missing)
                )
            trace = json.loads(artifacts[-1].read_text(encoding="utf-8"))
            residual_trace = trace.get("residual_control_trace", [])
            if len(residual_trace) != int(duration):
                raise ValueError(
                    f"Residual trace length mismatch for {case_uid}/N{duration:02d}: "
                    f"expected {duration}, found {len(residual_trace)}"
                )
            rows.append(
                {
                    "row_uid": f"residual_rk2::{case_uid}::N{duration:02d}",
                    "case_uid": case_uid,
                    "duration": int(duration),
                    "method": "residual_rk2",
                    "method_label": "Residual RK2 prefix",
                    "part": record.get("part"),
                    "edit": record.get("edit"),
                    "part_size": record.get("part_size"),
                    "target_prompt": record.get("target_prompt"),
                    "source_image": repo_relative(
                        repo_root, repo_root / str(record["source_image"])
                    ),
                    "gt_mask": repo_relative(
                        repo_root, repo_root / str(record["gt_mask"])
                    ),
                    "edited_image": repo_relative(repo_root, artifacts[0]),
                    "outside_mask_lpips": np.nan,
                }
            )
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("Residual RK2 evaluation contains no rows")
    if frame["row_uid"].duplicated().any():
        raise ValueError("Residual RK2 evaluation contains duplicate row_uid values")
    return frame.sort_values(["case_uid", "duration"]).reset_index(drop=True)


def build_unified_evaluation_rows(
    repo_root: Path,
    manifest: list[dict[str, Any]],
    fys_metrics: pd.DataFrame,
    projection_metrics: pd.DataFrame,
    residual_rows: pd.DataFrame,
) -> pd.DataFrame:
    baseline_rows = build_evaluation_rows(
        repo_root, manifest, fys_metrics, projection_metrics
    )
    prompts = {
        str(record["case_uid"]): record.get("target_prompt", "")
        for record in manifest
    }
    baseline_rows["target_prompt"] = baseline_rows["case_uid"].map(prompts)
    rows = pd.concat([baseline_rows, residual_rows], ignore_index=True, sort=False)
    if rows["row_uid"].duplicated().any():
        duplicates = rows.loc[rows["row_uid"].duplicated(), "row_uid"].tolist()
        raise ValueError(f"Unified evaluation contains duplicate row_uid values: {duplicates}")
    return rows.sort_values(
        ["method", "case_uid", "duration"], na_position="first"
    ).reset_index(drop=True)


def parse_durations(value: str) -> list[int]:
    if value == "0-15":
        return list(DEFAULT_DURATIONS)
    durations = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not durations or any(duration < 0 or duration > 15 for duration in durations):
        raise ValueError("durations must contain values from 0 through 15")
    return list(dict.fromkeys(durations))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repo_root = find_repo_root(Path.cwd())
    eval_dir = repo_root / "core/results/control_operations_eval/residual_rk2_prefix_sweep"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=repo_root / "core/data/partedit_subset/pilot_12_manifest.json",
    )
    parser.add_argument(
        "--fys-metrics",
        type=Path,
        default=repo_root / "core/results/controlled_revision/fys_run_metrics.csv",
    )
    parser.add_argument(
        "--projection-metrics",
        type=Path,
        default=repo_root
        / "core/results/control_operations_eval/latent_projection_all_cases_n0_n13/duration_sweep_metrics.csv",
    )
    parser.add_argument(
        "--residual-root",
        type=Path,
        default=repo_root / "core/results/control_operations/residual_rk2_prefix_sweep",
    )
    parser.add_argument("--durations", default="0-15")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, default=eval_dir / "unified_image_metrics.csv")
    parser.add_argument("--lpips", choices=("off", "auto", "require"), default="auto")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    residual_rows = build_residual_evaluation_rows(
        repo_root,
        manifest,
        args.residual_root.resolve(),
        durations=parse_durations(args.durations),
        seed=args.seed,
    )
    rows = build_unified_evaluation_rows(
        repo_root,
        manifest,
        pd.read_csv(args.fys_metrics),
        pd.read_csv(args.projection_metrics),
        residual_rows,
    )
    existing = pd.read_csv(args.output) if args.output.exists() else None
    evaluated = evaluate_rows(
        repo_root, rows, args.lpips, existing_output=existing
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    evaluated.to_csv(args.output, index=False)
    lpips_count = int(
        pd.to_numeric(evaluated["outside_mask_lpips"], errors="coerce")
        .notna()
        .sum()
    )
    print(f"saved: {args.output}")
    print(f"rows: {len(evaluated)}; LPIPS values: {lpips_count}/{len(evaluated)}")
    if args.lpips == "require" and lpips_count != len(evaluated):
        raise RuntimeError("LPIPS was required, but the output table is incomplete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
