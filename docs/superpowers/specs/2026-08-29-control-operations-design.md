# Configurable Control Operations for Part-Level FLUX Editing

## Objective

Add a separate, configuration-driven experiment path for testing spatial control operations without changing the default Follow-Your-Shape (FYS) workflow or overwriting existing results.

The first controlled experiment uses an oracle mask to isolate the control path from localization quality. It keeps source-prompt inversion and the original late image-KV injection mechanism, while adding an optional Stage 2 gate that restricts changed target-token influence to image queries inside the mask. A second control transfers the current Stage 2 part-token logit field to the edit-token column before softmax, using the part token for spatial grounding and the edit token value for target semantics.

## Compatibility Boundary

The following existing entry points retain their current default behavior:

- `core/scripts/run_fys_pilot.py`
- `core/third_party/FollowYourShape/src/edit.py`
- Existing FYS, oracle-mask, attention-gated TDM, and baseline result directories

The new experiment path does not invoke `edit.py` as a subprocess. It reuses the same FLUX model-loading, prompt-preparation, inversion, decoding, and image-KV injection primitives through a dedicated worker.

New control fields are optional and no-op when absent. This is required so legacy FYS calls through `edit.py` produce the same schedule and attention behavior as before.

When no Stage 2 control is active, single-stream blocks must continue to call the existing fused `scaled_dot_product_attention` path. The explicit-logit path is entered only for selected control steps and layer IDs; this keeps legacy numerical behavior and performance unchanged.

## Architecture

### Experiment runner

`core/scripts/run_control_plan.py` will:

1. Load a frozen case manifest and a JSON control plan.
2. Expand case and seed combinations.
3. Validate output isolation and required mask inputs.
4. Write a command matrix.
5. Invoke `control_plan_worker.py` once per run.

### Per-run worker

`core/scripts/control_plan_worker.py` will:

1. Load FLUX, T5, CLIP, and the autoencoder using existing FYS utilities.
2. Encode the source image.
3. Run the unchanged source-prompt inversion and cache source image K/V features.
4. Prepare target-prompt conditioning and identify target part/edit token indices.
5. Run denoising with a validated per-step control schedule.
6. Decode the edited image and save diagnostics, configuration, and logs.

### Control schedule

`core/third_party/FollowYourShape/src/flux/control_schedule.py` will define immutable stage and per-step control records. A plan maps each denoising step to:

- prompt conditioning (`target` initially; prompt switching remains representable but is out of scope for the first pilot),
- mask source,
- image-KV operation,
- IT gate operation and strength,
- image-KV layer IDs,
- IT gate layer IDs.

Stage ranges are inclusive and expressed in denoising step indices. Plans may leave gaps, which resolve to target-prompt denoising with no control operation. Plans must reject overlaps, invalid ranges, unavailable masks, and circular mask dependencies.

## Control Operations

### Image-KV preservation

The existing FYS operation is retained:

```text
inside mask:  current target-trajectory image K/V
outside mask: cached source-trajectory image K/V
```

The operation is active only on configured denoising steps and configured single-stream block IDs. The legacy default remains layers 20-37 and the existing late injection schedule.

### IT changed-token gate

For image-query rows and selected target text-token columns only, the controller adds a spatial gate bias before softmax:

```text
L'[image_i, token_j] = L[image_i, token_j] + gate_bias(mask_i, strength)
```

The first implementation supports:

- token modes: `edit`, `part`, and `part_edit`,
- mask modes: binary and soft,
- configurable gate strength,
- configurable single-stream block IDs.

Two Stage 2 operations are in scope:

- `spatial_logit_bias`: apply a binary or soft spatial gate to selected token columns,
- `part_to_edit_logit_transfer`: replace or blend the edit-token logits with the current part-token logits.

Text-query rows, unselected text-token columns, and image-key columns are not directly gated. This isolates the intended IT intervention.

For a binary oracle mask, inside-mask logits are unchanged. Outside-mask logits receive a finite negative bias controlled by `it_gate_strength`. A finite bias is preferred over `-inf` so the experiment can measure under- and over-suppression without introducing invalid softmax rows.

The spatial bias follows the same mathematical form as an attention condition scale:

```text
L'[image_i, edit] = L[image_i, edit] + strength * log(epsilon + (1 - epsilon) * M_i)
```

This directly changes only the selected IT logits. The subsequent joint softmax necessarily redistributes probability across the other text and image keys for the same image-query row.

## First Pilot Plans

The paired oracle plans use the same oracle mask, cases, seeds, latent inversion, prompt, guidance, step count, and Stage 3 image-KV operation. The part-to-edit plan is reported as a separate dynamic-control experiment rather than being conflated with the oracle-mask ablation.

### Oracle FYS control

```text
Stage 1: original target denoising behavior
Stage 2: target prompt, no IT gate, no image-KV injection
Stage 3: target prompt, oracle-mask image-KV injection
```

### Oracle Stage 2 IT-gated FYS

