#!/usr/bin/env python3
"""Run same-state source/target inversion diagnostics on selected pilot cases."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_fys_pilot import (
    FysCommand,
    build_fys_command,
    find_repo_root,
    format_shell_command,
    load_manifest,
    run_command,
    select_records as select_manifest_records,
    write_run_matrix,
)


DEFAULT_LAYERS = "28,29,30,31,32,33,34,35,36,37"


def select_records(records: list[dict], case_uids: list[str]) -> list[dict]:
    selected = select_manifest_records(records, case_uids, limit=None)
    found = {record["case_uid"] for record in selected}
    missing = [case_uid for case_uid in case_uids if case_uid not in found]
    if missing:
        raise ValueError(f"Unknown --case-uid value(s): {', '.join(missing)}")
    return selected


def build_commands(
    records: list[dict],
    *,
    repo_root: Path,
    python_executable: str,
    seed: int,
    name: str,
    guidance: float,
    num_steps: int,
    front: int,
    inject: int,
    layers: str,
    offload: bool,
    output_root: Path,
) -> list[FysCommand]:
    commands: list[FysCommand] = []
    for record in records:
        base = build_fys_command(
            record,
            repo_root=repo_root,
            python_executable=python_executable,
            seed=seed,
            seed_subdirs=True,
            use_oracle_mask=False,
            name=name,
            guidance=guidance,
            num_steps=num_steps,
            front=front,
            inject=inject,
            offload=offload,
            controlnet_type="none",
            tdm_mask_mode="original",
            output_root=output_root,
        )
        probe_dir = Path(base.run_config["output_dir"])
        if not probe_dir.is_absolute():
            probe_dir = repo_root / probe_dir
        args = [
            *base.args,
            "--same_state_probe_dir",
            str(probe_dir),
            "--probe_part",
            str(record["part"]),
            "--probe_edit",
            str(record["edit"]),
            "--probe_layers",
            layers,
        ]
        run_config = {
            **base.run_config,
            "run_type": "same_state_inversion_probe",
            "same_state_probe_dir": base.run_config["output_dir"],
            "probe_part": record["part"],
            "probe_edit": record["edit"],
            "probe_layers": layers,
            "diagnostic_masks_control_generation": False,
        }
        commands.append(
            FysCommand(
                case_uid=base.case_uid,
                run_uid=base.run_uid,
                seed=base.seed,
                cwd=base.cwd,
                args=args,
                log_path=base.log_path,
                config_path=base.config_path,
                run_config=run_config,
            )
        )
    return commands


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repo_root = find_repo_root(Path.cwd())
    parser = argparse.ArgumentParser(description="Run same-state inversion localization diagnostics.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=repo_root / "core" / "data" / "partedit_subset" / "pilot_12_manifest.json",
    )
    parser.add_argument("--case-uid", action="append", dest="case_uids")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--write-run-matrix", action="store_true")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--name", default="flux-dev")
    parser.add_argument("--guidance", type=float, default=2.0)
    parser.add_argument("--num-steps", type=int, default=15)
    parser.add_argument("--front", type=int, default=2)
    parser.add_argument("--inject", type=int, default=4)
    parser.add_argument("--layers", default=DEFAULT_LAYERS)
    parser.add_argument("--no-offload", action="store_true")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=repo_root / "core" / "results" / "same_state_inversion_probe",
    )
    parser.add_argument(
        "--run-matrix",
        type=Path,
        default=repo_root / "core" / "results" / "run_matrices" / "same_state_inversion_probe_matrix.csv",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.case_uids:
        raise ValueError("At least one explicit --case-uid is required")

    repo_root = find_repo_root(args.manifest)
    output_root = args.output_root if args.output_root.is_absolute() else repo_root / args.output_root
    run_matrix = args.run_matrix if args.run_matrix.is_absolute() else repo_root / args.run_matrix
    records = select_records(load_manifest(args.manifest), args.case_uids)
    commands = build_commands(
        records,
        repo_root=repo_root,
        python_executable=args.python,
        seed=args.seed,
        name=args.name,
        guidance=args.guidance,
        num_steps=args.num_steps,
        front=args.front,
        inject=args.inject,
        layers=args.layers,
        offload=not args.no_offload,
        output_root=output_root,
    )

    if args.execute or args.write_run_matrix:
        write_run_matrix(run_matrix, commands, repo_root)
        print(f"run matrix: {run_matrix}")
    else:
        print(f"run matrix path: {run_matrix} (not written in dry-run)")

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
