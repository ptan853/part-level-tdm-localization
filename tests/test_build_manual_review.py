import csv
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO_ROOT / "core" / "scripts" / "build_manual_review.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ManualReviewBuilderTest(unittest.TestCase):
    def test_builds_configurable_review_page_with_import_and_export(self):
        builder = load_module(BUILDER_PATH, "build_manual_review")
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            image = root / "image.png"
            image.write_bytes(b"image")
            input_path = root / "review.csv"
            with input_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "review_uid", "case_uid", "method", "part", "edit",
                        "part_size", "target_prompt", "source_image", "gt_mask",
                        "edited_image", "local_edit_success_0_2",
                        "non_target_preservation_0_2", "short_note",
                    ],
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerow({
                    "review_uid": "case_a::method_a",
                    "case_uid": "case_a",
                    "method": "method_a",
                    "part": "head",
                    "edit": "alien",
                    "part_size": "small",
                    "target_prompt": "an alien head",
                    "source_image": "image.png",
                    "gt_mask": "image.png",
                    "edited_image": "image.png",
                    "local_edit_success_0_2": "",
                    "non_target_preservation_0_2": "",
                    "short_note": "",
                })
            config_path = root / "config.json"
            config_path.write_text(json.dumps({
                "title": "Reusable review",
                "storage_key": "reusable-review-v1",
                "download_filename": "scores.csv",
                "id_field": "review_uid",
                "image_fields": [
                    {"key": "source_image", "label": "Source"},
                    {"key": "gt_mask", "label": "GT"},
                    {"key": "edited_image", "label": "Output"},
                ],
                "score_fields": [
                    {
                        "key": "local_edit_success_0_2",
                        "label": "Local edit success",
                        "hint": "0 failed; 1 partial; 2 successful.",
                        "values": [0, 1, 2],
                    },
                    {
                        "key": "non_target_preservation_0_2",
                        "label": "Non-target preservation",
                        "hint": "0 poor; 1 partial; 2 preserved.",
                        "values": [0, 1, 2],
                    },
                ],
                "note_field": "short_note",
            }), encoding="utf-8")
            output_path = root / "review.html"

            records = builder.build_review_page(
                repo_root=root,
                input_path=input_path,
                config_path=config_path,
                output_path=output_path,
            )
            html = output_path.read_text(encoding="utf-8")

        self.assertEqual(len(records), 1)
        self.assertIn("Reusable review", html)
        self.assertIn("case_a::method_a", html)
        self.assertIn("Import CSV", html)
        self.assertIn("Download CSV", html)
        self.assertIn("reusable-review-v1", html)
        self.assertIn('accept=".csv,text/csv"', html)
        self.assertIn('.join("\\r\\n")+"\\r\\n"', html)
        self.assertIn("char==='\\n'", html)

    def test_rejects_duplicate_review_ids(self):
        builder = load_module(BUILDER_PATH, "build_manual_review_duplicate")
        records = [{"review_uid": "same"}, {"review_uid": "same"}]
        with self.assertRaisesRegex(ValueError, "Duplicate review id"):
            builder.validate_records(records, "review_uid")


if __name__ == "__main__":
    unittest.main()
