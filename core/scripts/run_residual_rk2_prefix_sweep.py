#!/usr/bin/env python3
"""Run an oracle-mask inversion-referenced residual RK2 prefix sweep."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_HINT = SCRIPT_DIR.parents[1]
FYS_SRC = REPO_HINT / "core" / "third_party" / "FollowYourShape" / "src"
sys.path.insert(0, str(FYS_SRC))

from run_control_plan import (  # noqa: E402
    ControlCommand,
    build_control_command,
    execute_command,
    format_command,
    write_run_matrix,
)
from run_fys_pilot import (  # noqa: E402
    find_repo_root,
    load_manifest,
    resolve_repo_path,
    select_records,
)


DEFAULT_CASE_UIDS = ("real_0006", "real_0010")
MIN_DURATION = 0
MAX_DURATION = 15


def build_prefix_plan(duration: int) -> dict:
    if duration < MIN_DURATION or duration > MAX_DURATION:
        raise ValueError("duration must be between 0 and 15")

    stages = []
    if duration:
        stages.append(
            {
                "name": "residual_prefix",
                "start": 0,
                "end": duration - 1,
                "prompt": "target",
                "image_kv": "none",
                "it_gate": "none",
                "latent_projection": "none",
                "residual_control": "source_referenced_rk2",
            }
        )

    return {
        "name": f"residual_rk2_prefix_{duration:02d}",
        "num_steps": 15,
        "front": 2,
        "inject": 4,
        "tail_pad": 1,
        "mask_source": "oracle",
        "stages": stages,
        "image_kv_layers": [],
        "it_gate_layers": [],
    }


def write_prefix_plan(plan_dir: Path, duration: int) -> Path:
    plan_dir.mkdir(parents=True, exist_ok=True)
    path = plan_dir / f"duration_{duration:02d}.json"
    path.write_text(
        json.dumps(build_prefix_plan(duration), indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def build_sweep_commands(
    *,
    records: list[dict],
    plan_paths: list[Path],
    repo_root: Path,
    python_executable: str,
    seed: int,
    offload: bool,
    output_root: Path,
    guidance: float = 2.0,
    model_name: str = "flux-dev",
) -> list[ControlCommand]:
    commands = []
    for plan_path in plan_paths:
        duration = int(plan_path.stem.rsplit("_", 1)[-1])
        duration_root = output_root / f"duration_{duration:02d}"
        for record in records:
            commands.append(
                build_control_command(
                    record,
                    plan_path=plan_path,
                    repo_root=repo_root,
                    python_executable=python_executable,
                    seed=seed,
                    offload=offload,
                    guidance=guidance,
                    model_name=model_name,
                    output_root=duration_root,
                )
            )
    return commands


def parse_durations(value: str) -> list[int]:
    durations = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError(
                    "duration range end must be greater than or equal to start"
                )
            durations.extend(range(start, end + 1))
        else:
            durations.append(int(item))
    unique = list(dict.fromkeys(durations))
    if not unique:
        raise ValueError("at least one duration is required")
    for duration in unique:
        build_prefix_plan(duration)
    return unique


def select_sweep_records(
    manifest: list[dict],
    *,
    case_uids: list[str] | None,
    all_cases: bool,
) -> list[dict]:
    if all_cases and case_uids:
        raise ValueError("cannot combine --all-cases with --case-uid")
    if all_cases:
        if not manifest:
            raise ValueError("manifest contains no cases")
        return manifest
    selected_uids = case_uids or list(DEFAULT_CASE_UIDS)
    records = select_records(manifest, selected_uids, None)
    if {str(record["case_uid"]) for record in records} != set(selected_uids):
        raise ValueError("every requested case UID must exist in the manifest")
    return records


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repo_root = find_repo_root(Path.cwd())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=(
            repo_root
            / "core"
            / "data"
            / "partedit_subset"
            / "pilot_12_manifest.json"
        ),
    )
    parser.add_argument("--case-uid", action="append", dest="case_uids")
    parser.add_argument(
        "--all-cases",
        action="store_true",
        help="Run every case in the manifest instead of the two-case diagnostic default.",
    )
    parser.add_argument("--durations", default="0-15")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--run-matrix", type=Path)
    parser.add_argument("--guidance", type=float, default=2.0)
    parser.add_argument("--name", default="flux-dev")
    parser.add_argument("--no-offload", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--write-run-matrix", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = find_repo_root(args.manifest)
    records = select_sweep_records(
        load_manifest(args.manifest),
        case_uids=args.case_uids,
        all_cases=args.all_cases,
    )
    durations = parse_durations(args.durations)
    output_root = (
        resolve_repo_path(repo_root, str(args.output_root))
        if args.output_root is not None
        else (
            repo_root
            / "core"
            / "results"
            / "control_operations"
            / "residual_rk2_prefix_sweep"
        )
    )
    plan_paths = [
        write_prefix_plan(output_root / "plans", duration)
        for duration in durations
    ]
    commands = build_sweep_commands(
        records=records,
        plan_paths=plan_paths,
        repo_root=repo_root,
        python_executable=args.python,
        seed=args.seed,
        offload=not args.no_offload,
        output_root=output_root,
        guidance=args.guidance,
        model_name=args.name,
    )
    matrix_path = (
        resolve_repo_path(repo_root, str(args.run_matrix))
        if args.run_matrix is not None
        else (
            repo_root
            / "core"
            / "results"
            / "run_matrices"
            / "residual_rk2_prefix_sweep.csv"
        )
    )
    if args.execute or args.write_run_matrix:
        write_run_matrix(matrix_path, commands, repo_root)
        print(f"run matrix: {matrix_path}")
    else:
        print(f"run matrix path: {matrix_path} (not written in dry-run)")

    for index, command in enumerate(commands, start=1):
        print(f"[{index}/{len(commands)}] {command.plan.name}/{command.run_uid}")
        print(format_command(command))
        print(f"output: {command.output_dir}")
        if args.execute:
            returncode = execute_command(command, overwrite=args.overwrite)
            if returncode:
                print(
                    f"FAILED: {command.plan.name}/{command.run_uid} exited with {returncode}",
                    file=sys.stderr,
                )
                return returncode
    if not args.execute:
        print("Dry run only. Add --execute to run these commands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
