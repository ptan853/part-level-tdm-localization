from __future__ import annotations

from pathlib import Path
import hashlib
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "core" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from prepare_partedit_synth60 import (  # noqa: E402
    build_manifest_records,
    build_manifest_metadata,
    rank_part_sizes,
    validate_footprint_labels,
)


class PreparePartEditSynth60Tests(unittest.TestCase):
    def test_rank_part_sizes_uses_area_then_dataset_index(self):
        areas = {index: float(index // 2) for index in range(60)}

        sizes = rank_part_sizes(areas)

        self.assertEqual(sum(value == "small" for value in sizes.values()), 20)
        self.assertEqual(sum(value == "medium" for value in sizes.values()), 20)
        self.assertEqual(sum(value == "large" for value in sizes.values()), 20)
        self.assertEqual(sizes[0], "small")
        self.assertEqual(sizes[19], "small")
        self.assertEqual(sizes[20], "medium")
        self.assertEqual(sizes[40], "large")

    def test_footprint_labels_require_every_index_and_valid_category(self):
        labels = {index: "comparable" for index in range(60)}
        validate_footprint_labels(labels)

        labels.pop(59)
        with self.assertRaisesRegex(ValueError, "indices 0 through 59"):
            validate_footprint_labels(labels)

        labels[59] = "unknown"
        with self.assertRaisesRegex(ValueError, "invalid footprint"):
            validate_footprint_labels(labels)

    def test_build_manifest_records_preserves_all_dataset_indices(self):
        rows = [
            {
                "id": index,
                "subject": f"subject-{index}",
                "edit": f"edit-{index}",
                "part": "head",
                "class_name": "animal_head",
                "prompt_original": f"source {index}",
                "p2p_prompt": f"target {index}",
            }
            for index in range(60)
        ]
        areas = {index: (index + 1) / 1000 for index in range(60)}
        sizes = rank_part_sizes(areas)
        footprints = {index: "comparable" for index in range(60)}

        records = build_manifest_records(rows, areas, sizes, footprints)

        self.assertEqual(len(records), 60)
        self.assertEqual(
            [record["dataset_index"] for record in records], list(range(60))
        )
        self.assertEqual(records[0]["case_uid"], "synth_0000")
        self.assertEqual(records[0]["dataset_revision"], "v1.1")
        self.assertEqual(records[0]["source_prompt"], "source 0")
        self.assertEqual(records[0]["target_prompt"], "target 0")
        self.assertEqual(records[0]["gt_area_ratio"], 0.001)
        self.assertEqual(records[0]["part_size"], "small")
        self.assertEqual(
            records[0]["source_image"],
            "core/data/partedit_subset/cases/synth_0000/source.png",
        )

    def test_metadata_records_manifest_parquet_and_reviewed_label_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            parquet = root / "source.parquet"
            labels = root / "labels.csv"
            manifest.write_bytes(b"manifest")
            parquet.write_bytes(b"parquet")
            labels.write_bytes(b"labels")

            metadata = build_manifest_metadata(
                manifest_path=manifest,
                parquet_path=parquet,
                footprint_labels_path=labels,
                footprint_labels_reviewed=True,
                records=60,
            )

        self.assertEqual(
            metadata["footprint_labels_sha256"],
            hashlib.sha256(b"labels").hexdigest(),
        )
        self.assertTrue(metadata["footprint_labels_reviewed"])


if __name__ == "__main__":
    unittest.main()
