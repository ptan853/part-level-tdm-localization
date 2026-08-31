from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "core" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_latent_projection_duration_sweep import (  # noqa: E402
    build_duration_plan,
    build_sweep_commands,
    write_duration_plan,
)


def _record(case_uid: str) -> dict:
    return {
        "case_uid": case_uid,
        "source_image": f"core/data/partedit_subset/cases/{case_uid}/source.png",
        "gt_mask": f"core/data/partedit_subset/cases/{case_uid}/gt_mask.png",
        "source_prompt": "a person standing",
        "target_prompt": "a person with alien head standing",
        "part": "head",
        "edit": "alien",
        "part_size": "small",
    }


class DurationPlanTests(unittest.TestCase):
    def test_duration_zero_has_no_projection_stage(self):
        plan = build_duration_plan(0)

        self.assertEqual(plan["name"], "oracle_projection_duration_00")
        self.assertEqual(len(plan["stages"]), 1)
        self.assertFalse(any("latent_projection" in stage for stage in plan["stages"]))

    def test_duration_one_projects_only_step_two(self):
        plan = build_duration_plan(1)
        projection = plan["stages"][1]

        self.assertEqual((projection["start"], projection["end"]), (2, 2))
        self.assertEqual(projection["latent_projection"], "source_outside_mask")
        self.assertEqual(projection["image_kv"], "none")

    def test_duration_thirteen_projects_steps_two_through_fourteen(self):
        plan = build_duration_plan(13)
        projection = plan["stages"][1]

        self.assertEqual((projection["start"], projection["end"]), (2, 14))

    def test_rejects_duration_outside_supported_range(self):
        for duration in (-1, 14):
            with self.subTest(duration=duration):
                with self.assertRaisesRegex(ValueError, "duration must be between 0 and 13"):
                    build_duration_plan(duration)

    def test_builds_unique_commands_without_stage_three_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_root = root / "latent_projection_duration_sweep"
            plans = [write_duration_plan(output_root / "plans", duration) for duration in (0, 2)]
            commands = build_sweep_commands(
                records=[_record("real_0006"), _record("real_0011")],
                plan_paths=plans,
                repo_root=REPO_ROOT,
                python_executable="python",
                seed=0,
                offload=True,
                output_root=output_root,
            )

            self.assertEqual(len(commands), 4)
            self.assertEqual(len({command.output_dir for command in commands}), 4)
            for plan_path in plans:
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                self.assertFalse(
                    any(stage.get("image_kv") == "source_outside_mask" for stage in plan["stages"])
                )
            self.assertTrue(
                all("latent_projection_duration_sweep/duration_" in command.output_dir.as_posix() for command in commands)
            )


if __name__ == "__main__":
    unittest.main()
