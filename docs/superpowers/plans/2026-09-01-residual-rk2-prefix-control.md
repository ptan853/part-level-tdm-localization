# Residual RK2 Prefix Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an oracle-mask inversion-referenced residual RK2 control operation, run a prefix-duration sweep over `N=0..15`, evaluate it under the existing metric protocol, and keep late FYS image-KV injection as a separate fixed-duration ablation.

**Architecture:** Extend the FollowYourShape submodule with aligned cached inversion-reference midpoint recording and a pure residual RK2 state-update helper, then expose the operation through the existing control-plan schema. Add a dedicated parent-repository sweep runner whose `N` always means the first `N` denoising updates from step 0; reuse the established evaluation and manual-review conventions without changing old endpoint-projection artifacts.

**Tech Stack:** Python 3.10+, PyTorch 2.1, FLUX/FollowYourShape, JSON control plans, `unittest`/`pytest`, pandas, scikit-image, LPIPS, Jupyter.

## Global Constraints

- Use the locked 12-case manifest at `core/data/partedit_subset/pilot_12_manifest.json`.
- Use 15 denoising updates and duration values `N=0..15`.
- `N` controls exactly `range(N)`; it never starts at step 2.
- Primary runs use oracle masks, seed 0, target prompts, and a free tail with no image-KV injection.
- Residual control follows `d_next=d_i+M*delta`; it does not hard-project an
  existing residual to zero when `M=0`.
- Only `N=15` is a full-trajectory residual RK2 solve; `N<15` is prefix control
  followed by ordinary target RK2.
- Existing FYS, attention-gated, endpoint-projection, evaluation, and result paths must remain unchanged.
- Late image-KV injection is a secondary ablation at fixed `N`, not part of the primary sweep.
- Do not perform case-specific duration selection.

---

### Task 1: Add Residual RK2 State Algebra

**Files:**
- Modify: `core/third_party/FollowYourShape/src/flux/latent_control.py`
- Modify: `tests/test_latent_control.py`

**Interfaces:**
- Consumes: target state `x_i`, source endpoint `s_i`, cached inversion-reference midpoint `s_mid_i`, source next endpoint `s_next`, target velocities `v1` and `v2`, scalar `h`, spatial mask `M`.
- Produces: `build_residual_midpoint(...) -> Tensor`, `build_residual_endpoint(...) -> Tensor`, plus immutable per-step diagnostics.

- [ ] **Step 1: Write failing residual-preservation, zero-initial-residual, all-one, and mixed-mask tests**

Add tests equivalent to:

```python
def test_zero_mask_preserves_existing_residual():
    actual, _ = build_residual_midpoint(
        current=torch.tensor([[[2.0], [4.0]]]),
        source_current=torch.tensor([[[1.0], [3.0]]]),
        source_midpoint=torch.tensor([[[1.5], [3.5]]]),
        target_velocity=torch.tensor([[[10.0], [20.0]]]),
        step_size=-0.2,
        spatial_mask=torch.zeros(2),
    )
    torch.testing.assert_close(actual, torch.tensor([[[2.5], [4.5]]]))

def test_zero_mask_with_zero_initial_residual_returns_source_midpoint():
    actual, _ = build_residual_midpoint(
        current=torch.tensor([[[1.0], [3.0]]]),
        source_current=torch.tensor([[[1.0], [3.0]]]),
        source_midpoint=torch.tensor([[[1.5], [3.5]]]),
        target_velocity=torch.tensor([[[10.0], [20.0]]]),
        step_size=-0.2,
        spatial_mask=torch.zeros(2),
    )
    torch.testing.assert_close(actual, torch.tensor([[[1.5], [3.5]]]))

def test_zero_mask_endpoint_preserves_existing_residual():
    actual, _ = build_residual_endpoint(
        current=torch.tensor([[[2.0], [4.0]]]),
        source_current=torch.tensor([[[1.0], [3.0]]]),
        source_next=torch.tensor([[[0.5], [2.5]]]),
        target_mid_velocity=torch.tensor([[[10.0], [20.0]]]),
        step_size=-0.2,
        spatial_mask=torch.zeros(2),
    )
    torch.testing.assert_close(actual, torch.tensor([[[1.5], [3.5]]]))

def test_residual_endpoint_one_mask_matches_target_rk2_endpoint():
    actual, _ = build_residual_endpoint(
        current=torch.tensor([[[2.0], [4.0]]]),
        source_current=torch.tensor([[[1.0], [3.0]]]),
        source_next=torch.tensor([[[0.5], [2.5]]]),
        target_mid_velocity=torch.tensor([[[10.0], [20.0]]]),
        step_size=-0.2,
        spatial_mask=torch.ones(2),
    )
    torch.testing.assert_close(actual, torch.tensor([[[0.0], [0.0]]]))
```

