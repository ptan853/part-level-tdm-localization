#!/usr/bin/env python3
"""Run Follow-Your-Shape on the frozen PartEdit pilot manifest.

The default mode is a dry run. Pass --execute to launch the expensive model
commands on a GPU machine.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class FysCommand:
    case_uid: str
    run_uid: str
    seed: int | None
    cwd: Path
    args: list[str]
    log_path: Path
    config_path: Path
    run_config: dict


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


def parse_seeds(value: str | None) -> list[int | None]:
    if value is None or value.strip() == "":
        return [None]
    seeds = []
    for raw_seed in value.split(","):
        raw_seed = raw_seed.strip()
        if not raw_seed:
            continue
        seeds.append(int(raw_seed))
    if not seeds:
        raise ValueError("--seeds must contain at least one integer seed")
    return seeds


def to_repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def to_relative_from(base: Path, path: Path) -> str:
    try:
        return Path(os.path.relpath(path.resolve(), start=base.resolve())).as_posix()
    except ValueError:
        return str(path)


def build_fys_command(
    record: dict,
    *,
    repo_root: Path,
    python_executable: str,
    seed: int | None,
    seed_subdirs: bool,
    use_oracle_mask: bool,
    name: str,
    guidance: float,
    num_steps: int,
    front: int,
    inject: int,
    offload: bool,
    controlnet_type: str,
    tdm_mask_mode: str = "original",
    attention_token_mode: str = "part_edit",
    attention_layers: str = "28,29,30,31,32,33,34,35,36,37",
    output_root: Path | None = None,
) -> FysCommand:
    case_uid = record["case_uid"]
    run_uid = case_uid if seed is None else f"{case_uid}_seed_{seed:03d}"
    source_image = resolve_repo_path(repo_root, record["source_image"])
    if output_root is None:
        base_output_dir = resolve_repo_path(repo_root, record["follow_your_shape_output_dir"])
    else:
        base_output_dir = output_root / case_uid
    output_dir = base_output_dir / f"seed_{seed:03d}" if seed is not None and seed_subdirs else base_output_dir
    vis_path = output_dir / "tdm"
    feature_path = output_dir / "features"
    log_path = output_dir / "run.log"
    config_path = output_dir / "run_config.json"

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
    if seed is not None:
        args.extend(["--seed", str(seed)])
    if offload:
        args.append("--offload")
    if use_oracle_mask:
        args.extend(["--mask_path", str(resolve_repo_path(repo_root, record["gt_mask"]))])
    if tdm_mask_mode != "original":
        args.extend(
            [
                "--tdm_mask_mode",
                tdm_mask_mode,
                "--attention_token_mode",
                attention_token_mode,
                "--attention_part",
                str(record.get("part", "")),
                "--attention_edit",
                str(record.get("edit", "")),
                "--attention_layers",
                attention_layers,
            ]
        )

    run_config = {
        "run_uid": run_uid,
        "case_uid": case_uid,
        "seed": seed,
        "dataset_id": record.get("dataset_id"),
        "dataset_split": record.get("dataset_split"),
        "dataset_index": record.get("dataset_index"),
        "class_name": record.get("class_name"),
        "subject": record.get("subject"),
        "part": record.get("part"),
        "normalized_part": record.get("normalized_part"),
        "part_size": record.get("part_size"),
        "mask_area_ratio": record.get("mask_area_ratio"),
        "edit": record.get("edit"),
        "source_prompt": record["source_prompt"],
        "target_prompt": record["target_prompt"],
        "source_image": to_repo_relative(repo_root, source_image),
        "gt_mask": record.get("gt_mask"),
        "partedit_reference": record.get("partedit_reference"),
        "output_dir": to_repo_relative(repo_root, output_dir),
        "vis_path": to_repo_relative(repo_root, vis_path),
        "feature_path": to_repo_relative(repo_root, feature_path),
        "log_path": to_repo_relative(repo_root, log_path),
        "model_name": name,
        "guidance": guidance,
        "num_steps": num_steps,
        "front": front,
        "inject": inject,
        "offload": offload,
        "controlnet_type": controlnet_type,
        "use_oracle_mask": use_oracle_mask,
        "tdm_mask_mode": tdm_mask_mode,
        "attention_token_mode": attention_token_mode if tdm_mask_mode != "original" else None,
        "attention_part": record.get("part") if tdm_mask_mode != "original" else None,
        "attention_edit": record.get("edit") if tdm_mask_mode != "original" else None,
        "attention_layers": attention_layers if tdm_mask_mode != "original" else None,
    }

    return FysCommand(
        case_uid=case_uid,
        run_uid=run_uid,
        seed=seed,
        cwd=repo_root / "core" / "third_party" / "FollowYourShape" / "src",
        args=args,
        log_path=log_path,
        config_path=config_path,
        run_config=run_config,
    )


def format_shell_command(command: FysCommand) -> str:
    import shlex

    return f"cd {shlex.quote(str(command.cwd))} && " + " ".join(
        shlex.quote(str(part)) for part in command.args
    )


def format_repro_command(command: FysCommand, repo_root: Path) -> str:
    import shlex

    cwd = to_repo_relative(repo_root, command.cwd)
    parts = ["python", *command.args[1:]]
    relative_parts = []
    for part in parts:
        path = Path(str(part))
        if path.is_absolute():
            relative_parts.append(to_relative_from(command.cwd, path))
        else:
            relative_parts.append(str(part))
    return f"cd {shlex.quote(cwd)} && " + " ".join(shlex.quote(part) for part in relative_parts)


def run_command(command: FysCommand) -> int:
    command.log_path.parent.mkdir(parents=True, exist_ok=True)
    command.config_path.write_text(json.dumps(command.run_config, indent=2) + "\n", encoding="utf-8")
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


def write_run_matrix(path: Path, commands: list[FysCommand], repo_root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for command in commands:
        row = {
            **command.run_config,
            "cwd": to_repo_relative(repo_root, command.cwd),
            "config_path": to_repo_relative(repo_root, command.config_path),
            "repro_command": format_repro_command(command, repo_root),
        }
        rows.append(row)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


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
    parser.add_argument("--seeds", default=None, help="Comma-separated fixed seeds, e.g. '0,1,2'.")
    parser.add_argument(
        "--flat-output",
        action="store_true",
        help="Do not append seed_XXX to output dirs when --seeds is provided.",
    )
    parser.add_argument(
        "--run-matrix",
        type=Path,
        default=None,
        help="Optional CSV path for the generated command/config matrix.",
    )
    parser.add_argument(
        "--write-run-matrix",
        action="store_true",
        help="Write the command/config matrix during dry-run. --execute always writes it.",
    )
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
    parser.add_argument("--tdm-mask-mode", default="original", choices=["original", "attention_gated"])
    parser.add_argument("--attention-token-mode", default="part_edit", choices=["part", "edit", "part_edit"])
    parser.add_argument("--attention-layers", default="28,29,30,31,32,33,34,35,36,37")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Optional output root. Defaults to manifest output for original mode and an ablation root for attention-gated mode.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = find_repo_root(args.manifest)
    records = select_records(load_manifest(args.manifest), args.case_uids, args.limit)
    if not records:
        print("No cases selected.", file=sys.stderr)
        return 2

    seeds = parse_seeds(args.seeds)
    output_root = None
    if args.output_root is not None:
        output_root = args.output_root if args.output_root.is_absolute() else repo_root / args.output_root
    if output_root is None and args.tdm_mask_mode != "original":
        output_root = repo_root / "core" / "results" / "fys_mask_ablation" / "attention_gated_tdm"
    commands = []
    for record in records:
        for seed in seeds:
            commands.append(
                build_fys_command(
                    record,
                    repo_root=repo_root,
                    python_executable=args.python,
                    seed=seed,
                    seed_subdirs=not args.flat_output,
                    use_oracle_mask=args.oracle_mask,
                    name=args.name,
                    guidance=args.guidance,
                    num_steps=args.num_steps,
                    front=args.front,
                    inject=args.inject,
                    offload=not args.no_offload,
                    controlnet_type=args.controlnet_type,
                    tdm_mask_mode=args.tdm_mask_mode,
                    attention_token_mode=args.attention_token_mode,
                    attention_layers=args.attention_layers,
                    output_root=output_root,
                )
            )

    run_matrix_path = args.run_matrix
    if run_matrix_path is None:
        suffix = "single_seed" if args.seeds is None else "multi_seed"
        mode_prefix = "" if args.tdm_mask_mode == "original" else f"{args.tdm_mask_mode}_{args.attention_token_mode}_"
        run_matrix_path = repo_root / "core" / "results" / "run_matrices" / f"{mode_prefix}{args.manifest.stem}_{suffix}.csv"
    elif not run_matrix_path.is_absolute():
        run_matrix_path = repo_root / run_matrix_path
    should_write_matrix = args.execute or args.write_run_matrix or args.run_matrix is not None
    if should_write_matrix:
        write_run_matrix(run_matrix_path, commands, repo_root)
        print(f"run matrix: {run_matrix_path}")
    else:
        print(f"run matrix path: {run_matrix_path} (not written in dry-run)")

    for index, command in enumerate(commands, start=1):
        print(f"[{index}/{len(commands)}] {command.run_uid}")
        print(format_shell_command(command))
        print(f"log: {command.log_path}")
        print(f"config: {command.config_path}")
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
