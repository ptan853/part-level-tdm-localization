# Same-State Inversion Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a diagnostic experiment that records same-state source/target velocity differences and separate part/edit token attention maps during source inversion without changing the original FYS trajectory or generation.

**Architecture:** Add one optional, default-disabled inversion observer callback to the existing sampler. Implement the model-dependent probe and map serialization in a focused FLUX module, wire it into `edit.py` behind explicit CLI flags, and add a dedicated dry-run/execute runner for the two locked cases.

**Tech Stack:** Python 3.10+, PyTorch, NumPy, PIL, Matplotlib, existing FLUX/FYS modules, unittest/pytest.

## Global Constraints

- The locked smoke cases are `real_0006` and `real_0010`, seed 0, 15 steps.
- The target probe and source prediction must use the identical main-step `x_t` and timestep.
- Only the existing source prediction updates inversion; the target probe prediction is discarded.
- Part and edit attention must remain separate and use the true joint-attention softmax denominator.
- The diagnostic must not alter original FYS-TDM, attention-gated, oracle, or default `edit.py` behavior.
- Diagnostic outputs use a new result root and never overwrite prior results.
- The first experiment records main solver states only, not midpoint maps.

---

### Task 1: Add a default-disabled inversion observer hook

**Files:**
- Modify: `core/third_party/FollowYourShape/src/flux/sampling.py:198-323`
- Create: `tests/test_inversion_step_observer.py`

**Interfaces:**
- Produces: `InversionStepObserver = Callable[..., None]`
- Produces: optional `step_observer` argument on `denoise(...)`
- Callback keyword inputs: `step_index`, `img`, `img_ids`, `timestep`, `source_pred`, `guidance_vec`

- [ ] **Step 1: Write a failing unit test for observer state identity and call count**

Use a deterministic fake model and two-step schedule. Assert that the observer receives the exact pre-update `img`, matching `timestep`, and source prediction once per inversion main step. Also call `denoise` without an observer and assert the output matches the observer-enabled output.

```python
observed = []

def observer(**event):
    observed.append({key: value.clone() if torch.is_tensor(value) else value for key, value in event.items()})

z_plain, _ = sampling.denoise(fake_model, **inputs, inverse=True, step_observer=None)
z_probe, _ = sampling.denoise(fake_model, **inputs, inverse=True, step_observer=observer)

torch.testing.assert_close(z_plain, z_probe)
self.assertEqual(len(observed), len(timesteps) - 1)
self.assertEqual(observed[0]["step_index"], 0)
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `pytest -q tests/test_inversion_step_observer.py`

Expected: failure because `denoise` does not accept `step_observer`.

- [ ] **Step 3: Add the minimal callback invocation**

Add the optional parameter and invoke it only after the main source prediction and only when `inverse=True`:

```python
if inverse and step_observer is not None:
    step_observer(
        step_index=i,
        img=img,
        img_ids=img_ids,
        timestep=t_vec,
        source_pred=pred,
        guidance_vec=guidance_vec,
    )
```

Do not mutate `img`, `pred`, `info`, or solver state in the callback path.

- [ ] **Step 4: Run focused and existing tests**

Run: `pytest -q tests/test_inversion_step_observer.py tests/test_attention_gated_tdm_mask.py`

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add core/third_party/FollowYourShape/src/flux/sampling.py tests/test_inversion_step_observer.py
git commit -m "feat: add optional inversion step observer"
```

---

### Task 2: Implement same-state velocity and named-token attention collection

**Files:**
- Create: `core/third_party/FollowYourShape/src/flux/same_state_probe.py`
- Create: `tests/test_same_state_probe.py`

**Interfaces:**
- Produces: `compute_velocity_delta(source_pred: Tensor, target_pred: Tensor) -> np.ndarray`
- Produces: `aggregate_step_maps(step_maps: list[np.ndarray]) -> np.ndarray`
- Produces: `process_signal_map(step_maps, sigma=0.7) -> dict[str, np.ndarray | float]`
- Produces: `NamedSingleBlockAttentionProbe(model, token_groups, txt_len, layer_ids)`
- Produces: `SameStateInversionProbe(...)`, callable with Task 1 observer keywords

- [ ] **Step 1: Write failing tests for velocity delta and temporal aggregation**

```python
source = torch.tensor([[[0.0, 0.0], [1.0, 1.0]]])
target = torch.tensor([[[3.0, 4.0], [1.0, 1.0]]])
np.testing.assert_allclose(compute_velocity_delta(source, target), np.array([5.0, 0.0]))

aggregate = aggregate_step_maps([
    np.array([[0.0, 2.0]], dtype=np.float32),
    np.array([[3.0, 0.0]], dtype=np.float32),
])
np.testing.assert_allclose(aggregate, np.array([[0.5, 0.5]], dtype=np.float32))
```