Also test non-finite states, mismatched shapes, invalid masks, and non-scalar step sizes.

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```bash
python -m pytest tests/test_latent_control.py -q
```

Expected: failures because the residual helpers do not exist.

- [ ] **Step 3: Implement the two pure update helpers**

Use the exact algebra:

```python
residual = current - source_current
mask = validated_mask.reshape(1, -1, 1).to(current)
mid_residual = residual + mask * (
    0.5 * step_size * target_velocity - (source_midpoint - source_current)
)
midpoint = source_midpoint + mid_residual

next_residual = residual + mask * (
    step_size * target_mid_velocity - (source_next - source_current)
)
endpoint = source_next + next_residual
```

Return diagnostics containing mask area, outside residual before/after, and
maximum outside absolute error.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run the same pytest command. Expected: all latent-control tests pass.

- [ ] **Step 5: Commit the submodule change**

```bash
git -C core/third_party/FollowYourShape add src/flux/latent_control.py
git -C core/third_party/FollowYourShape commit -m "feat: add residual RK2 latent control algebra"
git add tests/test_latent_control.py core/third_party/FollowYourShape
git commit -m "test: cover residual RK2 latent algebra"
```

### Task 2: Record Aligned Inversion-Reference Midpoints

**Files:**
- Modify: `core/third_party/FollowYourShape/src/flux/sampling.py`
- Modify: `tests/test_inversion_step_alignment.py`
- Modify: `tests/test_control_plan_sampling.py`

**Interfaces:**
- Consumes: source inversion RK2 loop and `record_source_latents=True`.
- Produces: `info["source_midpoints"]` containing cached reversed-inversion-path midpoints keyed by denoising update index `0..14`, alongside `info["source_latents"]` keyed `0..15`.

- [ ] **Step 1: Write a failing source-midpoint alignment test**

For a two-update toy schedule, assert:

```python
self.assertEqual(set(info["source_latents"]), {0, 1, 2})
self.assertEqual(set(info["source_midpoints"]), {0, 1})
torch.testing.assert_close(info["source_midpoints"][1], first_inversion_midpoint)
torch.testing.assert_close(info["source_midpoints"][0], second_inversion_midpoint)
```

The test must verify reverse index mapping, not merely key count. It must call
these values cached inversion-reference midpoints and must not assume numerical
identity with an independently integrated forward source midpoint.

Also assert the endpoint identities:

```python
torch.testing.assert_close(info["source_latents"][T], encoded_source_latent)
torch.testing.assert_close(info["source_latents"][0], final_inverted_noise)
```

- [ ] **Step 2: Run alignment tests and confirm failure**

```bash
python -m pytest tests/test_inversion_step_alignment.py tests/test_control_plan_sampling.py -q
```

Expected: missing `source_midpoints` assertions fail.

- [ ] **Step 3: Record midpoint tensors during inversion**

Initialize an empty midpoint cache when source references are requested. After
computing `img_mid`, store:

```python
denoising_step = len(timesteps) - i - 2
info["source_midpoints"][denoising_step] = img_mid.detach().clone()
```

At inversion completion, require endpoint keys `range(T + 1)` and midpoint
keys `range(T)`; raise a descriptive `RuntimeError` otherwise.

- [ ] **Step 4: Run alignment and legacy projection tests**

```bash
python -m pytest tests/test_inversion_step_alignment.py tests/test_control_plan_sampling.py -q
```

Expected: new midpoint tests and all existing endpoint-projection tests pass.

- [ ] **Step 5: Commit the submodule and parent pointer**

```bash
git -C core/third_party/FollowYourShape add src/flux/sampling.py
git -C core/third_party/FollowYourShape commit -m "feat: record aligned source RK2 midpoints"
git add tests/test_inversion_step_alignment.py tests/test_control_plan_sampling.py core/third_party/FollowYourShape
git commit -m "test: verify source midpoint alignment"
```

### Task 3: Extend the Control-Plan Schema

**Files:**
- Modify: `core/third_party/FollowYourShape/src/flux/control_schedule.py`
- Modify: `tests/test_control_schedule.py`

