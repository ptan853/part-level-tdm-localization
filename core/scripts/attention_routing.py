"""Scoped, read-only IT/II statistics for actual FLUX denoising midpoint calls."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch


LAYERS = {"double": (0, 9, 18), "single": (0, 18, 37)}


def midpoint_step(info: dict | None, sampling_info: dict) -> int | None:
    # Scout passes use None or a separate info dictionary. Identity is intentional.
    if info is not sampling_info or info.get("inverse") or not info.get("second_order"):
        return None
    if info.get("inject") or info.get("attention_control") is not None:
        raise ValueError("Routing observation requires KV and IT control disabled")
    trace = info.get("control_trace", [])
    if not trace:
        raise ValueError("Routing observation requires an explicit control plan")
    return int(trace[-1]["step"])


@torch.no_grad()
def summarize_attention(q, k, text_length: int, image_mask, chunk_size: int = 16):
    """Mean joint weights over GT image queries, retaining each attention head.

    q/k must already include QK normalization and RoPE. No value/output is changed.
    All text keys (including special/padding positions) stay in the denominator.
    """
    mask = torch.as_tensor(image_mask, device=q.device).flatten()
    if q.ndim != 4 or q.shape != k.shape or q.shape[0] != 1:
        raise ValueError("Expected matching single-image [1, heads, tokens, dim] Q/K")
    if not 0 < text_length < q.shape[2] or mask.numel() != q.shape[2] - text_length:
        raise ValueError("Observation mask does not match the image-token grid")
    if not torch.isfinite(mask).all() or not ((mask == 0) | (mask == 1)).all() or not mask.any():
        raise ValueError("Observation mask must be nonempty, finite and binary")
    if chunk_size < 1:
        raise ValueError("Query chunk size must be positive")
    mask = mask.bool()
    queries = torch.nonzero(mask, as_tuple=False).flatten() + text_length
    with torch.autocast(device_type=q.device.type, enabled=False):
        keys = k.detach().float().transpose(-2, -1)
        text_sum = torch.zeros(q.shape[1], text_length, device=q.device)
        mass_sum = torch.zeros(q.shape[1], 3, device=q.device)
        max_error = torch.zeros((), device=q.device)
        for indices in queries.split(chunk_size):
            logits = q.detach().index_select(2, indices).float() @ keys
            weights = torch.softmax(logits * q.shape[-1] ** -0.5, dim=-1)[0]
            text_sum += weights[..., :text_length].sum(dim=1)
            image = weights[..., text_length:]
            mass_sum[:, 0] += weights[..., :text_length].sum(dim=(1, 2))
            mass_sum[:, 1] += image[..., mask].sum(dim=(1, 2))
            mass_sum[:, 2] += image[..., ~mask].sum(dim=(1, 2))
            max_error = torch.maximum(max_error, (weights.sum(-1) - 1).abs().max())
        text_mean = text_sum / len(queries)
        region_mass = mass_sum / len(queries)
    if not torch.isfinite(text_mean).all() or not torch.isfinite(region_mass).all():
        raise ValueError("Non-finite attention statistics")
    return text_mean.cpu().numpy(), region_mass.cpu().numpy(), float(max_error.item())


class RoutingRecorder:
    """Temporarily observe block inputs to attention; ordinary SDPA still runs.

    One recorder per process/model. Not intended for concurrent model execution.
    Only compact CPU arrays are retained across forward calls.
    """

    def __init__(self, model, sampling_info, image_mask, text_length, *, layers=None):
        self.model = model
        self.sampling_info = sampling_info
        self.mask = np.asarray(image_mask)
        self.text_length = text_length
        self.layers = LAYERS if layers is None else layers
        self.handles = []
        self.records = []
        self.seen = set()
        self.step = None
        self.layer = None
        self.t = None
        self.original_attention = None

    def _model_pre(self, module, inputs, kwargs):
        self.layer = None
        self.step = midpoint_step(kwargs.get("info"), self.sampling_info)
        if self.step is not None:
            self.t = float(kwargs["timesteps"][0].item())

    def _block_pre(self, label):
        def hook(module, inputs):
            self.layer = label
        return hook

    def _block_post(self, module, inputs, output):
        self.layer = None

    def _attention(self, q, k, v, pe, control=None):
        if self.step is not None and self.layer is not None:
            if control is not None:
                raise ValueError("IT-controlled attention is outside this diagnostic")
            from flux.math import apply_rope
            with torch.no_grad():
                qr, kr = apply_rope(q.detach(), k.detach(), pe)
                text, mass, error = summarize_attention(qr, kr, self.text_length, self.mask)
            key = (self.step, self.layer)
            if key in self.seen:
                raise ValueError(f"Duplicate midpoint record: {key}")
            self.seen.add(key)
            self.records.append({"step": self.step, "layer": self.layer, "t": self.t,
                                 "text": text, "mass": mass, "row_sum_error": error})
        return self.original_attention(q, k, v, pe=pe, control=control)

    def __enter__(self):
        from flux.modules import layers as flux_layers
        for stream, indices in self.layers.items():
            blocks = getattr(self.model, f"{stream}_blocks")
            if len(indices) != len(set(indices)) or any(i < 0 or i >= len(blocks) for i in indices):
                raise ValueError(f"Invalid {stream} layer selection: {indices}")
        self.original_attention = flux_layers.attention
        try:
            self.handles.append(self.model.register_forward_pre_hook(self._model_pre, with_kwargs=True))
            for stream, indices in self.layers.items():
                for index in indices:
                    block = getattr(self.model, f"{stream}_blocks")[index]
                    self.handles.append(block.register_forward_pre_hook(self._block_pre(f"{stream}_{index}")))
                    self.handles.append(block.register_forward_hook(self._block_post))
            flux_layers.attention = self._attention
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, exc_type, exc, tb):
        from flux.modules import layers as flux_layers
        if self.original_attention is not None:
            flux_layers.attention = self.original_attention
        for handle in self.handles:
            handle.remove()
        self.handles.clear()
        self.step = self.layer = None

    def save(self, directory: Path, *, num_steps: int, tokens: dict) -> None:
        expected = {(s, f"{stream}_{i}") for s in range(num_steps)
                    for stream, indices in self.layers.items() for i in indices}
        if self.seen != expected:
            raise ValueError(f"Incomplete routing coverage: missing={sorted(expected - self.seen)}")
        if len(tokens["token_ids"]) != self.text_length:
            raise ValueError("Token metadata does not match text sequence length")
        records = sorted(self.records, key=lambda r: (r["step"], r["layer"]))
        directory.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            directory / "attention_statistics.npz",
            text_attention=np.stack([r["text"] for r in records]),
            region_mass=np.stack([r["mass"] for r in records]),
            steps=np.asarray([r["step"] for r in records]),
            layers=np.asarray([r["layer"] for r in records]),
            times=np.asarray([r["t"] for r in records]),
        )
        metadata = {
            "schema_version": 1, "evaluation": "actual_forward_midpoint",
            "records": len(records), "layers": self.layers, "num_steps": num_steps,
            "text_length": self.text_length, "tokens": tokens,
            "query_region": "fixed_source_GT", "query_count": int(self.mask.sum()),
            "image_grid_shape": list(self.mask.shape),
            "mass_columns": ["all_text", "inside_image", "outside_image"],
            "max_row_sum_error": max(r["row_sum_error"] for r in records),
            "weight_definition": "FP32 softmax of normalized, RoPE-transformed QK; all joint keys",
            "note": "Reconstructed diagnostic weights; ordinary fused SDPA is unchanged. No AV stored.",
        }
        (directory / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