The aggregation expectation follows independent `[0,1]` normalization of each step followed by an unweighted mean.

- [ ] **Step 2: Run the tests and verify failure**

Run: `pytest -q tests/test_same_state_probe.py`

Expected: import failure because the module does not exist.

- [ ] **Step 3: Implement pure map functions**

Implement velocity norm over the channel dimension, finite-value validation, independent per-step normalization using `normalize01`, mean aggregation, Gaussian smoothing using `smooth_map`, and binary conversion using `otsu_threshold`.

- [ ] **Step 4: Add a named attention collector**

Compute Q/K once per selected single-stream block, preserve softmax over every joint token, then extract each named token group:

```python
attn = torch.softmax(logits, dim=-1)
for name, indices in self.token_groups.items():
    scores = attn[:, :, :, indices].sum(dim=-1).mean(dim=1)[0]
    self.current_records[name].append(scores.detach().cpu())
```

`finish_step()` must average layer records separately for `part` and `edit` and append exactly one map per main inversion step.

- [ ] **Step 5: Implement the callable same-state probe**

The callback evaluates target conditioning on the observer-provided `img`, `img_ids`, and `timestep`, with the same guidance vector as the source forward:

```python
target_pred, _ = self.model(
    img=img,
    img_ids=img_ids,
    txt=self.target_txt,
    txt_ids=self.target_txt_ids,
    y=self.target_vec,
    timesteps=timestep,
    guidance=guidance_vec,
    info=probe_info,
)
```

Record the delta before returning. Do not return a replacement prediction.

- [ ] **Step 6: Test named groups, shape validation, and empty-record errors**

Use fake recorded tensors to verify separate part/edit aggregation, expected patch shape, finite values, and explicit errors when a token group or step sequence is empty.

- [ ] **Step 7: Run focused tests and commit**

Run: `pytest -q tests/test_same_state_probe.py tests/test_inversion_step_observer.py`

Expected: all pass.

```bash
git add core/third_party/FollowYourShape/src/flux/same_state_probe.py tests/test_same_state_probe.py
git commit -m "feat: collect same-state inversion diagnostics"
```

---

### Task 3: Serialize per-step and aggregate diagnostic artifacts

**Files:**
- Modify: `core/third_party/FollowYourShape/src/flux/same_state_probe.py`
- Modify: `tests/test_same_state_probe.py`

**Interfaces:**
- Produces: `SameStateInversionProbe.finalize(output_dir: Path, metadata: dict) -> dict`
- Writes `steps/`, `aggregate/`, and `probe_metadata.json`

- [ ] **Step 1: Write a failing serialization test in a temporary directory**

Populate two synthetic steps and assert exact files for velocity delta, part attention, edit attention, aggregate raw/smoothed/binary arrays, PNG visualizations, and metadata.

```python
probe.finalize(tmp_path, {"case_uid": "case_test"})
self.assertTrue((tmp_path / "steps" / "step_00_velocity_delta.npy").exists())
self.assertTrue((tmp_path / "aggregate" / "part_attention_binary.npy").exists())
metadata = json.loads((tmp_path / "probe_metadata.json").read_text())
self.assertEqual(metadata["recorded_step_indices"], [0, 1])
```

- [ ] **Step 2: Run the test and verify failure**

Run: `pytest -q tests/test_same_state_probe.py -k serialize`

Expected: failure because `finalize` is absent.

- [ ] **Step 3: Implement deterministic serialization**

Use zero-padded step names, `np.float32` soft arrays, `np.uint8` binary arrays, and `plt.imsave` only for visual PNGs. Metadata must include per-step timestep values, token indices, layers, normalization, sigma, Otsu thresholds, map shape, and a note that the masks did not control generation.

- [ ] **Step 4: Run tests and commit**

Run: `pytest -q tests/test_same_state_probe.py`

Expected: all pass.

```bash
git add core/third_party/FollowYourShape/src/flux/same_state_probe.py tests/test_same_state_probe.py
git commit -m "feat: save same-state probe artifacts"
```

---

### Task 4: Wire the probe into `edit.py` behind explicit flags

**Files:**
- Modify: `core/third_party/FollowYourShape/src/edit.py:1-450`
- Modify: `tests/test_flux_attention_prompt_validation.py`

**Interfaces:**
- Adds CLI flags: `--same_state_probe_dir`, `--probe_part`, `--probe_edit`, `--probe_layers`
- Consumes: `SameStateInversionProbe` and Task 1 `step_observer`

- [ ] **Step 1: Write failing command-contract tests**

Extend command tests to assert the diagnostic command contains all probe arguments only when the probe is enabled, and default FYS commands contain none of them.

