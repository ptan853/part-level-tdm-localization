#!/usr/bin/env python3
"""Run Follow-Your-Shape on the frozen PartEdit pilot manifest.

The default mode is a dry run. Pass --execute to launch the expensive model
commands on a GPU machine.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class FysCommand:
    case_uid: str
    cwd: Path
    args: list[str]
    log_path: Path


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "core").exists():
            return candidate
    raise FileNotFoundError(f"Could not find repository root from {start}")


def resolve_repo_path(repo_root: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return repo_root / path


def load_manifest(path: Path) -> list[dict]:
    records = json.loads(path.read_text())
    if not isinstance(records, list):
        raise ValueError(f"Manifest must contain a list of records: {path}")
    return records


def select_records(records: list[dict], case_uids: Iterable[str] | None, limit: int | None) -> list[dict]:
    selected = records
    if case_uids:
        allowed = set(case_uids)
        selected = [record for record in selected if record.get("case_uid") in allowed]
    if limit is not None:
        selected = selected[:limit]
    return selected


def build_fys_command(
    record: dict,
    *,
    repo_root: Path,
    python_executable: str,
    use_oracle_mask: bool,
    name: str,
    guidance: float,
    num_steps: int,
    front: int,
    inject: int,
    offload: bool,
    controlnet_type: str,
) -> FysCommand:
    case_uid = record["case_uid"]
    source_image = resolve_repo_path(repo_root, record["source_image"])
    output_dir = resolve_repo_path(repo_root, record["follow_your_shape_output_dir"])
    vis_path = resolve_repo_path(repo_root, record["follow_your_shape_vis_path"])
    feature_path = output_dir / "features"
    log_path = output_dir / "run.log"

    args = [
        python_executable,
        "edit.py",
        "--source_img_dir",
        str(source_image),
        "--source_prompt",
        record["source_prompt"],
        "--target_prompt",
        record["target_prompt"],
        "--guidance",
        str(guidance),
        "--num_steps",
        str(num_steps),
        "--front",
        str(front),
        "--inject",
        str(inject),
        "--name",
        name,
        "--controlnet_type",
        controlnet_type,
        "--output_dir",
        str(output_dir),
        "--vis_path",
        str(vis_path),
        "--feature_path",
        str(feature_path),
    ]
    if offload:
        args.append("--offload")
    if use_oracle_mask:
        args.extend(["--mask_path", str(resolve_repo_path(repo_root, record["gt_mask"]))])

    return FysCommand(
        case_uid=case_uid,
        cwd=repo_root / "core" / "third_party" / "FollowYourShape" / "src",
        args=args,
        log_path=log_path,
    )


def format_shell_command(command: FysCommand) -> str:
    import shlex

    return f"cd {shlex.quote(str(command.cwd))} && " + " ".join(
        shlex.quote(str(part)) for part in command.args
    )


def run_command(command: FysCommand) -> int:
    command.log_path.parent.mkdir(parents=True, exist_ok=True)
    with command.log_path.open("w", encoding="utf-8") as log_file:
        log_file.write(format_shell_command(command) + "\n\n")
        log_file.flush()
        process = subprocess.run(
            command.args,
            cwd=command.cwd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return process.returncode


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    default_repo_root = find_repo_root(Path.cwd())
    parser = argparse.ArgumentParser(description="Run Follow-Your-Shape on pilot manifest cases.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=default_repo_root / "core" / "data" / "partedit_subset" / "pilot_manifest.json",
        help="Path to pilot_manifest.json.",
    )
    parser.add_argument("--case-uid", action="append", dest="case_uids", help="Run only this case UID. Repeatable.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N selected cases.")
    parser.add_argument("--execute", action="store_true", help="Actually run FYS. Default is dry-run only.")
    parser.add_argument("--oracle-mask", action="store_true", help="Pass gt_mask as --mask_path for oracle-mask runs.")
    parser.add_argument("--python", default=sys.executable, help="Python executable used inside FollowYourShape/src.")
    parser.add_argument("--name", default="flux-dev", help="FYS model name.")
    parser.add_argument("--guidance", type=float, default=2.0)
    parser.add_argument("--num-steps", type=int, default=15)
    parser.add_argument("--front", type=int, default=2)
    parser.add_argument("--inject", type=int, default=4)
    parser.add_argument("--no-offload", action="store_true", help="Do not pass --offload.")
    parser.add_argument("--controlnet-type", default="none", choices=["none", "single", "multi"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = find_repo_root(args.manifest)
    records = select_records(load_manifest(args.manifest), args.case_uids, args.limit)
    if not records:
        print("No cases selected.", file=sys.stderr)
        return 2

    commands = [
        build_fys_command(
            record,
            repo_root=repo_root,
            python_executable=args.python,
            use_oracle_mask=args.oracle_mask,
            name=args.name,
            guidance=args.guidance,
            num_steps=args.num_steps,
            front=args.front,
            inject=args.inject,
            offload=not args.no_offload,
            controlnet_type=args.controlnet_type,
        )
        for record in records
    ]

    for index, command in enumerate(commands, start=1):
        print(f"[{index}/{len(commands)}] {command.case_uid}")
        print(format_shell_command(command))
        print(f"log: {command.log_path}")
        if args.execute:
            returncode = run_command(command)
            if returncode != 0:
                print(f"FAILED: {command.case_uid} exited with {returncode}", file=sys.stderr)
                return returncode

    if not args.execute:
        print("Dry run only. Add --execute to run these commands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