**Interfaces:**
- Consumes: stage JSON field `residual_control`.
- Produces: accepted values `"none"` and `"source_referenced_rk2"`; `plan_requires_source_latents()` returns true for either endpoint projection or residual RK2.

- [ ] **Step 1: Write failing schema tests**

Cover:

```python
stage = ControlStage.from_dict({
    "name": "residual", "start": 0, "end": 2,
    "residual_control": "source_referenced_rk2",
})
self.assertEqual(stage.residual_control, "source_referenced_rk2")
```

Also assert rejection of unknown operations, mask requirement, serialization,
and source-reference requirement.

- [ ] **Step 2: Run schema tests and confirm failure**

```bash
python -m pytest tests/test_control_schedule.py -q
```

- [ ] **Step 3: Implement schema support without changing existing fields**

Add:

```python
RESIDUAL_CONTROL_OPERATIONS = {"none", "source_referenced_rk2"}
residual_control: str = "none"
```

Parse, serialize, and validate the field. A residual stage requires a mask;
`plan_requires_source_latents` must include it.

- [ ] **Step 4: Run schema tests and the full control-plan subset**

```bash
python -m pytest tests/test_control_schedule.py tests/test_run_control_plan.py -q
```

- [ ] **Step 5: Commit**

```bash
git -C core/third_party/FollowYourShape add src/flux/control_schedule.py
git -C core/third_party/FollowYourShape commit -m "feat: configure residual RK2 control stages"
git add tests/test_control_schedule.py core/third_party/FollowYourShape
git commit -m "test: validate residual control plans"
```

### Task 4: Verify Oracle Mask-to-Token Alignment

**Files:**
- Modify: `tests/test_flux_attention_prompt_validation.py`

**Interfaces:**
- Consumes: pixel-space oracle mask and encoded latent spatial dimensions.
- Produces: binary packed-token mask with verified spatial orientation and token count.

- [ ] **Step 1: Preserve the existing asymmetric non-square regression test**

Keep `test_main_aligns_mixed_nonsquare_oracle_mask_to_image_token_grid`, which
already verifies thresholding, nearest-neighbor resize, `2x2` max pooling,
row-major flattening, and orientation.

- [ ] **Step 2: Add a top-left-quarter rectangular fixture**

Create a binary mask whose top-left quarter is 1 and all other pixels are 0.
After conversion, assert that exactly the corresponding top-left quarter of the
packed token grid is 1, the flattened mask length equals `img.shape[1]`, and all
values belong to `{0, 1}`.

- [ ] **Step 3: Run the focused mask tests**

```bash
python -m pytest tests/test_flux_attention_prompt_validation.py -q
```

Expected: the old and new alignment tests pass without modifying the existing
conversion implementation.

- [ ] **Step 4: Commit the parent test**

```bash
git add tests/test_flux_attention_prompt_validation.py
git commit -m "test: verify oracle mask packed-token alignment"
```

### Task 5: Integrate Residual RK2 Into Denoising

**Files:**
- Modify: `core/third_party/FollowYourShape/src/flux/sampling.py`
- Modify: `tests/test_control_plan_sampling.py`

**Interfaces:**
- Consumes: resolved residual stage, source endpoints/midpoints, oracle spatial mask.
- Produces: controlled midpoint and endpoint states plus `residual_control_trace`.

- [ ] **Step 1: Write failing sampler integration tests**

Use a deterministic toy velocity model and assert:

```python
# N=0: no residual stage, unchanged ordinary RK2 output.
# zero mask: incoming residual is preserved, not erased.
# zero mask plus d_0=0 over a prefix: controlled endpoints equal source references.
# one mask: controlled endpoints equal ordinary target RK2.
# mixed mask: only masked tokens carry target residual.
# missing midpoint: RuntimeError names source_midpoints[step].
# trace steps for N=3: [0, 1, 2].
```

- [ ] **Step 2: Run tests and confirm failure**

```bash
python -m pytest tests/test_control_plan_sampling.py -q
```

- [ ] **Step 3: Replace the normal midpoint only inside residual stages**

At each step, resolve the stage before the first model evaluation. For
`source_referenced_rk2`, validate `source_latents[i]`,
`source_midpoints[i]`, and `source_latents[i + 1]`; compute `v1` normally,
construct the controlled midpoint with `build_residual_midpoint`, evaluate
`v2` at that midpoint, and construct the controlled endpoint with
`build_residual_endpoint`.

