# Stage 2 Attention Control Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add opt-in Stage 2 edit-token attention controls while preserving the byte-identical legacy FYS attention path when no control plan is supplied.

**Architecture:** Pure tensor helpers implement oracle spatial logit bias and per-step part-to-edit logit transfer. `flux.math.attention` keeps the existing fused SDPA call for legacy runs and enters an explicit-logit path only when a selected single-stream block receives an active control record. A separate runner and worker resolve JSON plans, reuse `edit.main`, isolate outputs, and leave existing `run_fys_pilot.py` commands unchanged.

**Tech Stack:** Python 3.10, PyTorch 2.1, NumPy, unittest/pytest-compatible tests, existing FollowYourShape FLUX utilities.

## Global Constraints

- Existing `run_fys_pilot.py` and `edit.py` commands without a control plan must preserve their current schedule, tensor path, and outputs.
- The first strategy applies an OminiControl-style additive pre-softmax bias only to image-query rows and selected edit-token columns.
- The second strategy blends the current part-token logits into selected edit-token columns before softmax; it does not replace post-softmax probabilities.
- Stage 3 image-KV injection remains the existing FYS implementation and is held fixed within paired comparisons.
- New outputs default to `core/results/control_operations/<plan_name>/<case_uid>/seed_<seed>/` and never overwrite existing FYS results.
- All production behavior is introduced test-first.

---

### Task 1: Pure IT Logit Controls

**Files:**
- Create: `core/third_party/FollowYourShape/src/flux/attention_control.py`
- Test: `tests/test_attention_control.py`

**Interfaces:**
- Produces: `AttentionControl` immutable configuration and `apply_attention_control(logits, control) -> Tensor`.
- `logits` shape is `[batch, heads, query_tokens, key_tokens]`.
- Text keys occupy `[0:txt_len]`; image-query rows occupy `[txt_len:]`.

- [ ] **Step 1: Write failing tests for oracle spatial bias**

```python
def test_spatial_bias_changes_only_image_query_edit_columns():
    logits = torch.zeros(1, 2, 6, 6)
    control = AttentionControl(
        operation="spatial_logit_bias",
        txt_len=2,
        edit_token_indices=(1,),
        image_mask=torch.tensor([1.0, 0.0, 1.0, 0.0]),
        strength=1.0,
        epsilon=0.01,
    )
    actual = apply_attention_control(logits, control)
    assert actual[0, 0, 2, 1] == 0
    assert torch.isclose(actual[0, 0, 3, 1], torch.tensor(math.log(0.01)))
    assert torch.equal(actual[:, :, :2], logits[:, :, :2])
    assert torch.equal(actual[:, :, 2:, 0], logits[:, :, 2:, 0])
    assert torch.equal(actual[:, :, 2:, 2:], logits[:, :, 2:, 2:])
```

- [ ] **Step 2: Run the oracle test and verify RED**

Run: `python -m pytest tests/test_attention_control.py::AttentionControlTests::test_spatial_bias_changes_only_image_query_edit_columns -v`

Expected: FAIL because `flux.attention_control` does not exist.

- [ ] **Step 3: Implement the immutable control record, validation, and spatial bias**

```python
@dataclass(frozen=True)
class AttentionControl:
    operation: str
    txt_len: int
    edit_token_indices: tuple[int, ...]
    part_token_indices: tuple[int, ...] = ()
    image_mask: Tensor | None = None
    strength: float = 1.0
    epsilon: float = 1e-4


def apply_attention_control(logits: Tensor, control: AttentionControl) -> Tensor:
    controlled = logits.clone()
    image_rows = slice(control.txt_len, logits.shape[-2])
    if control.operation == "spatial_logit_bias":
        gate = control.image_mask.to(device=logits.device, dtype=logits.dtype)
        bias = control.strength * torch.log(
            control.epsilon + (1.0 - control.epsilon) * gate
        )
        controlled[:, :, image_rows, list(control.edit_token_indices)] += bias.view(1, 1, -1, 1)
        return controlled
    raise ValueError(f"Unsupported attention control operation: {control.operation}")
```

- [ ] **Step 4: Run the oracle test and verify GREEN**

Run: `python -m pytest tests/test_attention_control.py -v`

Expected: PASS.

- [ ] **Step 5: Write failing tests for part-to-edit transfer**

