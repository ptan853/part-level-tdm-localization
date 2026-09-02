#!/usr/bin/env python3
"""Compute one image-metric table for original FYS and latent projection sweeps."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image


IMAGE_METRIC_COLUMNS = [
    "outside_mask_l1_aux",
    "inside_mask_l1_aux",
    "outside_mask_mse",
    "inside_mask_mse",
    "outside_mask_psnr",
    "inside_mask_psnr",
    "outside_mask_global_ssim",
    "inside_mask_global_ssim",
    "outside_mask_lpips",
]


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    while current != current.parent:
        if (current / "pyproject.toml").exists() and (current / "core").exists():
            return current
        current = current.parent
    raise FileNotFoundError(f"Could not find repository root from {start}")


def resolve_path(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def load_rgb(path: Path, size: tuple[int, int] | None = None) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    if size is not None and image.size != size:
        image = image.resize(size, Image.Resampling.BICUBIC)
    return np.asarray(image, dtype=np.float32) / 255.0


def load_mask(path: Path, size: tuple[int, int] | None = None) -> np.ndarray:
    image = Image.open(path).convert("L")
    if size is not None and image.size != size:
        image = image.resize(size, Image.Resampling.NEAREST)
    return np.asarray(image) > 0


def masked_l1(source: np.ndarray, edited: np.ndarray, mask: np.ndarray) -> float:
    selected = mask.astype(bool)
    if selected.sum() == 0:
        return float("nan")
    return float(np.abs(source[selected] - edited[selected]).mean())


def masked_mse(source: np.ndarray, edited: np.ndarray, mask: np.ndarray) -> float:
    selected = mask.astype(bool)
    if selected.sum() == 0:
        return float("nan")
    return float(((source[selected] - edited[selected]) ** 2).mean())


def psnr_from_mse(mse: float) -> float:
    if not np.isfinite(mse):
        return float("nan")
    if mse <= 1e-12:
        return float("inf")
    return float(10 * math.log10(1.0 / mse))


def masked_global_ssim(source: np.ndarray, edited: np.ndarray, mask: np.ndarray) -> float:
    """Match the lightweight selected-pixel SSIM proxy used by notebooks 03 and 05."""
    selected = mask.astype(bool)
    if selected.sum() < 2:
        return float("nan")
    source_gray = (0.299 * source[..., 0] + 0.587 * source[..., 1] + 0.114 * source[..., 2])[selected]
    edited_gray = (0.299 * edited[..., 0] + 0.587 * edited[..., 1] + 0.114 * edited[..., 2])[selected]
    c1 = 0.01**2
    c2 = 0.03**2
    source_mean = source_gray.mean()
    edited_mean = edited_gray.mean()
    source_var = source_gray.var()
    edited_var = edited_gray.var()
    covariance = ((source_gray - source_mean) * (edited_gray - edited_mean)).mean()
    numerator = (2 * source_mean * edited_mean + c1) * (2 * covariance + c2)
    denominator = (source_mean**2 + edited_mean**2 + c1) * (source_var + edited_var + c2)
    return float(numerator / denominator) if denominator != 0 else float("nan")


def compute_image_metrics(
    source: np.ndarray,
    edited: np.ndarray,
    gt_mask: np.ndarray,
) -> dict[str, float]:
    outside = ~gt_mask.astype(bool)
    inside = gt_mask.astype(bool)
    outside_mse = masked_mse(source, edited, outside)
    inside_mse = masked_mse(source, edited, inside)
    return {
        "outside_mask_l1_aux": masked_l1(source, edited, outside),
        "inside_mask_l1_aux": masked_l1(source, edited, inside),
        "outside_mask_mse": outside_mse,
        "inside_mask_mse": inside_mse,
        "outside_mask_psnr": psnr_from_mse(outside_mse),
        "inside_mask_psnr": psnr_from_mse(inside_mse),
        "outside_mask_global_ssim": masked_global_ssim(source, edited, outside),
        "inside_mask_global_ssim": masked_global_ssim(source, edited, inside),
    }


def build_evaluation_rows(
    repo_root: Path,
    manifest: list[dict[str, Any]],
    fys_metrics: pd.DataFrame,
    projection_metrics: pd.DataFrame,
) -> pd.DataFrame:
    case_metadata = pd.DataFrame(manifest)[
        ["case_uid", "part", "edit", "part_size", "source_image", "gt_mask"]
    ].copy()

    fys_unique = fys_metrics.copy()
    if "seed" in fys_unique.columns:
        seed_zero = fys_unique[pd.to_numeric(fys_unique["seed"], errors="coerce") == 0]
        if not seed_zero.empty:
            fys_unique = seed_zero
    fys_unique = fys_unique.drop_duplicates("case_uid")
    fys_rows = case_metadata.merge(
        fys_unique[["case_uid", "fys_image", "outside_mask_lpips"]],
        on="case_uid",
        how="inner",
        validate="one_to_one",
    )
    fys_rows["method"] = "original_fys"
    fys_rows["method_label"] = "Original FYS-TDM"
    fys_rows["duration"] = pd.NA
    fys_rows["edited_image"] = fys_rows["fys_image"]
    fys_rows["row_uid"] = "original_fys::" + fys_rows["case_uid"]
    fys_rows = fys_rows.drop(columns=["fys_image"])

    projection_rows = projection_metrics[["case_uid", "duration", "generated_image"]].copy()
    projection_rows["duration"] = pd.to_numeric(projection_rows["duration"], errors="raise").astype(int)
    projection_rows = case_metadata.merge(
        projection_rows,
        on="case_uid",
        how="inner",
        validate="one_to_many",
    )
    projection_rows["method"] = "latent_projection"
    projection_rows["method_label"] = "Oracle latent projection"
    projection_rows["edited_image"] = projection_rows["generated_image"]
    projection_rows["outside_mask_lpips"] = np.nan
    projection_rows["row_uid"] = projection_rows.apply(
        lambda row: f"latent_projection::{row['case_uid']}::N{int(row['duration']):02d}", axis=1
    )
    projection_rows = projection_rows.drop(columns=["generated_image"])

    rows = pd.concat([fys_rows, projection_rows], ignore_index=True)
    rows["source_image"] = rows["source_image"].map(lambda value: str(resolve_path(repo_root, value).relative_to(repo_root)))
    rows["gt_mask"] = rows["gt_mask"].map(lambda value: str(resolve_path(repo_root, value).relative_to(repo_root)))
    rows["edited_image"] = rows["edited_image"].map(
        lambda value: str(resolve_path(repo_root, value).relative_to(repo_root))
    )
    return rows.sort_values(["method", "case_uid", "duration"], na_position="first").reset_index(drop=True)


class OutsideLpips:
    def __init__(self, policy: str) -> None:
        self.model = None
        self.torch = None
        if policy == "off":
            return
        try:
            import lpips  # type: ignore
            import torch  # type: ignore
        except Exception as exc:
            if policy == "require":
                raise RuntimeError("LPIPS was required but torch/lpips could not be imported") from exc
            print("LPIPS unavailable; preserving existing values where present.")
            return
        self.torch = torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if policy == "require" and device != "cuda":
            raise RuntimeError("LPIPS policy 'require' expects an available CUDA device")
        self.model = lpips.LPIPS(net="alex").to(device).eval()
        print(f"LPIPS device: {device}")

    def __call__(self, source: np.ndarray, edited: np.ndarray, gt_mask: np.ndarray) -> float:
        if self.model is None or self.torch is None:
            return float("nan")
        outside = (~gt_mask.astype(bool))[..., None].astype(np.float32)
        neutral = np.full_like(source, 0.5, dtype=np.float32)
        source_outside = source * outside + neutral * (1 - outside)
        edited_outside = edited * outside + neutral * (1 - outside)
        source_tensor = self.torch.from_numpy(source_outside.transpose(2, 0, 1)).unsqueeze(0) * 2 - 1
        edited_tensor = self.torch.from_numpy(edited_outside.transpose(2, 0, 1)).unsqueeze(0) * 2 - 1
        device = next(self.model.parameters()).device
        with self.torch.no_grad():
            return float(self.model(source_tensor.to(device).float(), edited_tensor.to(device).float()).item())


def evaluate_rows(
    repo_root: Path,
    rows: pd.DataFrame,
    lpips_policy: str,
    existing_output: pd.DataFrame | None = None,
) -> pd.DataFrame:
    existing_lpips: dict[str, float] = {}
    if existing_output is not None and {"row_uid", "outside_mask_lpips"}.issubset(existing_output.columns):
        values = pd.to_numeric(existing_output["outside_mask_lpips"], errors="coerce")
        existing_lpips = dict(zip(existing_output.loc[values.notna(), "row_uid"], values[values.notna()]))

    lpips_metric = OutsideLpips(lpips_policy)
    evaluated: list[dict[str, Any]] = []
    for index, row in rows.iterrows():
        source_path = resolve_path(repo_root, row["source_image"])
        gt_path = resolve_path(repo_root, row["gt_mask"])
        edited_path = resolve_path(repo_root, row["edited_image"])
        missing = [str(path) for path in (source_path, gt_path, edited_path) if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Missing evaluation artifact(s) for {row['row_uid']}: {missing}")
        with Image.open(source_path) as source_image:
            image_size = source_image.size
        source = load_rgb(source_path)
        edited = load_rgb(edited_path, size=image_size)
        gt_mask = load_mask(gt_path, size=image_size)
        metrics = compute_image_metrics(source, edited, gt_mask)
        lpips_value = lpips_metric(source, edited, gt_mask)
        if not np.isfinite(lpips_value):
            lpips_value = existing_lpips.get(row["row_uid"], row.get("outside_mask_lpips", float("nan")))
        evaluated.append({**row.to_dict(), **metrics, "outside_mask_lpips": lpips_value})
        if (index + 1) % 20 == 0 or index + 1 == len(rows):
            print(f"evaluated {index + 1}/{len(rows)}")
    return pd.DataFrame(evaluated)


def parse_args() -> argparse.Namespace:
    repo_root = find_repo_root(Path.cwd())
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
        "--output",
        type=Path,
        default=repo_root
        / "core/results/control_operations_eval/latent_projection_all_cases_n0_n13/unified_image_metrics.csv",
    )
    parser.add_argument("--lpips", choices=("off", "auto", "require"), default="auto")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    manifest = json.loads(args.manifest.read_text())
    fys_metrics = pd.read_csv(args.fys_metrics)
    projection_metrics = pd.read_csv(args.projection_metrics)
    rows = build_evaluation_rows(repo_root, manifest, fys_metrics, projection_metrics)
    existing = pd.read_csv(args.output) if args.output.exists() else None
    evaluated = evaluate_rows(repo_root, rows, args.lpips, existing_output=existing)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    evaluated.to_csv(args.output, index=False)
    lpips_count = int(pd.to_numeric(evaluated["outside_mask_lpips"], errors="coerce").notna().sum())
    print(f"saved: {args.output}")
    print(f"rows: {len(evaluated)}; LPIPS values: {lpips_count}/{len(evaluated)}")
    if args.lpips == "require" and lpips_count != len(evaluated):
        raise RuntimeError("LPIPS was required, but the output table is incomplete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