For all other stages and for `control_plan is None`, preserve the existing
Heun/RK2 block byte-for-byte as far as practical.

- [ ] **Step 4: Record auditable traces**

Write one record per controlled step containing:

```python
{
    "step": i,
    "source_endpoint_index": i,
    "source_midpoint_index": i,
    "source_next_index": i + 1,
    "mask_area_ratio": ...,
    "outside_residual_max_midpoint": ...,
    "outside_residual_max_endpoint": ...,
}
```

Include this list in `tdm/control_trace.json`.

- [ ] **Step 5: Run integration and regression tests**

```bash
python -m pytest tests/test_control_plan_sampling.py tests/test_control_schedule.py tests/test_latent_control.py -q
python -m pytest tests -q
```

Expected: all tests pass; original endpoint projection assertions are unchanged.

- [ ] **Step 6: Commit**

```bash
git -C core/third_party/FollowYourShape add src/flux/sampling.py
git -C core/third_party/FollowYourShape commit -m "feat: apply source-referenced residual RK2 control"
git add tests/test_control_plan_sampling.py core/third_party/FollowYourShape
git commit -m "test: verify residual RK2 sampler integration"
```

### Task 6: Add the N=0..15 Primary Sweep Runner

**Files:**
- Create: `core/scripts/run_residual_rk2_prefix_sweep.py`
- Create: `tests/test_run_residual_rk2_prefix_sweep.py`
- Modify: `core/scripts/README.md`

**Interfaces:**
- Consumes: locked manifest and durations string.
- Produces: one generated plan per `N`, 192 isolated output directories, and one run matrix.

- [ ] **Step 1: Write failing runner tests**

Specify these exact contracts:

```python
build_prefix_plan(0)["stages"] == []
build_prefix_plan(1)["stages"][0]["start"] == 0
build_prefix_plan(1)["stages"][0]["end"] == 0
build_prefix_plan(15)["stages"][0]["end"] == 14
parse_durations("0-15") == list(range(16))
```

Assert `-1` and `16` are rejected, all primary plans contain no image-KV
operation, and 12 records times 16 plans create 192 unique output paths.

- [ ] **Step 2: Run the new tests and confirm failure**

```bash
python -m pytest tests/test_run_residual_rk2_prefix_sweep.py -q
```

- [ ] **Step 3: Implement the dedicated runner**

Follow `run_latent_projection_duration_sweep.py` for command construction but
generate plans with:

```python
stages = [] if duration == 0 else [{
    "name": "residual_prefix",
    "start": 0,
    "end": duration - 1,
    "prompt": "target",
    "image_kv": "none",
    "it_gate": "none",
    "latent_projection": "none",
    "residual_control": "source_referenced_rk2",
}]
```

Default output root:
`core/results/control_operations/residual_rk2_prefix_sweep`; default matrix:
`core/results/run_matrices/residual_rk2_prefix_sweep.csv`.

- [ ] **Step 4: Verify dry-run metadata**

```bash
python core/scripts/run_residual_rk2_prefix_sweep.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --all-cases --durations 0-15 --seed 0 --write-run-matrix
```

Expected: 192 commands, duration 0 has no controlled steps, duration 15 traces
steps `0..14`, and no existing result path is referenced.

- [ ] **Step 5: Run runner tests and full local tests**

```bash
python -m pytest tests/test_run_residual_rk2_prefix_sweep.py -q
python -m pytest tests -q
```

- [ ] **Step 6: Commit**

```bash
git add core/scripts/run_residual_rk2_prefix_sweep.py core/scripts/README.md tests/test_run_residual_rk2_prefix_sweep.py
git commit -m "feat: add residual RK2 prefix sweep"
```

### Task 7: GPU Smoke Test and Full Primary Run

**Files:**
- Generated: `core/results/control_operations/residual_rk2_prefix_sweep/**`
- Generated: `core/results/run_matrices/residual_rk2_prefix_sweep.csv`

**Interfaces:**
- Consumes: implemented runner and GPU FLUX environment.
- Produces: validated smoke outputs, then 192 primary outputs.

- [ ] **Step 1: Run three diagnostic durations on two cases**

```bash
python core/scripts/run_residual_rk2_prefix_sweep.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --case-uid real_0006 --case-uid real_0010 \
  --durations 0,3,15 --seed 0 --execute
```

Expected: six successful runs with images, configs, logs, and control traces.

- [ ] **Step 2: Audit numerical invariants**

