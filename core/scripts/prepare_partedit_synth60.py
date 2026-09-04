#!/usr/bin/env python3
"""Export the frozen 60-case PartEdit-Bench synth manifest from its Parquet shard."""

from __future__ import annotations

import argparse
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


DATASET_ID = "Aleksandar/PartEdit-Bench"
DATASET_REVISION = "v1.1"
DATASET_COMMIT = "e6e132f8bb32bec49269ae979659f2bab341e813"
VALID_FOOTPRINTS = {"contraction", "comparable", "expansion"}


def rank_part_sizes(area_by_index: dict[int, float]) -> dict[int, str]:
    if set(area_by_index) != set(range(60)):
        raise ValueError("part-size ranking requires dataset indices 0 through 59")
    ordered = sorted(area_by_index, key=lambda index: (area_by_index[index], index))
    return {
        index: ("small" if rank < 20 else "medium" if rank < 40 else "large")
        for rank, index in enumerate(ordered)
    }


def validate_footprint_labels(labels: dict[int, str]) -> None:
    if set(labels) != set(range(60)):
        raise ValueError("footprint labels must cover dataset indices 0 through 59")
    invalid = {value for value in labels.values() if value not in VALID_FOOTPRINTS}
    if invalid:
        raise ValueError(f"invalid footprint label(s): {sorted(invalid)}")


def build_manifest_records(
    rows: list[dict[str, Any]],
    area_by_index: dict[int, float],
    size_by_index: dict[int, str],
    footprint_by_index: dict[int, str],
) -> list[dict[str, Any]]:
    validate_footprint_labels(footprint_by_index)
    indexed = {int(row["id"]): row for row in rows}
    if set(indexed) != set(range(60)):
        raise ValueError("synth shard must contain exactly dataset IDs 0 through 59")
    records = []
    for index in range(60):
        row = indexed[index]
        case_uid = f"synth_{index:04d}"
        case_root = f"core/data/partedit_subset/cases/{case_uid}"
        records.append(
            {
                "case_uid": case_uid,
                "dataset_id": DATASET_ID,
                "dataset_revision": DATASET_REVISION,
                "dataset_commit": DATASET_COMMIT,
                "dataset_split": "synth",
                "dataset_index": index,
                "subject": str(row["subject"]),
                "class_name": str(row["class_name"]),
                "part": str(row["part"]),
                "edit": str(row["edit"]),
                "source_prompt": str(row["prompt_original"]),
                "target_prompt": str(row["p2p_prompt"]),
                "source_image": f"{case_root}/source.png",
                "gt_mask": f"{case_root}/gt_mask.png",
                "partedit_reference": f"{case_root}/partedit_reference.png",
                "gt_area_ratio": float(area_by_index[index]),
                "part_size": size_by_index[index],
                "footprint_change": footprint_by_index[index],
            }
        )
    return records


def _image_from_value(value: Any) -> Image.Image:
    if isinstance(value, Image.Image):
        return value.copy()
    if isinstance(value, dict):
        if value.get("bytes") is not None:
            return Image.open(BytesIO(value["bytes"])).copy()
        if value.get("path"):
            return Image.open(value["path"]).copy()
    if isinstance(value, (bytes, bytearray)):
        return Image.open(BytesIO(value)).copy()
    raise TypeError(f"unsupported Parquet image value: {type(value).__name__}")


def read_parquet_rows(path: Path) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as parquet  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "pyarrow is required only for dataset export; run with `uv run --with pyarrow`."
        ) from exc
    return parquet.read_table(path).to_pylist()


def load_footprint_labels(path: Path) -> dict[int, str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    labels = {
        int(row["dataset_index"]): row["footprint_change"].strip() for row in rows
    }
    validate_footprint_labels(labels)
    return labels


def write_footprint_template(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "dataset_index",
        "part",
        "edit",
        "source_prompt",
        "target_prompt",
        "footprint_change",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in sorted(rows, key=lambda value: int(value["id"])):
            writer.writerow(
                {
                    "dataset_index": int(row["id"]),
                    "part": row["part"],
                    "edit": row["edit"],
                    "source_prompt": row["prompt_original"],
                    "target_prompt": row["p2p_prompt"],
                    "footprint_change": "",
                }
            )


def export_cases(repo_root: Path, rows: list[dict[str, Any]]) -> dict[int, float]:
    area_by_index: dict[int, float] = {}
    for row in rows:
        index = int(row["id"])
        case_dir = repo_root / "core/data/partedit_subset/cases" / f"synth_{index:04d}"
        case_dir.mkdir(parents=True, exist_ok=True)
        source = _image_from_value(row["original_image"]).convert("RGB")
        mask = _image_from_value(row["gt_mask"]).convert("L")
        reference = _image_from_value(row["partedit"]).convert("RGB")
        source.save(case_dir / "source.png")
        mask.save(case_dir / "gt_mask.png")
        reference.save(case_dir / "partedit_reference.png")
        area_by_index[index] = float((np.asarray(mask) > 0).mean())
    return area_by_index


def build_manifest_metadata(
    *,
    manifest_path: Path,
    parquet_path: Path,
    footprint_labels_path: Path,
    footprint_labels_reviewed: bool,
    records: int,
) -> dict[str, Any]:
    return {
        "dataset_id": DATASET_ID,
        "dataset_revision": DATASET_REVISION,
        "dataset_commit": DATASET_COMMIT,
        "source_parquet": parquet_path.name,
        "source_parquet_sha256": hashlib.sha256(parquet_path.read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "records": records,
        "footprint_labels_sha256": hashlib.sha256(
            footprint_labels_path.read_bytes()
        ).hexdigest(),
        "footprint_labels_reviewed": footprint_labels_reviewed,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, required=True)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--footprint-labels", type=Path)
    parser.add_argument(
        "--footprint-labels-reviewed",
        action="store_true",
        help="Record that all 60 footprint labels were manually reviewed before generation.",
    )
    parser.add_argument("--write-footprint-template", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("core/data/partedit_subset/synth_60_frozen_manifest.json"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    rows = read_parquet_rows(args.parquet)
    if args.write_footprint_template is not None:
        write_footprint_template(args.write_footprint_template, rows)
        print(f"footprint template: {args.write_footprint_template}")
        if args.footprint_labels is None:
            return 0
    if args.footprint_labels is None:
        raise ValueError("--footprint-labels is required to freeze the manifest")

    area_by_index = export_cases(repo_root, rows)
    size_by_index = rank_part_sizes(area_by_index)
    labels = load_footprint_labels(args.footprint_labels)
    records = build_manifest_records(rows, area_by_index, size_by_index, labels)
    manifest_path = (
        args.manifest if args.manifest.is_absolute() else repo_root / args.manifest
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    metadata_path = manifest_path.with_suffix(".meta.json")
    metadata_path.write_text(
        json.dumps(
            build_manifest_metadata(
                manifest_path=manifest_path,
                parquet_path=args.parquet,
                footprint_labels_path=args.footprint_labels,
                footprint_labels_reviewed=args.footprint_labels_reviewed,
                records=len(records),
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"manifest: {manifest_path}")
    print(f"metadata: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
