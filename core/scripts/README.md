# Scripts

This directory contains runner and evaluation scripts for the PartEdit pilot.

## Config-Driven Control Operations

New Stage 2 attention controls are opt-in and run under isolated result roots.
Preview the paired oracle experiment without loading FLUX:

```bash
python core/scripts/run_control_plan.py \
  --plan core/configs/control_plans/oracle_stage2_edit_logit_gate.json \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --limit 1
```

Add `--execute` on a configured GPU machine. The locked plans are:

- `oracle_fys_control.json`: no Stage 2 IT gate; oracle Stage 3 image-KV control.
- `oracle_stage2_edit_logit_gate.json`: oracle-mask edit-token logit gate in Stage 2.
- `part_to_edit_logit_transfer.json`: per-step part-token logits transferred to edit-token logits in Stage 2.

All three keep the same source inversion, target prompt, 15-step schedule, and
Stage 3 image-KV operation. Outputs are written to
`core/results/control_operations/<plan_name>/<case_uid>/seed_<seed>/`. Existing
FYS result directories are never reused, and non-empty output directories are
rejected unless `--overwrite` is explicitly supplied.

### Locked Oracle Latent-Projection Pilots

These two plans test direct latent-state projection, not a learned editor. Both
use the manifest GT part mask only as an oracle upper bound on localization
support. It establishes whether a control operation can preserve the source
trajectory outside an already-correct region. It is not a mask-free result,
and it is not an upper bound on semantic edit success or visual quality:
spatially expanding edits can still be suppressed by a fixed GT part mask.

Run these commands from the repository root on local parent branch
`experiment/latent-state-projection`, with FollowYourShape initialized at
gitlink `4aee1e642ecf64573e19e36a3a2e216e5d41e85d`. Use the pinned environment
and setup from the [root reproduction instructions](../../README.md), including
accepted FLUX.1-dev access, local model cache, and a CUDA-capable GPU for
commands with `--execute`.

Preview the Stage 2 projection plan without loading FLUX or writing outputs:

```bash
python core/scripts/run_control_plan.py \
  --plan core/configs/control_plans/oracle_stage2_latent_projection.json \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --limit 1
```

Run its locked four-case, seed-0 pilot on a configured GPU machine. The
explicit case IDs freeze the cohort as `real_0006`, `real_0010`, `real_0011`,
and `real_0001`; do not replace them with `--limit 4`.

```bash
python core/scripts/run_control_plan.py \
  --plan core/configs/control_plans/oracle_stage2_latent_projection.json \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --case-uid real_0006 \
  --case-uid real_0010 \
  --case-uid real_0011 \
  --case-uid real_0001 \
  --seeds 0 \
  --execute
```

The Stage 2 plan projects endpoints for steps `2-8` and retains the original
source-outside image-KV operation for steps `10-13`. The extended plan instead
projects endpoints from steps `2-14` and has no Stage 3 image-KV operation.
Preview it with its own isolated plan name and output directory:

```bash
python core/scripts/run_control_plan.py \
  --plan core/configs/control_plans/oracle_extended_latent_projection.json \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --limit 1
```

Run its corresponding GPU pilot:

```bash
python core/scripts/run_control_plan.py \
  --plan core/configs/control_plans/oracle_extended_latent_projection.json \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --case-uid real_0006 \
  --case-uid real_0010 \
  --case-uid real_0011 \
  --case-uid real_0001 \
  --seeds 0 \
  --execute
```

For either executed plan, the artifact contract is:

```text
core/results/control_operations/<plan_name>/<case_uid>/seed_<seed>/
  case_record.json
  resolved_control_plan.json
  run_config.json
  run.log
  img_0.jpg                  # when accepted by the existing safety filter
  tdm/oracle_gt_mask_patch_grid.npy
  tdm/selected_injection_mask.npy
  tdm/tdm_metadata.json
  tdm/control_trace.json
```