```python
def test_full_transfer_copies_mean_part_logits_to_each_edit_column():
    logits = torch.arange(36, dtype=torch.float32).reshape(1, 1, 6, 6)
    control = AttentionControl(
        operation="part_to_edit_logit_transfer",
        txt_len=3,
        part_token_indices=(0, 1),
        edit_token_indices=(2,),
        strength=1.0,
    )
    actual = apply_attention_control(logits, control)
    expected = logits[:, :, 3:, [0, 1]].mean(dim=-1)
    assert torch.equal(actual[:, :, 3:, 2], expected)
    assert torch.equal(actual[:, :, :3], logits[:, :, :3])
```

- [ ] **Step 6: Run the transfer test and verify RED**

Run: `python -m pytest tests/test_attention_control.py::AttentionControlTests::test_full_transfer_copies_mean_part_logits_to_each_edit_column -v`

Expected: FAIL with unsupported operation.

- [ ] **Step 7: Implement transfer and strength-zero no-op**

```python
if control.operation == "part_to_edit_logit_transfer":
    if control.strength == 0:
        return logits
    part_field = controlled[:, :, image_rows, list(control.part_token_indices)].mean(dim=-1, keepdim=True)
    edit = controlled[:, :, image_rows, list(control.edit_token_indices)]
    controlled[:, :, image_rows, list(control.edit_token_indices)] = (
        (1.0 - control.strength) * edit + control.strength * part_field
    )
    return controlled
```

- [ ] **Step 8: Run all pure-control tests**

Run: `python -m pytest tests/test_attention_control.py -v`

Expected: PASS, including invalid mask length, invalid token index, empty part/edit token set, epsilon range, and strength range tests.

- [ ] **Step 9: Commit Task 1**

```bash
git add tests/test_attention_control.py core/third_party/FollowYourShape/src/flux/attention_control.py
git commit -m "feat: add pure stage two attention controls"
```

### Task 2: Opt-In Controlled Attention Path

**Files:**
- Modify: `core/third_party/FollowYourShape/src/flux/math.py`
- Modify: `core/third_party/FollowYourShape/src/flux/modules/layers.py`
- Test: `tests/test_controlled_attention_integration.py`

**Interfaces:**
- Consumes: `AttentionControl`, `apply_attention_control` from Task 1.
- Produces: `attention(q, k, v, pe, control=None)` with the original fused call when `control is None`.
- `SingleStreamBlock` reads `info.get("attention_control")` only when its `info["id"]` is selected.

- [ ] **Step 1: Write a failing test that legacy attention still calls fused SDPA**

```python
def test_attention_without_control_uses_fused_sdpa(monkeypatch):
    calls = []
    monkeypatch.setattr(torch.nn.functional, "scaled_dot_product_attention", lambda q, k, v: calls.append(True) or v)
    attention(q, k, v, pe, control=None)
    assert calls == [True]
```

- [ ] **Step 2: Run the legacy-path test and verify RED**

Run: `python -m pytest tests/test_controlled_attention_integration.py::test_attention_without_control_uses_fused_sdpa -v`

Expected: FAIL because `attention` does not accept `control`.

- [ ] **Step 3: Add the optional explicit-logit path**

```python
def attention(q, k, v, pe, control=None):
    q, k = apply_rope(q, k, pe)
    if control is None:
        x = torch.nn.functional.scaled_dot_product_attention(q, k, v)
    else:
        logits = torch.matmul(q, k.transpose(-2, -1)) * (q.shape[-1] ** -0.5)
        logits = apply_attention_control(logits, control)
        weights = torch.softmax(logits.float(), dim=-1).to(v.dtype)
        x = torch.matmul(weights, v)
    return rearrange(x, "B H L D -> B L (H D)")
```

- [ ] **Step 4: Run legacy and controlled attention tests**

Run: `python -m pytest tests/test_controlled_attention_integration.py -v`

Expected: PASS; controlled outputs match a hand-computed softmax reference and uncontrolled calls use fused SDPA once.

- [ ] **Step 5: Write a failing layer-selection test**

```python
def test_single_block_passes_control_only_to_selected_layers(monkeypatch):
    info = {"id": 27, "attention_control": control, "attention_control_layers": (28, 29)}
    assert resolve_block_attention_control(info) is None
    info["id"] = 28
    assert resolve_block_attention_control(info) is control
```

- [ ] **Step 6: Implement layer selection and pass control to attention**

```python
def resolve_block_attention_control(info):
    if info is None:
        return None
    if info.get("id") not in info.get("attention_control_layers", ()):
        return None
    return info.get("attention_control")
```

- [ ] **Step 7: Run focused and existing attention tests**

Run: `python -m pytest tests/test_controlled_attention_integration.py tests/test_attention_control.py tests/test_attention_gated_tdm_mask.py tests/test_attention_mask_utils.py -v`

Expected: PASS.

