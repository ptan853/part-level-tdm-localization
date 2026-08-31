# Latent State Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in control operation that directly blends the target denoising endpoint latent with the matching source inversion latent, preserving source state outside a configured mask.

**Architecture:** Source inversion optionally records all schedule-node latent states in denoising order. The existing target Heun update remains unchanged; after a configured step completes, a focused helper computes `M * z_target + (1 - M) * z_source`. JSON control plans select the projection window, while legacy plans default to no latent projection.

**Tech Stack:** Python 3.10, PyTorch 2.1, unittest, FLUX/FollowYourShape sampler, JSON control plans.

## Global Constraints

- Blend latent state `z` directly; do not blend velocity, attention, K/V, or model hidden state.
- Apply projection only after the complete target Heun step.
- Use source endpoint `source_latents[i + 1]` for denoising step `i`.
- The first implementation uses the existing oracle binary mask.
- Existing behavior must remain unchanged when `latent_projection` is omitted or `none`.
- Existing FYS-TDM, attention-control, same-state-probe, and control-plan tests must continue to pass.
- Do not change the legacy command interface; select the operation through a control-plan JSON file.
- FollowYourShape is a Git submodule. Every submodule source change must be committed and pushed on `feature/latent-state-projection` before the parent repository records the new submodule pointer.

---

## File Structure

- Create `core/third_party/FollowYourShape/src/flux/latent_control.py`: pure latent projection and diagnostics.
- Modify `core/third_party/FollowYourShape/src/flux/control_schedule.py`: parse and validate per-stage latent operation.
- Modify `core/third_party/FollowYourShape/src/flux/sampling.py`: record source states and apply projection after Heun updates.
- Modify `core/third_party/FollowYourShape/src/edit.py`: enable source-state recording only for plans that require it.
- Create `core/configs/control_plans/oracle_stage2_latent_projection.json`: Stage 2 projection plus legacy Stage 3 KV injection.
- Create `core/configs/control_plans/oracle_extended_latent_projection.json`: projection from steps 2 through 14 without Stage 3 KV injection.
- Create `tests/test_latent_control.py`: pure projection unit tests.
- Modify `tests/test_control_schedule.py`: schema and locked-plan tests.
- Modify `tests/test_inversion_step_observer.py`: source-state recording and index-alignment tests.
- Modify `tests/test_control_plan_sampling.py`: configured-step projection integration and legacy no-op tests.
- Modify `core/scripts/README.md`: exact pilot commands and artifact contract.

---

### Task 0: Establish the Submodule Feature Branch

**Files:**
- No source files changed

**Interfaces:**
- Produces: clean FollowYourShape branch `feature/latent-state-projection`

- [ ] **Step 1: Verify both repositories are clean**

```bash
git status --short
git -C core/third_party/FollowYourShape status --short
```

Expected: both commands print no changes.

- [ ] **Step 2: Create the isolated submodule branch**

```bash
git -C core/third_party/FollowYourShape switch -c feature/latent-state-projection
```

Expected: the submodule switches from `feature/attention-gated-fys` without changing its current commit.