- [ ] **Step 2: Run the focused test and verify failure**

Run: `pytest -q tests/test_flux_attention_prompt_validation.py`

Expected: failure because probe flags are not supported.

- [ ] **Step 3: Add CLI validation and probe construction**

When `--same_state_probe_dir` is present:

1. require non-empty `--probe_part` and `--probe_edit`;
2. select target-prompt indices separately with token modes `part` and `edit`;
3. instantiate the probe after source/target conditioning is prepared;
4. pass it as `step_observer` only to source inversion;
5. close hooks and finalize artifacts immediately after inversion;
6. continue unchanged through original `denoise_with_TDM` and image decoding.

Use `try/finally` around inversion so hooks are removed on model failure.

- [ ] **Step 4: Confirm probe target guidance equals source inversion guidance**

The probe must consume the callback's `guidance_vec`; do not substitute target-denoising guidance `2.0`. This keeps prompt conditioning as the only changed forward input.

- [ ] **Step 5: Run tests and commit**

Run: `pytest -q tests/test_flux_attention_prompt_validation.py tests/test_inversion_step_observer.py tests/test_same_state_probe.py`

Expected: all pass.

```bash
git add core/third_party/FollowYourShape/src/edit.py tests/test_flux_attention_prompt_validation.py
git commit -m "feat: expose same-state inversion probe"
```

---

### Task 5: Add the locked two-case runner

**Files:**
- Create: `core/scripts/run_same_state_inversion_probe.py`
- Create: `tests/test_run_same_state_inversion_probe.py`
- Modify: `core/scripts/README.md`

**Interfaces:**
- CLI defaults: manifest `pilot_12_manifest.json`, seed `0`, 15 steps, layers `28..37`
- Requires explicit repeatable `--case-uid`; documented smoke command supplies `real_0006` and `real_0010`
- Dry-run by default; `--execute` launches `edit.py`

- [ ] **Step 1: Write failing runner tests**

Assert that selecting the two case IDs creates two commands, uses separate output directories, passes part/edit terms and probe layers, writes no files during an ordinary dry run, and includes `--execute` behavior behind an explicit flag.

- [ ] **Step 2: Run and verify failure**

Run: `pytest -q tests/test_run_same_state_inversion_probe.py`

Expected: import failure because the runner does not exist.

- [ ] **Step 3: Implement the runner using existing orchestration patterns**

Use the same manifest/path/log/config conventions as `run_fys_pilot.py`. Default output root:

```text
core/results/same_state_inversion_probe
```

The exact smoke command is:

```bash
python core/scripts/run_same_state_inversion_probe.py \
  --case-uid real_0006 \
  --case-uid real_0010 \
  --seed 0 \
  --execute
```

- [ ] **Step 4: Document outputs and dry-run/execute commands**

Add a concise section to `core/scripts/README.md` explaining that this is localization diagnostics, not a new editing method, and that `img_0.jpg` remains the original FYS output.

- [ ] **Step 5: Run tests and commit**

Run: `pytest -q tests/test_run_same_state_inversion_probe.py tests/test_flux_attention_prompt_validation.py`

Expected: all pass.

```bash
git add core/scripts/run_same_state_inversion_probe.py core/scripts/README.md tests/test_run_same_state_inversion_probe.py
git commit -m "feat: add same-state probe runner"
```

---

### Task 6: Regression verification and GPU handoff

**Files:**
- Modify only if verification reveals an issue in files from Tasks 1-5.

**Interfaces:**
- Produces a dry-run command suitable for the existing GPU environment.

- [ ] **Step 1: Run static and unit verification**

```bash
python -m compileall -q core/scripts core/third_party/FollowYourShape/src/flux
pytest -q
git diff --check
```

Expected: compilation succeeds, all tests pass, and `git diff --check` emits no output.

- [ ] **Step 2: Inspect the dry-run command**

```bash
python core/scripts/run_same_state_inversion_probe.py \
  --case-uid real_0006 \
  --case-uid real_0010 \
  --seed 0
```

Expected: exactly two commands, distinct result paths, correct source/target prompts, and explicit part/edit probe arguments.

- [ ] **Step 3: Verify original runner remains unchanged**

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --limit 1
```

Expected: the command contains no same-state probe flags and points to the existing FYS output root.

- [ ] **Step 4: Review branch diff**

Confirm there are no tracked model caches, generated images, `__pycache__`, or existing result modifications. Confirm the default sampler path differs only by a `None` check.

- [ ] **Step 5: Commit any final documentation-only corrections**

```bash
git add docs/superpowers/specs/2026-08-26-same-state-inversion-probe-design.md docs/superpowers/plans/2026-08-26-same-state-inversion-probe.md
git commit -m "docs: finalize same-state probe workflow"
```
