
# Harry Final Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Harry Yang's requested controlled image-generation mini-project deliverables after the Follow-Your-Shape main experiment.

**Architecture:** Keep the existing FYS 12-case x 3-seed results fixed. Add one lightweight FLUX attention localization baseline, merge it with the completed FYS metrics, select four representative success/failure examples, and write a compact English note plus email draft.

**Tech Stack:** Python 3.10, PyTorch, Follow-Your-Shape FLUX submodule, pandas, NumPy, PIL, Jupyter notebook, PartEdit-Bench 12-case subset.

## Global Constraints

- Do not rerun `core/scripts/run_fys_pilot.py --execute` unless explicitly requested.
- Do not overwrite human manual scores in `core/results/controlled_revision/manual_review_template.csv`.
- Preserve server-computed LPIPS values when local LPIPS is unavailable.
- Use the fixed 12-case manifest: `core/data/partedit_subset/pilot_12_manifest.json`.
- Use fixed seeds: `0,1,2`.
- Do not expand to broad editing baselines unless Harry asks.
- Do not use oracle masks as model input for the main FYS experiment.

---

### Task 1: Finish Manual Failure Labels

**Files:**

- Modify: `core/results/controlled_revision/manual_review_template.csv`
- Read: `core/results/controlled_revision/figures/manual_scoring_sheet_part1.jpg`
- Read: `core/results/controlled_revision/figures/manual_scoring_sheet_part2.jpg`
- Read: `core/results/controlled_revision/figures/manual_scoring_sheet_part3.jpg`

**Interfaces:**

- Consumes: existing 36-row manual review CSV with completed local-edit and outside-preservation scores.
- Produces: the same CSV with `failure_category` filled for all 36 rows.

- [ ] **Step 1: Check current missing labels**

Run:

```bash
python - <<'PY'
import pandas as pd
df = pd.read_csv('core/results/controlled_revision/manual_review_template.csv')
print(df['failure_category'].isna().sum())
print(df.loc[df['failure_category'].isna(), ['run_uid','part','edit','target_prompt']])
PY
```

Expected: shows the remaining unlabeled rows.

- [ ] **Step 2: Fill remaining labels**

Use only these categories:

```text
success
over_localization
under_editing
background_drift
object_identity_drift
generation_failure
other
```

Interpretation:

```text
success: requested local edit is clear and non-target regions are acceptable
under_editing: target local edit is weak or missing
over_localization: edit spreads beyond the intended part
background_drift: background changes materially
object_identity_drift: main object identity/shape changes too much
generation_failure: image has severe visual artifacts
other: ambiguous case not captured above
```

- [ ] **Step 3: Verify labels are complete**

Run:

```bash
python - <<'PY'
import pandas as pd
df = pd.read_csv('core/results/controlled_revision/manual_review_template.csv')
assert len(df) == 36
assert df['local_edit_success_0_2'].notna().all()
assert df['outside_preservation_0_2'].notna().all()
assert df['failure_category'].notna().all()
print('manual labels complete')
PY
```

Expected: `manual labels complete`.

---

### Task 2: Add Simple FLUX Attention Localization Baseline

**Files:**

- Create: `core/scripts/run_flux_attention_baseline.py`
- Create: `core/results/flux_attention_baseline/`
- Modify: `core/notebooks/03_evaluate_controlled_revision.ipynb`

**Interfaces:**

- Consumes: `core/data/partedit_subset/pilot_12_manifest.json`.
- Consumes: existing FYS source images and prompts.
- Produces: one attention heatmap per run or per case under `core/results/flux_attention_baseline/<case_uid>/seed_<seed>/`.
- Produces metrics compatible with FYS localization columns: `binary_iou`, `soft_ap`, `pred_to_gt_area_ratio`, `soft_inside_gt_mass`.

- [ ] **Step 1: Define the baseline**

Use a minimal comparison baseline:

```text
Run plain FLUX target-prompt denoising from the same seed and extract an attention-derived heatmap for target part/edit tokens.
Evaluate the heatmap against the same GT part mask.
```

If token-specific attention is too invasive in the FYS code, use the fallback:

```text
Capture image-token attention change magnitude between source-prompt and target-prompt denoising without KV injection.
```

Both are acceptable as "simple FLUX attention signal" because the baseline is diagnostic, not a full editing method.

- [ ] **Step 2: Implement a dry-run CLI first**

Create `core/scripts/run_flux_attention_baseline.py` with arguments:

```text
--manifest
--seeds
--limit
--case-uid
--execute
--python
--num-steps
--name
--output-root
```

Expected dry run:

```bash
python core/scripts/run_flux_attention_baseline.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --limit 1
```

Expected output: printed commands and target output dirs, no model execution.

- [ ] **Step 3: Run one-case smoke test on server**

Run on GPU server:

```bash
python core/scripts/run_flux_attention_baseline.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --limit 1 \
  --execute
```

Expected artifacts:

```text
core/results/flux_attention_baseline/<case_uid>/seed_000/attention_soft.npy
core/results/flux_attention_baseline/<case_uid>/seed_000/attention_binary.npy
core/results/flux_attention_baseline/<case_uid>/seed_000/run_config.json
core/results/flux_attention_baseline/<case_uid>/seed_000/run.log
```

- [ ] **Step 4: Run full 12 x 3 baseline if smoke test passes**

Run:

```bash
python core/scripts/run_flux_attention_baseline.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --execute
```

Expected: 36 baseline runs.

---

### Task 3: Merge Baseline Metrics Into Evaluation Notebook

**Files:**

- Modify: `core/notebooks/03_evaluate_controlled_revision.ipynb`
- Create: `core/results/controlled_revision/flux_attention_metrics.csv`
- Modify: `core/results/controlled_revision/compact_fys_summary_for_harry.csv`