Check that duration 0 has no residual trace, duration 3 traces `[0,1,2]`,
duration 15 traces `[0..14]`, and all controlled endpoints have finite values
and near-zero outside-mask residual error.

- [ ] **Step 3: Visually inspect the six outputs**

Reject the run if `N=0` differs from the unchanged target baseline under the
same command inputs, if outputs are blank/corrupt, or if the oracle mask is
misaligned with the latent token grid.

- [ ] **Step 4: Run all 192 outputs**

```bash
python core/scripts/run_residual_rk2_prefix_sweep.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --all-cases --durations 0-15 --seed 0 --execute
```

- [ ] **Step 5: Validate completeness**

Require 192 output images, 192 run configs, 192 logs with zero exit status,
and no duplicate `(case_uid, N)` rows.

### Task 8: Unified Automated Evaluation and Human Review

**Files:**
- Create: `core/scripts/evaluate_residual_rk2_prefix_sweep.py`
- Create: `core/scripts/build_residual_rk2_manual_review.py`
- Create: `tests/test_evaluate_residual_rk2_prefix_sweep.py`
- Create: `tests/test_build_residual_rk2_manual_review.py`
- Generated: `core/results/control_operations_eval/residual_rk2_prefix_sweep/**`

**Interfaces:**
- Consumes: 192 outputs, locked manifest, frozen FYS metrics, and completed endpoint-projection tables.
- Produces: one metric table, one editable review CSV/HTML, and completeness summaries.

- [ ] **Step 1: Write failing evaluation fixture tests**

Assert one synthetic case produces the same outside/inside L1, PSNR, SSIM
proxy, and LPIPS field conventions as
`evaluate_latent_projection_against_fys.py`; assert existing LPIPS values are
preserved when LPIPS is unavailable.

- [ ] **Step 2: Implement evaluation by reusing existing metric helpers**

Do not duplicate formulas. Refactor shared image metric functions only if
needed, with regression tests proving notebook 09 values remain unchanged.

- [ ] **Step 3: Build generalized manual review**

Each row must contain source, GT overlay, generated output, `case_uid`, `N`,
target prompt, editable local-edit score `0..2`, preservation score `0..2`, and
short note. Export must preserve all 192 rows.

- [ ] **Step 4: Run server-side LPIPS evaluation**

```bash
TORCH_HOME=/path/to/torch_cache python \
  core/scripts/evaluate_residual_rk2_prefix_sweep.py --lpips require
```

Expected: all 192 residual outputs have non-empty LPIPS values.

- [ ] **Step 5: Complete human review and validate it**

Require both human score columns to be integers in `[0,2]` for every row and
reject duplicate/missing `(case_uid, N)` pairs.

- [ ] **Step 6: Run tests and commit analysis code**

```bash
python -m pytest tests/test_evaluate_residual_rk2_prefix_sweep.py tests/test_build_residual_rk2_manual_review.py -q
git add core/scripts/evaluate_residual_rk2_prefix_sweep.py core/scripts/build_residual_rk2_manual_review.py tests
git commit -m "feat: evaluate residual RK2 prefix sweep"
```

### Task 9: Notebook and Standalone Report

**Files:**
- Create: `core/scripts/build_residual_rk2_prefix_notebook.py`
- Create: `core/scripts/build_residual_rk2_prefix_report.py`
- Create: `tests/test_build_residual_rk2_prefix_notebook.py`
- Create: `tests/test_build_residual_rk2_prefix_report.py`
- Generated: `core/notebooks/10_evaluate_residual_rk2_prefix_sweep.ipynb`
- Generated: `core/reports/residual_rk2_prefix_study.md`

**Interfaces:**
- Consumes: complete automated and human metrics.
- Produces: reproducible duration curves, case grids, locked global-duration selection, conclusions, and exact commands.

- [ ] **Step 1: Write builder tests for required sections and artifacts**

Require separate sections for method, correctness checks, preservation,
target-region activity, human semantic scores, part-size breakdown, per-case
heatmaps, representative outputs, limitations, and reproduction.

- [ ] **Step 2: Build the notebook from a deterministic Python script**

Plot all `N=0..15`; do not label `N=0` as a separate method. Keep preservation
and semantic editing in separate figures. Select one global duration by:

```text
max joint success (both >= 1)
then max preservation mean
then minimum N
```

- [ ] **Step 3: Build the report from notebook tables**

