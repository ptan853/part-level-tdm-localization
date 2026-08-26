# Same-State Inversion Probe Design

## Objective

Test whether source/target prompt sensitivity measured at the same source-inversion latent state provides a cleaner part-localization signal than the original Follow-Your-Shape trajectory difference.

The locked smoke experiment uses two existing pilot cases at seed 0:

- `real_0006`: `head -> alien`
- `real_0010`: `head -> dragon`

This experiment is diagnostic only. Its masks do not control generation in this phase.

## Motivation

The current FYS-TDM compares a cached source-inversion velocity with a velocity evaluated on a target-denoising state. Its magnitude therefore mixes prompt sensitivity with source/target trajectory-state divergence.

The proposed signal evaluates both prompts at the same latent state and timestep:

\[
v_s = f(x_t, t, c_s), \qquad v_t = f(x_t, t, c_t)
\]

For image token `i`, the per-step localization score is:

\[
D_t(i) = \lVert v_t(i) - v_s(i) \rVert_2
\]

Since `x_t` and `t` are fixed, the prompt is the only changed model input.

## Data Flow

At every main source-inversion step:

1. Run the existing source-prompt forward pass and obtain `v_source`.
2. Before updating the latent, evaluate the target prompt on the same `x_t` and `t`.
3. Record the per-image-token norm of `v_target - v_source`.
4. During the target-prompt probe, record true softmax attention mass from image-token queries to:
   - the part token (`head`), and
   - the edit token (`alien` or `dragon`).
5. Discard the target velocity. Update inversion only with the existing source velocity and existing midpoint calculation.

Only the main solver state is probed for the first experiment. Midpoint maps are not mixed into the primary per-step sequence, which keeps one interpretable map per inversion step. A later ablation may record midpoint states separately.

## Architecture

### Optional inversion observer

Extend the existing `denoise` function with an optional observer interface. The default is `None`, so existing FYS, attention-gated, and oracle executions follow the unchanged code path.

The observer receives the current source state, timestep, source prediction, and step index. It performs the target-prompt forward pass and records diagnostics without returning a state update.

### Attention collection

Reuse the existing late single-stream attention definition:

- image tokens are queries;
- all joint text/image tokens remain in the softmax denominator;
- only selected target text-token columns are summed;
- scores are averaged over attention heads and the fixed layer set `28..37`.

Part and edit attention are retained as separate maps rather than merged.

### Experiment entry point

Add a dedicated runner and worker for this diagnostic. They load the frozen manifest, select the two case IDs, run seed 0, and write outputs under a new result root. Existing run scripts and result directories are not reused or overwritten.

## Outputs

For each case:

```text
core/results/same_state_inversion_probe/<case_uid>/seed_000/
  run_config.json
  run.log
  generated.png
  steps/
    step_00_velocity_delta.npy
    step_00_velocity_delta.png
    step_00_part_attention.npy
    step_00_part_attention.png
    step_00_edit_attention.npy
    step_00_edit_attention.png
    ...
  aggregate/
    velocity_delta_raw.npy
    velocity_delta_smoothed.npy
    velocity_delta_binary.npy
    part_attention_raw.npy
    part_attention_smoothed.npy
    part_attention_binary.npy
    edit_attention_raw.npy
    edit_attention_smoothed.npy
    edit_attention_binary.npy
  step_overview.png
```

`run_config.json` records prompts, part/edit strings, token indices, layer IDs, timestep values, normalization, smoothing, thresholding, and generation parameters.

## Map Processing

Each per-step map is normalized independently to `[0, 1]` before temporal aggregation so timestep-scale differences do not dominate. The primary aggregate is an unweighted mean across all recorded inversion steps.

For each signal:

1. save the raw aggregate;
2. apply Gaussian smoothing with the existing fixed sigma;
3. apply Otsu thresholding to produce a diagnostic binary mask.

The `.npy` values are the authoritative analytical outputs; PNG files are visualizations.

## Generated Image

After inversion, run the existing original FYS target-denoising path. The diagnostic maps are not passed as `edit_map` and do not alter injection. The generated image provides qualitative context for each localization sequence.

Because the current pipeline is deterministic for a fixed source and configuration, the probe-enabled generated image must match the corresponding original FYS output within the repository's numerical tolerance.

## Validation

Automated tests must establish:

1. Existing callers that omit the observer retain the original behavior.
2. Probe on/off produces an identical or numerically all-close inverted latent `z`.
3. Source and target predictions used by a delta map share the same latent tensor and timestep.
4. Part and edit token indices are selected separately and recorded.
5. Saved arrays have the expected number of steps, `32 x 32` spatial shape for 512-pixel inputs, finite values, and stable filenames.
6. Dry-run command construction selects only the requested cases and writes to the new output root.
7. The full existing test suite still passes.

## Non-Goals

- Do not use the new velocity-difference map for injection or latent blending.
- Do not tune thresholds, layers, timesteps, or prompts per case.
- Do not change the original FYS-TDM definition or overwrite prior results.
- Do not treat binary masks as segmentation ground truth; evaluate them against GT masks before considering a control experiment.

