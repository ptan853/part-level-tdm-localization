#!/usr/bin/env python3
"""Run the simple FLUX target-token attention localization baseline.

Default mode is a dry run. Pass --execute on a GPU machine to extract maps.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class BaselineCommand:
    run_uid: str
    case_uid: str
    seed: int
    args: list[str]
    log_path: Path
    config_path: Path
    row: dict


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "core").exists():
            return candidate
    raise FileNotFoundError(f"Could not find repository root from {start}")


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


def parse_seeds(value: str) -> list[int]:
    seeds = []
    for raw in value.split(","):
        raw = raw.strip()
        if raw:
            seeds.append(int(raw))
    if not seeds:
        raise ValueError("--seeds must contain at least one seed")
    return seeds


def to_repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def format_shell_command(command: BaselineCommand) -> str:
    import shlex

    return " ".join(shlex.quote(str(part)) for part in command.args)


def format_repro_command(
    *,
    repo_root: Path,
    case_json_path: Path,
    output_dir: Path,
    seed: int,
    name: str,
    guidance: float,
    num_steps: int,
    layers: str,
    front: int,
    inject: int,
    tail_pad: int,
    offload: bool,
) -> str:
    import shlex

    parts = [
        "python",
        "core/scripts/flux_attention_worker.py",
        "--case-json",
        to_repo_relative(repo_root, case_json_path),
        "--output-dir",
        to_repo_relative(repo_root, output_dir),
        "--seed",
        str(seed),
        "--name",
        name,
        "--guidance",
        str(guidance),
        "--num-steps",
        str(num_steps),
        "--layers",
        layers,
        "--front",
        str(front),
        "--inject",
        str(inject),
        "--tail-pad",
        str(tail_pad),
    ]
    if offload:
        parts.append("--offload")
    return " ".join(shlex.quote(part) for part in parts)


def write_run_matrix(path: Path, commands: list[BaselineCommand]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [command.row for command in commands]
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_command(
    record: dict,
    *,
    repo_root: Path,
    python_executable: str,
    seed: int,
    name: str,
    guidance: float,
    num_steps: int,
    layers: str,
    front: int,
    inject: int,
    tail_pad: int,
    offload: bool,
    output_root: Path,
    case_json_path: Path,
) -> BaselineCommand:
    case_uid = record["case_uid"]
    run_uid = f"{case_uid}_seed_{seed:03d}"
    output_dir = output_root / case_uid / f"seed_{seed:03d}"
    log_path = output_dir / "run.log"
    config_path = output_dir / "run_config.json"
    worker = repo_root / "core" / "scripts" / "flux_attention_worker.py"

    args = [
        python_executable,
        str(worker),
        "--case-json",
        str(case_json_path),
        "--output-dir",
        str(output_dir),
        "--seed",
        str(seed),
        "--name",
        name,
        "--guidance",
        str(guidance),
        "--num-steps",
        str(num_steps),
        "--layers",
        layers,
        "--front",
        str(front),
        "--inject",
        str(inject),
        "--tail-pad",
        str(tail_pad),
    ]
    if offload:
        args.append("--offload")

    row = {
        "run_uid": run_uid,
        "case_uid": case_uid,
        "seed": seed,
        "dataset_split": record.get("dataset_split"),
        "dataset_index": record.get("dataset_index"),
        "part_size": record.get("part_size"),
        "part": record.get("part"),
        "edit": record.get("edit"),
        "source_prompt": record.get("source_prompt"),
        "target_prompt": record.get("target_prompt"),
        "source_image": record.get("source_image"),
        "gt_mask": record.get("gt_mask"),
        "output_dir": to_repo_relative(repo_root, output_dir),
        "log_path": to_repo_relative(repo_root, log_path),
        "config_path": to_repo_relative(repo_root, config_path),
        "attention_proxy_raw": to_repo_relative(repo_root, output_dir / "attention_proxy_raw.npy"),
        "attention_proxy_smoothed": to_repo_relative(repo_root, output_dir / "attention_proxy_smoothed.npy"),
        "attention_proxy_binary": to_repo_relative(repo_root, output_dir / "attention_proxy_binary.npy"),
        "model_name": name,
        "guidance": guidance,
        "num_steps": num_steps,
        "layers": layers,
        "front": front,
        "inject": inject,
        "tail_pad": tail_pad,
        "offload": offload,
        "repro_command": format_repro_command(
            repo_root=repo_root,
            case_json_path=case_json_path,
            output_dir=output_dir,
            seed=seed,
            name=name,
            guidance=guidance,
            num_steps=num_steps,
            layers=layers,
            front=front,
            inject=inject,
            tail_pad=tail_pad,
            offload=offload,
        ),
    }
    return BaselineCommand(run_uid, case_uid, seed, args, log_path, config_path, row)


def run_command(command: BaselineCommand) -> int:
    command.log_path.parent.mkdir(parents=True, exist_ok=True)
    command.config_path.write_text(json.dumps(command.row, indent=2) + "\n", encoding="utf-8")
    with command.log_path.open("w", encoding="utf-8") as log_file:
        log_file.write(format_shell_command(command) + "\n\n")
        log_file.flush()
        process = subprocess.run(command.args, stdout=log_file, stderr=subprocess.STDOUT, check=False)
    return process.returncode


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    default_repo_root = find_repo_root(Path.cwd())
    parser = argparse.ArgumentParser(description="Run simple FLUX target-token attention localization baseline.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=default_repo_root / "core" / "data" / "partedit_subset" / "pilot_12_manifest.json",
    )
    parser.add_argument("--case-uid", action="append", dest="case_uids")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--name", default="flux-dev")
    parser.add_argument("--guidance", type=float, default=2.0)
    parser.add_argument("--num-steps", type=int, default=15)
    parser.add_argument("--layers", default="28,29,30,31,32,33,34,35,36,37")
    parser.add_argument("--front", type=int, default=2)
    parser.add_argument("--inject", type=int, default=4)
    parser.add_argument("--tail-pad", type=int, default=1)
    parser.add_argument("--no-offload", action="store_true")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=default_repo_root / "core" / "results" / "flux_attention_baseline",
    )
    parser.add_argument("--run-matrix", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = find_repo_root(args.manifest)
    records = select_records(load_manifest(args.manifest), args.case_uids, args.limit)
    if not records:
        print("No cases selected.", file=sys.stderr)
        return 2

    seeds = parse_seeds(args.seeds)
    output_root = args.output_root if args.output_root.is_absolute() else repo_root / args.output_root
    run_matrix_path = args.run_matrix or repo_root / "core" / "results" / "run_matrices" / "flux_attention_baseline_matrix.csv"

    commands: list[BaselineCommand] = []
    for record in records:
        for seed in seeds:
            case_json_path = output_root / record["case_uid"] / f"seed_{seed:03d}" / "case_record.json"
            case_json_path.parent.mkdir(parents=True, exist_ok=True)
            case_json_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            commands.append(
                build_command(
                    record,
                    repo_root=repo_root,
                    python_executable=args.python,
                    seed=seed,
                    name=args.name,
                    guidance=args.guidance,
                    num_steps=args.num_steps,
                    layers=args.layers,
                    front=args.front,
                    inject=args.inject,
                    tail_pad=args.tail_pad,
                    offload=not args.no_offload,
                    output_root=output_root,
                    case_json_path=case_json_path,
                )
            )

    write_run_matrix(run_matrix_path, commands)
    print(f"run matrix: {run_matrix_path}")
    for index, command in enumerate(commands, start=1):
        print(f"[{index}/{len(commands)}] {command.run_uid}")
        print(format_shell_command(command))
        print(f"log: {command.log_path}")
        if args.execute:
            returncode = run_command(command)
            if returncode != 0:
                print(f"FAILED: {command.run_uid} exited with {returncode}", file=sys.stderr)
                return returncode

    if not args.execute:
        print("Dry run only. Add --execute to run these commands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
