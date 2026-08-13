# Scripts

This directory contains runner and evaluation scripts for the PartEdit pilot.

## Follow-Your-Shape Pilot Runner

Preview the first manifest case without launching the model:

```bash
python core/scripts/run_fys_pilot.py --limit 1
```

Run the first case on a GPU machine:

```bash
python core/scripts/run_fys_pilot.py --limit 1 --execute
```

Preview the controlled-revision run matrix without launching the model:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2
```

Run the controlled revision:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --execute
```

Run a specific case:

```bash
python core/scripts/run_fys_pilot.py --case-uid real_0008 --execute
```

Run the oracle-mask variant:

```bash
python core/scripts/run_fys_pilot.py --case-uid real_0008 --oracle-mask --execute
```

The runner reads `core/data/partedit_subset/pilot_manifest.json` by default,
writes model outputs under `core/results/follow_your_shape/`, and keeps a
`run.log` per case. When `--seeds` is provided, each run is written to a
separate `seed_XXX` directory and gets its own `run_config.json`.

The runner also writes a command/config matrix to
`core/results/run_matrices/<manifest>_multi_seed.csv`. This table is intended
for reproducibility and should be the source for later evaluation tables.

## FLUX Target-Token Attention Baseline

This baseline is a simple localization comparison for the FYS TDM maps. It
does not perform FYS KV injection and does not use the oracle GT mask as model
input.

For each case/seed, the worker:

1. encodes the source image,
2. runs source-prompt inversion to recover the same kind of starting latent
   `z` used by FYS,
3. runs plain target-prompt FLUX denoising from that `z`,
4. records true softmax attention mass from image-token queries to selected
   target part/edit text tokens in late single-stream blocks, restricted to
   the same middle denoising steps used by the FYS TDM construction.

Dry-run one baseline command:

```bash
python core/scripts/run_flux_attention_baseline.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --limit 1
```

Run one smoke test on a GPU machine:

```bash
python core/scripts/run_flux_attention_baseline.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --limit 1 \
  --execute
```

Run the full 12-case x 3-seed baseline:

```bash
python core/scripts/run_flux_attention_baseline.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --execute
```

Outputs are written under:

```text
core/results/flux_attention_baseline/<case_uid>/seed_<seed>/
```

Each run saves:

```text
attention_proxy_raw.npy
attention_proxy_smoothed.npy
attention_proxy_binary.npy
case_record.json
run_config.json
run.log
```

The saved files keep the `attention_proxy_*` names for compatibility with
the evaluation notebook, but the underlying score is true target-token
softmax attention mass, not a raw Q/K dot-product proxy.

The run matrix is written to:

```text
core/results/run_matrices/flux_attention_baseline_matrix.csv
```