When latent projection is enabled, `tdm/control_trace.json` records both the
per-step control `trace` and `latent_projection_trace`, including the selected
source endpoint and outside-mask error diagnostics. `tdm/tdm_metadata.json`
contains TDM and mask-construction metadata. The runner writes the matching
command matrix to
`core/results/run_matrices/<plan_name>.csv` only with `--execute` (or
`--write-run-matrix`); dry runs print the isolated matrix path without writing
it.

### Latent-Projection Duration Sweep

The locked duration sweep isolates endpoint projection from Stage 3 image-KV
injection. The canonical experiment evaluates all 12 manifest cases at seed 0. Duration `N`
projects the target endpoint outside the oracle GT mask for denoising steps
`2..N+1`; `N=0` is the no-projection control and `N=13` covers steps `2-14`.
No sweep plan uses `source_outside_mask` image-KV injection.

Preview all 168 commands without loading FLUX:

```bash
python core/scripts/run_latent_projection_duration_sweep.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --all-cases \
  --durations 0-13 \
  --seed 0
```

Run the complete sweep on a configured GPU machine:

```bash
python core/scripts/run_latent_projection_duration_sweep.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --all-cases \
  --durations 0-13 \
  --seed 0 \
  --execute \
  --overwrite
```

Outputs are isolated by duration:

```text
core/results/control_operations/latent_projection_duration_sweep/
  plans/duration_NN.json
  duration_NN/<case_uid>/seed_000/
```

The command matrix is written to
`core/results/run_matrices/latent_projection_duration_sweep.csv`. Earlier
attention-control and Stage 3 image-KV experiments are not part of this locked
duration sweep or its final evaluation.

After all 168 runs finish, validate every trace and generate the metrics table,
continuous comparison sheet, and inside/outside change curves:

```bash
python core/scripts/summarize_latent_projection_duration_sweep.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --all-cases \
  --durations 0-13 \
  --output-dir core/results/control_operations_eval/latent_projection_all_cases_n0_n13
```

The summary artifacts are written to
`core/results/control_operations_eval/latent_projection_all_cases_n0_n13/`.
The summarizer rejects incomplete runs, incorrect source endpoint indices,
nonzero post-projection outside-mask error, and accidental Stage 3 image-KV
injection before calculating any image metric.

This produces per-run metrics plus overall and part-size-stratified summaries.
`inside_retention_vs_n0` measures retained GT-region change and
`outside_reduction_vs_n0` measures reduced non-target change; neither is a
semantic edit-success score.

### Reusable Manual Review

`build_manual_review.py` creates a standalone scoring page from a long-form
CSV and a JSON configuration. Each CSV row represents one review item. The
configuration selects the unique ID, image panels, score dimensions, browser
storage key, note field, and downloaded filename.

```bash
python core/scripts/build_manual_review.py \
  --input <review.csv> \
  --config <review_config.json> \
  --output <manual_review.html>
```

The generated page supports browser-local autosave, importing a prior CSV,
copying CSV text, downloading current scores, and keyboard navigation. Give
each task a distinct `storage_key` so unrelated experiments cannot share
ratings.

Without `--control-plan-resolved`, `edit.py` uses the original fused attention
and legacy FYS injection schedule.

## Follow-Your-Shape Pilot Runner

Preview the first manifest case without launching the model:

```bash
python core/scripts/run_fys_pilot.py --limit 1
```

Run the first case on a GPU machine:

```bash
python core/scripts/run_fys_pilot.py --limit 1 --execute
```

Preview the controlled-revision commands without launching the model or writing outputs:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2
```

Regenerate the controlled-revision run matrix without launching the model:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --write-run-matrix
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

Run a one-case GT-mask oracle smoke test:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --case-uid real_0008 \
  --seeds 0 \
  --oracle-mask \
  --execute
```

