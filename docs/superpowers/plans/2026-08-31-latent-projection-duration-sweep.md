# Latent Projection Duration Sweep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a reproducible oracle-mask latent-projection duration sweep for `real_0006` and `real_0011`, then produce a continuous visual comparison and separate edit/preservation measurements.

**Architecture:** Add a thin sweep runner that generates immutable duration-specific control plans and delegates every inference run to the existing `run_control_plan` interfaces. Add a separate result summarizer that validates traces before reading images, computes inside/outside pixel change, and renders one full-resolution comparison sheet. The FLUX/FYS inference implementation remains unchanged.

**Tech Stack:** Python 3.10, existing control-plan runner, JSON/CSV, NumPy, Pillow, unittest.

## Global Constraints

- Locked cases: `real_0006` and `real_0011`.
- Locked seed: `0`.
- Primary durations: `N=0,1,...,13`, beginning at denoising step 2.
- Primary sweep must not use Stage 3 image-KV injection.
- Each projected step `i` must use source endpoint `i+1` and produce `outside_mae_after=0.0`.
- Existing inference behavior and existing plans must remain unchanged.

---

### Task 1: Duration-plan generation and sweep runner

**Files:**
- Create: `core/scripts/run_latent_projection_duration_sweep.py`
- Create: `tests/test_run_latent_projection_duration_sweep.py`
- Modify: `core/scripts/README.md`

**Interfaces:**
- Produces: `build_duration_plan(duration: int) -> dict`
- Produces: `build_sweep_commands(...) -> list[ControlCommand]`
- Produces: persisted plans under `core/results/control_operations/latent_projection_duration_sweep/plans/duration_NN.json`
- Reuses: `build_control_command`, `execute_command`, and `write_run_matrix` from `run_control_plan.py`

- [ ] **Step 1: Write failing plan-boundary tests**

Test that duration 0 has no latent-projection stage, duration 1 projects only step 2, duration 13 projects steps 2-14, and values outside 0-13 raise `ValueError`.

- [ ] **Step 2: Run the focused test and verify failure**

Run: `python -m unittest tests.test_run_latent_projection_duration_sweep -v`

Expected: import failure because the sweep runner does not exist.

- [ ] **Step 3: Implement immutable duration-plan generation**

Generate plans with fixed Stage 1 (`0-1`, target prompt, `source_all` image KV) and an optional projection stage (`2..duration+1`, target prompt, no image KV, `source_outside_mask` latent projection). Persist each exact JSON plan before building commands.

- [ ] **Step 4: Add command construction and CLI**

Support `--manifest`, repeatable `--case-uid` (defaulting to the two locked cases), `--durations` (default `0-13`), `--seed 0`, `--execute`, and `--overwrite`. Write one combined run matrix containing 28 rows for the default sweep.

- [ ] **Step 5: Test command isolation**

Assert that two cases and two requested durations produce four unique output directories and that no generated primary plan contains `image_kv: source_outside_mask`.

- [ ] **Step 6: Run regression tests**

Run: `python -m unittest tests.test_run_latent_projection_duration_sweep tests.test_run_control_plan tests.test_control_schedule tests.test_latent_control -v`

Expected: all tests pass.

- [ ] **Step 7: Document dry-run and execution commands**

Add exact commands to `core/scripts/README.md`, including the result root and the fact that the reference run remains separate.

- [ ] **Step 8: Commit runner work**

```bash
git add core/scripts/run_latent_projection_duration_sweep.py tests/test_run_latent_projection_duration_sweep.py core/scripts/README.md
git commit -m "feat: add latent projection duration sweep"
```

### Task 2: Trace validation, metrics, and continuous comparison image

**Files:**
- Create: `core/scripts/summarize_latent_projection_duration_sweep.py`
- Create: `tests/test_summarize_latent_projection_duration_sweep.py`
- Modify: `core/scripts/README.md`

**Interfaces:**
- Consumes: sweep root with `duration_NN/<case_uid>/seed_000/` outputs and the existing `oracle_stage2_latent_projection` reference root
- Produces: `duration_sweep_metrics.csv`
- Produces: `duration_sweep_comparison.jpg`
- Produces: `duration_sweep_change_curve.png`

- [ ] **Step 1: Write failing validation tests**

Create temporary trace fixtures and test rejection of missing images, wrong projection steps, wrong source endpoint indices, nonzero `outside_mae_after`, and any Stage 3 image-KV injection in a primary run.

- [ ] **Step 2: Run the focused test and verify failure**

Run: `python -m unittest tests.test_summarize_latent_projection_duration_sweep -v`

Expected: import failure because the summarizer does not exist.

- [ ] **Step 3: Implement trace validation and metrics**

For each case/duration, verify the expected projection trace and compute mean absolute RGB change separately inside and outside the resized GT mask. Save one CSV row per output.

- [ ] **Step 4: Render the comparison sheet**

Render two case rows in this order: source, GT overlay, `N=0` through `N=13`, and the separate `N=7 + Stage 3 KV` reference. Use fixed-size thumbnails and explicit column labels so every duration is visually comparable.

- [ ] **Step 5: Render the change curve**

Plot duration against inside-mask and outside-mask mean absolute change for each case. This separates semantic/edit activity from preservation instead of combining them into one score.

- [ ] **Step 6: Run focused and regression tests**

Run: `python -m unittest tests.test_summarize_latent_projection_duration_sweep tests.test_run_latent_projection_duration_sweep -v`

Expected: all tests pass.

- [ ] **Step 7: Commit summarizer work**

```bash
git add core/scripts/summarize_latent_projection_duration_sweep.py tests/test_summarize_latent_projection_duration_sweep.py core/scripts/README.md
git commit -m "feat: summarize latent projection duration sweep"
```

### Task 3: GPU execution and artifact verification

**Files:**
- Generate: `core/results/control_operations/latent_projection_duration_sweep/`
- Generate: `core/results/control_operations_eval/latent_projection_duration_sweep/`

**Interfaces:**
- Consumes: Task 1 runner and the locked two-case manifest records
- Produces: 28 inference runs plus one metrics CSV and two visual artifacts

- [ ] **Step 1: Run a dry-run matrix check**

Run the sweep without `--execute` and verify 28 unique commands, two case IDs, 14 durations, and seed 0 only.

- [ ] **Step 2: Run one-duration GPU smoke test**

Execute duration 1 for both cases and validate both traces before launching the full sweep.

- [ ] **Step 3: Run the full GPU sweep**

Execute all 28 primary runs sequentially with the existing offline model caches and no concurrent model process.

- [ ] **Step 4: Audit all outputs**

Verify 28 images, 28 configs, 28 resolved plans, 28 traces, zero traceback logs, exact projection-step ranges, and zero post-projection outside-mask MAE.

- [ ] **Step 5: Synchronize results locally**

Package the result root on the server, download it once, and extract it into the matching local ignored results directory.

- [ ] **Step 6: Generate and inspect the comparison artifacts**

Run the summarizer locally, visually inspect the full-resolution sheet, and confirm the CSV contains 28 rows with durations 0-13 for both cases.

- [ ] **Step 7: Run final verification**

Run the full relevant unittest suite and `git diff --check`. Confirm code/config worktrees are clean apart from intentionally generated ignored result artifacts.