The report compares the residual sweep to frozen original FYS and endpoint
projection results while clearly noting the old endpoint sweep's step-2-based
duration semantics.

- [ ] **Step 4: Execute and verify generated artifacts**

```bash
python core/scripts/build_residual_rk2_prefix_notebook.py
jupyter nbconvert --to notebook --execute \
  core/notebooks/10_evaluate_residual_rk2_prefix_sweep.ipynb \
  --output 10_evaluate_residual_rk2_prefix_sweep.ipynb --inplace
python core/scripts/build_residual_rk2_prefix_report.py
```

Expected: notebook executes without error; report image links resolve; all 12
cases appear in qualitative material.

- [ ] **Step 5: Commit**

```bash
git add core/scripts/build_residual_rk2_prefix_notebook.py core/scripts/build_residual_rk2_prefix_report.py core/notebooks/10_evaluate_residual_rk2_prefix_sweep.ipynb core/reports/residual_rk2_prefix_study.md tests
git commit -m "docs: report residual RK2 prefix experiment"
```

### Task 10: Fixed-N Late-KV Ablation

**Files:**
- Create: `core/scripts/run_residual_rk2_late_kv_ablation.py`
- Create: `tests/test_run_residual_rk2_late_kv_ablation.py`
- Modify: `core/notebooks/10_evaluate_residual_rk2_prefix_sweep.ipynb` through its builder
- Modify: `core/reports/residual_rk2_prefix_study.md` through its builder

**Interfaces:**
- Consumes: completed primary experiment and fixed candidate durations.
- Produces: free-tail versus standard late-KV comparison without changing primary outputs.

- [ ] **Step 1: Write plan-generation tests**

For `N=3`, require:

```text
residual stage: steps 0..2
uncontrolled gap: steps 3..9
late image-KV stage: steps 10..13
final free step: 14
```

Reject `N>10` because it overlaps the fixed late window. Ensure ablation output
paths are separate from primary sweep paths.

- [ ] **Step 2: Implement the ablation runner**

Default to `N=3`; accept `--durations 2,3,5` for sensitivity runs. The late
stage uses `image_kv="source_outside_mask"` and the existing layers `20..37`.

- [ ] **Step 3: Run the 12-case N=3 ablation first**

```bash
python core/scripts/run_residual_rk2_late_kv_ablation.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --all-cases --durations 3 --seed 0 --execute
```

- [ ] **Step 4: Evaluate with identical automated and human metrics**

Compare only `Residual RK2 N=3 + free` against
`Residual RK2 N=3 + late KV`. Do not combine the 12 pairs with the 192-row
duration curve as if they were independent methods.

- [ ] **Step 5: Add the ablation to notebook/report and commit**

State whether late KV improves preservation, suppresses semantic editing, or
changes neither. Add N=2/N=5 only if N=3 is inconclusive and compute permits.

### Task 11: Final Reproducibility Audit

**Files:**
- Modify: `README.md`
- Modify: `core/scripts/README.md`
- Modify: `core/reports/residual_rk2_prefix_study.md` through its builder

**Interfaces:**
- Consumes: final code, tests, commands, output schema, and environment.
- Produces: a clean, reproducible branch ready for review.

- [ ] **Step 1: Run all local tests**

```bash
python -m pytest tests -q
git diff --check
```

Expected: all tests pass and no whitespace errors.

- [ ] **Step 2: Verify backward compatibility explicitly**

Dry-run the original FYS command, original control plan, endpoint-projection
duration runner, residual runner, and late-KV runner. Confirm each resolves to
its own output root and old control JSON files load unchanged.

- [ ] **Step 3: Audit the submodule pointer and remote commit**

```bash
git -C core/third_party/FollowYourShape status -sb
git submodule status
git status -sb
```

Require a clean submodule whose recorded commit exists on its remote before
pushing the parent branch.

- [ ] **Step 4: Document exact commands and expected compute**

README must include environment setup, model/cache prerequisites, primary
192-run command, LPIPS command, notebook command, and late-KV command. The
report contains the exact primary reproduction command directly.

- [ ] **Step 5: Final commit and push only after review**

```bash
git add README.md core/scripts/README.md core/reports/residual_rk2_prefix_study.md core/third_party/FollowYourShape
git commit -m "docs: finalize residual RK2 reproduction workflow"
git push -u origin experiment/residual-ode-control
```

Do not merge this branch into `main` until the residual study and the late-KV
ablation have been reviewed as one coherent second control strategy.
