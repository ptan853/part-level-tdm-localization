#!/usr/bin/env python3
"""Run isolated, config-driven FYS control-operation experiments."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_HINT = SCRIPT_DIR.parents[1]
FYS_SRC = REPO_HINT / "core" / "third_party" / "FollowYourShape" / "src"
sys.path.insert(0, str(FYS_SRC))

from flux.control_schedule import ControlPlan, load_control_plan  # noqa: E402
from run_fys_pilot import (  # noqa: E402
    find_repo_root,
    load_manifest,
    parse_seeds,
    resolve_repo_path,
    select_records,
    to_repo_relative,
)


@dataclass(frozen=True)
class ControlCommand:
    case_uid: str
    run_uid: str
    seed: int
    cwd: Path
    args: list[str]
    output_dir: Path
    log_path: Path
    run_config: dict
    case_record: dict
    plan: ControlPlan


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_output_dir(path: Path, *, overwrite: bool) -> None:
    if path.exists() and any(path.iterdir()) and not overwrite:
        raise FileExistsError(
            f"output directory is not empty: {path}; pass --overwrite to replace it"
        )


def build_control_command(
    record: dict,
    *,
    plan_path: Path,
    repo_root: Path,
    python_executable: str,
    seed: int,
    offload: bool,
    guidance: float = 2.0,
    model_name: str = "flux-dev",
    output_root: Path | None = None,
    control_mask_path: Path | None = None,
) -> ControlCommand:
    plan_path = plan_path.resolve()
    plan = load_control_plan(plan_path)
    case_uid = str(record["case_uid"])
    run_uid = f"{case_uid}_seed_{seed:03d}"
    if output_root is None:
        output_root = repo_root / "core" / "results" / "control_operations" / plan.name
    output_dir = output_root / case_uid / f"seed_{seed:03d}"
    source_image = resolve_repo_path(repo_root, record["source_image"])
    gt_mask = resolve_repo_path(repo_root, record["gt_mask"])
    if plan.mask_source == "precomputed" and control_mask_path is None:
        raise ValueError("precomputed control plan requires control_mask_path")
    if plan.mask_source not in {None, "oracle", "precomputed"}:
        raise ValueError(
            f"control runner does not yet support mask_source={plan.mask_source!r}"
        )
    cwd = repo_root / "core" / "third_party" / "FollowYourShape" / "src"
    args = [
        python_executable,
        "edit.py",
        "--source_img_dir",
        str(source_image),
        "--source_prompt",
        str(record["source_prompt"]),
        "--target_prompt",
        str(record["target_prompt"]),
        "--guidance",
        str(guidance),
        "--num_steps",
        str(plan.num_steps),
        "--front",
        str(plan.front),
        "--inject",
        str(plan.inject),
        "--seed",
        str(seed),
        "--name",
        model_name,
        "--controlnet_type",
        "none",
        "--output_dir",
        str(output_dir),
        "--vis_path",
        str(output_dir / "tdm"),
        "--feature_path",
        str(output_dir / "features"),
        "--attention_part",
        str(record.get("part", "")),
        "--attention_edit",
        str(record.get("edit", "")),
        "--control-plan-resolved",
        str(plan_path),
    ]
    if plan.mask_source == "oracle":
        args.extend(["--mask_path", str(gt_mask), "--tdm_mask_mode", "oracle"])
    else:
        args.extend(["--tdm_mask_mode", "original"])
    if plan.mask_source == "precomputed":
        args.extend(["--control-mask-path", str(control_mask_path)])
    if offload:
        args.append("--offload")

    run_config = {
        "run_uid": run_uid,
        "case_uid": case_uid,
        "seed": seed,
        "plan_name": plan.name,
        "plan_path": to_repo_relative(repo_root, plan_path),
        "plan_sha256": _sha256(plan_path),
        "source_image": record["source_image"],
        "gt_mask": record["gt_mask"],
        "mask_source": plan.mask_source,
        "control_mask_path": (
            None if control_mask_path is None else str(control_mask_path)
        ),
        "source_prompt": record["source_prompt"],
        "target_prompt": record["target_prompt"],
        "part": record.get("part"),
        "edit": record.get("edit"),
        "part_size": record.get("part_size"),
        "output_dir": to_repo_relative(repo_root, output_dir),
        "model_name": model_name,
        "guidance": guidance,
        "num_steps": plan.num_steps,
        "front": plan.front,
        "inject": plan.inject,
        "tail_pad": plan.tail_pad,
        "offload": offload,
        "resolved_control_plan": plan.to_dict(),
    }
    return ControlCommand(
        case_uid=case_uid,
        run_uid=run_uid,
        seed=seed,
        cwd=cwd,
        args=args,
        output_dir=output_dir,
        log_path=output_dir / "run.log",
        run_config=run_config,
        case_record=dict(record),
        plan=plan,
    )


def format_command(command: ControlCommand) -> str:
    return f"cd {shlex.quote(str(command.cwd))} && " + " ".join(
        shlex.quote(str(value)) for value in command.args
    )


def execute_command(command: ControlCommand, *, overwrite: bool) -> int:
    validate_output_dir(command.output_dir, overwrite=overwrite)
    if overwrite and command.output_dir.exists():
        shutil.rmtree(command.output_dir)
    command.output_dir.mkdir(parents=True, exist_ok=True)
    (command.output_dir / "case_record.json").write_text(
        json.dumps(command.case_record, indent=2) + "\n", encoding="utf-8"
    )
    (command.output_dir / "resolved_control_plan.json").write_text(
        json.dumps(command.plan.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    (command.output_dir / "run_config.json").write_text(
        json.dumps(command.run_config, indent=2) + "\n", encoding="utf-8"
    )
    with command.log_path.open("w", encoding="utf-8") as log:
        log.write(format_command(command) + "\n\n")
        log.flush()
        result = subprocess.run(
            command.args,
            cwd=command.cwd,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return result.returncode


def write_run_matrix(path: Path, commands: list[ControlCommand], repo_root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            **command.run_config,
            "resolved_control_plan": json.dumps(command.run_config["resolved_control_plan"]),
            "command": format_command(command),
        }
        for command in commands
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repo_root = find_repo_root(Path.cwd())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=repo_root / "core" / "data" / "partedit_subset" / "pilot_12_manifest.json",
    )
    parser.add_argument("--case-uid", action="append", dest="case_uids")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--seeds", default="0")
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
    plan_path = resolve_repo_path(repo_root, str(args.plan))
    plan = load_control_plan(plan_path)
    records = select_records(load_manifest(args.manifest), args.case_uids, args.limit)
    seeds = parse_seeds(args.seeds)
    if not records or any(seed is None for seed in seeds):
        raise ValueError("at least one case and one integer seed are required")
    output_root = (
        resolve_repo_path(repo_root, str(args.output_root))
        if args.output_root is not None
        else repo_root / "core" / "results" / "control_operations" / plan.name
    )
    commands = [
        build_control_command(
            record,
            plan_path=plan_path,
            repo_root=repo_root,
            python_executable=args.python,
            seed=int(seed),
            offload=not args.no_offload,
            guidance=args.guidance,
            model_name=args.name,
            output_root=output_root,
        )
        for record in records
        for seed in seeds
    ]
    matrix_path = (
        resolve_repo_path(repo_root, str(args.run_matrix))
        if args.run_matrix is not None
        else repo_root / "core" / "results" / "run_matrices" / f"{plan.name}.csv"
    )
    if args.execute or args.write_run_matrix:
        write_run_matrix(matrix_path, commands, repo_root)
        print(f"run matrix: {matrix_path}")
    else:
        print(f"run matrix path: {matrix_path} (not written in dry-run)")

    for index, command in enumerate(commands, start=1):
        print(f"[{index}/{len(commands)}] {command.run_uid}")
        print(format_command(command))
        print(f"output: {command.output_dir}")
        if args.execute:
            returncode = execute_command(command, overwrite=args.overwrite)
            if returncode:
                print(f"FAILED: {command.run_uid} exited with {returncode}", file=sys.stderr)
                return returncode
    if not args.execute:
        print("Dry run only. Add --execute to run these commands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
