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
`i`, and let `s_mid_i` be the cached inversion-reference midpoint for update
`i`. Let `x_i` be the target editing state and define the residual:

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

This first version uses residual-ODE semantics rather than hard residual
projection. For a binary mask:

- where `M=0`, the existing residual is preserved: `d_next=d_i`; no new
  residual is introduced, but a historical residual is not erased;
- inside the mask, the target RK2 residual is retained relative to the source
  trajectory.

Because every primary controlled interval begins at step 0, `d_0=0`, and the
oracle mask is fixed, the outside-mask residual remains zero throughout the
controlled prefix. Consequently the outside-mask controlled state equals the
source reference in this experiment. This equality is a consequence of the
initial condition and fixed mask, not a general hard-projection rule. A future
dynamic-mask method must separately define whether residuals are retained or
removed when a mask location changes from 1 to 0.

The midpoint reference is required. Reusing only source endpoints would reduce
the method to post-update endpoint projection and would not test the proposed
control operation.

## Source-Trajectory Alignment

Source inversion already stores endpoints under denoising schedule indices.
It must additionally store one cached inversion-reference midpoint per
denoising update. If inversion loop index is `k` and there are `T=15` updates,
the aligned denoising update is:

```text
i = T - 1 - k
```

The cache contracts are:

```text
source_latents:  keys 0..15
source_midpoints: keys 0..14
```

`source_midpoints[i]` is the midpoint state actually visited by the reversed
inversion reference path. It is not claimed to equal a midpoint obtained by
running an independent forward source RK2 solve, because explicit RK2 is not
generally time-reversible. The method defines `s(t)` as this cached reversed
inversion path, so its visited midpoint is the required reference.

The endpoint identities are part of the cache contract:

```text
source_latents[15] = encoded source-image VAE latent
source_latents[0]  = final inverted source noise latent
```

The sampler must reject missing keys, shape mismatches, non-finite values, and
masks outside `[0, 1]` before executing residual control.

## Oracle Mask to FLUX Token Mapping

The experiment preserves the repository's existing deterministic conversion:

1. Read the pixel-space mask as grayscale and threshold with `pixel > 0`.
2. Resize the binary mask with nearest-neighbor interpolation to the encoded
   VAE latent spatial grid.
3. Re-threshold to binary.
4. Apply `2x2` max pooling with stride 2, matching FLUX's `2x2` latent packing.
5. Flatten the pooled grid in row-major order, the same order used by
   `rearrange(..., "b c (h ph) (w pw) -> b (h w) (c ph pw)", ph=2, pw=2)`.
6. Require the flattened mask length to equal the packed image-token count and
   retain strictly binary values.

The existing asymmetric non-square mask regression test must continue to pass.
A rectangular top-left-quarter fixture additionally verifies that spatial
orientation and packed-token support remain aligned for residual control.

## Primary Sweep

Run one method, `residual_rk2`, for all `N=0..15` and all 12 cases:

```text
12 cases x 16 durations = 192 outputs
```

`N=0` is not described as a separate method. Residual Euler is limited to a
unit-level numerical sanity check and is not included in image evaluation.

Only `N=15` applies the residual ODE discretization over the complete generation
trajectory. Runs with `N<15` are explicitly described as residual RK2 prefix
control followed by release to ordinary target RK2, not as complete residual
ODE solutions.

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
- with an all-zero mask, residual-control helpers preserve the incoming
  residual rather than erase it;
- with an all-zero mask and the primary initial condition `d_0=0`, every
  controlled endpoint equals the aligned source endpoint;
- with an all-one mask, controlled RK2 equals ordinary target RK2 within the
  configured numerical tolerance;
- source endpoint identities and pixel-to-packed-token mask alignment pass
  automated tests;
- controlled-step traces are exactly `range(N)`;
- all 192 primary runs are complete and non-overwriting.

Experimental success is not defined as automatically beating all baselines.
The experiment succeeds scientifically if it produces a reproducible curve
that distinguishes semantic edit activity from non-target preservation and
shows whether residual midpoint control changes that trade-off.