- [ ] **Step 8: Commit Task 2**

```bash
git add tests/test_controlled_attention_integration.py core/third_party/FollowYourShape/src/flux/math.py core/third_party/FollowYourShape/src/flux/modules/layers.py
git commit -m "feat: add opt-in controlled attention path"
```

### Task 3: Validated Control Schedule

**Files:**
- Create: `core/third_party/FollowYourShape/src/flux/control_schedule.py`
- Test: `tests/test_control_schedule.py`

**Interfaces:**
- Produces: `ControlStage`, `ControlPlan`, `load_control_plan(path)`, and `resolve_stage(plan, step) -> ControlStage | None`.
- Stage ranges are inclusive denoising indices.

- [ ] **Step 1: Write failing tests for boundaries, gaps, and overlap rejection**

```python
def test_resolve_stage_uses_inclusive_boundaries_and_allows_gaps():
    plan = ControlPlan.from_dict(VALID_PLAN)
    assert resolve_stage(plan, 2).name == "stage2"
    assert resolve_stage(plan, 8).name == "stage2"
    assert resolve_stage(plan, 9) is None

def test_plan_rejects_overlapping_stages():
    with pytest.raises(ValueError, match="overlap"):
        ControlPlan.from_dict(OVERLAPPING_PLAN)
```

- [ ] **Step 2: Run schedule tests and verify RED**

Run: `python -m pytest tests/test_control_schedule.py -v`

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement strict parsing and resolution**

The parser must reject unknown operations, missing edit/part labels for the selected operation, out-of-range steps/layers, overlap, and explicit-mask operations without a mask source. It must preserve gaps as uncontrolled target denoising.

- [ ] **Step 4: Run schedule tests and verify GREEN**

Run: `python -m pytest tests/test_control_schedule.py -v`

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add tests/test_control_schedule.py core/third_party/FollowYourShape/src/flux/control_schedule.py
git commit -m "feat: validate configurable control schedules"
```

### Task 4: Sampling and Prompt-Token Integration

**Files:**
- Modify: `core/third_party/FollowYourShape/src/flux/sampling.py`
- Modify: `core/third_party/FollowYourShape/src/edit.py`
- Test: `tests/test_control_plan_sampling.py`

**Interfaces:**
- Consumes: resolved `ControlPlan` and selected part/edit T5 token indices.
- Produces: per-step `info["attention_control"]`, `info["attention_control_layers"]`, and diagnostics.

- [ ] **Step 1: Write failing tests for per-step control construction**

```python
def test_oracle_stage_builds_spatial_control_only_inside_configured_window():
    assert build_step_attention_control(plan, step=1, txt_len=512, oracle_mask=mask) is None
    control = build_step_attention_control(plan, step=2, txt_len=512, oracle_mask=mask)
    assert control.operation == "spatial_logit_bias"
    assert control.edit_token_indices == (4, 5)
    assert build_step_attention_control(plan, step=9, txt_len=512, oracle_mask=mask) is None
```

- [ ] **Step 2: Run the sampling test and verify RED**

Run: `python -m pytest tests/test_control_plan_sampling.py -v`

Expected: FAIL because the builder does not exist.

- [ ] **Step 3: Implement step control construction and diagnostics**

At each first- and second-order model call, resolve the same integer denoising step and place the control record in `info`. Save operation, step, layers, part/edit indices, mask source, strength, and epsilon to the per-run metadata. Do not alter `inject_list`, `edit_map`, or Stage 3 image-KV code.

- [ ] **Step 4: Add optional `--control-plan-resolved` support to `edit.py`**

When absent, skip all new plan loading and token selection. When present, select complete target part/edit subtoken spans with the existing `select_target_token_indices`, load the oracle patch-grid mask when requested, and pass the plan to `denoise_with_TDM`.

- [ ] **Step 5: Run sampling, prompt-validation, and legacy tests**

Run: `python -m pytest tests/test_control_plan_sampling.py tests/test_flux_attention_prompt_validation.py tests/test_attention_control.py tests/test_controlled_attention_integration.py -v`

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

```bash
git add tests/test_control_plan_sampling.py core/third_party/FollowYourShape/src/flux/sampling.py core/third_party/FollowYourShape/src/edit.py
git commit -m "feat: apply scheduled controls during denoising"
```

### Task 5: Isolated Runner, Worker, Plans, and Reproduction Docs

**Files:**
- Create: `core/scripts/run_control_plan.py`
- Create: `core/scripts/control_plan_worker.py`
- Create: `core/configs/control_plans/oracle_fys_control.json`
- Create: `core/configs/control_plans/oracle_stage2_edit_logit_gate.json`
- Create: `core/configs/control_plans/part_to_edit_logit_transfer.json`
- Modify: `core/scripts/README.md`
- Test: `tests/test_run_control_plan.py`

**Interfaces:**
- Runner consumes manifest, plan, seeds, case filters, and output root.
- Worker consumes one case JSON and one resolved plan JSON, then imports and calls `edit.main` without subprocess nesting.

- [ ] **Step 1: Write failing dry-run and output-isolation tests**

```python
def test_runner_builds_isolated_command_with_plan_and_mask(tmp_path):
    command = build_control_command(record, plan, repo_root=REPO_ROOT, seed=0)
    assert command.output_dir.as_posix().endswith("control_operations/oracle_stage2_edit_logit_gate/real_0006/seed_000")
    assert "--control-plan-resolved" in command.args
    assert command.case_record["gt_mask"] == record["gt_mask"]

