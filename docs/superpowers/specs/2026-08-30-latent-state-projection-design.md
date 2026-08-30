# Latent State Projection Design

## Objective

Test whether the control bottleneck in part-level FLUX editing is caused by
allowing target-prompt drift to accumulate outside the intended edit region.
The new operation uses an oracle binary mask and the source inversion
trajectory to enforce source-consistent latent state outside that region after
selected denoising steps.

This is an opt-in experimental control operation. Existing FYS-TDM,
attention-gated, same-state probe, and control-plan behavior must remain
unchanged when latent projection is not configured.

## Mathematical Definition

Let the denoising schedule be

```text
t_0 = 1 > t_1 > ... > t_N = 0.
```

Source-prompt inversion starts from the encoded source image at `t_N` and
integrates to `t_0`. It records a source reference latent at every schedule
node:

```text
Z_src = {z_src[0], z_src[1], ..., z_src[N]},
```

where `z_src[i]` corresponds to denoising time `t_i`. The indexing contract is
defined by timestep identity, not by inversion loop order.

Target denoising starts from `z_src[0]`. At denoising step `i`, the existing
second-order update produces a target candidate:

```text
z_candidate[i+1] = HeunStep(z[i], target_prompt, t_i, t_{i+1}).
```

For a configured latent-projection stage, the accepted endpoint is

```text
z[i+1] = M * z_candidate[i+1] + (1 - M) * z_src[i+1],
```

where `M` is broadcast from one scalar per packed image token to all latent
channels. `M=1` retains the target update and `M=0` restores the source
trajectory. The first implementation uses the oracle binary mask.

Projection is applied after the complete Heun update. No inversion midpoint is
used: the reverse numerical midpoint is not guaranteed to be the denoising
direction's source midpoint.

## Source-Trajectory Capture

The existing inversion path stores only interval-average source velocity in
`info["inv_noise"]`. Latent projection requires complete endpoint states.

The inversion sampler will accept an opt-in `record_source_latents` flag. When
enabled, it stores exactly `N+1` detached source states in denoising order:

- the encoded source image at index `N`;
- each inversion endpoint at its corresponding denoising schedule index;
- the final inversion latent at index `0`.

The sampler must validate that every index from `0` through `N` is present.
The default flag is false so legacy runs do not retain extra tensors.

## Configuration Model

Each control stage gains a `latent_projection` field with two allowed values:

```text
none
source_outside_mask
```

The default is `none`. `source_outside_mask` requires a configured mask source
and a recorded source trajectory. Existing `image_kv` and `it_gate` operations
remain independent. The runtime trace records the resolved latent operation
for every step.

Two locked plans will be provided:

### Stage 2 Projection

- steps 0-1: existing source-all image-KV initialization;
- steps 2-8: oracle source-outside latent projection;
- step 9: no control;
- steps 10-13: existing source-outside-mask image-KV injection;
- step 14: no control.

This plan differs from `oracle_fys_control` by adding state projection during
Stage 2. It tests whether preventing early outside-region drift improves the
existing three-stage procedure.

### Extended Projection

- steps 0-1: existing source-all image-KV initialization;
- steps 2-14: oracle source-outside latent projection;
- no Stage 3 image-KV injection.

This is the stronger state-control baseline. It tests what the model can do
when non-target latent state is restored throughout the remainder of
denoising.

## Implementation Boundaries

Add a focused latent helper that:

- validates target/source latent shape equality;
- validates one mask value per image token;
- moves and casts the source state and mask to the target tensor;
- computes the projection without mutating inputs.

The denoising sampler invokes this helper only after its existing Heun update
and only when the resolved stage requests projection. The source endpoint must
be `source_latents[i + 1]` for denoising step `i`.

The edit entry point enables source-state recording only when the resolved
control plan contains latent projection. Existing command-line and runner
interfaces remain unchanged; experiments continue to be selected by JSON
control plans.

## Diagnostics

For every projected step, record:

- step index and source-latent index;
- current and next timestep;
- mask area ratio;
- mean absolute outside-mask error before projection;
- mean absolute outside-mask error after projection.

For a binary mask, the post-projection outside error against the selected
source endpoint must be zero up to tensor precision. Diagnostics are written
with the existing resolved plan and control trace.

## Verification

Tests must be written before implementation and cover:

1. Inversion records `N+1` source states in denoising order.
2. Recording is opt-in and does not change the inversion output.
3. An all-zero mask returns the source endpoint.
4. An all-one mask returns the target candidate.
5. Mixed masks broadcast across latent channels correctly.
6. Shape and source-index errors fail explicitly.
7. Projection is active only on configured steps.
8. Denoising step `i` uses source endpoint `i+1`.
9. Legacy plans retain byte-for-byte control decisions and sampler behavior.
10. The existing attention-control and schedule regression suites still pass.

## Pilot Protocol

Run seed 0 first because the current inversion/denoising path is deterministic.
Use four representative cases:

- `real_0006`: head to alien;
- `real_0010`: head to dragon;
- `real_0011`: hair to curly hair;
- `real_0001`: head to cat.

Compare both projection plans with `oracle_fys_control` using:

- local edit success;
- outside-mask SSIM and LPIPS;
- overall visual quality;
- representative visual comparisons;
- per-step projection diagnostics.

Do not expand to all 12 cases until the pilot shows that projection materially
changes the semantic/preservation trade-off. A null result remains useful: it
would show that strict source-state restoration alone does not resolve target
semantic generation under the fixed oracle mask.

