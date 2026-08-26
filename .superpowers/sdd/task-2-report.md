# Task 2 Report: Same-State Velocity and Named-Token Attention Collection

Date: 2026-08-26

## Scope completed

Implemented the focused probe module requested for Task 2 in the FollowYourShape submodule and added parent-repo tests.

Production file:
- `core/third_party/FollowYourShape/src/flux/same_state_probe.py`

Parent test file:
- `tests/test_same_state_probe.py`

## What was implemented

### Pure signal functions

- `compute_velocity_delta(source_pred, target_pred)`
  - validates matching `[batch, tokens, channels]` shapes
  - rejects non-finite inputs
  - computes per-token `L2` norm over the channel dimension
  - returns the batch-0 token map as `np.float32`

- `aggregate_step_maps(step_maps)`
  - rejects empty input
  - validates consistent shapes and finite values
  - normalizes each step independently with `normalize01`
  - averages the normalized maps with an unweighted mean

- `process_signal_map(step_maps, sigma=0.7)`
  - aggregates via `aggregate_step_maps`
  - smooths with existing `smooth_map`
  - thresholds with existing `otsu_threshold`
  - returns `raw`, `smoothed`, `binary`, and `threshold`

### Named attention probe

- `NamedSingleBlockAttentionProbe(model, token_groups, txt_len, layer_ids)`
  - registers forward-pre-hooks only on selected single-stream blocks
  - recomputes Q/K once inside the hook
  - preserves the softmax over all joint tokens
  - sums selected token columns separately for each named group
  - stores per-layer records for the current step
  - `finish_step()` averages layer records independently for each group and appends exactly one map per step
  - rejects empty token groups and empty step records explicitly

### Same-state inversion observer

- `SameStateInversionProbe(...)`
  - callable with Task 1 observer keywords
  - runs the target-conditioning forward on the observer-provided same `img`, `img_ids`, `timestep`, and `guidance_vec`
  - records velocity delta without returning a replacement prediction
  - invokes named attention collection through a fresh `probe_info` dict with `record_attention`
  - stores `step_indices` and `velocity_step_maps`

## TDD record

1. Added `tests/test_same_state_probe.py`.
2. Ran focused red test:
   - `.venv/bin/python -m pytest -q tests/test_same_state_probe.py`
   - initial failure: missing `flux/same_state_probe.py`
3. Implemented `flux/same_state_probe.py`.
4. Fixed one test-fixture bug in the dummy normalization module.
5. Expanded Task 2 coverage for shape-preserving finite processing and empty-record errors.
6. Re-ran focused tests and full suite to green.

## Test evidence

Focused Task 2 tests:

```bash
.venv/bin/python -m pytest -q tests/test_same_state_probe.py tests/test_inversion_step_observer.py
```

Result:
- `8 passed in 1.01s`

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Result:
- `18 passed, 12 subtests passed in 1.48s`

## Commits

Submodule commit:
- `5a2337f` — `feat: collect same-state inversion diagnostics`

Parent commit:
- `1bab654` — `test: cover same-state probe diagnostics`

## Concerns

- The repo-local `.venv` did not include `pytest`, `torch`, or `einops`, so I installed the minimal set needed to execute the required tests locally. No dependency manifest files were changed as part of Task 2.
- This task intentionally does not wire the probe into `edit.py`, serialization, runners, or docs.

## Review-fix addendum

Root cause addressed:
- `SameStateInversionProbe` was forwarding `info={"record_attention": ...}` into the real Flux path.
- `Flux.forward()` mutates `info["type"]` and `info["id"]`, and `SingleStreamBlock.forward()` directly dereferences `info["inject"]`.
- That meant the old probe payload crashed with `KeyError: 'inject'` before any same-state comparison could complete.

Fix implemented:
- Added a fresh non-injecting probe-info builder in `core/third_party/FollowYourShape/src/flux/same_state_probe.py`.
- The payload now matches the non-injecting sampling contract used by the actual model path:
  - `feature: {}`
  - `map: {}`
  - `edit_map: None`
  - `inject: False`
  - `inverse: False`
  - `second_order: False`
  - `record_attention: <bool>`
  - `t: float(timestep[0])`
- The dict is rebuilt per observer call, so the probe does not trigger feature injection and does not carry mutable state across steps.

Regression coverage added:
- `tests/test_same_state_probe.py`
  - proves the actual Flux single-block path fails with the old incomplete payload
  - proves `SameStateInversionProbe` now supplies the full non-injecting payload and survives a real Flux forward
- `tests/test_inversion_step_observer.py`
  - drives `sampling.denoise(..., step_observer=SameStateInversionProbe)` through the actual Flux/SingleStreamBlock path
  - verifies identical source/target conditioning produces zero velocity maps after the fix

TDD evidence:

Red:
```bash
.venv/bin/python -m pytest -q tests/test_same_state_probe.py tests/test_inversion_step_observer.py
```
Output:
- `2 failed, 9 passed in 1.07s`
- both failing paths crashed at `core/third_party/FollowYourShape/src/flux/modules/layers.py:253` with `KeyError: 'inject'`

Green:
```bash
.venv/bin/python -m pytest -q tests/test_same_state_probe.py tests/test_inversion_step_observer.py
```
Output:
- `11 passed in 0.98s`

Review-fix submodule commit:
- `3b74d65` — `fix: supply full same-state probe info`