Oracle mode projects the manifest GT mask to the FLUX image-token grid and uses
it as the final Stage 3 `edit_map`. It keeps the original source inversion,
target trajectory, and late KV-injection schedule. Outputs are isolated under
`core/results/fys_mask_ablation/oracle_gt_mask/`.

Each Oracle run saves the diagnostic TDM as well as the actual control mask:

```text
tdm/oracle_gt_mask_patch_grid.npy
tdm/selected_injection_mask.npy
tdm/tdm_metadata.json
```

Preview the attention-gated TDM variant without launching the model:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --limit 1 \
  --tdm-mask-mode attention_gated \
  --attention-token-mode part_edit
```

Run one attention-gated TDM smoke test on a GPU machine:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --limit 1 \
  --tdm-mask-mode attention_gated \
  --attention-token-mode part_edit \
  --execute
```

The runner reads `core/data/partedit_subset/pilot_manifest.json` by default,
writes model outputs under `core/results/follow_your_shape/`, and keeps a
`run.log` per case. When `--seeds` is provided, each run is written to a
separate `seed_XXX` directory and gets its own `run_config.json`.

The default `--tdm-mask-mode original` keeps the original Follow-Your-Shape
behavior. `--tdm-mask-mode attention_gated` computes the original TDM and a
target-token attention map on the same middle denoising steps, uses
`normalize(TDM) * normalize(attention)` as the localization score, binarizes it
with Otsu thresholding, and uses that selected mask for Stage 3 KV injection.
Attention-gated outputs are written to
`core/results/fys_mask_ablation/attention_gated_tdm/` by default, so original
FYS outputs are not overwritten.

With `--execute`, the runner also writes a command/config matrix to
`core/results/run_matrices/<manifest>_multi_seed.csv`. To write the matrix
during dry-run, pass `--write-run-matrix`. This table is intended for
reproducibility and should be the source for later evaluation tables.

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
   target text tokens in late single-stream blocks, restricted to
   the same middle denoising steps used by the FYS TDM construction.

Use `--token-mode part` for the current attention-gated TDM experiment. This
uses the target part token as a where-only localization signal while the full
target prompt still supplies the edit semantics during denoising. The older
`--token-mode part_edit` setting is retained for comparison with the previous
baseline.

Dry-run one baseline command without writing outputs:

```bash
python core/scripts/run_flux_attention_baseline.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --limit 1 \
  --token-mode part
```

Run one smoke test on a GPU machine:

```bash
python core/scripts/run_flux_attention_baseline.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --limit 1 \
  --token-mode part \
  --execute
```

Run the full 12-case x 3-seed baseline:

```bash
python core/scripts/run_flux_attention_baseline.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --token-mode part \
  --execute
```

Outputs are written under:

```text
core/results/flux_attention_baseline/<case_uid>/seed_<seed>/
```

For `--token-mode part`, the default output directory is:

```text
core/results/flux_part_attention_baseline/<case_uid>/seed_<seed>/
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

For `--token-mode part`, the default matrix is:

```text
core/results/run_matrices/flux_part_attention_baseline_matrix.csv
```

With `--execute`, the matrix is written automatically. To regenerate only the
matrix during dry-run, add `--write-run-matrix`.

## Same-State Inversion Probe

This diagnostic compares the source and target prompts at the same source-
inversion latent and timestep. It records per-step velocity differences plus
separate target part-token and edit-token attention maps. These maps do not
control generation; `img_0.jpg` is produced by the unchanged original FYS path.

Preview the locked two-case experiment without writing outputs:

```bash
python core/scripts/run_same_state_inversion_probe.py \
  --case-uid real_0006 \
  --case-uid real_0010 \
  --seed 0
```

Run it on a GPU machine by adding `--execute`. Results are isolated under
`core/results/same_state_inversion_probe/<case_uid>/seed_000/` and include
authoritative `.npy` maps, PNG previews, `step_overview.png`, `img_0.jpg`,
`probe_metadata.json`, `run_config.json`, and `run.log`.
