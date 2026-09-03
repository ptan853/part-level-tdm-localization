#!/usr/bin/env python3
"""Run the frozen three-method comparison with a shared automatic mask scout."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_HINT = SCRIPT_DIR.parents[1]
FYS_SRC = REPO_HINT / "core" / "third_party" / "FollowYourShape" / "src"
sys.path.insert(0, str(FYS_SRC))

from run_control_plan import (  # noqa: E402
    ControlCommand,
    build_control_command,
    execute_command,
    format_command,
    validate_output_dir,
)
from run_fys_pilot import (  # noqa: E402
    FysCommand,
    build_fys_command,
    find_repo_root,
    format_shell_command,
    load_manifest,
    parse_seeds,
    resolve_repo_path,
    run_command,
    select_records,
)


CONTROL_DURATION = 7
EVALUATED_METHODS = (
    "original_fys_tdm",
    "endpoint_projection",
    "residual_rk2",
)
SCOUT_MASK_FILENAME = "hybrid_binary_tdm_attention.npy"


@dataclass(frozen=True)
class ComparisonRun:
    role: str
    case_uid: str
    seed: int
    command: FysCommand | ControlCommand
    control_mask_path: Path | None = None

    @property
    def evaluated(self) -> bool:
        return self.role in EVALUATED_METHODS


def build_matched_control_plan(method: str) -> dict[str, Any]:
    if method not in {"endpoint_projection", "residual_rk2"}:
        raise ValueError(f"unsupported matched control method: {method}")

    stage = {
        "name": f"{method}_prefix",
        "start": 0,
        "end": CONTROL_DURATION - 1,
        "prompt": "target",
        "image_kv": "none",
        "it_gate": "none",
        "latent_projection": "none",
        "residual_control": "none",
    }
    if method == "endpoint_projection":
        stage["latent_projection"] = "source_outside_mask"
    else:
        stage["residual_control"] = "source_referenced_rk2"

    return {
        "name": f"heldout_{method}_n{CONTROL_DURATION:02d}",
        "num_steps": 15,
        "front": 2,
        "inject": 4,
        "tail_pad": 1,
        "mask_source": "precomputed",
        "stages": [stage],
        "image_kv_layers": [],
        "it_gate_layers": [],
    }


def write_matched_control_plans(plan_dir: Path) -> dict[str, Path]:
    plan_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for method in ("endpoint_projection", "residual_rk2"):
        path = plan_dir / f"{method}_n{CONTROL_DURATION:02d}.json"
        path.write_text(
            json.dumps(build_matched_control_plan(method), indent=2) + "\n",
            encoding="utf-8",
        )
        paths[method] = path
    return paths


def _resolved_output_path(repo_root: Path, command: FysCommand) -> Path:
    return resolve_repo_path(repo_root, str(command.run_config["output_dir"]))


def build_comparison_runs(
    *,
    records: list[dict],
    seeds: list[int],
    repo_root: Path,
    python_executable: str,
    offload: bool,
    output_root: Path,
    plan_dir: Path,
    attention_token_mode: str,
    attention_layers: str = "28,29,30,31,32,33,34,35,36,37",
    guidance: float = 2.0,
    model_name: str = "flux-dev",
) -> list[ComparisonRun]:
    if attention_token_mode not in {"part", "part_edit"}:
        raise ValueError("attention_token_mode must be part or part_edit")
    if not records:
        raise ValueError("at least one held-out record is required")
    if not seeds:
        raise ValueError("at least one fixed seed is required")

    plan_paths = write_matched_control_plans(plan_dir)
    runs: list[ComparisonRun] = []
    for record in records:
        for seed in seeds:
            common_fys = {
                "record": record,
                "repo_root": repo_root,
                "python_executable": python_executable,
                "seed": seed,
                "seed_subdirs": True,
                "use_oracle_mask": False,
                "name": model_name,
                "guidance": guidance,
                "num_steps": 15,
                "front": 2,
                "inject": 4,
                "offload": offload,
                "controlnet_type": "none",
                "attention_layers": attention_layers,
            }
            baseline = build_fys_command(
                **common_fys,
                tdm_mask_mode="original",
                attention_token_mode=attention_token_mode,
                output_root=output_root / "original_fys_tdm",
            )
            scout = build_fys_command(
                **common_fys,
                tdm_mask_mode="attention_gated",
                attention_token_mode=attention_token_mode,
                output_root=output_root / "attention_mask_scout",
            )
            mask_path = _resolved_output_path(repo_root, scout) / "tdm" / SCOUT_MASK_FILENAME

            runs.append(
                ComparisonRun("original_fys_tdm", str(record["case_uid"]), seed, baseline)
            )
            runs.append(
                ComparisonRun(
                    "attention_mask_scout",
                    str(record["case_uid"]),
                    seed,
                    scout,
                    control_mask_path=mask_path,
                )
            )
            for method in ("endpoint_projection", "residual_rk2"):
                command = build_control_command(
                    record,
                    plan_path=plan_paths[method],
                    repo_root=repo_root,
                    python_executable=python_executable,
                    seed=seed,
                    offload=offload,
                    guidance=guidance,
                    model_name=model_name,
                    output_root=output_root / method,
                    control_mask_path=mask_path,
                )
                runs.append(
                    ComparisonRun(
                        method,
                        str(record["case_uid"]),
                        seed,
                        command,
                        control_mask_path=mask_path,
                    )
                )
    return runs


def format_run_command(run: ComparisonRun) -> str:
    if isinstance(run.command, FysCommand):
        return format_shell_command(run.command)
    return format_command(run.command)


def write_comparison_matrix(path: Path, runs: list[ComparisonRun]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for run in runs:
        rows.append(
            {
                "role": run.role,
                "evaluated": run.evaluated,
                "case_uid": run.case_uid,
                "seed": run.seed,
                "control_mask_path": (
                    "" if run.control_mask_path is None else str(run.control_mask_path)
                ),
                "command": format_run_command(run),
                "run_config": json.dumps(run.command.run_config, sort_keys=True),
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _run_output_dir(repo_root: Path, run: ComparisonRun) -> Path:
    if isinstance(run.command, FysCommand):
        return _resolved_output_path(repo_root, run.command)
    return run.command.output_dir


def execute_comparison_runs(
    runs: list[ComparisonRun],
    *,
    repo_root: Path,
    overwrite: bool,
) -> int:
    for run in runs:
        output_dir = _run_output_dir(repo_root, run)
        if isinstance(run.command, FysCommand):
            validate_output_dir(output_dir, overwrite=overwrite)
            if overwrite and output_dir.exists():
                shutil.rmtree(output_dir)
            returncode = run_command(run.command)
        else:
            if run.control_mask_path is None or not run.control_mask_path.is_file():
                raise FileNotFoundError(
                    f"shared scout mask is missing for {run.case_uid}, seed {run.seed}: "
                    f"{run.control_mask_path}"
                )
            returncode = execute_command(run.command, overwrite=overwrite)
        if returncode != 0:
            return returncode
        if run.role == "attention_mask_scout":
            if run.control_mask_path is None or not run.control_mask_path.is_file():
                raise FileNotFoundError(
                    f"attention mask scout did not produce {run.control_mask_path}"
                )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--seeds", required=True, help="Comma-separated fixed integer seeds")
    parser.add_argument("--case-uid", action="append", dest="case_uids")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--run-matrix", type=Path)
    parser.add_argument("--attention-token-mode", choices=["part", "part_edit"], default="part")
    parser.add_argument("--attention-layers", default="28,29,30,31,32,33,34,35,36,37")
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
    manifest_path = resolve_repo_path(repo_root, str(args.manifest))
    records = select_records(load_manifest(manifest_path), args.case_uids, args.limit)
    seeds = [int(seed) for seed in parse_seeds(args.seeds)]
    output_root = (
        resolve_repo_path(repo_root, str(args.output_root))
        if args.output_root is not None
        else repo_root / "core" / "results" / "heldout_control_comparison"
    )
    plan_dir = output_root / "resolved_plans"
    runs = build_comparison_runs(
        records=records,
        seeds=seeds,
        repo_root=repo_root,
        python_executable=args.python,
        offload=not args.no_offload,
        output_root=output_root,
        plan_dir=plan_dir,
        attention_token_mode=args.attention_token_mode,
        attention_layers=args.attention_layers,
        guidance=args.guidance,
        model_name=args.name,
    )
    matrix_path = (
        resolve_repo_path(repo_root, str(args.run_matrix))
        if args.run_matrix is not None
        else output_root / "run_matrix.csv"
    )
    if args.execute or args.write_run_matrix or args.run_matrix is not None:
        write_comparison_matrix(matrix_path, runs)
        print(f"run matrix: {matrix_path}")

    for index, run in enumerate(runs, start=1):
        evaluated = "evaluated" if run.evaluated else "preprocessing"
        print(f"[{index}/{len(runs)}] {run.role} ({evaluated}) {run.case_uid} seed={run.seed}")
        print(format_run_command(run))

    if not args.execute:
        print("Dry run only. Add --execute to run the comparison.")
        return 0
    return execute_comparison_runs(runs, repo_root=repo_root, overwrite=args.overwrite)


if __name__ == "__main__":
    raise SystemExit(main())
