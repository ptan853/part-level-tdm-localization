from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "core" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_residual_rk2_prefix_sweep import (  # noqa: E402
    build_prefix_plan,
    build_sweep_commands,
    parse_durations,
    select_sweep_records,
    write_prefix_plan,
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


class ResidualPrefixSweepTests(unittest.TestCase):
    def test_duration_zero_has_no_control_stage(self):
        self.assertEqual(build_prefix_plan(0)["stages"], [])

    def test_duration_one_controls_only_step_zero(self):
        stage = build_prefix_plan(1)["stages"][0]

        self.assertEqual(stage["start"], 0)
        self.assertEqual(stage["end"], 0)
        self.assertEqual(stage["residual_control"], "source_referenced_rk2")

    def test_duration_fifteen_controls_complete_trajectory(self):
        stage = build_prefix_plan(15)["stages"][0]

        self.assertEqual(stage["start"], 0)
        self.assertEqual(stage["end"], 14)

    def test_parse_complete_duration_range(self):
        self.assertEqual(parse_durations("0-15"), list(range(16)))

    def test_rejects_duration_outside_supported_range(self):
        for duration in (-1, 16):
            with self.subTest(duration=duration):
                with self.assertRaisesRegex(ValueError, "between 0 and 15"):
                    build_prefix_plan(duration)

    def test_primary_plans_never_enable_image_kv(self):
        for duration in range(16):
            with self.subTest(duration=duration):
                plan = build_prefix_plan(duration)
                self.assertFalse(any(stage.get("image_kv") != "none" for stage in plan["stages"]))

    def test_all_cases_selects_complete_manifest(self):
        records = [_record(f"real_{index:04d}") for index in range(12)]

        selected = select_sweep_records(records, case_uids=None, all_cases=True)

        self.assertEqual(selected, records)

    def test_twelve_cases_times_sixteen_durations_have_unique_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / "residual_rk2_prefix_sweep"
            plans = [
                write_prefix_plan(output_root / "plans", duration)
                for duration in range(16)
            ]
            commands = build_sweep_commands(
                records=[_record(f"real_{index:04d}") for index in range(12)],
                plan_paths=plans,
                repo_root=REPO_ROOT,
                python_executable="python",
                seed=0,
                offload=True,
                output_root=output_root,
            )

            self.assertEqual(len(commands), 192)
            self.assertEqual(len({command.output_dir for command in commands}), 192)
            self.assertTrue(
                all(
                    "residual_rk2_prefix_sweep/duration_" in command.output_dir.as_posix()
                    for command in commands
                )
            )
            for plan_path in plans:
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                self.assertFalse(
                    any(stage.get("image_kv") != "none" for stage in plan["stages"])
                )


if __name__ == "__main__":
    unittest.main()
