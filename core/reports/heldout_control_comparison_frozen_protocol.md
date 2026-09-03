# Frozen Protocol: Held-Out PartEdit Control Comparison

**Protocol version:** 1.0

**Frozen on:** 2026-09-03

**Status:** Frozen before held-out generation. Execution is blocked until the manifest and runner changes specified below pass preflight validation.

**Repository branch:** `experiment/heldout-control-comparison`

**Outer repository reference:** `af5860b91264dee282dcba456b9c246be51b0229`

**FollowYourShape submodule reference:** `b096e8f7736b0f44d820933d5046fe252059a5eb`

## 1. Objective

This experiment tests whether a stronger control operation, rather than a better mask alone, is required for training-free part-level editing in FLUX.

The experiment holds the dataset, target prompts, model, seed, and step count fixed across all evaluated conditions. The causal comparison between endpoint projection and residual RK2 additionally holds the automatic spatial mask and seven-step control duration fixed, changing only the state-control operation. Original FYS-TDM remains a full-method reference with its native mask and schedule:

1. Original Follow-Your-Shape trajectory difference masking (Original FYS-TDM).
2. Endpoint latent projection with a shared automatic mask, controlled for seven prefix steps.
3. Source-referenced residual RK2 control with the same mask and seven-step prefix.

A three-step endpoint condition is retained only as a pre-registered supplemental operating point. It is not used as the matched primary comparison.

## 2. Frozen Dataset

