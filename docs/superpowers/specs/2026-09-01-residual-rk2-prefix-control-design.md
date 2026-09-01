# Residual RK2 Prefix Control Design

## Objective

Test a second oracle-mask control operation for part-level FLUX editing without
mixing it with the completed endpoint latent-projection study. The new operation
tracks the deviation from an aligned source inversion trajectory and constrains
that deviation with the oracle part mask at both RK2 evaluation points.

The experiment must answer two separate questions:

1. Does inversion-referenced residual RK2 control improve the edit/preservation
   trade-off as its controlled prefix grows?
2. After fixing a global prefix duration, does standard late FYS image-KV
   injection provide an additional benefit?

Question 1 is the primary experiment. Question 2 is a secondary ablation and
must not be mixed into the primary duration curve.

## Frozen Experiment Semantics

The denoising schedule has 15 updates indexed `0..14`. `N` is the number of
consecutive updates controlled from the beginning of denoising:

```text
controlled steps = 0, 1, ..., N - 1
free steps       = N, N + 1, ..., 14
```

Therefore:

- `N=0` is ordinary target-prompt denoising and is the shared no-control
  baseline.
- `N=1` controls only step 0.
- `N=15` controls every denoising update.

This definition intentionally differs from the completed endpoint-projection
sweep, where `N` counted projection updates beginning at step 2. Existing
outputs and reports keep their original meaning and are not rewritten.

Every primary run uses:

- the locked 12-case manifest;
- seed 0, because this inversion path is deterministic under the current
  implementation;
- the same source image, source prompt, target prompt, guidance, number of
  steps, and FLUX checkpoint;
- the oracle GT part mask;
- no attention gating;
- no image-KV injection.

## Residual RK2 Operation

Let `s_i` be the aligned source inversion endpoint at denoising schedule index
`i`, and let `s_mid_i` be the aligned source midpoint for update `i`. Let `x_i`
be the target editing state and define the residual:

```text
d_i = x_i - s_i
```

The initial state is aligned, so `d_0 = 0`. Let `M` be the oracle mask broadcast
over latent channels and let `h_i = t_{i+1} - t_i`.

For every controlled step `i < N`:

```text
v1 = v_target(x_i, t_i)
d_mid = d_i + M * (0.5 * h_i * v1 - (s_mid_i - s_i))
x_mid = s_mid_i + d_mid

v2 = v_target(x_mid, t_mid_i)
d_next = d_i + M * (h_i * v2 - (s_{i+1} - s_i))
x_{i+1} = s_{i+1} + d_next
```

For each free step `i >= N`, use the repository's unchanged target-prompt RK2
update from the current `x_i`.

This operation has two invariants for a binary mask:

- outside the mask, a controlled endpoint equals `s_{i+1}` exactly;
- inside the mask, the target RK2 residual is retained relative to the source
  trajectory.

The midpoint reference is required. Reusing only source endpoints would reduce
the method to post-update endpoint projection and would not test the proposed
control operation.

## Source-Trajectory Alignment

Source inversion already stores endpoints under denoising schedule indices.
It must additionally store one midpoint per denoising update. If inversion loop
index is `k` and there are `T=15` updates, the aligned denoising update is:

```text
i = T - 1 - k
```

The cache contracts are:

```text
source_latents:  keys 0..15
source_midpoints: keys 0..14
```

The sampler must reject missing keys, shape mismatches, non-finite values, and
masks outside `[0, 1]` before executing residual control.

## Primary Sweep

Run one method, `residual_rk2`, for all `N=0..15` and all 12 cases:

```text
12 cases x 16 durations = 192 outputs
```

`N=0` is not described as a separate method. Residual Euler is limited to a
unit-level numerical sanity check and is not included in image evaluation.

The output hierarchy is isolated from previous experiments:

```text
core/results/control_operations/residual_rk2_prefix_sweep/
  duration_00/<case_uid>/seed_000/
  ...
  duration_15/<case_uid>/seed_000/
```

Each run records the resolved plan, source-reference coverage, controlled step
indices, per-step outside-mask residual error, command, log, and output image.

## Evaluation

Use the same metric definitions as notebook 09 so comparisons are compatible:

- outside-mask L1, PSNR, global SSIM proxy, and LPIPS;
- inside-mask L1, PSNR, and global SSIM proxy as descriptive activity measures;
- human local-edit success `0..2`;
- human non-target preservation `0..2`;
- joint success rates for both scores `>=1` and both scores `=2`;
- breakdowns by small, medium, and large parts;
- per-case qualitative grids across representative `N` values.

LPIPS is computed on the GPU/server when available. Existing FYS and endpoint
projection results are read as frozen baselines; this experiment must not
overwrite them.

No case-specific `N` is selected. The report shows the full curve and, if a
single duration is needed, uses one global duration selected by the locked
criterion: maximize joint success (`both >= 1`), then preservation mean, then
choose the smaller `N`.

## Secondary Late-KV Ablation

Only after the primary sweep and its correctness checks pass, test whether late
image-KV injection adds value. Keep the residual prefix fixed and use the
standard FYS late window, steps `10..13`.

Primary candidate:

```text
Residual RK2 N=3 + free tail
Residual RK2 N=3 + source-outside-mask image-KV at steps 10..13
```

`N=3` is predeclared from the completed endpoint-projection pilot rather than
selected per case from the new outputs. If compute permits, `N=2` and `N=5`
are sensitivity checks. Injection never begins immediately at `N`, because
that would make injection duration vary with `N` and confound the comparison.

## Compatibility Requirements

- A missing control plan continues to execute the original FYS path unchanged.
- Existing `source_outside_mask` endpoint projection remains unchanged.
- Existing control-plan JSON files retain their current semantics.
- The new sweep uses a new script and output root; it does not modify the old
  duration sweep or its reports.
- Parent-repository and FollowYourShape-submodule commits remain independently
  reproducible.

## Success Criteria

Implementation correctness requires:

- all unit and integration tests pass;
- `N=0` is numerically identical to the unchanged free target path;
- with an all-zero mask, every controlled endpoint equals the aligned source
  endpoint;
- with an all-one mask, controlled RK2 equals ordinary target RK2 within the
  configured numerical tolerance;
- controlled-step traces are exactly `range(N)`;
- all 192 primary runs are complete and non-overwriting.

Experimental success is not defined as automatically beating all baselines.
The experiment succeeds scientifically if it produces a reproducible curve
that distinguishes semantic edit activity from non-target preservation and
shows whether residual midpoint control changes that trade-off.
