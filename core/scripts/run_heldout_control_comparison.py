#!/usr/bin/env python3
"""Run the frozen held-out comparison with a shared automatic mask scout."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
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
from heldout_review_randomization import (  # noqa: E402
    build_frozen_randomization,
    validate_frozen_randomization,
    write_frozen_randomization,
)


CONTROL_DURATION = 7
EVALUATED_METHODS = (
    "original_fys_tdm",
    "endpoint_projection",
    "residual_rk2",
    "endpoint_projection_n3",
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


def build_supplemental_endpoint_plan() -> dict[str, Any]:
    """Reproduce the historical endpoint N=3 schedule as a supplemental condition."""
    return {
        "name": "heldout_endpoint_projection_historical_n03",
        "num_steps": 15,
        "front": 2,
        "inject": 4,
        "tail_pad": 1,
        "mask_source": "precomputed",
        "stages": [
            {
                "name": "source_structure",
                "start": 0,
                "end": 1,
                "prompt": "target",
                "image_kv": "source_all",
                "it_gate": "none",
                "latent_projection": "none",
                "residual_control": "none",
            },
            {
                "name": "endpoint_projection",
                "start": 2,
                "end": 4,
                "prompt": "target",
                "image_kv": "none",
                "it_gate": "none",
                "latent_projection": "source_outside_mask",
                "residual_control": "none",
            },
        ],
        "image_kv_layers": list(range(20, 38)),
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
    supplemental_path = plan_dir / "endpoint_projection_historical_n03.json"
    supplemental_path.write_text(
        json.dumps(build_supplemental_endpoint_plan(), indent=2) + "\n",
        encoding="utf-8",
    )
    paths["endpoint_projection_n3"] = supplemental_path
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
    include_endpoint_n3: bool = False,
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
            mask_path = (
                _resolved_output_path(repo_root, scout) / "tdm" / SCOUT_MASK_FILENAME
            )

            runs.append(
                ComparisonRun(
                    "original_fys_tdm", str(record["case_uid"]), seed, baseline
                )
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
            if include_endpoint_n3:
                command = build_control_command(
                    record,
                    plan_path=plan_paths["endpoint_projection_n3"],
                    repo_root=repo_root,
                    python_executable=python_executable,
                    seed=seed,
                    offload=offload,
                    guidance=guidance,
                    model_name=model_name,
                    output_root=output_root / "endpoint_projection_n3",
                    control_mask_path=mask_path,
                )
                runs.append(
                    ComparisonRun(
                        "endpoint_projection_n3",
                        str(record["case_uid"]),
                        seed,
                        command,
                        control_mask_path=mask_path,
                    )
                )
    return runs


def validate_frozen_preflight(
    records: list[dict],
    seeds: list[int],
    runs: list[ComparisonRun],
    repo_root: Path,
    *,
    allow_full_rerun: bool = False,
) -> dict[str, int]:
    """Validate the immutable 60-case protocol before any model command runs."""
    if len(records) != 60:
        raise ValueError(
            f"frozen manifest must contain exactly 60 records, found {len(records)}"
        )
    if seeds != [0]:
        raise ValueError(f"frozen protocol requires exactly seed 0, found {seeds}")

    required = {
        "case_uid",
        "dataset_revision",
        "dataset_split",
        "dataset_index",
        "source_image",
        "source_prompt",
        "target_prompt",
        "part",
        "edit",
        "gt_mask",
        "gt_area_ratio",
        "part_size",
        "footprint_change",
    }
    case_uids = [str(record.get("case_uid", "")) for record in records]
    indices = [record.get("dataset_index") for record in records]
    if len(set(case_uids)) != 60 or "" in case_uids:
        raise ValueError("frozen manifest requires 60 unique non-empty case IDs")
    if set(indices) != set(range(60)):
        raise ValueError("frozen manifest dataset indices must be exactly 0 through 59")
    if any(required - set(record) for record in records):
        missing = sorted(set.union(*(required - set(record) for record in records)))
        raise ValueError(
            f"frozen manifest records are missing required fields: {missing}"
        )
    if any(record["dataset_revision"] != "v1.1" for record in records):
        raise ValueError("frozen manifest dataset_revision must be v1.1")
    if any(record["dataset_split"] != "synth" for record in records):
        raise ValueError("frozen manifest dataset_split must be synth")
    if Counter(record["part_size"] for record in records) != Counter(
        {"small": 20, "medium": 20, "large": 20}
    ):
        raise ValueError(
            "frozen manifest must contain 20 small, 20 medium, and 20 large cases"
        )
    footprint_values = {"contraction", "comparable", "expansion"}
    if any(record["footprint_change"] not in footprint_values for record in records):
        raise ValueError("frozen manifest contains an invalid footprint_change label")
    for record in records:
        for field in ("source_image", "gt_mask"):
            path = resolve_repo_path(repo_root, str(record[field]))
            if not path.is_file():
                raise FileNotFoundError(
                    f"missing frozen {field} for {record['case_uid']}: {path}"
                )

    expected_roles = Counter(
        {role: 60 for role in (*EVALUATED_METHODS, "attention_mask_scout")}
    )
    actual_roles = Counter(run.role for run in runs)
    if len(runs) != 300 or actual_roles != expected_roles:
        raise ValueError(
            f"frozen run matrix must contain exactly 300 rows with 60 per role; found {actual_roles}"
        )
    scout_masks = {
        (run.case_uid, run.seed): run.control_mask_path
        for run in runs
        if run.role == "attention_mask_scout"
    }
    for run in runs:
        if run.seed != 0 or run.command.run_config.get("num_steps") != 15:
            raise ValueError("every frozen run must use seed 0 and 15 solver steps")
        if float(run.command.run_config.get("guidance")) != 2.0:
            raise ValueError("every frozen run must use guidance 2.0")
        if run.evaluated and (
            "--mask_path" in run.command.args or "oracle" in run.command.args
        ):
            raise ValueError(
                f"GT/oracle mask leaked into generation arguments for {run.role}"
            )
        if run.role in {
            "endpoint_projection",
            "residual_rk2",
            "endpoint_projection_n3",
        }:
            if run.control_mask_path != scout_masks[(run.case_uid, run.seed)]:
                raise ValueError(
                    f"control methods do not share the scout mask for {run.case_uid}"
                )
        output_dir = _run_output_dir(repo_root, run)
        if not allow_full_rerun and output_dir.exists() and any(output_dir.iterdir()):
            raise FileExistsError(
                f"frozen output directory is not empty: {output_dir}; "
                "use --overwrite only for a complete rerun"
            )
    return {
        "manifest_records": len(records),
        "command_rows": len(runs),
        "evaluated_outputs": sum(run.evaluated for run in runs),
    }


def format_run_command(run: ComparisonRun) -> str:
    if isinstance(run.command, FysCommand):
        return format_shell_command(run.command)
    return format_command(run.command)


def build_review_randomization_inputs(
    records: list[dict], runs: list[ComparisonRun]
) -> list[dict[str, object]]:
    records_by_uid = {str(record["case_uid"]): record for record in records}
    rows = []
    for run in runs:
        if not run.evaluated:
            continue
        record = records_by_uid.get(run.case_uid)
        if record is None:
            raise KeyError(f"run case is absent from manifest: {run.case_uid}")
        rows.append(
            {
                "row_uid": f"{run.role}::{run.case_uid}::seed_{run.seed:03d}",
                "case_uid": run.case_uid,
                "seed": run.seed,
                "method": run.role,
                "part_size": record["part_size"],
                "footprint_change": record["footprint_change"],
            }
        )
    if len({str(row["row_uid"]) for row in rows}) != len(rows):
        raise ValueError("evaluated runs produce duplicate row_uid values")
    return rows


def _portable_value(value: str, repo_root: Path | None) -> str:
    if repo_root is None:
        return value
    return value.replace(str(repo_root.resolve()), "${REPO_ROOT}")


def write_comparison_matrix(
    path: Path,
    runs: list[ComparisonRun],
    *,
    repo_root: Path | None = None,
    portable: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for run in runs:
        control_mask_path = (
            "" if run.control_mask_path is None else str(run.control_mask_path)
        )
        command = format_run_command(run)
        run_config = json.dumps(run.command.run_config, sort_keys=True)
        if portable:
            if repo_root is None:
                raise ValueError("repo_root is required for a portable command matrix")
            control_mask_path = _portable_value(control_mask_path, repo_root)
            command = _portable_value(command, repo_root)
            run_config = _portable_value(run_config, repo_root)
        rows.append(
            {
                "role": run.role,
                "evaluated": run.evaluated,
                "case_uid": run.case_uid,
                "seed": run.seed,
                "control_mask_path": control_mask_path,
                "command": command,
                "run_config": run_config,
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def write_preflight_evidence(
    evidence_dir: Path,
    *,
    records: list[dict],
    runs: list[ComparisonRun],
    repo_root: Path,
    manifest_path: Path,
    preflight: dict[str, int],
    submodule_commit: str,
    execution_commit: str | None = None,
) -> dict[str, object]:
    """Archive all deterministic evidence that must exist before generation."""
    evidence_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = evidence_dir / "command_matrix.csv"
    write_comparison_matrix(
        matrix_path,
        runs,
        repo_root=repo_root,
        portable=True,
    )

    randomization_inputs = build_review_randomization_inputs(records, runs)
    assignments = build_frozen_randomization(randomization_inputs)
    expected_row_uids = {
        str(row["row_uid"]) for row in randomization_inputs
    }
    validate_frozen_randomization(
        assignments,
        expected_row_uids=expected_row_uids,
    )
    randomization_path = evidence_dir / "reviewer_randomization.csv"
    write_frozen_randomization(randomization_path, assignments)

    lock_paths = [
        repo_root / "pyproject.toml",
        repo_root / "uv.lock",
        repo_root / "core" / "third_party" / "FollowYourShape" / "pyproject.toml",
    ]
    environment_lock = {
        "follow_your_shape_commit": submodule_commit,
        "files": [
            {
                "path": _display_path(path, repo_root),
                "sha256": _sha256(path),
            }
            for path in lock_paths
            if path.is_file()
        ],
        "runtime_snapshot": "runtime_environment.json is written immediately before --execute starts the first command",
    }
    environment_path = evidence_dir / "environment_lock.json"
    environment_path.write_text(
        json.dumps(environment_lock, indent=2) + "\n",
        encoding="utf-8",
    )

    frozen = {
        **preflight,
        "review_assignments": len(assignments),
        "manifest": _display_path(manifest_path, repo_root),
        "manifest_sha256": _sha256(manifest_path),
        "command_matrix_sha256": _sha256(matrix_path),
        "reviewer_randomization_sha256": _sha256(randomization_path),
        "environment_lock_sha256": _sha256(environment_path),
        "execution_commit": execution_commit,
        "follow_your_shape_commit": submodule_commit,
    }
    summary_path = evidence_dir / "preflight_summary.json"
    summary_path.write_text(
        json.dumps(frozen, indent=2) + "\n",
        encoding="utf-8",
    )
    return frozen


def capture_runtime_environment(
    path: Path, python_executable: str
) -> dict[str, dict[str, object]]:
    """Capture package and accelerator state before the first model command."""
    commands = {
        "python_version": [python_executable, "--version"],
        "pip_freeze": [python_executable, "-m", "pip", "freeze"],
        "nvidia_smi": [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total",
            "--format=csv,noheader",
        ],
    }
    payload: dict[str, dict[str, object]] = {}
    for name, command in commands.items():
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
            payload[name] = {
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except OSError as error:
            payload[name] = {
                "command": command,
                "returncode": None,
                "stdout": "",
                "stderr": str(error),
            }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def _git_head(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def validate_execution_commit(repo_root: Path, expected_commit: str) -> None:
    actual_commit = _git_head(repo_root)
    if actual_commit != expected_commit:
        raise ValueError(
            f"execution commit {expected_commit} does not match current HEAD {actual_commit}"
        )


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
    parser.add_argument(
        "--seeds", required=True, help="Comma-separated fixed integer seeds"
    )
    parser.add_argument("--case-uid", action="append", dest="case_uids")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--run-matrix", type=Path)
    parser.add_argument(
        "--preflight-evidence-dir",
        type=Path,
        help="Directory for the frozen portable matrix, randomization, plans, and checksums.",
    )
    parser.add_argument(
        "--execution-commit",
        help="Exact outer-repository commit approved for execution; recorded in preflight evidence.",
    )
    parser.add_argument(
        "--attention-token-mode", choices=["part", "part_edit"], default="part"
    )
    parser.add_argument(
        "--include-endpoint-n3",
        action="store_true",
        help="Add the frozen historical endpoint N=3 supplemental condition and enforce formal preflight.",
    )
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
    evidence_dir = (
        resolve_repo_path(repo_root, str(args.preflight_evidence_dir))
        if args.preflight_evidence_dir is not None
        else repo_root
        / "core"
        / "protocols"
        / "heldout_control_comparison_v1"
    )
    plan_dir = (
        evidence_dir / "resolved_plans"
        if args.include_endpoint_n3
        else output_root / "resolved_plans"
    )
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
        include_endpoint_n3=args.include_endpoint_n3,
    )
    preflight = None
    if args.include_endpoint_n3:
        preflight = validate_frozen_preflight(
            records,
            seeds,
            runs,
            repo_root,
            allow_full_rerun=args.overwrite,
        )
    matrix_path = (
        resolve_repo_path(repo_root, str(args.run_matrix))
        if args.run_matrix is not None
        else output_root / "run_matrix.csv"
    )
    if (
        args.execute
        or args.write_run_matrix
        or args.run_matrix is not None
        or preflight is not None
    ):
        write_comparison_matrix(matrix_path, runs)
        print(f"run matrix: {matrix_path}")
    if preflight is not None:
        submodule_path = repo_root / "core" / "third_party" / "FollowYourShape"
        frozen = write_preflight_evidence(
            evidence_dir,
            records=records,
            runs=runs,
            repo_root=repo_root,
            manifest_path=manifest_path,
            preflight=preflight,
            submodule_commit=_git_head(submodule_path),
            execution_commit=args.execution_commit,
        )
        print(f"preflight evidence: {evidence_dir}")
        print(f"manifest SHA-256: {frozen['manifest_sha256']}")

    for index, run in enumerate(runs, start=1):
        evaluated = "evaluated" if run.evaluated else "preprocessing"
        print(
            f"[{index}/{len(runs)}] {run.role} ({evaluated}) {run.case_uid} seed={run.seed}"
        )
        print(format_run_command(run))

    if not args.execute:
        print("Dry run only. Add --execute to run the comparison.")
        return 0
    if not args.execution_commit:
        raise ValueError("--execute requires the approved --execution-commit")
    validate_execution_commit(repo_root, args.execution_commit)
    capture_runtime_environment(
        evidence_dir / "runtime_environment.json", args.python
    )
    return execute_comparison_runs(runs, repo_root=repo_root, overwrite=args.overwrite)


if __name__ == "__main__":
    raise SystemExit(main())
