#!/usr/bin/env python3
"""Run the existing FYS edit entry point with a scoped read-only observer."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
FYS_SRC = ROOT / "core/third_party/FollowYourShape/src"
sys.path.insert(0, str(FYS_SRC))

from attention_routing import RoutingRecorder
from flux.attention_mask_utils import select_target_token_indices


def fingerprint(tensor) -> dict:
    array = tensor.detach().float().cpu().numpy()
    return {"shape": list(array.shape), "dtype": str(tensor.dtype),
            "sha256_float32": hashlib.sha256(array.tobytes()).hexdigest()}


@contextmanager
def observe_edit(edit_module, args, mask, *, recording: bool, subject: str, mode: str = "compact"):
    original_prepare = edit_module.prepare
    original_denoise = edit_module.denoise_with_TDM
    token_metadata = {}
    directory = Path(args.output_dir) / "routing"

    def prepare(t5, clip, img, prompt):
        result = original_prepare(t5, clip, img, prompt)
        if prompt == args.target_prompt:
            encoded = t5.tokenizer(
                [prompt], truncation=True, max_length=t5.max_length,
                padding="max_length", return_tensors="pt",
            )
            ids = encoded["input_ids"][0].tolist()
            token_metadata.update({
                "prompt": prompt, "token_ids": ids,
                "token_strings": t5.tokenizer.convert_ids_to_tokens(ids),
                "valid_positions": encoded["attention_mask"][0].tolist(),
                "groups": {},
            })
            for name, phrase in (("subject", subject), ("part", args.attention_part),
                                 ("edit", args.attention_edit)):
                token_metadata["groups"][name] = select_target_token_indices(
                    t5.tokenizer, prompt, part=phrase, edit="", token_mode="part",
                    max_length=result["txt"].shape[1],
                )
        return result

    def denoise(model, **kwargs):
        if int(np.asarray(mask).size) != kwargs["img"].shape[1]:
            raise ValueError("GT observation grid differs from the actual image-token grid")
        expected_shape = (kwargs["height"] // 16, kwargs["width"] // 16)
        if tuple(np.asarray(mask).shape) != expected_shape:
            raise ValueError(f"GT observation grid must be {expected_shape}, got {np.asarray(mask).shape}")
        directory.mkdir(parents=True, exist_ok=True)
        initial = fingerprint(kwargs["img"])
        np.save(directory / "initial_latent.npy", kwargs["img"].detach().float().cpu().numpy())
        start = time.perf_counter()
        if recording:
            if not token_metadata:
                raise ValueError("Target token metadata was not captured")
            if mode == "rich":
                from attention_routing_rich import RichRoutingRecorder
                recorder = RichRoutingRecorder(model, kwargs["info"], mask, kwargs["txt"].shape[1],
                                                directory=directory, tokens=token_metadata)
                for field in ("source_latents", "source_midpoints"):
                    values = kwargs["info"].get(field, {})
                    if values:
                        np.savez_compressed(directory / f"{field}.npz",
                                            **{str(k): v.detach().float().cpu().numpy()
                                               for k, v in values.items()})
            else:
                recorder = RoutingRecorder(model, kwargs["info"], mask, kwargs["txt"].shape[1])
            with recorder:
                result, info = original_denoise(model, **kwargs)
            recorder.save(directory, num_steps=len(kwargs["timesteps"]) - 1, tokens=token_metadata)
        else:
            result, info = original_denoise(model, **kwargs)
        np.save(directory / "final_latent.npy", result.detach().float().cpu().numpy())
        (directory / "latent_record.json").write_text(json.dumps({
            "initial": initial, "final": fingerprint(result), "recording": recording, "mode": mode,
            "schedule": [float(t) for t in kwargs["timesteps"]],
            "forward_seconds": time.perf_counter() - start,
        }, indent=2) + "\n")
        return result, info

    edit_module.prepare = prepare
    edit_module.denoise_with_TDM = denoise
    try:
        yield
    finally:
        edit_module.prepare = original_prepare
        edit_module.denoise_with_TDM = original_denoise


def runtime_record(mask_path: Path) -> dict:
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    files = [Path(__file__), Path(__file__).with_name("attention_routing.py"),
             Path(__file__).with_name("attention_routing_rich.py"),
             FYS_SRC / "edit.py", FYS_SRC / "flux/sampling.py",
             FYS_SRC / "flux/latent_control.py", FYS_SRC / "flux/math.py",
             FYS_SRC / "flux/model.py", FYS_SRC / "flux/modules/layers.py"]
    return {
        "execution_commit": git("rev-parse", "HEAD"),
        "working_tree_status": git("status", "--short"),
        "submodule": git("submodule", "status"),
        "file_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        "mask_sha256": hashlib.sha256(mask_path.read_bytes()).hexdigest(),
        "torch": torch.__version__, "cuda": torch.version.cuda,
        "python": sys.version, "device": torch.cuda.get_device_name() if torch.cuda.is_available() else "cpu",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--observation-mask", type=Path, required=True)
    parser.add_argument("--routing-recording", choices=("on", "off"), default="on")
    parser.add_argument("--routing-subject", required=True)
    parser.add_argument("--routing-mode", choices=("compact", "rich"), default="compact")
    routing, remaining = parser.parse_known_args(argv)
    import edit
    from flux.control_schedule import load_control_plan
    edit_parser = edit.build_arg_parser()
    args = edit_parser.parse_args(remaining)
    edit.validate_args(edit_parser, args)
    if not args.control_plan_resolved or args.controlnet_type != "none" or args.same_state_probe_dir:
        raise ValueError("Diagnostic requires an explicit plan, no ControlNet and no inversion probe")
    plan = load_control_plan(args.control_plan_resolved)
    if plan.image_kv_layers or plan.it_gate_layers or any(
        s.image_kv != "none" or s.it_gate != "none" or s.latent_projection != "none" for s in plan.stages
    ):
        raise ValueError("This observation study supports only uncontrolled or residual-RK2 sampling")
    mask = np.load(routing.observation_mask, allow_pickle=False)
    if mask.ndim != 2 or not np.isfinite(mask).all() or not np.isin(mask, [0, 1]).all() or not mask.any():
        raise ValueError("Expected a nonempty binary GT image-token grid")
    if plan.stages and not np.array_equal(mask, np.load(args.control_mask_path, allow_pickle=False)):
        raise ValueError("RK2 control and observation must use the same GT grid")
    output = Path(args.output_dir)
    if (output / "routing").exists() or list(output.glob("img_*.jpg")):
        raise FileExistsError(f"Refusing to overwrite diagnostic results: {output}")
    output.mkdir(parents=True, exist_ok=True)
    (output / "routing_runtime.json").write_text(json.dumps(runtime_record(routing.observation_mask), indent=2) + "\n")
    with observe_edit(edit, args, mask, recording=routing.routing_recording == "on",
                      subject=routing.routing_subject, mode=routing.routing_mode):
        edit.main(args)
    available = (output / "img_0.jpg").is_file()
    (output / "generation_status.json").write_text(json.dumps({
        "image_available": available, "routing_complete": (output / "routing/latent_record.json").is_file(),
    }, indent=2) + "\n")
    return 0 if available else 2


if __name__ == "__main__":
    raise SystemExit(main())
