# Inversion Step Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the same-state inversion notebook aggregate only inversion states corresponding to the configured FYS denoising control interval.

**Architecture:** Add a small pure step-mapping helper in the test suite and use the reverse index mapping in `06_inspect_same_state_inversion_probe.ipynb`. The notebook will keep the existing normalization, mean aggregation, smoothing, and Otsu thresholding, while exposing both the selected denoising steps and their inversion counterparts.

**Tech Stack:** Python, pytest, Jupyter notebook JSON, NumPy, Matplotlib.

## Global Constraints

- Do not rerun model inference or modify existing result artifacts.
- Preserve the current all-step diagnostic behavior as an explicit comparison option.
- Use the actual configured `num_steps`, `front`, `inject`, and `tail_pad` values.
- Prefer timestep/index alignment documentation over silently assuming equal inversion and denoising indices.

---

### Task 1: Add and test reverse step mapping

**Files:**
- Create: `tests/test_inversion_step_alignment.py`
- Modify: `core/notebooks/06_inspect_same_state_inversion_probe.ipynb`

**Interfaces:**
- Test helper contract: `reverse_step_indices(denoise_steps: list[int], num_steps: int) -> list[int]` returns `[num_steps - 1 - step for step in denoise_steps]` in denoising order.
- Notebook contract: selected inversion steps are computed from the denoising interval and displayed before aggregation.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_reverse_step_indices_maps_fys_interval():
    namespace = {}
    source = Path("core/notebooks/06_inspect_same_state_inversion_probe.ipynb").read_text()
    assert "reverse_step_indices" in source

    assert [14 - step for step in range(2, 9)] == [12, 11, 10, 9, 8, 7, 6]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest -q tests/test_inversion_step_alignment.py`

Expected: FAIL because the notebook does not yet define the reverse mapping.

- [ ] **Step 3: Update the notebook with the minimal mapping and aggregation change**

Add a configuration cell containing:

```python
NUM_STEPS = int(metadata.get("num_steps", 15))
FRONT = int(config.get("front", metadata.get("front", 2)))
INJECT = int(config.get("inject", metadata.get("inject", 4)))
TAIL_PAD = int(config.get("tail_pad", metadata.get("tail_pad", 1)))

DENoise_RECORD_END = NUM_STEPS - INJECT - 2 - TAIL_PAD
denoise_steps = list(range(FRONT, DENoise_RECORD_END + 1))
inversion_steps = [NUM_STEPS - 1 - step for step in denoise_steps]
selected_inversion_steps = sorted(inversion_steps)

display(Markdown(
    "### Step alignment\n"
    f"Denoising control steps: `{denoise_steps}`\n\n"
    f"Corresponding inversion steps: `{inversion_steps}`\n\n"
    f"Aggregated inversion steps: `{selected_inversion_steps}`"
))
```

Use `selected_inversion_steps` when loading the step maps for the aligned aggregate. Keep a second explicit `all_inversion_steps` path for comparison, without making it the default.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest -q tests/test_inversion_step_alignment.py`

Expected: PASS.

- [ ] **Step 5: Validate the notebook statically**

Run: `python -m json.tool core/notebooks/06_inspect_same_state_inversion_probe.ipynb >/dev/null`

Expected: exit code 0.

- [ ] **Step 6: Review the diff**

Run: `git diff --check`

Expected: no whitespace errors; existing result directories remain unchanged.
