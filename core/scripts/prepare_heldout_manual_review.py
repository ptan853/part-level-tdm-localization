#!/usr/bin/env python3
"""Build two independently randomized, method-blinded held-out review packages."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from build_manual_review import build_review_page  # noqa: E402
from heldout_review_randomization import (  # noqa: E402
    validate_frozen_randomization,
)


SCORE_FIELDS = (
    "local_edit_success_0_2",
    "non_target_preservation_0_2",
    "overall_prompt_adherence_0_2",
    "visual_quality_0_2",
)


def build_blinded_assignments(
    rows: pd.DataFrame,
    frozen_randomization: pd.DataFrame,
    reviewer_id: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {
        "row_uid",
        "case_uid",
        "seed",
        "method",
        "part",
        "edit",
        "part_size",
        "footprint_change",
        "source_prompt",
        "target_prompt",
        "source_image",
        "gt_mask",
        "edited_image",
    }
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"evaluation table is missing review fields: {missing}")
    if rows["row_uid"].duplicated().any():
        raise ValueError("evaluation table contains duplicate row_uid values")

    validate_frozen_randomization(
        frozen_randomization.to_dict("records"),
        expected_row_uids=set(rows["row_uid"].astype(str)),
    )
    mapping = (
        frozen_randomization[
            frozen_randomization["reviewer_id"].astype(str) == reviewer_id
        ]
        .sort_values("review_position")
        .reset_index(drop=True)
    )
    if mapping.empty:
        raise ValueError(f"frozen randomization has no rows for {reviewer_id}")
    indexed_rows = rows.set_index("row_uid", drop=False)
    review_rows = []
    for frozen in mapping.to_dict("records"):
        row = indexed_rows.loc[str(frozen["row_uid"])].to_dict()
        review_uid = str(frozen["review_uid"])
        review = {
            "review_uid": review_uid,
            "part": row["part"],
            "edit": row["edit"],
            "source_prompt": row["source_prompt"],
            "target_prompt": row["target_prompt"],
            "source_image": row["source_image"],
            "candidate_image": row["edited_image"],
            **{field: "" for field in SCORE_FIELDS},
            "short_note": "",
        }
        review_rows.append(review)
    return pd.DataFrame(review_rows), mapping


def _copy_blinded_assets(review: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    assets = output_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    output = review.copy()
    source_aliases: dict[str, str] = {}
    for index, row in output.iterrows():
        source = Path(str(row["source_image"]))
        candidate = Path(str(row["candidate_image"]))
        if not source.is_file() or not candidate.is_file():
            raise FileNotFoundError(f"missing review image for {row['review_uid']}")
        source_key = hashlib.sha256(str(source).encode()).hexdigest()[:12]
        source_name = source_aliases.get(
            str(source), f"source_{source_key}{source.suffix.lower()}"
        )
        source_aliases[str(source)] = source_name
        candidate_name = f"{row['review_uid']}{candidate.suffix.lower()}"
        shutil.copy2(source, assets / source_name)
        shutil.copy2(candidate, assets / candidate_name)
        output.at[index, "source_image"] = str(assets / source_name)
        output.at[index, "candidate_image"] = str(assets / candidate_name)
    return output


def _review_config(reviewer_id: str) -> dict:
    return {
        "title": "Part-level editing review",
        "storage_key": f"heldout-control-{reviewer_id}-v1",
        "download_filename": f"{reviewer_id}_scores.csv",
        "id_field": "review_uid",
        "image_fields": [
            {"key": "source_image", "label": "Source"},
            {"key": "candidate_image", "label": "Candidate"},
        ],
        "score_fields": [
            {
                "key": SCORE_FIELDS[0],
                "label": "Local edit success",
                "hint": "0 failed; 1 partial; 2 successful.",
                "values": [0, 1, 2],
            },
            {
                "key": SCORE_FIELDS[1],
                "label": "Non-target preservation",
                "hint": "0 poor; 1 partial; 2 preserved.",
                "values": [0, 1, 2],
            },
            {
                "key": SCORE_FIELDS[2],
                "label": "Overall prompt adherence",
                "hint": "0 conflicts; 1 partial; 2 clearly follows.",
                "values": [0, 1, 2],
            },
            {
                "key": SCORE_FIELDS[3],
                "label": "Visual quality",
                "hint": "0 unusable; 1 acceptable with defects; 2 coherent and high quality.",
                "values": [0, 1, 2],
            },
        ],
        "note_field": "short_note",
    }


def write_review_package(
    rows: pd.DataFrame,
    *,
    frozen_randomization: pd.DataFrame,
    reviewer_id: str,
    repo_root: Path,
    output_root: Path,
) -> None:
    review, mapping = build_blinded_assignments(
        rows, frozen_randomization, reviewer_id
    )
    output_dir = output_root / reviewer_id
    output_dir.mkdir(parents=True, exist_ok=True)
    review = _copy_blinded_assets(review, output_dir)
    review_csv = output_dir / "review_template.csv"
    mapping_csv = output_root / f"{reviewer_id}_private_mapping.csv"
    config_json = output_dir / "review_config.json"
    html = output_dir / "review.html"
    review.to_csv(review_csv, index=False, lineterminator="\n")
    mapping.to_csv(mapping_csv, index=False, lineterminator="\n")
    config_json.write_text(
        json.dumps(_review_config(reviewer_id), indent=2) + "\n", encoding="utf-8"
    )
    build_review_page(
        repo_root=repo_root,
        input_path=review_csv,
        config_path=config_json,
        output_path=html,
    )
    print(f"{reviewer_id}: {html}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--randomization", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = pd.read_csv(args.metrics)
    frozen_randomization = pd.read_csv(args.randomization)
    if len(rows) != 240:
        raise ValueError(
            f"formal blinded review requires exactly 240 outputs, found {len(rows)}"
        )
    write_review_package(
        rows,
        frozen_randomization=frozen_randomization,
        reviewer_id="reviewer_1",
        repo_root=args.repo_root.resolve(),
        output_root=args.output_root,
    )
    write_review_package(
        rows,
        frozen_randomization=frozen_randomization,
        reviewer_id="reviewer_2",
        repo_root=args.repo_root.resolve(),
        output_root=args.output_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