- Dataset: [`Aleksandar/PartEdit-Bench`](https://huggingface.co/datasets/Aleksandar/PartEdit-Bench)
- Revision: `v1.1`
- Split: `synth`
- Cases: every dataset index from 0 through 59, with no exclusions
- Total unique source-edit pairs: 60
- Source image: dataset source image
- Source prompt: `prompt_original`
- Target prompt: the dataset's part-aware edit prompt used by the existing pilot (`p2p_prompt`)
- Part and edit labels: dataset metadata
- Evaluation mask: native `gt_mask`

The PartEdit reference output is neither an input to generation nor visible during human evaluation. The native GT mask is used only for evaluation and is never supplied to any generation method.

This split is held out from the earlier 12-case pilot, which used the PartEdit-Bench `real` split.

### 2.1 Frozen manifest

Before any held-out output is inspected, create:

`core/data/partedit_subset/synth_60_frozen_manifest.json`

The manifest must contain exactly 60 records and preserve the dataset index. Each record must contain at least:

- `case_uid`
- `dataset_revision`
- `dataset_split`
- `dataset_index`
- `source_image`
- `source_prompt`
- `target_prompt`
- `part`
- `edit`
- `gt_mask`
- `gt_area_ratio`
- `part_size`
- `footprint_change`

The manifest SHA-256 checksum must be written to the run metadata before generation begins.

### 2.2 Part-size strata

Part size is assigned only from the native GT-mask area ratio:

1. Sort all 60 cases by `gt_area_ratio` in ascending order.
2. Break exact ties by `dataset_index` in ascending order.
3. Label ranks 1-20 `small`, ranks 21-40 `medium`, and ranks 41-60 `large`.

This produces three fixed 20-case strata without inspecting generated outputs.

### 2.3 Edit-footprint categories

Each case is labeled before generation as one of:

- `contraction`: the requested target is expected to occupy less spatial support than the source part;
- `comparable`: the expected source and target support are approximately equal;
- `expansion`: the requested target is expected to extend beyond the source-part support.

The assignment may use only the source image, prompts, and part/edit labels. Generated outputs must not be inspected. Every case is retained, and the natural category counts are reported rather than forced to be equal.

## 3. Frozen Model and Shared Settings

- Model: FLUX.1-dev through the repository's FollowYourShape pipeline
- Resolution: the repository's fixed 512-pixel evaluation configuration
- Number of solver steps: 15
- Guidance: 2.0
- Seed: 0 only
- ControlNet: disabled
- Offloading: an execution setting only; it must not change numerical configuration

The current pipeline is deterministic for the tested seed configuration. Seeds 1 and 2 are not treated as independent evidence. Statistical uncertainty is estimated across held-out cases and human reviewers, not from repeated identical seeds.

## 4. Shared Automatic Mask

Endpoint projection and residual RK2 use exactly the same precomputed mask for each case. No method-specific mask tuning is allowed.

The mask is the existing **part-only attention-gated TDM** mask:

$$
M = \mathrm{Binarize}(\mathrm{Smooth}(\mathrm{Norm}(\Delta v) \odot \mathrm{Norm}(A_{\mathrm{part}})))
$$

Here, $\Delta v$ is the target-conditioned trajectory-difference signal produced during the FYS scout pass and $A_{\mathrm{part}}$ is the FLUX attention map for the part token. “Part-only” describes which text token is used for the attention gate; this is not a pure attention mask.

Frozen scout settings:

- FYS mask mode: `attention_gated`
- Attention token mode: `part`
- Attention layers: 28-37 inclusive
- FYS middle mask-estimation interval: steps 2-8
- Saved mask: `hybrid_binary_tdm_attention.npy`

The scout-generated image is discarded and is not an evaluated output. The mask is static after the scout and is reused unchanged by both primary control methods and the supplemental endpoint condition.

## 5. Evaluated Conditions

### 5.1 Original FYS-TDM

This is the unmodified FYS editing baseline:

- native three-stage FYS schedule;
- `front=2`, `inject=4`, and `tail_pad=1`;
- original trajectory-difference mask;
- native late source image-KV injection.

It does not consume the shared attention-gated scout mask.

### 5.2 Endpoint projection, N=7

For solver prefix steps $i=0,\ldots,6$, first compute the normal target-prompt solver endpoint $\tilde{x}_{i+1}$ and then project the region outside the shared mask onto the time-aligned inversion state $s_{i+1}$:

$$
x_{i+1}=M\odot\tilde{x}_{i+1}+(1-M)\odot s_{i+1}.
$$

Steps 7-14 continue normal target-prompt denoising from the resulting state. Image-KV injection and text-image attention gating are disabled for all 15 steps so that the endpoint operation is measured directly.

### 5.3 Source-referenced residual RK2, N=7

Define the edited residual relative to the time-aligned inversion path as

$$
d_i=x_i-s_i.
$$

For prefix steps $i=0,\ldots,6$, the mask constrains the residual at both midpoint and endpoint evaluations of midpoint RK2:

$$
d_{i+\frac12}
=d_i+M\odot\left[\frac{h_i}{2}v_1-\left(s_{i+\frac12}-s_i\right)\right],
$$

$$
x_{i+\frac12}=s_{i+\frac12}+d_{i+\frac12},
$$

$$
d_{i+1}
=d_i+M\odot\left[h_i v_2-\left(s_{i+1}-s_i\right)\right],
\qquad
x_{i+1}=s_{i+1}+d_{i+1},
$$

where

$$
v_1=v_\theta(x_i,t_i,c_{\mathrm{tgt}}),
\qquad
v_2=v_\theta(x_{i+\frac12},t_{i+\frac12},c_{\mathrm{tgt}}).
$$

Outside the mask, the residual is zero during the controlled prefix. Inside the mask, the target-prompt RK2 update is retained. Steps 7-14 continue normal target-prompt denoising. Image-KV injection and text-image attention gating are disabled for all 15 steps.

### 5.4 Supplemental endpoint operating point, N=3

This condition preserves the earlier endpoint schedule as a secondary robustness check:

- steps 0-1: full source image-KV preservation;
- steps 2-4: endpoint projection using the same automatic mask;
- steps 5-14: normal target-prompt denoising with no projection and no image-KV injection;
- image-KV layers: 20-37.

This condition differs from the matched N=7 design in both timing and early source-KV use. It is therefore supplemental and cannot replace, tune, or redefine the primary comparison.

## 6. Execution Count

For each of the 60 cases:

- 1 Original FYS-TDM output;
- 1 automatic-mask scout run, whose image is discarded;
- 1 endpoint N=7 output;
- 1 residual RK2 N=7 output;
- 1 supplemental endpoint N=3 output.

This gives 300 command executions, comprising 60 preprocessing scouts and 240 evaluated images.

## 7. Automatic Evaluation

### 7.1 Mask localization

The shared scout signal is evaluated against the native GT mask using:

- binary IoU;
- pixelwise average precision (AP) from the continuous pre-threshold score;
- predicted-mask area divided by GT-mask area.

These metrics characterize the common control mask; they are not method-specific outcome metrics.

### 7.2 Non-target preservation

Each generated output is compared with its source image outside the native source-part GT mask using:

- outside L1, lower is better;
- outside PSNR, higher is better;
- outside global-SSIM proxy, higher is better;
- outside LPIPS, lower is better.

Two non-target regions are reported:

1. **Strict:** the complement of the native GT mask.
2. **Buffered:** the complement of the GT mask dilated by a disk of radius two FLUX image-token cells. On a 32 by 32 token grid at 512-pixel resolution, this is a 32-pixel radius.

The buffered analysis prevents expected spatial expansion immediately around the source part from being counted automatically as non-target corruption. Strict results remain primary; buffered results are a pre-registered sensitivity analysis.

### 7.3 Target-region activity

Inside-mask L1, PSNR, and the global-SSIM proxy are reported only as descriptive measures of how much the target region changed. They are not interpreted as semantic edit success.

## 8. Human Evaluation

Two independent reviewers score all 240 outputs. Review pages use random opaque IDs and randomized presentation order. Method names, filenames, and directory structure are hidden.

Reviewers see only:

- the source image;
- target prompt;
- part and edit labels;
- one candidate output.

They do not see the GT mask, PartEdit reference output, or another method's output beside the candidate.

Each item receives four 0-2 scores:

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Local-edit success | Requested part edit is absent or incorrect | Edit is partial, weak, or ambiguous | Requested edit is clear and coherent at the intended part |
| Non-target preservation | Major unrelated content or identity changes | Noticeable but limited non-target changes | Non-target content is closely preserved |
| Overall prompt adherence | Output conflicts with important target-prompt content | Target prompt is only partly satisfied | Output clearly follows the target prompt |
| Visual quality | Severe artifacts or unusable image | Acceptable with visible defects | Coherent, high-quality image without important artifacts |

Reviewers work independently. No adjudication occurs before the primary analysis. Both raw ratings are retained; the mean of the two reviewer scores is used for method-level mean-score comparisons. Weighted Cohen's kappa is reported for each ordinal criterion.

Derived binary outcomes are:

- **Joint success:** local-edit success is at least 1 and preservation is at least 1 for a reviewer.
- **Strict joint success:** local-edit success equals 2 and preservation equals 2 for a reviewer.

Primary joint rates pool reviewer-level binary judgments while preserving case-method pairing in resampling. As a sensitivity analysis, consensus joint success requires both reviewers to satisfy the corresponding rule.

## 9. Frozen Statistical Analysis

All comparisons are paired by `case_uid`. For each reported difference:

1. Resample 60 case IDs with replacement.
2. Resample separately within the fixed small, medium, and large strata, drawing 20 cases from each stratum.
3. Keep every selected case's method outputs and reviewer ratings together.
4. Repeat 10,000 times.
5. Use the 2.5th and 97.5th percentiles as the paired stratified bootstrap 95% confidence interval.

Report method means or rates, paired differences, and 95% CIs. Also report descriptive results by part-size stratum and footprint-change category. Subgroup results are exploratory because their sample sizes are smaller.

## 10. Pre-Registered Success Criteria

Residual RK2 N=7 supports the central control-operation claim only if all three criteria hold:

1. **Preservation superiority:** versus both endpoint N=7 and Original FYS-TDM, the lower bound of the paired 95% CI for the difference in mean human preservation score is greater than 0.
2. **Local-edit non-inferiority:** versus the stronger of endpoint N=7 and Original FYS-TDM, the lower bound of the paired 95% CI for mean human local-edit score difference is greater than -0.20 on the 0-2 scale.
3. **Joint utility:** reviewer-level joint success exceeds Original FYS-TDM by at least 10 percentage points and is not lower than endpoint N=7.

Automatic preservation metrics must move in the expected direction to support, but not override, the human result. If any primary criterion fails, the conclusion must state that this held-out experiment does not establish superiority. No duration, method, subgroup, or individual case may replace the frozen primary analysis after outputs are inspected.

The supplemental endpoint N=3 result is reported separately and cannot be used to select the primary endpoint configuration.

## 11. Reproduction Contract

The canonical command, after the frozen manifest and supplemental runner option are implemented, is:

```bash
python core/scripts/run_heldout_control_comparison.py \
  --manifest core/data/partedit_subset/synth_60_frozen_manifest.json \
  --seeds 0 \
  --attention-token-mode part \
  --include-endpoint-n3 \
  --execute
```

Before executing, the runner must print and save a command matrix containing exactly 300 rows and must reject the run unless:

- the manifest contains exactly 60 unique dataset indices and case IDs;
- all source images and GT masks exist;
- the dataset revision and manifest checksum are recorded;
- all methods use seed 0, 15 solver steps, and guidance 2.0;
- endpoint N=7 and residual RK2 N=7 reference the identical scout-mask path for each case;
- no evaluated method receives a GT mask as generation input;
- all output directories are empty unless an explicit full-rerun flag is provided.

The `--include-endpoint-n3` option is part of this frozen command contract but is not yet implemented at this protocol revision. Held-out generation must not begin until its implementation and tests are complete.

Expected A800 serial runtime is approximately 4-6 GPU hours, including scout passes and orchestration overhead. Actual wall time, peak GPU memory, disk use, package lock, CUDA/PyTorch versions, complete commands, run logs, and output checksums must be archived with the experiment.

## 12. Change Control

After any held-out output has been inspected:

- no case may be removed;
- no per-case duration or threshold may be selected;
- no method-specific mask may be introduced;
- no score rubric or success threshold may be changed;
- no failed output may be rerun selectively.

Implementation bugs may be fixed only with a protocol version increment, a written change log, and a complete rerun of every affected condition. Any scientific parameter change requires a new protocol version before generation. Exploratory dynamic-mask experiments belong to a later study and are outside this protocol.
