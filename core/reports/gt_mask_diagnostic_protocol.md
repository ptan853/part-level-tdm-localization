# GT-Mask Diagnostic: Matched Controller Comparison

Version: v2, dated 2026-09-08. This pre-generation revision adds two supplemental N=15 conditions. The superseded, unexecuted v1 preparation is retained only in Git history.
Status: prepared for pre-launch review; GPU generation has not started.

## 1. Question and Scope

Does replacing the automatic mask with a native part annotation improve editing under otherwise unchanged Endpoint and source-referenced Residual RK2 control?

This is a separate exploratory diagnostic on an already-inspected split. It does not replace the completed frozen comparison. A source-part GT mask is not an oracle target-edit footprint, particularly for expansion edits. Failure with GT does not by itself prove a limitation of the model.

## 2. Conditions

| Controller | Automatic mask | GT mask |
| --- | --- | --- |
| Endpoint, N=7 | Reuse cached output | Generate once |
| Residual RK2, N=7 | Reuse cached output | Generate once |

Supplement: also generate Residual RK2 N=15 with the same automatic mask and with GT. N=15 means all solver steps 0 through 14, including midpoint and endpoint residual control, not a full-image mask. Keep the original four N=7 conditions as the primary comparison. Do not select whichever duration looks best afterward.

Retain all 60 records and their indices from `core/data/partedit_subset/synth_60_frozen_manifest.json`. Its SHA-256 is `8e69fd42969286ce028c00c285a5a12600a5a4127e18a2c1f03d5ccbc3283147`.

For the primary N=7 comparison, control applies at steps 0 through 6; steps 7 through 14 are free target-prompt updates. Image-KV injection and IT gating remain disabled in all six conditions. Keep FLUX-dev, native 1024-pixel resolution, seed 0, 15 steps, guidance 2.0, source/target prompts, source inversion procedure, solver and offload settings unchanged. The N=7 resolved plans are audited against each cached run. Within each controller-duration condition, only the precomputed control-mask path changes.

Source inversion is recomputed by the existing runner, not loaded from an archived latent trajectory. Before generation, compare the server environment with the original runtime record; record any differences and resolve material numerical differences before launch. Do not claim bitwise identity of recomputed reference states without checking it.

## 3. GT Conversion

Use the native annotation with nonzero pixels treated as foreground. Match the existing oracle conversion: nearest-neighbor resize to the VAE grid (128 by 128), followed by 2 by 2 max pooling to the FLUX image-token grid (64 by 64). Nearest-neighbor sampling uses floor indices, matching PyTorch `interpolate(mode='nearest')`. Foreground 1 means editable; 0 means preserved.

Do not dilate, tune thresholds, select components or adapt masks per controller. Check source/GT geometry, finite values, nonempty edit and preservation regions, grid dimensions and checksums for all cases. The generated grids and native-mask area audit are retained under `core/protocols/gt_mask_diagnostic_v2/`. N=15 reuses precisely the same mask files as its N=7 counterpart; it changes only the control interval, with no KV injection.

## 4. Coverage and Failures

Register 360 condition records: 240 primary and 120 supplemental. Reuse 118 existing automatic-mask images; `synth_0014` is absent for both cached controllers. Generate the 120 primary GT conditions and 120 supplemental N=15 conditions once, including that case, without regenerating missing cached automatic outputs.

The primary paired set is the intersection of cases with valid readable outputs and complete required metrics in all four conditions. It contains at most 59 cases. Report coverage and failure reasons for every registered condition. Never silently drop a failed case or impute a score. Complete both reviewers' ratings for the common set before human analysis; otherwise explicitly report the reduced rating coverage without mixing unequal method sets.

For the supplemental duration comparison, use the intersection of this primary set with valid outputs and metrics for both N=15 conditions. Report its coverage separately. Missing supplemental outputs must not shrink the primary analysis. Prepare reviews for the primary set plus available supplemental candidates on that set; finalize all required ratings before analysis.

Do not selectively regenerate safety-filtered or unattractive outputs. Infrastructure recovery may resume unattempted commands; preserve attempt logs. A scientific parameter change or a material implementation fix requires a new protocol revision and an explicit affected-condition rerun policy.

## 5. Evaluation