- [ ] **Step 3: Run the baseline regression suite**

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/irp/bin/python -m unittest tests.test_attention_control tests.test_controlled_attention_integration tests.test_control_plan_sampling tests.test_control_schedule tests.test_run_control_plan -v
```

Expected: 25 tests pass before production changes begin.

---

### Task 1: Pure Latent Projection Operation

**Files:**
- Create: `tests/test_latent_control.py`
- Create: `core/third_party/FollowYourShape/src/flux/latent_control.py`

**Interfaces:**
- Produces: `project_source_outside(target_latent: Tensor, source_latent: Tensor, spatial_mask: Tensor | np.ndarray) -> tuple[Tensor, LatentProjectionMetrics]`
- Produces: immutable `LatentProjectionMetrics(mask_area_ratio: float, outside_mae_before: float, outside_mae_after: float)`

- [ ] **Step 1: Write failing projection tests**

Create tests for all-zero, all-one, mixed-token, non-mutating, shape-mismatch, and mask-length behavior. The core mixed-mask assertion is:

```python
target = torch.tensor([[[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]])
source = torch.tensor([[[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]]])
mask = torch.tensor([1.0, 0.0, 1.0])

actual, metrics = project_source_outside(target, source, mask)

expected = torch.tensor([[[1.0, 2.0], [30.0, 40.0], [5.0, 6.0]]])
torch.testing.assert_close(actual, expected)
self.assertEqual(metrics.outside_mae_after, 0.0)
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/irp/bin/python -m unittest tests.test_latent_control -v
```

Expected: import failure because `flux.latent_control` does not exist.

- [ ] **Step 3: Implement the minimal pure helper**

Implement exact shape validation and broadcast the mask as `[1, image_tokens, 1]`. Cast source and mask to the target tensor's device and dtype. Compute metrics using the weighted outside region; return zero outside errors when the mask contains no outside tokens.

```python
@dataclass(frozen=True)
class LatentProjectionMetrics:
    mask_area_ratio: float
    outside_mae_before: float
    outside_mae_after: float


def project_source_outside(target_latent, source_latent, spatial_mask):
    if target_latent.shape != source_latent.shape:
        raise ValueError("target and source latent shapes must match")
    if target_latent.ndim != 3:
        raise ValueError("latents must have shape [batch, image_tokens, channels]")
    mask = torch.as_tensor(
        spatial_mask,
        device=target_latent.device,
        dtype=target_latent.dtype,
    ).flatten()
    if mask.numel() != target_latent.shape[1]:
        raise ValueError("spatial mask length must match image token count")
    if torch.any((mask < 0) | (mask > 1)):
        raise ValueError("spatial mask values must be in [0, 1]")
    source = source_latent.to(device=target_latent.device, dtype=target_latent.dtype)
    mask_3d = mask.view(1, -1, 1)
    projected = mask_3d * target_latent + (1 - mask_3d) * source
    # Compute and return detached scalar diagnostics without mutating inputs.
```

- [ ] **Step 4: Run the test and verify GREEN**

Run the Task 1 command. Expected: all tests pass.

- [ ] **Step 5: Commit the helper in the submodule, then record it in the parent**

```bash
git -C core/third_party/FollowYourShape add src/flux/latent_control.py
git -C core/third_party/FollowYourShape commit -m "feat: add source-outside latent projection"
git add tests/test_latent_control.py core/third_party/FollowYourShape
git commit -m "feat: add source-outside latent projection"
```

---

### Task 2: Control-Plan Schema

**Files:**
- Modify: `tests/test_control_schedule.py`
- Modify: `core/third_party/FollowYourShape/src/flux/control_schedule.py`
- Create: `core/configs/control_plans/oracle_stage2_latent_projection.json`
- Create: `core/configs/control_plans/oracle_extended_latent_projection.json`

**Interfaces:**
- Produces: `ControlStage.latent_projection: str`
- Produces: `plan_requires_source_latents(plan: ControlPlan | None) -> bool`
- Allowed values: `none`, `source_outside_mask`

- [ ] **Step 1: Write failing schema tests**

Add tests asserting:

```python
stage = ControlPlan.from_dict({
    "name": "projection",
    "num_steps": 15,
    "mask_source": "oracle",
    "stages": [{
        "name": "stage2",
        "start": 2,
        "end": 8,
        "latent_projection": "source_outside_mask",
    }],
}).stages[0]
self.assertEqual(stage.latent_projection, "source_outside_mask")
```

Also assert that an unknown operation is rejected, a spatial projection without `mask_source` is rejected, omitted values resolve to `none`, and `plan_requires_source_latents` is true only when at least one stage enables projection.

- [ ] **Step 2: Run schedule tests and verify RED**

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/irp/bin/python -m unittest tests.test_control_schedule -v
```

Expected: failure because `ControlStage` has no `latent_projection` field.

- [ ] **Step 3: Extend the schema minimally**

Add:

```python
LATENT_PROJECTION_OPERATIONS = {"none", "source_outside_mask"}

@dataclass(frozen=True)
class ControlStage:
    # existing fields
    latent_projection: str = "none"


def plan_requires_source_latents(plan: ControlPlan | None) -> bool:
    return plan is not None and any(
        stage.latent_projection != "none" for stage in plan.stages
    )
```

Parse the field in `from_dict`, validate allowed values, and mark `source_outside_mask` as requiring a mask source.

- [ ] **Step 4: Add the two locked JSON plans**

The Stage 2 plan must configure source-all image KV at steps 0-1, latent projection at steps 2-8, no stage at step 9, source-outside image KV at steps 10-13, and no stage at step 14. The extended plan must configure source-all image KV at steps 0-1 and latent projection at steps 2-14 with no source-outside image KV.

- [ ] **Step 5: Verify schema tests and JSON loading**

Run:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/irp/bin/python -m unittest tests.test_control_schedule -v
```

Expected: all tests pass and both plans load with 15 steps.

- [ ] **Step 6: Commit the schema in the submodule, then record plans and pointer in the parent**

```bash
git -C core/third_party/FollowYourShape add src/flux/control_schedule.py
git -C core/third_party/FollowYourShape commit -m "feat: configure latent projection stages"
git add tests/test_control_schedule.py core/configs/control_plans/oracle_stage2_latent_projection.json core/configs/control_plans/oracle_extended_latent_projection.json core/third_party/FollowYourShape
git commit -m "feat: configure latent projection stages"
```

---

### Task 3: Record Source Inversion States

**Files:**
- Modify: `tests/test_inversion_step_observer.py`
- Modify: `core/third_party/FollowYourShape/src/flux/sampling.py`

**Interfaces:**
- Extends: `denoise(..., record_source_latents: bool = False)`
- Produces when enabled: `info["source_latents"]: dict[int, Tensor]`, keyed in denoising schedule order from `0` through `N`

- [ ] **Step 1: Write failing trajectory-recording tests**

For `timesteps=[1.0, 0.5, 0.0]` with `inverse=True`, assert:

```python
_, info = sampling.denoise(
    fake_model,
    img=initial.clone(),
    img_ids=img_ids,
    txt=txt,
    txt_ids=txt_ids,
    vec=vec,
    timesteps=timesteps,
    inverse=True,
    info={},
    inject_list=[False, False],
    record_source_latents=True,
)
self.assertEqual(sorted(info["source_latents"]), [0, 1, 2])
torch.testing.assert_close(info["source_latents"][2], initial)
torch.testing.assert_close(info["source_latents"][0], final_output)
```

Run a second inversion without recording and assert its final output matches exactly and `source_latents` is absent.

- [ ] **Step 2: Run the recording tests and verify RED**

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/irp/bin/python -m unittest tests.test_inversion_step_observer -v
```

Expected: `denoise()` rejects the new keyword argument.

- [ ] **Step 3: Implement denoising-order state capture**

When inversion begins, let `N = len(timesteps) - 1` after schedule reversal and save the input image at key `N`. After inversion loop iteration `i` updates `img`, save it at key `N - i - 1`. At completion validate keys equal `set(range(N + 1))`. Store detached clones so later denoising cannot mutate reference states.

- [ ] **Step 4: Verify recording tests and legacy equality**

Run the Task 3 command. Expected: all tests pass and recorded/unrecorded final tensors are equal.

- [ ] **Step 5: Commit source-state capture in the submodule and update the parent pointer**

```bash
git -C core/third_party/FollowYourShape add src/flux/sampling.py
git -C core/third_party/FollowYourShape commit -m "feat: record source inversion latent states"
git add tests/test_inversion_step_observer.py core/third_party/FollowYourShape
git commit -m "feat: record source inversion latent states"
```

---

### Task 4: Apply Projection After Target Heun Updates

**Files:**
- Modify: `tests/test_control_plan_sampling.py`
- Modify: `core/third_party/FollowYourShape/src/flux/sampling.py`

**Interfaces:**
- Consumes: `ControlStage.latent_projection`
- Consumes: `info["source_latents"][i + 1]`
- Consumes: `control_spatial_mask`
- Produces: `info["latent_projection_trace"]: list[dict[str, int | float | str]]`

- [ ] **Step 1: Write failing sampler integration tests**

Use a deterministic fake model and a three-step plan. Assert that:

- an enabled step returns mask-inside target candidate values and mask-outside `source_latents[i+1]` values;
- a disabled step returns the unchanged Heun candidate;
- missing source state raises an error naming `i+1`;
- the trace records step, source index, timesteps, mask ratio, and pre/post outside MAE;
- post-projection outside MAE is zero.

- [ ] **Step 2: Run integration tests and verify RED**

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/irp/bin/python -m unittest tests.test_control_plan_sampling -v
```

Expected: projected values do not match because the sampler does not yet call the helper.

- [ ] **Step 3: Apply projection after the existing Heun assignment**

Immediately after the existing expression that assigns the completed Heun update to `img`, resolve the current stage. If it requests `source_outside_mask`, require `info["source_latents"]`, select key `i + 1`, and call `project_source_outside(img, source_latent, control_spatial_mask)`. Replace `img` with the returned projected tensor and append detached scalar diagnostics.

Extend each existing control-trace item with:

```python
"latent_projection": None if stage is None else stage.latent_projection
```

Include `latent_projection_trace` in `control_trace.json`.

- [ ] **Step 4: Verify integration and existing control tests**

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/irp/bin/python -m unittest tests.test_control_plan_sampling tests.test_controlled_attention_integration -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit sampler integration in the submodule and update the parent pointer**

```bash
git -C core/third_party/FollowYourShape add src/flux/sampling.py
git -C core/third_party/FollowYourShape commit -m "feat: project target endpoints onto source trajectory"
git add tests/test_control_plan_sampling.py core/third_party/FollowYourShape
git commit -m "feat: project target endpoints onto source trajectory"
```

---

### Task 5: Wire Opt-In Recording Through Edit Runtime

**Files:**
- Modify: `tests/test_flux_attention_prompt_validation.py`
- Modify: `core/third_party/FollowYourShape/src/edit.py`

**Interfaces:**
- Consumes: `plan_requires_source_latents(control_plan)`
- Passes: `record_source_latents=True` only for a plan containing latent projection

- [ ] **Step 1: Write failing runtime wiring tests**

Patch `denoise` and assert that a latent-projection plan passes:

```python
record_source_latents=True
```

Assert that no plan and the existing attention-control plans pass false or omit the flag, preserving current behavior.

- [ ] **Step 2: Run the wiring test and verify RED**

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/irp/bin/python -m unittest tests.test_flux_attention_prompt_validation -v
```

Expected: the inversion call does not contain the expected flag.

- [ ] **Step 3: Add minimal edit.py wiring**

Import `plan_requires_source_latents` and pass its result to the source inversion `denoise` call. Do not change denoising inputs or CLI arguments.

- [ ] **Step 4: Verify runtime tests**

Run the Task 5 command. Expected: all tests pass.

- [ ] **Step 5: Commit runtime wiring in the submodule and update the parent pointer**

```bash
git -C core/third_party/FollowYourShape add src/edit.py
git -C core/third_party/FollowYourShape commit -m "feat: enable source trajectory capture for projection plans"
git add tests/test_flux_attention_prompt_validation.py core/third_party/FollowYourShape
git commit -m "feat: enable source trajectory capture for projection plans"
```

---

### Task 6: Document and Verify the Pilot Workflow

**Files:**
- Modify: `core/scripts/README.md`

**Interfaces:**
- Uses existing: `core/scripts/run_control_plan.py`
- Produces outputs under isolated plan-name directories in `core/results/control_operations/`

- [ ] **Step 1: Add exact dry-run and pilot commands**

Document both plans and the four-case seed-0 pilot. The initial dry run must be:

```bash
python core/scripts/run_control_plan.py \
  --plan core/configs/control_plans/oracle_stage2_latent_projection.json \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --limit 1
```

The executed pilot repeats the command with `--limit 4 --execute`. Document the extended plan as a separate command and state that it must use a distinct plan name/output directory.

- [ ] **Step 2: Run all focused and regression tests**

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/irp/bin/python -m unittest \
  tests.test_latent_control \
  tests.test_inversion_step_observer \
  tests.test_control_schedule \
  tests.test_control_plan_sampling \
  tests.test_flux_attention_prompt_validation \
  tests.test_attention_control \
  tests.test_controlled_attention_integration \
  tests.test_run_control_plan -v
```

Expected: all tests pass.

- [ ] **Step 3: Run static artifact checks**

```bash
git diff --check
python -m json.tool core/configs/control_plans/oracle_stage2_latent_projection.json >/dev/null
python -m json.tool core/configs/control_plans/oracle_extended_latent_projection.json >/dev/null
```

Expected: all commands exit zero.

- [ ] **Step 4: Run both plans in dry-run mode**

Run each plan with `--seeds 0 --limit 1` and without `--execute`. Expected: each prints one isolated command, writes a distinct run matrix, and does not launch FLUX inference.

- [ ] **Step 5: Commit documentation and final verification state**

```bash
git add core/scripts/README.md
git commit -m "docs: add latent projection pilot workflow"
```

- [ ] **Step 6: Push the submodule branch before the parent branch**

```bash
git -C core/third_party/FollowYourShape push -u origin feature/latent-state-projection
git push -u origin experiment/latent-state-projection
```

Expected: a fresh clone can initialize the exact submodule commit referenced by the parent branch.
