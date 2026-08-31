import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from core.scripts.summarize_latent_projection_duration_sweep import (
    compute_region_metrics,
    validate_primary_run,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SummarizeLatentProjectionDurationSweepTests(unittest.TestCase):
    def make_run(self, root: Path, duration: int = 2) -> Path:
        run_dir = root / f"duration_{duration:02d}" / "real_0006" / "seed_000"
        (run_dir / "tdm").mkdir(parents=True)
        Image.new("RGB", (8, 8), "white").save(run_dir / "img_0.jpg")
        stages = [
            {
                "name": "stage1",
                "start": 0,
                "end": 1,
                "image_kv": "source_all",
                "latent_projection": "none",
            }
        ]
        if duration:
            stages.append(
                {
                    "name": "projection",
                    "start": 2,
                    "end": duration + 1,
                    "image_kv": "none",
                    "latent_projection": "source_outside_mask",
                }
            )
        plan = {"name": f"duration_{duration:02d}", "stages": stages}
        write_json(run_dir / "resolved_control_plan.json", plan)
        write_json(run_dir / "run_config.json", {"seed": 0})
        write_json(
            run_dir / "tdm" / "control_trace.json",
            {
                "plan": plan,
                "latent_projection_trace": [
                    {
                        "step": step,
                        "source_latent_index": step + 1,
                        "outside_mae_after": 0.0,
                    }
                    for step in range(2, duration + 2)
                ],
            },
        )
        return run_dir

    def test_validates_expected_projection_trace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = self.make_run(Path(temp_dir), duration=2)
            validated = validate_primary_run(run_dir, duration=2)
            self.assertEqual(validated["projection_steps"], [2, 3])

    def test_rejects_missing_generated_image(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = self.make_run(Path(temp_dir), duration=1)
            (run_dir / "img_0.jpg").unlink()
            with self.assertRaisesRegex(FileNotFoundError, "img_0.jpg"):
                validate_primary_run(run_dir, duration=1)

    def test_rejects_wrong_projection_steps(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = self.make_run(Path(temp_dir), duration=2)
            trace_path = run_dir / "tdm" / "control_trace.json"
            trace = json.loads(trace_path.read_text())
            trace["latent_projection_trace"].pop()
            write_json(trace_path, trace)
            with self.assertRaisesRegex(ValueError, "projection steps"):
                validate_primary_run(run_dir, duration=2)

    def test_rejects_wrong_source_endpoint_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = self.make_run(Path(temp_dir), duration=1)
            trace_path = run_dir / "tdm" / "control_trace.json"
            trace = json.loads(trace_path.read_text())
            trace["latent_projection_trace"][0]["source_latent_index"] = 2
            write_json(trace_path, trace)
            with self.assertRaisesRegex(ValueError, "source latent index"):
                validate_primary_run(run_dir, duration=1)

    def test_rejects_nonzero_outside_projection_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = self.make_run(Path(temp_dir), duration=1)
            trace_path = run_dir / "tdm" / "control_trace.json"
            trace = json.loads(trace_path.read_text())
            trace["latent_projection_trace"][0]["outside_mae_after"] = 0.01
            write_json(trace_path, trace)
            with self.assertRaisesRegex(ValueError, "outside_mae_after"):
                validate_primary_run(run_dir, duration=1)

    def test_rejects_stage3_source_outside_image_kv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = self.make_run(Path(temp_dir), duration=1)
            plan_path = run_dir / "resolved_control_plan.json"
            plan = json.loads(plan_path.read_text())
            plan["stages"].append(
                {"name": "stage3", "start": 10, "end": 13, "image_kv": "source_outside_mask"}
            )
            write_json(plan_path, plan)
            with self.assertRaisesRegex(ValueError, "image-KV"):
                validate_primary_run(run_dir, duration=1)

    def test_computes_inside_and_outside_rgb_mae(self):
        source = np.zeros((2, 2, 3), dtype=np.uint8)
        edited = source.copy()
        edited[0, 0] = 255
        edited[1, 1] = 128
        mask = np.array([[255, 0], [0, 0]], dtype=np.uint8)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            Image.fromarray(source).save(root / "source.png")
            Image.fromarray(edited).save(root / "edited.png")
            Image.fromarray(mask).save(root / "mask.png")
            metrics = compute_region_metrics(root / "source.png", root / "edited.png", root / "mask.png")
        self.assertAlmostEqual(metrics["inside_mask_rgb_mae"], 1.0)
        self.assertAlmostEqual(metrics["outside_mask_rgb_mae"], (128 / 255) / 3)


if __name__ == "__main__":
    unittest.main()