**Interfaces:**

- Consumes: `core/results/flux_attention_baseline/**/attention_soft.npy`.
- Consumes: `core/results/flux_attention_baseline/**/attention_binary.npy`.
- Produces: baseline metrics using the same GT masks and same metric functions as FYS.

- [ ] **Step 1: Add a baseline loading section**

Add a notebook section after FYS metric loading:

```text
Load FLUX attention baseline artifacts
Validate 36 expected baseline runs
Map each baseline run to source image, GT mask, case_uid, seed
```

- [ ] **Step 2: Reuse existing localization metric helpers**

Compute:

```text
binary_iou
soft_ap
pred_to_gt_area_ratio
soft_inside_gt_mass
```

Do not compute image preservation metrics for attention baseline unless a generated image is also saved.

- [ ] **Step 3: Add compact comparison table**

Final table should contain rows:

```text
FYS TDM / large
FYS TDM / medium
FYS TDM / small
FLUX attention / large
FLUX attention / medium
FLUX attention / small
```

Expected columns:

```text
method
part_size
n_runs
manual_local_edit_success_0_2
manual_outside_preservation_0_2
binary_iou
soft_ap
pred_to_gt_area_ratio
soft_inside_gt_mass
outside_mask_psnr
outside_mask_global_ssim
outside_mask_lpips
```

For baseline rows without editing images, use `NA` for manual and preservation columns.

- [ ] **Step 4: Execute notebook**

Run:

```bash
python -m jupyter nbconvert --execute --to notebook --inplace \
  core/notebooks/03_evaluate_controlled_revision.ipynb
```

Expected:

```text
core/results/controlled_revision/flux_attention_metrics.csv
core/results/controlled_revision/compact_fys_summary_for_harry.csv
```

---

### Task 4: Select Four Representative Cases

**Files:**

- Modify: `core/results/controlled_revision/representative_case_candidates.csv`
- Create: `core/results/controlled_revision/final_representative_cases.csv`
- Create: `core/results/controlled_revision/figures/final_representative_cases_sheet.jpg`

**Interfaces:**

- Consumes: FYS generated images, GT masks, TDM overlays, manual scores, failure labels.
- Produces: four selected examples for Harry's note.

- [ ] **Step 1: Select one success and three failures**

Use this target composition:

```text
1 successful or partially successful local edit
1 over-localization failure
1 under-editing failure
1 object/background drift failure
```

- [ ] **Step 2: Save final case table**

Columns:

```text
case_uid
seed
part_size
part
edit
source_prompt
target_prompt
local_edit_success_0_2
outside_preservation_0_2
failure_category
binary_iou
pred_to_gt_area_ratio
outside_mask_lpips
short_interpretation
```

- [ ] **Step 3: Generate final sheet**

Each row should show:

```text
source image
GT part overlay
FYS edited image
soft TDM overlay
binary TDM overlay
difference map
short interpretation
```

Expected output:

```text
core/results/controlled_revision/figures/final_representative_cases_sheet.jpg
```

---

### Task 5: Write Final English Note And Email Draft

**Files:**

- Create: `core/reports/final_note.md`
- Create: `core/reports/email_to_harry.md`
- Reference: `core/results/controlled_revision/compact_fys_summary_for_harry.csv`
- Reference: `core/results/controlled_revision/figures/final_representative_cases_sheet.jpg`

**Interfaces:**

- Consumes: final metrics table and representative cases.
- Produces: a compact research-note response suitable for Harry.

- [ ] **Step 1: Write final note structure**

Use this structure:

```markdown
# Mini-Project Note: Part-Level Localization Limits in Follow-Your-Shape

## Problem
## Closest Related Work
## Technical Gap
## Experimental Setup
## Metrics
## Results
## Representative Successes and Failure Cases
## Takeaways and Next Steps
## Reproducibility
```

- [ ] **Step 2: State the core finding**

Use this claim only if supported by final table:

```text
The pilot suggests that trajectory-divergence localization becomes much less part-aware as the target edit region becomes smaller. Small-part edits show the lowest binary IoU and the largest predicted/GT area ratio, indicating over-expanded localization.
```

- [ ] **Step 3: Write email draft**

Email should mention:

```text
completed fixed 12-case x 3-seed FYS pilot
included logs/configs/artifacts
included LPIPS/SSIM/IoU/manual review
added simple FLUX attention localization comparison
attached note and repo link
interest in continuing as RA on controllable image/video generation
```

- [ ] **Step 4: Final validation**

Run:

```bash
python - <<'PY'
from pathlib import Path
required = [
    'core/results/controlled_revision/compact_fys_summary_for_harry.csv',
    'core/results/controlled_revision/final_representative_cases.csv',
    'core/results/controlled_revision/figures/final_representative_cases_sheet.jpg',
    'core/reports/final_note.md',
    'core/reports/email_to_harry.md',
]
for item in required:
    path = Path(item)
    print(item, path.exists(), path.stat().st_size if path.exists() else 0)
    assert path.exists()
    assert path.stat().st_size > 0
PY
```

Expected: all required artifacts exist and are non-empty.

---

## Self-Review

**Spec coverage:** The plan covers Harry's remaining requirements: simple localization comparison, compact comparison table, representative results/failures, reproducibility materials, and final note/email.

**Known gap before execution:** The exact FLUX attention extraction hook still needs implementation detail inspection in the FYS/FLUX code. If token-specific attention is too costly, the fallback image-token attention-change signal is acceptable as the "simple localization comparison."

**Do not change:** Existing FYS generated results and manual scores should remain fixed.
