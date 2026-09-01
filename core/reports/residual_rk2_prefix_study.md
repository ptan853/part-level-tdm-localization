# Source-Referenced Residual RK2 Prefix Control

## Current Status

The implementation, sweep runner, frozen metric evaluator, and reusable manual-review page are complete. The 12-case by 16-duration GPU sweep and its empirical conclusions are **pending** because the configured GPU host is currently closing SSH connections before authentication. This report intentionally does not claim a winning duration before those 192 outputs and human scores exist.

## Method

The method maintains a **source-referenced residual** instead of replacing a completed latent state after an RK2 step. Let `s_i`, `s_mid`, and `s_next` be aligned source-inversion states, `x_i = s_i + d_i` the current edited state, `h` the denoising step, and `M` the oracle edit mask on packed image tokens. For each controlled prefix step:

```text
d_mid  = d_i + M * (0.5 h v1 - (s_mid  - s_i))
x_mid  = s_mid  + d_mid
d_next = d_i + M * (h v2     - (s_next - s_i))
x_next = s_next + d_next
```

`v1` is evaluated at `x_i`; `v2` is evaluated at the controlled midpoint `x_mid`. Outside the mask, an initially zero residual remains on the aligned source trajectory. Inside the mask, an all-one mask recovers ordinary target-prompt RK2. This is therefore different from endpoint-only latent projection: control is integrated consistently at both RK2 stages.

The sweep varies projection duration `N` from 0 through 15. `N=0` is the uncontrolled target trajectory. For `N>0`, residual control is active on denoising steps `0..N-1`. The primary experiment does not enable image-KV injection, so it isolates the residual-state control operation.

## Frozen Evaluation

- Dataset: the frozen 12-case manifest balanced across small, medium, and large parts.
- Outputs: 192 unique residual RK2 images (`12 cases x 16 durations`) at seed 0.
- Baselines: Original FYS-TDM and the completed oracle endpoint-projection sweep.
- Non-target preservation: outside-mask L1, PSNR, global-SSIM proxy, and LPIPS.
- Target-region activity: inside-mask L1, PSNR, and global-SSIM proxy. These are descriptive change measures, not semantic-success measures.
- Semantic evaluation: separate 0-2 human scores for local-edit success and non-target preservation for every case-duration output.
- Selection rule: choose a duration only after reviewing both preservation and semantic success; no case-specific tuning.

All automatic metrics reuse the same functions as the existing endpoint-projection/FYS comparison. LPIPS must be completed on a CUDA machine with `--lpips require`.

## Result Artifacts

When the sweep is complete, the durable outputs are:

- `core/results/control_operations/residual_rk2_prefix_sweep/`: images, plans, logs, run configurations, and control traces.
- `core/results/run_matrices/residual_rk2_prefix_sweep.csv`: exact 192-command matrix.
- `core/results/control_operations_eval/residual_rk2_prefix_sweep/unified_image_metrics.csv`: FYS, endpoint projection, and residual RK2 under one metric implementation.
- `core/results/control_operations_eval/residual_rk2_prefix_sweep/manual_review.html`: all 192 residual outputs for scoring.
- `core/results/control_operations_eval/residual_rk2_prefix_sweep/manual_review_scores.csv`: completed human ratings.
- `core/notebooks/10_evaluate_residual_rk2_prefix_sweep.ipynb`: final quantitative and qualitative analysis.

## Reproduction

Run the complete GPU sweep:

```bash
python core/scripts/run_residual_rk2_prefix_sweep.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --all-cases --durations 0-15 --seed 0 --execute
```

Then compute metrics and create the scoring page:

```bash
python core/scripts/evaluate_residual_rk2_prefix_sweep.py --lpips require
python core/scripts/build_residual_rk2_manual_review.py
```

After scoring, save the downloaded CSV as `manual_review_scores.csv`, validate it, and execute Notebook 10:

```bash
python core/scripts/build_residual_rk2_manual_review.py \
  --validate core/results/control_operations_eval/residual_rk2_prefix_sweep/manual_review_scores.csv
python -m jupyter nbconvert --execute --to notebook --inplace \
  core/notebooks/10_evaluate_residual_rk2_prefix_sweep.ipynb
```