```text
Stage 1: unchanged
Stage 2: target prompt, oracle-mask edit-token IT gate, no image-KV injection
Stage 3: unchanged oracle-mask image-KV injection
```

The only intended difference is the Stage 2 IT gate.

### Per-step part-to-edit Stage 2 transfer

```text
Stage 1: unchanged
Stage 2: target prompt, current part-token logits transferred to edit-token IT logits
Stage 3: unchanged image-KV injection schedule and operation
```

For image position `i`, part token `p`, edit token `e`, and transfer strength `lambda`:

```text
L'[image_i, edit_token] = (1 - lambda) * L[image_i, edit_token] + lambda * L[image_i, part_token]
```

The replacement is performed before softmax, so every image-query row remains normalized after the normal attention operation. At `lambda = 1`, the edit token inherits the part token's current spatial matching logits; at `lambda = 0`, behavior is unchanged. When a phrase spans multiple subword tokens, the implementation aggregates the selected part logits by mean and applies the resulting field to every selected edit-token column.

This operation is not a mask estimator and does not use a previously thresholded map. It is a dynamic semantic-routing intervention evaluated separately from the oracle spatial gate.

## Example Plan Schema

```json
{
  "name": "oracle_stage2_edit_gate",
  "num_steps": 15,
  "mask_source": "oracle",
  "stages": [
    {
      "name": "stage1",
      "start": 0,
      "end": 1,
      "prompt": "target",
      "image_kv": "none",
      "it_gate": "none"
    },
    {
      "name": "stage2",
      "start": 2,
      "end": 8,
      "prompt": "target",
      "image_kv": "none",
      "it_gate": "edit",
      "it_gate_strength": 1.0
    },
    {
      "name": "stage3",
      "start": 10,
      "end": 13,
      "prompt": "target",
      "image_kv": "source_outside_mask",
      "it_gate": "none"
    },
    {
      "name": "final",
      "start": 14,
      "end": 14,
      "prompt": "target",
      "image_kv": "none",
      "it_gate": "none"
    }
  ],
  "image_kv_layers": [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37],
  "it_gate_layers": [28, 29, 30, 31, 32, 33, 34, 35, 36, 37]
}
```

Gaps in the stage list mean no control while retaining target-prompt denoising. This preserves the current gap between localization and late injection without inventing an additional stage operation.

## Mask Providers

The control-plan interface will support the following provider names for operations that require an explicit spatial mask:

- `oracle`: load the case GT mask and resize it to the FLUX patch grid,
- `precomputed`: load a saved binary or soft mask,
- `inversion_part_attention`,
- `inversion_edit_attention`,
- `inversion_part_edit_attention`,
- `fys_tdm` for operations that begin only after the TDM exists.

The first spatial-gate pilot implements and validates `oracle`. Other providers can be added behind the same interface. The per-step part-to-edit transfer does not consume a mask provider. A plan must fail before model loading if it requests a mask that is unavailable at the first controlled step.

## Result Isolation and Provenance

The default output path is:

```text
core/results/control_operations/<plan_name>/<case_uid>/seed_<seed>/
```

Every run saves:

- `run_config.json` containing the resolved per-step schedule,
- `run.log`,
- generated image files,
- selected patch-grid mask,
- gate metadata and token indices,
- optional per-step gate diagnostics,
- feature outputs required by the configured image-KV operation.

The runner refuses to reuse a non-empty run directory unless an explicit overwrite option is supplied. Existing FYS result roots are never defaults for control-plan runs.

## Testing Strategy

Implementation follows test-driven development. Required tests include:

1. Legacy schedule equivalence when no control plan is supplied.
2. Inclusive stage boundary resolution and gap handling.
3. Rejection of overlapping or out-of-range stages.
4. Rejection of circular or unavailable mask sources.
5. IT gating changes only image-query rows and selected text-token columns.
6. Binary gate leaves inside-mask logits unchanged and suppresses outside-mask logits.
7. Image-KV selection preserves target K/V inside and source K/V outside.
8. Layer filtering keeps all non-selected layers unchanged.
9. Runner command/config propagation and isolated output paths.
10. Part-to-edit transfer changes only selected edit-token columns for image-query rows and preserves text-query rows.
11. Transfer strength zero is exactly a no-op; strength one copies the mean selected part-token logit field before softmax.
12. Dry-run generation for all first-pilot plans without loading the model.

Focused CPU tests validate tensor shapes and exact interventions. A single-case GPU smoke test validates model integration before the 12-case run.

## Success Criteria

The control implementation is ready for the locked pilot when:

- all legacy and new focused tests pass,
- original dry-run commands remain unchanged without a control plan,
- the oracle and part-to-edit-transfer plans produce complete, non-overlapping run matrices,
- a one-case GPU smoke test completes for each plan,
- the gated plan records the expected edit-token indices and active Stage 2 steps,
- Stage 3 records the intended fixed image-KV mask and the same schedule across each paired comparison.

The scientific comparison will report local-edit success and non-target preservation separately. Improved preservation accompanied by suppressed editing is not considered a successful control result.
