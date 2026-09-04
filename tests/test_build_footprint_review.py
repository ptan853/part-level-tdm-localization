import csv
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO_ROOT / "core" / "scripts" / "build_footprint_review.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_fixture(root: Path, *, record_count: int = 60) -> tuple[Path, Path]:
    manifest = []
    labels_path = root / "labels.csv"
    with labels_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "dataset_index",
                "part",
                "edit",
                "source_prompt",
                "target_prompt",
                "footprint_change",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for index in range(record_count):
            image = root / f"source_{index:04d}.png"
            image.write_bytes(b"image")
            source_prompt = f"source prompt {index}"
            target_prompt = f"target prompt {index}"
            manifest.append(
                {
                    "case_uid": f"synth_{index:04d}",
                    "dataset_index": index,
                    "part": "head",
                    "edit": "robot",
                    "part_size": "small" if index < 20 else "medium" if index < 40 else "large",
                    "source_prompt": source_prompt,
                    "target_prompt": target_prompt,
                    "source_image": image.name,
                    "gt_mask": f"forbidden_gt_{index}.png",
                    "partedit_reference": f"forbidden_reference_{index}.png",
                    "footprint_change": "comparable",
                }
            )
            writer.writerow(
                {
                    "dataset_index": index,
                    "part": "head",
                    "edit": "robot",
                    "source_prompt": source_prompt,
                    "target_prompt": target_prompt,
                    "footprint_change": "comparable",
                }
            )
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, labels_path


class FootprintReviewBuilderTest(unittest.TestCase):
    def test_builds_safe_60_case_review_with_overview_and_csv_export(self):
        builder = load_module(BUILDER_PATH, "build_footprint_review")
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest, labels = write_fixture(root)
            output = root / "review.html"

            records = builder.build_footprint_review_page(
                repo_root=root,
                manifest_path=manifest,
                labels_path=labels,
                output_path=output,
            )
            html = output.read_text(encoding="utf-8")

        self.assertEqual(len(records), 60)
        self.assertIn("Review all 60", html)
        self.assertIn("Overview", html)
        self.assertIn("source prompt 0", html)
        self.assertIn("target prompt 0", html)
        self.assertIn("contraction", html)
        self.assertIn("comparable", html)
        self.assertIn("expansion", html)
        self.assertIn("footprint_change", html)
        self.assertIn("reviewed:false", html)
        self.assertIn("localStorage", html)
        self.assertIn("Download CSV", html)
        self.assertNotIn("gt_mask", html)
        self.assertNotIn("partedit_reference", html)
        self.assertNotIn("forbidden_gt", html)
        self.assertNotIn("forbidden_reference", html)

    def test_rejects_non_frozen_case_count(self):
        builder = load_module(BUILDER_PATH, "build_footprint_review_short")
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest, labels = write_fixture(root, record_count=59)
            with self.assertRaisesRegex(ValueError, "exactly 60"):
                builder.build_footprint_review_page(
                    repo_root=root,
                    manifest_path=manifest,
                    labels_path=labels,
                    output_path=root / "review.html",
                )


if __name__ == "__main__":
    unittest.main()
