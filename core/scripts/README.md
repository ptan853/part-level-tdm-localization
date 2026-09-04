# Scripts

This directory contains runner and evaluation scripts for the PartEdit pilot.

## Held-Out Automatic-Mask Comparison

`run_heldout_control_comparison.py` prepares the frozen comparison without
using GT masks during generation. For each case and seed it runs five jobs in
dependency order:

1. Original FYS-TDM, retained as an evaluated baseline.
2. An attention-gated FYS scout that saves one automatic patch-grid mask.
3. Endpoint projection using the saved scout mask for steps `0..6`.
4. Source-referenced Residual RK2 using the same mask and steps `0..6`.
5. Supplemental historical endpoint projection with source image-KV at steps
   `0..1` and projection at steps `2..4`.

The four non-scout conditions are evaluated; the scout is shared preprocessing.
No evaluated method receives the manifest GT mask as model input. The matched
endpoint and RK2 plans use `mask_source=precomputed`, disable image-KV
injection, and fix the global duration at `N=7`.

Preview one existing case locally without loading FLUX:

```bash
python core/scripts/run_heldout_control_comparison.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --limit 1 \
  --write-run-matrix
```

Before execution, validate and write the exact 300-row matrix without loading
FLUX:

```bash
python core/scripts/run_heldout_control_comparison.py \
  --manifest core/data/partedit_subset/synth_60_frozen_manifest.json \
  --seeds 0 \
  --attention-token-mode part \
  --include-endpoint-n3 \
  --write-run-matrix
```

After sending the frozen identifiers requested in the pre-launch record, add
`--execute` on the configured GPU machine:

```bash
python core/scripts/run_heldout_control_comparison.py \
  --manifest core/data/partedit_subset/synth_60_frozen_manifest.json \
  --seeds 0 \
  --attention-token-mode part \
  --include-endpoint-n3 \
  --execution-commit <approved-full-commit-sha> \
  --execute
```

The runner refuses `--execute` unless `--execution-commit` exactly matches the
current outer-repository `HEAD`.

The runner writes `run_matrix.csv`, three resolved control plans, and five
isolated output trees under
`core/results/heldout_control_comparison/`. The automatic control mask is
loaded from each scout run's
`tdm/hybrid_binary_tdm_attention.npy`; the loader rejects non-binary, non-finite,
or incorrectly shaped arrays before denoising.

The formal dry run also freezes portable pre-generation evidence under
`core/protocols/heldout_control_comparison_v1/`: the 300-row command matrix,
the three resolved control plans, 480 deterministic assignments covering two
independent blinded reviewer orders, the package-lock hashes, and the
preflight checksums. With `--execute`, `runtime_environment.json` is captured
before the first model command.

After all 300 jobs finish, compute the frozen automatic metrics:

```bash
python core/scripts/evaluate_heldout_control_comparison.py \
  --manifest core/data/partedit_subset/synth_60_frozen_manifest.json \
  --run-matrix core/results/heldout_control_comparison/run_matrix.csv \
  --output core/results/heldout_control_comparison/evaluation_metrics.csv \
  --lpips require
```

Then create two independently randomized blinded review packages:

```bash
python core/scripts/prepare_heldout_manual_review.py \
  --metrics core/results/heldout_control_comparison/evaluation_metrics.csv \
  --randomization core/protocols/heldout_control_comparison_v1/reviewer_randomization.csv \
  --output-root core/results/heldout_control_comparison/blinded_review
```

After both reviewers export their completed CSVs, run the registered analysis:

```bash
python core/scripts/analyze_heldout_reviews.py \
  --review reviewer_1_scores.csv reviewer_1_private_mapping.csv \
  --review reviewer_2_scores.csv reviewer_2_private_mapping.csv \
  --output-dir core/results/heldout_control_comparison/analysis
```

## Latent-Projection Duration Sweep

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

### Residual RK2 Prefix Sweep

This oracle-mask experiment controls the deviation from the aligned inversion
reference at both RK2 evaluations. Duration `N` controls denoising updates
`0..N-1`; `N=0` is ordinary target RK2 and `N=15` controls the complete
15-update trajectory. Durations below 15 are controlled prefixes followed by
an ordinary target-RK2 tail. The primary sweep does not use image-KV injection.

Preview the complete 12-case by 16-duration matrix without loading FLUX:

```bash
python core/scripts/run_residual_rk2_prefix_sweep.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --all-cases \
  --durations 0-15 \
  --seed 0 \
  --write-run-matrix
```

Add `--execute` on the configured GPU machine to run all 192 outputs. Results
are isolated from prior control experiments:

```text
core/results/control_operations/residual_rk2_prefix_sweep/
  plans/duration_NN.json
  duration_NN/<case_uid>/seed_000/
```

Each controlled run records aligned source endpoint and midpoint indices plus
outside-mask residual diagnostics in `tdm/control_trace.json`. The complete
matrix is written to
`core/results/run_matrices/residual_rk2_prefix_all_cases_n0_n15.csv`.

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

## Residual RK2 Prefix Sweep

This oracle-mask control keeps a residual relative to the aligned source
inversion trajectory and applies that residual consistently at both RK2
midpoints and endpoints. Preview the full 12-case, N=0..15 matrix with:

```bash
python core/scripts/run_residual_rk2_prefix_sweep.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --all-cases --durations 0-15 --seed 0 --write-run-matrix
```

Add `--execute` on the GPU machine. Outputs are isolated under
`core/results/control_operations/residual_rk2_prefix_sweep/`.

After all 192 runs are complete, compute the frozen FYS-compatible metrics
(including LPIPS on a CUDA machine) and build the manual-review page:

```bash
python core/scripts/evaluate_residual_rk2_prefix_sweep.py --lpips require
python core/scripts/build_residual_rk2_manual_review.py
```

The evaluation command rejects incomplete runs and preserves existing LPIPS
values when rerun with `--lpips auto` or `--lpips off`. The review bundle is
written to `core/results/control_operations_eval/residual_rk2_prefix_sweep/`.

Notebook 10 regenerates the frozen three-method qualitative comparison used by
the final note after both evaluation tables are available. It joins rows by
`case_uid` and compares Original FYS-TDM, endpoint projection `N=3`, and
Residual RK2 `N=15`.
