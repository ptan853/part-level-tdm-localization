from __future__ import annotations

import argparse
import json
import math
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METRICS = (
    REPO_ROOT
    / "core/results/control_operations_eval/residual_rk2_prefix_sweep/unified_image_metrics.csv"
)
DEFAULT_MANIFEST = REPO_ROOT / "core/data/partedit_subset/pilot_12_manifest.json"
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT / "core/results/control_operations_eval/control_operation_comparison"
)


def _select_one(
    metrics: pd.DataFrame,
    case_uid: str,
    method: str,
    duration: int | None,
) -> pd.Series:
    selected = metrics[
        metrics["case_uid"].eq(case_uid) & metrics["method"].eq(method)
    ]
    if duration is not None:
        selected = selected[pd.to_numeric(selected["duration"], errors="coerce").eq(duration)]
    if len(selected) != 1:
        raise ValueError(
            f"{case_uid}: expected exactly one {method}"
            + (f" N={duration}" if duration is not None else "")
            + f" row, found {len(selected)}"
        )
    return selected.iloc[0]


def build_comparison_rows(
    metrics: pd.DataFrame, case_order: list[str]
) -> pd.DataFrame:
    required = {
        "case_uid",
        "part",
        "edit",
        "part_size",
        "target_prompt",
        "source_image",
        "gt_mask",
        "edited_image",
        "method",
        "duration",
    }
    missing = sorted(required - set(metrics.columns))
    if missing:
        raise ValueError(f"Metrics table is missing required columns: {missing}")

    rows: list[dict[str, object]] = []
    for case_uid in case_order:
        fys = _select_one(metrics, case_uid, "original_fys", None)
        endpoint = _select_one(metrics, case_uid, "latent_projection", 3)
        residual = _select_one(metrics, case_uid, "residual_rk2", 15)
        rows.append(
            {
                "case_uid": case_uid,
                "part": fys["part"],
                "edit": fys["edit"],
                "part_size": fys["part_size"],
                "target_prompt": fys["target_prompt"],
                "source_image": fys["source_image"],
                "gt_mask": fys["gt_mask"],
                "fys_image": fys["edited_image"],
                "endpoint_image": endpoint["edited_image"],
                "residual_image": residual["edited_image"],
            }
        )
    return pd.DataFrame(rows)


def _font(size: int) -> ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _resolve(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else REPO_ROOT / value


def _fit_image(path: str | Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(_resolve(path)) as opened:
        image = opened.convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def _gt_overlay(
    source_path: str | Path,
    mask_path: str | Path,
    size: tuple[int, int],
) -> Image.Image:
    with Image.open(_resolve(source_path)) as opened:
        source = opened.convert("RGB")
    with Image.open(_resolve(mask_path)) as opened:
        mask = opened.convert("L").resize(source.size, Image.Resampling.NEAREST)
    binary = np.asarray(mask) > 127
    source_array = np.asarray(source, dtype=np.float32).copy()
    source_array[binary] = 0.45 * source_array[binary] + 0.55 * np.array(
        [220, 35, 35], dtype=np.float32
    )
    overlay = Image.fromarray(np.clip(source_array, 0, 255).astype(np.uint8))
    overlay.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(
        overlay,
        ((size[0] - overlay.width) // 2, (size[1] - overlay.height) // 2),
    )
    return canvas


def _metadata_panel(row: pd.Series, size: tuple[int, int]) -> Image.Image:
    panel = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(panel)
    title_font = _font(18)
    body_font = _font(14)
    draw.text(
        (8, 8),
        f"{row['case_uid']} | {row['part_size']}",
        fill="black",
        font=title_font,
    )
    draw.text(
        (8, 36),
        f"{row['part']} -> {row['edit']}",
        fill="black",
        font=title_font,
    )
    prompt = "\n".join(textwrap.wrap(str(row["target_prompt"]), width=30))
    draw.multiline_text((8, 72), prompt, fill=(45, 45, 45), font=body_font, spacing=5)
    return panel


def render_comparison_sheets(
    rows: pd.DataFrame,
    output_dir: Path,
    cases_per_sheet: int = 6,
) -> list[Path]:
    if rows.empty:
        raise ValueError("No comparison rows were provided")
    if cases_per_sheet <= 0:
        raise ValueError("cases_per_sheet must be positive")

    output_dir.mkdir(parents=True, exist_ok=True)
    image_size = (250, 250)
    metadata_size = (285, 250)
    gap = 10
    header_height = 52
    row_height = image_size[1] + gap
    headers = (
        "Case / target",
        "Source",
        "GT part",
        "Original FYS-TDM",
        "Endpoint N=3",
        "Residual RK2 N=15",
    )
    widths = (metadata_size[0],) + (image_size[0],) * 5
    sheet_width = sum(widths) + gap * (len(widths) + 1)
    header_font = _font(17)
    outputs: list[Path] = []

    for sheet_index in range(math.ceil(len(rows) / cases_per_sheet)):
        subset = rows.iloc[
            sheet_index * cases_per_sheet : (sheet_index + 1) * cases_per_sheet
        ]
        sheet_height = header_height + len(subset) * row_height + gap
        sheet = Image.new("RGB", (sheet_width, sheet_height), "white")
        draw = ImageDraw.Draw(sheet)
        x = gap
        for header, width in zip(headers, widths):
            bbox = draw.textbbox((0, 0), header, font=header_font)
            text_width = bbox[2] - bbox[0]
            draw.text(
                (x + max(0, (width - text_width) // 2), 16),
                header,
                fill="black",
                font=header_font,
            )
            x += width + gap

        for row_index, (_, row) in enumerate(subset.iterrows()):
            y = header_height + row_index * row_height
            panels = (
                _metadata_panel(row, metadata_size),
                _fit_image(row["source_image"], image_size),
                _gt_overlay(row["source_image"], row["gt_mask"], image_size),
                _fit_image(row["fys_image"], image_size),
                _fit_image(row["endpoint_image"], image_size),
                _fit_image(row["residual_image"], image_size),
            )
            x = gap
            for panel, width in zip(panels, widths):
                sheet.paste(panel, (x, y))
                x += width + gap

        output_path = output_dir / f"control_comparison_part{sheet_index + 1}.jpg"
        sheet.save(output_path, quality=92, optimize=True)
        outputs.append(output_path)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build aligned FYS/endpoint/Residual RK2 comparison sheets."
    )
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = pd.read_csv(args.metrics)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    case_order = [str(record["case_uid"]) for record in manifest]
    rows = build_comparison_rows(metrics, case_order)
    outputs = render_comparison_sheets(rows, args.output_dir)
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
