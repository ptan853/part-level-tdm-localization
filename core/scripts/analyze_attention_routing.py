#!/usr/bin/env python3
"""Validate compact attention records, compare observer on/off, and plot paired runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def verify_latents(first: Path, second: Path) -> dict:
    results = {}
    for name in ("initial", "final"):
        a = np.load(first / f"routing/{name}_latent.npy", allow_pickle=False)
        b = np.load(second / f"routing/{name}_latent.npy", allow_pickle=False)
        valid = a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
        results[name] = {
            "equal": bool(valid and np.array_equal(a, b)),
            "within_tolerance": bool(valid and np.allclose(a, b, atol=1e-6, rtol=1e-6)),
            "max_abs_difference": float(np.max(np.abs(a - b))) if valid else None,
        }
    return {"passed": results["initial"]["equal"] and results["final"]["within_tolerance"],
            "atol": 1e-6, "rtol": 1e-6, "latents": results}


def read_run(path: Path):
    directory = path / "routing"
    metadata = json.loads((directory / "metadata.json").read_text())
    with np.load(directory / "attention_statistics.npz", allow_pickle=False) as source:
        data = {k: source[k] for k in source.files}
    text, mass = data["text_attention"], data["region_mass"]
    if text.ndim != 3 or mass.shape != (*text.shape[:2], 3):
        raise ValueError("Unexpected attention array dimensions")
    if text.shape[0] != metadata["records"] or text.shape[2] != metadata["text_length"]:
        raise ValueError("Metadata/array shape mismatch")
    if not np.isfinite(text).all() or not np.isfinite(mass).all() or (text < 0).any() or (mass < 0).any():
        raise ValueError("Invalid probability values")
    if not np.allclose(mass.sum(-1), 1, atol=1e-5) or not np.allclose(text.sum(-1), mass[..., 0], atol=1e-5):
        raise ValueError("Joint probability mass is not conserved")
    expected = {(s, f"{stream}_{i}") for s in range(metadata["num_steps"])
                for stream, indices in metadata["layers"].items() for i in indices}
    pairs = list(zip(data["steps"].tolist(), data["layers"].tolist()))
    if len(pairs) != len(set(pairs)) or set(pairs) != expected:
        raise ValueError("Incomplete or duplicate layer/step coverage")
    return metadata, data


def plot_runs(paths: list[Path], output: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    runs = [read_run(path) for path in paths]
    tokens = runs[0][0]["tokens"]
    for metadata, data in runs[1:]:
        if metadata["tokens"] != tokens or metadata["layers"] != runs[0][0]["layers"]:
            raise ValueError("Paired plots require the same target tokens and selected layers")
        if metadata["num_steps"] != runs[0][0]["num_steps"]:
            raise ValueError("Paired plots require identical step counts")
    if len(paths) > 1:
        initial = [np.load(p / "routing/initial_latent.npy") for p in paths]
        if any(not np.array_equal(initial[0], x) for x in initial[1:]):
            raise ValueError("Paired plots require exactly matching initial inversion latents")
    layers = [f"{stream}_{i}" for stream, ids in runs[0][0]["layers"].items() for i in ids]
    positions = np.flatnonzero(tokens["valid_positions"])
    labels = [f"{i}: {tokens['token_strings'][i]}" for i in positions]
    titles = []
    for path in paths:
        config = json.loads((path / "run_config.json").read_text()) if (path / "run_config.json").exists() else {}
        titles.append(f"{config.get('case_uid', path.name)} | {config.get('plan_name', 'diagnostic')}")
    output.mkdir(parents=True, exist_ok=True)
    for conditional in (False, True):
        matrices = []
        for meta, data in runs:
            text = data["text_attention"].mean(axis=1)
            # Ratio of query/head means, not an average of per-query conditional probabilities.
            if conditional:
                denominator = text[:, positions].sum(-1, keepdims=True)
                text = np.divide(text, denominator, out=np.zeros_like(text), where=denominator > 0)
            matrices.append(text[:, positions])
        vmax = max(float(x.max()) for x in matrices) or 1.0
        fig, axes = plt.subplots(len(layers), len(paths), figsize=(9 * len(paths), 3.2 * len(layers)),
                                 squeeze=False, layout="constrained")
        for col, ((meta, data), values) in enumerate(zip(runs, matrices)):
            for row, layer in enumerate(layers):
                indices = np.flatnonzero(data["layers"] == layer)
                indices = indices[np.argsort(data["steps"][indices])]
                ax = axes[row, col]
                im = ax.imshow(values[indices], aspect="auto", vmin=0, vmax=vmax, cmap="viridis")
                ax.set_xticks(range(len(labels)), labels, rotation=55, ha="right", fontsize=8)
                ax.set_yticks(range(len(indices)), data["steps"][indices])
                ax.set_ylabel("Denoising step")
                ax.set_title(f"{titles[col]} | {layer}", fontsize=10)
        kind = "conditional_valid_text" if conditional else "joint_text"
        fig.suptitle(f"GT-query attention: {kind}\nMidpoint only; mean across queries and heads; shared color scale")
        fig.colorbar(im, ax=axes.ravel().tolist(), shrink=.5, label="Attention weight")
        fig.savefig(output / f"{kind}.png", dpi=130)
        plt.close(fig)
    fig, axes = plt.subplots(len(layers), len(paths), figsize=(8 * len(paths), 2.8 * len(layers)),
                             squeeze=False, layout="constrained")
    for col, (meta, data) in enumerate(runs):
        for row, layer in enumerate(layers):
            indices = np.flatnonzero(data["layers"] == layer)
            indices = indices[np.argsort(data["steps"][indices])]
            mass = data["region_mass"][indices].mean(axis=1)
            ax = axes[row, col]
            for group, (label, style) in enumerate(zip(meta["mass_columns"], ("-", "--", ":"))):
                ax.plot(data["steps"][indices], mass[:, group], linestyle=style, label=label)
            pad = np.flatnonzero(np.asarray(tokens["valid_positions"]) == 0)
            pad_mass = data["text_attention"][indices].mean(axis=1)[:, pad].sum(-1)
            ax.plot(data["steps"][indices], pad_mass, color="gray", linestyle="-.", label="padding (part of text)")
            ax.set(xlabel="Denoising step", ylabel="Joint attention mass", ylim=(0, 1),
                   title=f"{titles[col]} | {layer}")
            if row == 0:
                ax.legend(fontsize=8)
    fig.suptitle("GT-query information sources\nMidpoint only; mean across queries and heads")
    fig.savefig(output / "region_mass.png", dpi=130)
    plt.close(fig)
    (output / "summary.json").write_text(json.dumps({
        "runs": [str(p.resolve()) for p in paths], "records_per_run": [m["records"] for m, _ in runs],
        "interpretation": "Descriptive attention routing, not causal attribution or semantic success.",
    }, indent=2) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--compare-run", type=Path)
    parser.add_argument("--verify-against", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.verify_against:
        result = verify_latents(args.run, args.verify_against)
        (args.run / "routing/observer_verification.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    paths = [args.run] + ([] if args.compare_run is None else [args.compare_run])
    plot_runs(paths, args.output or args.run / "routing/analysis")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
