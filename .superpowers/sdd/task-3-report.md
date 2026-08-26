# Task 3 Report: Serialize Per-Step and Aggregate Diagnostic Artifacts

Date: 2026-08-26

## Scope completed

Implemented deterministic finalization for the same-state inversion probe in the FollowYourShape submodule and added parent-repo coverage for the serialization contract.

Production file:
- `core/third_party/FollowYourShape/src/flux/same_state_probe.py`

Parent test file:
- `tests/test_same_state_probe.py`

## What was implemented

### Finalization and artifact writing

- Added `SameStateInversionProbe.finalize(output_dir: Path, metadata: dict) -> dict`
- Writes:
  - `steps/`
  - `aggregate/`
  - `probe_metadata.json`

### Per-step artifacts

For each recorded step, `finalize` now writes:

- `step_XX_velocity_delta.npy`
- `step_XX_velocity_delta.png`
- `step_XX_part_attention.npy`
- `step_XX_part_attention.png`
- `step_XX_edit_attention.npy`
- `step_XX_edit_attention.png`

### Aggregate artifacts

For each signal, `finalize` now writes:

- `*_raw.npy`
- `*_smoothed.npy`
- `*_binary.npy`
- `*_raw.png`
- `*_smoothed.png`
- `*_binary.png`

Signals:

- `velocity_delta`
- `part_attention`
- `edit_attention`

### Metadata

The generated `probe_metadata.json` records:

- `recorded_step_indices`
- `recorded_step_timesteps`
- `part_token_indices`
- `edit_token_indices`
- `layer_ids`
- `normalization`
- `smoothing_sigma`
- `threshold_method`
- per-signal Otsu thresholds
- `map_shape`
- a note that the diagnostic masks did not control generation or injection

## TDD record

1. Added a focused serialization test to `tests/test_same_state_probe.py`.
2. Ran the red check:
   - `./.venv/bin/pytest -q tests/test_same_state_probe.py -k serialize`
   - initial failure: `AttributeError: 'SameStateInversionProbe' object has no attribute 'finalize'`
3. Implemented deterministic serialization in `core/third_party/FollowYourShape/src/flux/same_state_probe.py`.
4. Re-ran the focused test and then the full file to green.

## Test evidence

Focused serialization test:

```bash
./.venv/bin/pytest -q tests/test_same_state_probe.py -k serialize
```

Result:
- `1 passed, 9 deselected`

Full same-state probe test file:

```bash
./.venv/bin/pytest -q tests/test_same_state_probe.py
```

Result:
- `10 passed`

## Commits

Submodule commit:
- `3e6bc8e` — `feat: save same-state probe artifacts`

## Concerns

- The repo-local submodule still has generated `__pycache__` files from the test run, but they were not staged or committed.
- This task intentionally does not wire the probe into `edit.py` or add runner logic.