def test_runner_refuses_nonempty_output_without_overwrite(tmp_path):
    (tmp_path / "occupied.txt").write_text("keep")
    with pytest.raises(FileExistsError):
        validate_output_dir(tmp_path, overwrite=False)
```

- [ ] **Step 2: Run runner tests and verify RED**

Run: `python -m pytest tests/test_run_control_plan.py -v`

Expected: FAIL because the runner does not exist.

- [ ] **Step 3: Implement runner, worker, run matrix, and provenance files**

Dry-run prints commands without creating per-run directories unless `--write-run-matrix` is supplied. Execute mode writes `case_record.json`, `resolved_control_plan.json`, `run_config.json`, and `run.log`. `--overwrite` is the only way to reuse a non-empty run directory.

- [ ] **Step 4: Add the three locked pilot plans**

The oracle pair must differ only by the Stage 2 operation. The transfer plan uses the same Stage 2 steps and layers, sets `strength=1.0`, and keeps the intended Stage 3 oracle image-KV schedule fixed for the initial mechanistic comparison.

- [ ] **Step 5: Run runner tests and all dry runs**

Run:

```bash
python -m pytest tests/test_run_control_plan.py -v
python core/scripts/run_control_plan.py --plan core/configs/control_plans/oracle_fys_control.json --manifest core/data/partedit_subset/pilot_12_manifest.json --seeds 0 --limit 1
python core/scripts/run_control_plan.py --plan core/configs/control_plans/oracle_stage2_edit_logit_gate.json --manifest core/data/partedit_subset/pilot_12_manifest.json --seeds 0 --limit 1
python core/scripts/run_control_plan.py --plan core/configs/control_plans/part_to_edit_logit_transfer.json --manifest core/data/partedit_subset/pilot_12_manifest.json --seeds 0 --limit 1
```

Expected: tests PASS; each dry run prints one isolated worker command and does not load a model.

- [ ] **Step 6: Run the full local regression suite**

Run: `python -m pytest tests -v`

Expected: PASS. GPU-dependent model execution is not attempted locally.

- [ ] **Step 7: Commit Task 5**

```bash
git add tests/test_run_control_plan.py core/scripts/run_control_plan.py core/scripts/control_plan_worker.py core/configs/control_plans core/scripts/README.md
git commit -m "feat: add isolated control-plan experiments"
```

### Task 6: GPU Smoke-Test Gate

**Files:**
- Modify only if the smoke test reveals a reproducible integration bug, with a failing CPU regression test added first.

**Interfaces:**
- Consumes the three locked plan files and one frozen manifest case.
- Produces one complete output directory per plan with generated image, metadata, diagnostics, and log.

- [ ] **Step 1: Run one oracle baseline case on the GPU host**

```bash
python core/scripts/run_control_plan.py \
  --plan core/configs/control_plans/oracle_fys_control.json \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 --limit 1 --execute
```

- [ ] **Step 2: Run one oracle logit-gated case on the GPU host**

```bash
python core/scripts/run_control_plan.py \
  --plan core/configs/control_plans/oracle_stage2_edit_logit_gate.json \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 --limit 1 --execute
```

- [ ] **Step 3: Run one part-to-edit transfer case on the GPU host**

```bash
python core/scripts/run_control_plan.py \
  --plan core/configs/control_plans/part_to_edit_logit_transfer.json \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 --limit 1 --execute
```

- [ ] **Step 4: Verify artifacts and compare the oracle pair**

Confirm each run has `img_0.jpg`, `run_config.json`, `resolved_control_plan.json`, and `run.log`; confirm the baseline and gated oracle configs differ only in the Stage 2 operation; confirm logs contain selected edit-token indices and active steps/layers.

