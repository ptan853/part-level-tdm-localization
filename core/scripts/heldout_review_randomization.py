#!/usr/bin/env python3
"""Freeze deterministic, method-blinded reviewer orders before generation."""

from __future__ import annotations

from collections import Counter
import csv
import hashlib
from pathlib import Path
import random
from typing import Iterable, Mapping


REVIEWER_SEEDS = {
    "reviewer_1": 1701,
    "reviewer_2": 2903,
}


def opaque_review_id(reviewer_id: str, row_uid: str) -> str:
    digest = hashlib.sha256(
        f"heldout-v1|{reviewer_id}|{row_uid}".encode("utf-8")
    ).hexdigest()[:12]
    return f"item_{digest}"


def build_frozen_randomization(
    rows: Iterable[Mapping[str, object]],
    reviewer_seeds: Mapping[str, int] = REVIEWER_SEEDS,
) -> list[dict[str, object]]:
    required = {
        "row_uid",
        "case_uid",
        "seed",
        "method",
        "part_size",
        "footprint_change",
    }
    source_rows = [dict(row) for row in rows]
    if not source_rows:
        raise ValueError("at least one evaluated row is required")
    missing = sorted(required - set(source_rows[0]))
    if missing:
        raise ValueError(f"randomization rows are missing fields: {missing}")
    row_uids = [str(row["row_uid"]) for row in source_rows]
    if len(row_uids) != len(set(row_uids)):
        raise ValueError("randomization rows contain duplicate row_uid values")

    canonical = sorted(source_rows, key=lambda row: str(row["row_uid"]))
    assignments: list[dict[str, object]] = []
    for reviewer_id, seed in reviewer_seeds.items():
        shuffled = list(canonical)
        random.Random(seed).shuffle(shuffled)
        for position, row in enumerate(shuffled, start=1):
            row_uid = str(row["row_uid"])
            assignments.append(
                {
                    "reviewer_id": reviewer_id,
                    "review_position": position,
                    "review_uid": opaque_review_id(reviewer_id, row_uid),
                    "row_uid": row_uid,
                    "case_uid": row["case_uid"],
                    "seed": int(row["seed"]),
                    "method": row["method"],
                    "part_size": row["part_size"],
                    "footprint_change": row["footprint_change"],
                }
            )
    return assignments


def validate_frozen_randomization(
    assignments: Iterable[Mapping[str, object]],
    *,
    expected_row_uids: set[str],
    reviewer_ids: set[str] | None = None,
) -> None:
    rows = [dict(row) for row in assignments]
    expected_reviewers = reviewer_ids or set(REVIEWER_SEEDS)
    expected_count = len(expected_row_uids) * len(expected_reviewers)
    if len(rows) != expected_count:
        raise ValueError(
            f"frozen randomization assignment count must be {expected_count}, "
            f"found {len(rows)}"
        )
    if Counter(str(row.get("reviewer_id")) for row in rows) != Counter(
        {reviewer: len(expected_row_uids) for reviewer in expected_reviewers}
    ):
        raise ValueError("frozen randomization has incorrect reviewer counts")
    if len({str(row.get("review_uid")) for row in rows}) != len(rows):
        raise ValueError("frozen randomization contains duplicate review_uid values")
    for reviewer in expected_reviewers:
        reviewer_rows = [
            row for row in rows if str(row.get("reviewer_id")) == reviewer
        ]
        actual_uids = {str(row.get("row_uid")) for row in reviewer_rows}
        if actual_uids != expected_row_uids:
            raise ValueError(
                f"frozen randomization for {reviewer} does not match evaluation rows"
            )
        positions = {int(row.get("review_position", 0)) for row in reviewer_rows}
        if positions != set(range(1, len(expected_row_uids) + 1)):
            raise ValueError(
                f"frozen randomization for {reviewer} has invalid positions"
            )


def write_frozen_randomization(
    path: Path, assignments: Iterable[Mapping[str, object]]
) -> None:
    rows = [dict(row) for row in assignments]
    if not rows:
        raise ValueError("cannot write an empty frozen randomization")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
