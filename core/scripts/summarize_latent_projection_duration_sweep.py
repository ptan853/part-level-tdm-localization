#!/usr/bin/env python3
"""Validate and summarize the locked latent-projection duration sweep."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


DEFAULT_CASE_UIDS = ("real_0006", "real_0011")
DEFAULT_DURATIONS = tuple(range(14))
IMAGE_NAME = "img_0.jpg"


def parse_duration_spec(value: str) -> tuple[int, ...]:
    durations = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError("duration range end must be greater than or equal to start")
            durations.extend(range(start, end + 1))
        else:
            durations.append(int(item))
    unique = tuple(dict.fromkeys(durations))
    if not unique or min(unique) < 0 or max(unique) > 13:
        raise ValueError("durations must be between 0 and 13")
    return unique


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise FileNotFoundError(f"Could not find repository root from {start}")


def read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def validate_primary_run(run_dir: Path, duration: int) -> dict:
    required = [
        run_dir / IMAGE_NAME,
        run_dir / "resolved_control_plan.json",
        run_dir / "run_config.json",
        run_dir / "tdm" / "control_trace.json",
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)

    plan = read_json(run_dir / "resolved_control_plan.json")
    if any(stage.get("image_kv") == "source_outside_mask" for stage in plan.get("stages", [])):
        raise ValueError(f"Primary duration sweep must not contain Stage 3 image-KV injection: {run_dir}")

    trace = read_json(run_dir / "tdm" / "control_trace.json")
    projection_trace = trace.get("latent_projection_trace", [])
    expected_steps = list(range(2, duration + 2))
    actual_steps = [int(item["step"]) for item in projection_trace]
    if actual_steps != expected_steps:
        raise ValueError(
            f"Unexpected projection steps for duration {duration}: expected {expected_steps}, got {actual_steps}"
        )
    for item in projection_trace:
        step = int(item["step"])
        if int(item.get("source_latent_index", -1)) != step + 1:
            raise ValueError(f"Wrong source latent index at step {step}: {item}")
        if float(item.get("outside_mae_after", float("inf"))) != 0.0:
            raise ValueError(f"outside_mae_after must be zero at step {step}: {item}")

    return {
        "image_path": run_dir / IMAGE_NAME,
        "projection_steps": actual_steps,
        "plan": plan,
        "trace": trace,
    }


def _load_rgb(path: Path, size: tuple[int, int] | None = None) -> Image.Image:
    image = Image.open(path).convert("RGB")
    if size is not None and image.size != size:
        image = image.resize(size, Image.Resampling.BICUBIC)
    return image


def _load_mask(path: Path, size: tuple[int, int]) -> np.ndarray:
    image = Image.open(path).convert("L")
    if image.size != size:
        image = image.resize(size, Image.Resampling.NEAREST)
    return np.asarray(image, dtype=np.uint8) > 127


def compute_region_metrics(source_path: Path, edited_path: Path, gt_mask_path: Path) -> dict:
    source_image = _load_rgb(source_path)
    edited_image = _load_rgb(edited_path, source_image.size)
    source = np.asarray(source_image, dtype=np.float32) / 255.0
    edited = np.asarray(edited_image, dtype=np.float32) / 255.0
    mask = _load_mask(gt_mask_path, source_image.size)
    if not mask.any() or mask.all():
        raise ValueError(f"GT mask must contain both inside and outside pixels: {gt_mask_path}")
    difference = np.abs(source - edited)
    return {
        "inside_mask_rgb_mae": float(difference[mask].mean()),
        "outside_mask_rgb_mae": float(difference[~mask].mean()),
    }


def load_manifest(path: Path) -> dict[str, dict]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(records, dict):
        records = records.get("cases", records.get("records", []))
    return {str(record["case_uid"]): record for record in records}


def collect_metrics(
    *,
    repo_root: Path,
    manifest_path: Path,
    sweep_root: Path,
    case_uids: tuple[str, ...] = DEFAULT_CASE_UIDS,
    durations: tuple[int, ...] = DEFAULT_DURATIONS,
) -> tuple[list[dict], dict[str, dict]]:
    manifest = load_manifest(manifest_path)
    rows = []
    for case_uid in case_uids:
        if case_uid not in manifest:
            raise KeyError(f"Case not found in manifest: {case_uid}")
        record = manifest[case_uid]
        source_path = repo_root / record["source_image"]
        gt_mask_path = repo_root / record["gt_mask"]
        for duration in durations:
            run_dir = sweep_root / f"duration_{duration:02d}" / case_uid / "seed_000"
            validated = validate_primary_run(run_dir, duration)
            row = {
                "case_uid": case_uid,
                "part": record["part"],
                "edit": record["edit"],
                "part_size": record["part_size"],
                "duration": duration,
                "projection_start_step": 2 if duration else "",
                "projection_end_step": duration + 1 if duration else "",
                "projection_step_count": duration,
                "generated_image": str(validated["image_path"].relative_to(repo_root)),
            }
            row.update(compute_region_metrics(source_path, validated["image_path"], gt_mask_path))
            rows.append(row)
    return rows, manifest


def write_metrics_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def aggregate_metrics(rows: list[dict], group_field: str | None = None) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (row[group_field], int(row["duration"])) if group_field else (int(row["duration"]),)
        groups.setdefault(key, []).append(row)

    baseline_by_group = {}
    for key, group_rows in groups.items():
        duration = key[-1]
        if duration == 0:
            group_name = key[0] if group_field else "all"
            baseline_by_group[group_name] = (
                float(np.mean([float(row["inside_mask_rgb_mae"]) for row in group_rows])),
                float(np.mean([float(row["outside_mask_rgb_mae"]) for row in group_rows])),
            )

    output = []
    for key in sorted(groups):
        group_rows = groups[key]
        duration = key[-1]
        group_name = key[0] if group_field else "all"
        inside = np.asarray([float(row["inside_mask_rgb_mae"]) for row in group_rows], dtype=np.float64)
        outside = np.asarray([float(row["outside_mask_rgb_mae"]) for row in group_rows], dtype=np.float64)
        baseline_inside, baseline_outside = baseline_by_group[group_name]
        summary = {
            "duration": duration,
            "n_cases": len(group_rows),
            "inside_mean": float(inside.mean()),
            "inside_std": float(inside.std(ddof=0)),
            "outside_mean": float(outside.mean()),
            "outside_std": float(outside.std(ddof=0)),
            "inside_retention_vs_n0": float(inside.mean() / baseline_inside),
            "outside_reduction_vs_n0": float(1.0 - outside.mean() / baseline_outside),
        }
        if group_field:
            summary = {group_field: group_name, **summary}
        output.append(summary)
    return output


def _thumbnail(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.pad(image.convert("RGB"), size, method=Image.Resampling.LANCZOS, color="white")


def _gt_overlay(source_path: Path, mask_path: Path) -> Image.Image:
    source = _load_rgb(source_path).convert("RGBA")
    mask = _load_mask(mask_path, source.size)
    overlay = np.zeros((source.height, source.width, 4), dtype=np.uint8)
    overlay[mask] = (230, 45, 45, 120)
    return Image.alpha_composite(source, Image.fromarray(overlay)).convert("RGB")


def render_comparison_sheet(
    *,
    path: Path,
    repo_root: Path,
    manifest: dict[str, dict],
    sweep_root: Path,
    reference_root: Path,
    case_uids: tuple[str, ...] = DEFAULT_CASE_UIDS,
    durations: tuple[int, ...] = DEFAULT_DURATIONS,
) -> None:
    thumb_size = (180, 180)
    label_width = 280
    header_height = 44
    row_height = 220
    columns = ["source", "GT"] + [f"N={duration}" for duration in durations] + ["N=7 + Stage 3 KV"]
    canvas = Image.new(
        "RGB",
        (label_width + len(columns) * thumb_size[0], header_height + len(case_uids) * row_height),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, label in enumerate(columns):
        x = label_width + index * thumb_size[0]
        draw.text((x + 6, 14), label, fill="black", font=font)

    for row_index, case_uid in enumerate(case_uids):
        record = manifest[case_uid]
        y = header_height + row_index * row_height
        source_path = repo_root / record["source_image"]
        mask_path = repo_root / record["gt_mask"]
        label_lines = [
            case_uid,
            f"{record['part']} -> {record['edit']}",
            f"part size: {record['part_size']}",
        ]
        for line_index, line in enumerate(label_lines):
            draw.text((10, y + 16 + line_index * 18), line, fill="black", font=font)
        images = [_load_rgb(source_path), _gt_overlay(source_path, mask_path)]
        images.extend(
            _load_rgb(sweep_root / f"duration_{duration:02d}" / case_uid / "seed_000" / IMAGE_NAME)
            for duration in durations
        )
        reference_path = reference_root / case_uid / "seed_000" / IMAGE_NAME
        if not reference_path.exists():
            raise FileNotFoundError(reference_path)
        images.append(_load_rgb(reference_path))
        for column_index, image in enumerate(images):
            x = label_width + column_index * thumb_size[0]
            canvas.paste(_thumbnail(image, thumb_size), (x, y))
        draw.line((0, y + row_height - 1, canvas.width, y + row_height - 1), fill=(210, 210, 210))

    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, quality=95)


def render_change_curve(path: Path, rows: list[dict], case_uids: tuple[str, ...] = DEFAULT_CASE_UIDS) -> None:
    columns = min(4, len(case_uids))
    plot_rows = math.ceil(len(case_uids) / columns)
    fig, axes = plt.subplots(plot_rows, columns, figsize=(4.2 * columns, 3.4 * plot_rows), sharey=True)
    axes = np.atleast_1d(axes).ravel()
    for ax, case_uid in zip(axes, case_uids):
        case_rows = sorted((row for row in rows if row["case_uid"] == case_uid), key=lambda row: row["duration"])
        durations = [row["duration"] for row in case_rows]
        ax.plot(durations, [row["inside_mask_rgb_mae"] for row in case_rows], marker="o", label="inside GT")
        ax.plot(durations, [row["outside_mask_rgb_mae"] for row in case_rows], marker="o", label="outside GT")
        ax.set_title(case_uid)
        ax.set_xlabel("projection duration N")
        ax.grid(alpha=0.25)
        ax.legend()
    axes[0].set_ylabel("mean absolute RGB change")
    for ax in axes[len(case_uids):]:
        ax.axis("off")
    fig.suptitle("Edit activity and non-target drift vs latent-projection duration")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--sweep-root", type=Path)
    parser.add_argument("--reference-root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--case-uid", action="append", dest="case_uids")
    parser.add_argument("--durations", default="0-13")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = find_repo_root(args.repo_root or Path.cwd())
    manifest_path = args.manifest or repo_root / "core/data/partedit_subset/pilot_12_manifest.json"
    sweep_root = args.sweep_root or repo_root / "core/results/control_operations/latent_projection_duration_sweep"
    reference_root = (
        args.reference_root
        or repo_root / "core/results/control_operations/oracle_stage2_latent_projection"
    )
    output_dir = (
        args.output_dir
        or repo_root / "core/results/control_operations_eval/latent_projection_duration_sweep"
    )
    case_uids = tuple(args.case_uids or DEFAULT_CASE_UIDS)
    durations = parse_duration_spec(args.durations)
    rows, manifest = collect_metrics(
        repo_root=repo_root,
        manifest_path=manifest_path,
        sweep_root=sweep_root,
        case_uids=case_uids,
        durations=durations,
    )
    metrics_path = output_dir / "duration_sweep_metrics.csv"
    summary_path = output_dir / "duration_sweep_summary.csv"
    part_size_summary_path = output_dir / "duration_sweep_summary_by_part_size.csv"
    comparison_path = output_dir / "duration_sweep_comparison.jpg"
    curve_path = output_dir / "duration_sweep_change_curve.png"
    write_metrics_csv(metrics_path, rows)
    write_metrics_csv(summary_path, aggregate_metrics(rows))
    write_metrics_csv(part_size_summary_path, aggregate_metrics(rows, group_field="part_size"))
    render_comparison_sheet(
        path=comparison_path,
        repo_root=repo_root,
        manifest=manifest,
        sweep_root=sweep_root,
        reference_root=reference_root,
        case_uids=case_uids,
        durations=durations,
    )
    render_change_curve(curve_path, rows, case_uids=case_uids)
    print(f"validated runs: {len(rows)}")
    print(f"metrics: {metrics_path}")
    print(f"summary: {summary_path}")
    print(f"part-size summary: {part_size_summary_path}")
    print(f"comparison: {comparison_path}")
    print(f"curve: {curve_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
