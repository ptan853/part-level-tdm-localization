#!/usr/bin/env python3
"""Dry-run-first, read-only attention diagnostic on five previously evaluated cases."""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

from run_control_plan import build_control_command, execute_command, format_command
from run_fys_pilot import find_repo_root, load_manifest


CASES = ("synth_0032", "synth_0028", "synth_0033", "synth_0036", "synth_0023")
RICH_CASES = ("synth_0006", "synth_0003", "synth_0033", "synth_0032", "synth_0036")
CONDITIONS = {"uncontrolled": 0, "rk2_gt_n07": 7}


def make_plan(duration: int) -> dict:
    if duration not in (0, 7):
        raise ValueError("This diagnostic fixes duration to 0 or 7")
    return {
        "name": f"attention_routing_n{duration:02d}",
        "num_steps": 15, "front": 2, "inject": 4, "tail_pad": 1,
        "mask_source": "precomputed", "image_kv_layers": [], "it_gate_layers": [],
        "stages": [] if duration == 0 else [{
            "name": "residual_rk2_prefix", "start": 0, "end": duration - 1,
            "prompt": "target", "image_kv": "none", "it_gate": "none",
            "latent_projection": "none", "residual_control": "source_referenced_rk2",
        }],
    }


def main(argv: list[str] | None = None) -> int:
    repo = find_repo_root(Path(__file__).resolve())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-uid", action="append", dest="cases")
    parser.add_argument("--condition", action="append", choices=tuple(CONDITIONS))
    parser.add_argument("--recording", choices=("on", "off"), default="on")
    parser.add_argument("--mode", choices=("compact", "rich"), default="compact")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--execute", action="store_true")
    # Keep invalid selection errors programmatically distinguishable from argparse syntax errors.
    args = parser.parse_args(argv)
    case_pool = RICH_CASES if args.mode == "rich" else CASES
    selected = args.cases or list(case_pool)
    if set(selected) - set(case_pool):
        raise ValueError(f"Case selection must be drawn from {case_pool}")
    if len(selected) != len(set(selected)):
        raise ValueError("Duplicate case selection")
    conditions = args.condition or list(CONDITIONS)
    if len(conditions) != len(set(conditions)):
        raise ValueError("Duplicate condition selection")
    manifest = repo / "core/data/partedit_subset/synth_60_frozen_manifest.json"
    records = {r["case_uid"]: r for r in load_manifest(manifest)}
    root = (args.output_root or repo / "core/results" / (
        "attention_routing_rich" if args.mode == "rich" else "attention_routing_diagnostic"
    )).resolve()
    commands = []
    for condition in conditions:
        plan = make_plan(CONDITIONS[condition])
        plan_path = root / "plans" / f"{condition}.json"
        if args.prepare or args.execute:
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(plan, indent=2) + "\n"
            if plan_path.exists() and plan_path.read_text() != text:
                raise ValueError(f"Existing plan differs: {plan_path}")
            plan_path.write_text(text)
        for case in selected:
            mask = repo / "core/protocols/gt_mask_diagnostic_v2/gt_masks" / f"{case}.npy"
            if not mask.is_file():
                raise FileNotFoundError(mask)
            if not (args.prepare or args.execute):
                print(f"{case} | {condition} | recording={args.recording} | observation={mask}")
                continue
            command = build_control_command(
                records[case], plan_path=plan_path, repo_root=repo,
                python_executable=args.python, seed=0, offload=True, guidance=2.0,
                output_root=root / f"recording_{args.recording}" / condition,
                control_mask_path=mask,
            )
            worker = Path(__file__).with_name("attention_routing_worker.py")
            worker_args = [args.python, str(worker), "--observation-mask", str(mask),
                           "--routing-recording", args.recording,
                           "--routing-subject", records[case]["subject"], *command.args[2:]]
            if args.mode == "rich":
                worker_args[2:2] = ["--routing-mode", "rich"]
            config = {
                **command.run_config, "routing_recording": args.recording,
                "observation_mask_sha256": hashlib.sha256(mask.read_bytes()).hexdigest(),
                "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                "record_layers": {"double": [0, 9, 18], "single": [0, 18, 37]},
                "record_evaluation": "actual_forward_midpoint", "query_chunk_size": 16,
            }
            if args.mode == "rich":
                config.update(routing_mode="rich", record_layers="all_double_and_single",
                              record_evaluation=["start", "midpoint"], query_chunk_size=32,
                              text_storage="all_valid_positions_plus_padding_mass", storage_dtype="float32")
            commands.append(replace(command, args=worker_args, run_config=config))
    for command in commands:
        if args.execute and command.output_dir.exists() and any(command.output_dir.iterdir()):
            raise FileExistsError(f"Refusing to overwrite existing run: {command.output_dir}")
    for command in commands:
        print(format_command(command))
        if args.execute:
            code = execute_command(command, overwrite=False)
            if code:
                return code
    if not args.execute:
        print("No generation launched. Use --prepare for commands or --execute to run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
