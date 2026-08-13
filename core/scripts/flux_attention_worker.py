#!/usr/bin/env python3
"""Extract a simple FLUX target-token attention localization signal for one case.

This is a diagnostic baseline, not an editing method. It reuses the same
source-image inversion setup as the FYS pilot, then runs plain target-prompt
denoising without KV injection and records true softmax attention mass from
image-token queries to target part/edit text-token keys.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import torch
from einops import rearrange
from PIL import Image
from scipy.ndimage import gaussian_filter
from skimage.filters import threshold_otsu


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "core").exists():
            return candidate
    raise FileNotFoundError(f"Could not find repository root from {start}")


REPO_ROOT = find_repo_root(Path(__file__))
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"
if str(FYS_SRC) not in sys.path:
    sys.path.insert(0, str(FYS_SRC))

from flux.math import apply_rope  # noqa: E402
from flux.sampling import denoise, get_schedule, prepare  # noqa: E402
from flux.util import configs, load_ae, load_clip, load_flow_model, load_t5  # noqa: E402


def resolve_repo_path(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else REPO_ROOT / path


def encode_image(image_np: np.ndarray, device: torch.device, ae) -> torch.Tensor:
    image = torch.from_numpy(image_np.copy()).permute(2, 0, 1).float() / 127.5 - 1
    image = image.unsqueeze(0).to(device)
    return ae.encode(image).to(torch.bfloat16)


def normalize01(values: np.ndarray) -> np.ndarray:
    values = values.astype(np.float32)
    finite = np.isfinite(values)
    if not finite.any():
        return np.zeros_like(values, dtype=np.float32)
    lo = float(values[finite].min())
    hi = float(values[finite].max())
    if hi <= lo:
        return np.zeros_like(values, dtype=np.float32)
    return (values - lo) / (hi - lo)


def wordpiece_ids(tokenizer, text: str) -> list[int]:
    encoded = tokenizer(
        text.replace("_", " "),
        add_special_tokens=False,
        return_attention_mask=False,
        return_tensors=None,
    )
    return [int(x) for x in encoded["input_ids"] if int(x) != tokenizer.pad_token_id]


def find_subsequence_positions(sequence: list[int], subsequence: list[int]) -> list[int]:
    if not subsequence:
        return []
    out: list[int] = []
    n = len(subsequence)
    for i in range(0, len(sequence) - n + 1):
        if sequence[i : i + n] == subsequence:
            out.extend(range(i, i + n))
    return out


def select_target_token_indices(tokenizer, target_prompt: str, part: str, edit: str, max_length: int) -> list[int]:
    encoding = tokenizer(
        [target_prompt],
        truncation=True,
        max_length=max_length,
        padding="max_length",
        return_tensors="pt",
    )
    pad_id = tokenizer.pad_token_id
    prompt_ids = [int(x) for x in encoding["input_ids"][0].tolist()]
    nonpad = [idx for idx, token_id in enumerate(prompt_ids) if token_id != pad_id]

    selected: list[int] = []
    for phrase in [edit, part, f"{edit} {part}"]:
        selected.extend(find_subsequence_positions(prompt_ids, wordpiece_ids(tokenizer, phrase)))

    # SentencePiece sometimes splits differently in context; fall back to token
    # string containment for simple part/edit words.
    if not selected:
        tokens = tokenizer.convert_ids_to_tokens(prompt_ids)
        needles = [part.lower().replace("_", ""), edit.lower().replace("_", "")]
        for idx in nonpad:
            token = str(tokens[idx]).lower().replace("▁", "").replace("_", "")
            if any(needle and needle in token for needle in needles):
                selected.append(idx)

    # Final fallback keeps the baseline runnable but records the fallback in
    # metadata. It uses all non-padding prompt tokens rather than failing.
    if not selected:
        selected = nonpad

    return sorted(set(idx for idx in selected if 0 <= idx < max_length))


class SingleBlockAttentionProbe:
    def __init__(self, model, token_indices: list[int], txt_len: int, layer_ids: list[int]) -> None:
        self.token_indices = token_indices
        self.txt_len = txt_len
        self.layer_ids = set(layer_ids)
        self.records: list[torch.Tensor] = []
        self.handles = []
        for layer_id, block in enumerate(model.single_blocks):
            if layer_id in self.layer_ids:
                self.handles.append(block.register_forward_pre_hook(self._make_hook(layer_id), with_kwargs=True))

    def close(self) -> None:
        for handle in self.handles:
            handle.remove()
        self.handles = []

    def _make_hook(self, layer_id: int):
        def hook(module, inputs, kwargs) -> None:
            x = inputs[0] if inputs else kwargs["x"]
            vec = kwargs["vec"]
            pe = kwargs["pe"]
            info = kwargs.get("info")
            if not self.token_indices:
                return None
            if info is not None and not info.get("record_attention", False):
                return None
            with torch.no_grad():
                mod, _ = module.modulation(vec)
                x_mod = (1 + mod.scale) * module.pre_norm(x) + mod.shift
                qkv, _ = torch.split(module.linear1(x_mod), [3 * module.hidden_size, module.mlp_hidden_dim], dim=-1)
                q, k, v = rearrange(qkv, "B L (K H D) -> K B H L D", K=3, H=module.num_heads)
                q, k = module.norm(q, k, v)
                q, k = apply_rope(q, k, pe)

                img_q = q[:, :, self.txt_len :, :]
                scale = img_q.shape[-1] ** -0.5
                logits = torch.einsum("bhid,bhjd->bhij", img_q.float(), k.float()) * scale
                attn = torch.softmax(logits, dim=-1)
                scores = attn[:, :, :, self.token_indices].sum(dim=-1).mean(dim=1)[0].detach().cpu()
                self.records.append(scores)
            return None

        return hook


def run_plain_target_denoise_with_probe(
    model,
    img: torch.Tensor,
    img_ids: torch.Tensor,
    txt: torch.Tensor,
    txt_ids: torch.Tensor,
    vec: torch.Tensor,
    timesteps: list[float],
    token_indices: list[int],
    guidance: float,
    layer_ids: list[int],
    record_start_step: int,
    record_end_step: int,
) -> np.ndarray:
    probe = SingleBlockAttentionProbe(model, token_indices, txt_len=txt.shape[1], layer_ids=layer_ids)
    try:
        guidance_vec = torch.full((img.shape[0],), guidance, device=img.device, dtype=img.dtype)
        info = {"feature": {}, "map": {}, "edit_map": None}
        for step_idx, (t_curr, t_prev) in enumerate(zip(timesteps[:-1], timesteps[1:])):
            should_record = record_start_step <= step_idx <= record_end_step
            t_vec = torch.full((img.shape[0],), t_curr, dtype=img.dtype, device=img.device)
            info.update(
                {
                    "t": t_curr,
                    "inverse": False,
                    "second_order": False,
                    "inject": False,
                    "step_index": step_idx,
                    "record_attention": should_record,
                }
            )
            pred, info = model(
                img=img,
                img_ids=img_ids,
                txt=txt,
                txt_ids=txt_ids,
                y=vec,
                timesteps=t_vec,
                guidance=guidance_vec,
                info=info,
            )

            img_mid = img + (t_prev - t_curr) / 2 * pred
            t_vec_mid = torch.full(
                (img.shape[0],),
                (t_curr + (t_prev - t_curr) / 2),
                dtype=img.dtype,
                device=img.device,
            )
            info.update(
                {
                    "t": float(t_vec_mid[0].item()),
                    "second_order": True,
                    "record_attention": should_record,
                }
            )
            pred_mid, info = model(
                img=img_mid,
                img_ids=img_ids,
                txt=txt,
                txt_ids=txt_ids,
                y=vec,
                timesteps=t_vec_mid,
                guidance=guidance_vec,
                info=info,
            )

            first_order = (pred_mid - pred) / ((t_prev - t_curr) / 2)
            img = img + (t_prev - t_curr) * pred + 0.5 * (t_prev - t_curr) ** 2 * first_order
    finally:
        probe.close()

    if not probe.records:
        raise RuntimeError("No target-token attention records were captured.")
    stack = torch.stack(probe.records, dim=0)
    return stack.mean(dim=0).numpy()


@torch.inference_mode()
def main() -> int:
    parser = argparse.ArgumentParser(description="Extract one FLUX target-token attention localization map.")
    parser.add_argument("--case-json", type=Path, required=True, help="JSON file containing one manifest record.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--name", default="flux-dev", choices=sorted(configs.keys()))
    parser.add_argument("--guidance", type=float, default=2.0)
    parser.add_argument("--num-steps", type=int, default=15)
    parser.add_argument("--layers", default="28,29,30,31,32,33,34,35,36,37")
    parser.add_argument("--front", type=int, default=2)
    parser.add_argument("--inject", type=int, default=4)
    parser.add_argument("--tail-pad", type=int, default=1)
    parser.add_argument("--offload", action="store_true")
    args = parser.parse_args()

    record = json.loads(args.case_json.read_text())
    args.output_dir.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    source_path = resolve_repo_path(record["source_image"])
    raw = Image.open(source_path).convert("RGB")
    image_np = np.asarray(raw)
    new_h = image_np.shape[0] if image_np.shape[0] % 16 == 0 else image_np.shape[0] - image_np.shape[0] % 16
    new_w = image_np.shape[1] if image_np.shape[1] % 16 == 0 else image_np.shape[1] - image_np.shape[1] % 16
    image_np = image_np[:new_h, :new_w, :]

    t5 = load_t5(device, max_length=256 if args.name == "flux-schnell" else 512)
    clip = load_clip(device)
    model = load_flow_model(args.name, device="cpu" if args.offload else device)
    ae = load_ae(args.name, device="cpu" if args.offload else device)

    if args.offload:
        model.cpu()
        torch.cuda.empty_cache()
        ae.encoder.to(device)

    init_image = encode_image(image_np, device, ae)
    inp_source = prepare(t5, clip, init_image, prompt=record["source_prompt"])
    inp_target = prepare(t5, clip, init_image, prompt=record["target_prompt"])
    timesteps = get_schedule(args.num_steps, inp_source["img"].shape[1], shift=(args.name != "flux-schnell"))

    if args.offload:
        ae = ae.cpu()
        t5, clip = t5.cpu(), clip.cpu()
        torch.cuda.empty_cache()
        model = model.to(device)

    # Match the FYS starting point: invert the source image with the source prompt.
    inverse_info = {"feature": {}, "map": {}, "edit_map": None}
    z, _ = denoise(
        model,
        **inp_source,
        timesteps=timesteps,
        guidance=1.0,
        inverse=True,
        info=inverse_info,
        inject_list=[False] * (len(timesteps) - 1),
    )
    inp_target["img"] = z

    token_indices = select_target_token_indices(
        t5.tokenizer,
        target_prompt=record["target_prompt"],
        part=record.get("part", ""),
        edit=record.get("edit", ""),
        max_length=t5.max_length,
    )
    layer_ids = [int(x) for x in args.layers.split(",") if x.strip()]
    num_denoising_steps = len(timesteps) - 1
    record_start_step = args.front
    record_end_step = num_denoising_steps - args.inject - 2 - args.tail_pad
    if record_end_step < record_start_step:
        raise ValueError(
            f"Invalid record step range: start={record_start_step}, end={record_end_step}. "
            "Check --front, --inject, --tail-pad, and --num-steps."
        )
    attention_flat = run_plain_target_denoise_with_probe(
        model,
        **inp_target,
        timesteps=get_schedule(args.num_steps, inp_target["img"].shape[1], shift=(args.name != "flux-schnell")),
        token_indices=token_indices,
        guidance=args.guidance,
        layer_ids=layer_ids,
        record_start_step=record_start_step,
        record_end_step=record_end_step,
    )

    h_patch = math.ceil(new_h / 16)
    w_patch = math.ceil(new_w / 16)
    attention_map = normalize01(attention_flat.reshape(h_patch, w_patch))
    smoothed = gaussian_filter(attention_map, sigma=0.7)
    threshold = float(threshold_otsu(smoothed)) if np.unique(smoothed).size > 1 else float(smoothed.mean())
    binary = (smoothed > threshold).astype(np.uint8)

    np.save(args.output_dir / "attention_proxy_raw.npy", attention_map)
    np.save(args.output_dir / "attention_proxy_smoothed.npy", smoothed.astype(np.float32))
    np.save(args.output_dir / "attention_proxy_binary.npy", binary)

    metadata = {
        "run_type": "plain_flux_target_token_attention",
        "case_uid": record["case_uid"],
        "seed": args.seed,
        "model_name": args.name,
        "guidance": args.guidance,
        "num_steps": args.num_steps,
        "front": args.front,
        "inject": args.inject,
        "tail_pad": args.tail_pad,
        "record_start_step": record_start_step,
        "record_end_step": record_end_step,
        "recorded_step_indices": list(range(record_start_step, record_end_step + 1)),
        "recorded_forwards": "first_order_and_midpoint",
        "source_prompt": record["source_prompt"],
        "target_prompt": record["target_prompt"],
        "part": record.get("part"),
        "edit": record.get("edit"),
        "token_indices": token_indices,
        "layer_ids": layer_ids,
        "map_shape": list(attention_map.shape),
        "threshold_method": "otsu",
        "threshold": threshold,
        "binary_mask_area_ratio_patch_grid": float(binary.mean()),
        "note": "True softmax attention mass from image-token queries to selected target part/edit T5 tokens in late FLUX single-stream blocks; same inverted z as FYS, no KV injection, no oracle mask.",
    }
    (args.output_dir / "run_config.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
