import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO_ROOT / "core" / "scripts" / "build_oracle_review.py"


def load_builder_module():
    spec = importlib.util.spec_from_file_location("build_oracle_review", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class OracleReviewBuilderTest(unittest.TestCase):
    def test_build_review_page_contains_all_cases_and_review_controls(self):
        builder = load_builder_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "oracle_review.html"
            records = builder.build_review_page(REPO_ROOT, output_path)
            html = output_path.read_text(encoding="utf-8")

        self.assertEqual(len(records), 12)
        self.assertIn("real_0006", html)
        self.assertIn("oracle_local_edit_0_2", html)
        self.assertIn("oracle_preservation_0_2", html)
        self.assertIn("localStorage", html)
        self.assertIn("downloadCsv", html)
        self.assertIn("Copy CSV", html)

    def test_all_review_images_exist(self):
        builder = load_builder_module()
        records = builder.load_review_records(REPO_ROOT)

        for record in records:
            with self.subTest(case_uid=record["case_uid"]):
                for key in ("source_image", "gt_mask", "oracle_image", "actual_mask"):
                    self.assertTrue((REPO_ROOT / record[key]).is_file(), record[key])


if __name__ == "__main__":
    unittest.main()