Reuse the previous metric definitions and implementation at 512-pixel evaluation resolution: region L1, PSNR, global selected-pixel SSIM proxy, and masked AlexNet LPIPS. Strict preservation uses the complement of native GT; buffered preservation uses the complement of GT dilated by a disk of radius 32 evaluation pixels. These regions are identical for all six conditions, regardless of the generation mask. Inside-region pixel similarity is descriptive, not semantic edit success.

Re-score all six conditions in one new blinded review, including cached automatic outputs. Retain the previous ratings unchanged and exclude them from this diagnostic's primary comparisons. Use the existing 0-2 rubric for local edit, non-target preservation, overall prompt adherence and visual quality. Each of two reviewers scores individual candidates with the source image and prompts, without method labels or side-by-side competing methods.

Freeze new opaque IDs and randomization for all 360 records before generation, using reviewer seeds 202609081 and 202609082. After availability is known, filter by the predefined primary and supplemental coverage rules without re-randomizing. Materialize and checksum the final review pages before scoring; use separate browser storage keys and export filenames. The rubric template and renderer checksum are recorded in the preparation artifacts. Up to 354 images per reviewer (708 ratings total) enter review when all new outputs for the 59 primary cases are available.

Joint success is defined per reviewer as local edit >=1 AND preservation >=1. Strict joint success requires both scores to equal 2. Average these indicators, not thresholded average ratings.

## 6. Analysis and Interpretation

Report paired GT-minus-automatic changes within each controller, and RK2-minus-Endpoint changes within each mask source, for local edit, preservation and joint success. Also report the difference between the two controllers' GT-minus-automatic changes as an exploratory interaction contrast.

Separately report RK2 N=15 minus N=7 under each fixed mask source using the supplemental common set, with the same metrics and paired bootstrap rules. Preserve all six conditions together in supplemental resampling. Improved preservation with reduced semantic success is a tradeoff. These contrasts do not replace the primary N=7 results and do not establish an optimal duration.

Use 10,000 case-level bootstrap resamples, seed 20260908, within the available part-size strata. Keep all four conditions and both reviewers together for each sampled case. Report percentile 95% intervals, conditional on these two reviewers, without multiplicity correction. Report all prespecified contrasts; do not select a favorable metric or declare equivalence from a nonsignificant difference.

Retain expansion cases and report them separately, alongside the other footprint categories and sample counts. Better preservation accompanied by weaker local editing is a tradeoff, not an unqualified improvement. GT benefits under both controllers would motivate better masks and make Endpoint a useful simpler reference. Persistent failures under both GT conditions would motivate investigating semantic editability, source-footprint mismatch and the generation schedule. An apparent RK2-specific benefit requires confirmation on fresh cases.

## 7. Execution Record and Outputs

CPU preparation command, from the repository root:

```bash
.venv/bin/python core/scripts/prepare_gt_mask_diagnostic.py
.venv/bin/python -m unittest discover -s tests -p 'test_gt_mask_diagnostic.py'
```

The preparation script never launches generation. It freezes GT grids, resolved plans, 240 generation commands, 360 evaluation records, 720 reviewer assignments, cache hashes and a preflight summary. Existing artifacts must match byte-for-byte on repeated preparation. Generation commands in `run_matrix.csv` use `${REPO_ROOT}` for the server checkout location.

New outputs belong under `core/results/gt_mask_diagnostic_v2/`; the completed comparison, reports and original ratings must remain unchanged. Keep this work on the experiment branch, without merging to main. Only the v2 matrix is active.

Before generation, provide a separate pre-launch record containing the exact execution commit, submodule revision, protocol/artifact checksums, server runtime environment, and run-count/compute estimate. Send that record and this protocol for review before launching. The pre-launch record references an already-created execution commit.

Planned compute: 240 new generations, no new scout passes. Scaling the earlier approximately nine-hour 300-command run gives roughly 7.2 hours. This is only a lower-confidence planning estimate: N=15 adds source-reference evaluations at eight additional controlled steps relative to N=7, so the cost cannot be assumed identical per run. Provision roughly 8-12 GPU-hours on the same A800 80GB environment, plus metric evaluation, and refine from observed initial timings without changing conditions. This is not a measured timing guarantee.

Launch requires the recorded server preflight and complete test results. Final review pages are materialized after output availability is audited and before scoring. Diagnostic results will be reported separately from the completed comparison.
