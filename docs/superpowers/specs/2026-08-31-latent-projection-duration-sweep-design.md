# Latent Projection Duration Sweep

## Objective

Measure how the duration of oracle-mask latent projection changes the trade-off between target-edit strength and non-target preservation. The sweep isolates latent projection from late-stage FYS image-KV injection.

## Locked Case

- Case: `real_0006`
- Part/edit: `head -> alien`
- Seed: `0`
- Model and sampler settings: unchanged from the existing 15-step controlled experiments
- Mask source: oracle GT part mask

## Primary Sweep

All runs use the same source inversion and target-prompt denoising schedule.

- Steps 0-1: existing `source_all` image-KV initialization, held constant.
- Steps 2-14: target-prompt denoising with no image-KV injection.
- Latent projection starts at step 2 and is applied for `N` consecutive steps.
- Evaluate `N = 0, 1, ..., 13`:
  - `N=0`: no latent projection.
  - `N=1`: project after step 2.
  - `N=13`: project after every step from 2 through 14.

At each projected step `i`, use the matching source endpoint:

```text
z_next = M * z_target_candidate + (1 - M) * z_source[i + 1]
```

Stage 3 image-KV injection is disabled in every primary-sweep run so projection duration is the only changing control variable.

## Reference Run

Retain the existing `oracle_stage2_latent_projection` result (`N=7`, projection on steps 2-8 plus image-KV injection on steps 10-13) as a separate reference. It is not part of the primary duration curve.

## Outputs

Each run must save:

- generated image;
- resolved control plan and run configuration;
- control trace containing the exact projected steps and source-latent indices;
- per-step projection diagnostics.

The comparison artifact should show all 14 primary outputs in duration order, plus the source, GT mask overlay, and the separate Stage 3-injection reference.

## Validation

- Exactly 14 primary runs are present.
- Run `N` projects exactly steps `2..(N+1)` when `N > 0`.
- Every projected step uses source endpoint index `i+1`.
- `outside_mae_after` is zero at every projected step.
- No primary plan enables Stage 3 image-KV injection.
- The comparison reports edit-region change and non-target preservation as separate quantities.
