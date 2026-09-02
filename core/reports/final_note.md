# Controlled Revision Note: Attention-Gated And Oracle Part Control In Follow-Your-Shape

Code and artifacts: `https://github.com/ptan853/part-level-tdm-localization`

## Problem

This mini-project tests a narrow controllable image-editing question: when the requested edit targets a local object part, does Follow-Your-Shape's trajectory divergence map (TDM) localize the intended part, or does it expand to a broader object/background region? I then test whether target-token attention can gate the TDM and improve part-level control.

The motivating gap is that Follow-Your-Shape is effective for shape-aware object editing, but its TDM is derived from denoising trajectory divergence rather than explicit part-token localization. For small local components such as a head, hair, seat, hood, torso, or car body, this signal may capture broader edit-induced change instead of the intended part boundary.

## Experimental Setup

I used a fixed PartEdit-Bench subset of 12 cases, balanced by target part size: 4 small, 4 medium, and 4 large cases. Each case was executed with three fixed seeds, `0, 1, 2`, giving 36 command runs per method. In this inversion-based FYS path, the outputs are deterministic, so I report the results as 12 unique case outputs per method rather than treating repeated seed rows as independent samples. The target prompt uses PartEdit's part-aware `p2p_prompt`, such as

```
"a dog with bear head standing in a field with grass and water"
```

because the original changed prompt can imply whole-object replacement.

The FYS configuration is fixed as `flux-dev`, guidance `2.0`, `15` denoising steps, `front=2`, `inject=4`, no ControlNet, and offload enabled. Original and attention-gated runs estimate the injection mask; the Oracle ablation substitutes the projected GT part mask at the same Stage-3 decision point. The pinned Follow-Your-Shape submodule revision is `1090ed42af153fd696aaaa659c509a97bdd249d1`.

The exact commands for reproducing the five main experiment runs are listed below. The repository README provides the full environment setup, dataset extraction, dependency installation, and notebook evaluation commands.

Original FYS-TDM:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --execute
```

FLUX target-token attention localization baseline:

```bash
python core/scripts/run_flux_attention_baseline.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --execute
```

Attention-gated FYS with part+edit tokens:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --tdm-mask-mode attention_gated \
  --attention-token-mode part_edit \
  --execute
```

Attention-gated FYS with part-only tokens:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --tdm-mask-mode attention_gated \
  --attention-token-mode part \
  --output-root core/results/fys_mask_ablation/attention_gated_tdm_part \
  --run-matrix core/results/run_matrices/attention_gated_part_pilot_12_manifest_multi_seed.csv \
  --execute
```

Oracle GT-mask FYS:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0 \
  --oracle-mask \
  --execute
```

## Baseline And Variant

I added a simple FLUX target-token attention localization baseline. For each case and seed, the baseline encodes the source image, performs source-prompt inversion, and then runs plain target-prompt FLUX denoising from the same inverted latent, without FYS KV injection or oracle masks. For localization, it records the softmax attention mass from image-token queries to the selected target part/edit T5 tokens. I use late FLUX single-stream blocks `28-37` and the same middle denoising window as FYS-TDM, i.e. step indices `2-8` under the 15-step schedule. The maps are averaged over selected tokens, heads, layers, and recorded steps, reshaped to the `32 x 32` image-token grid, smoothed, and binarized with Otsu thresholding. This baseline is localization-only; it does not edit the image.

The main tested variant is attention-gated FYS. It keeps the original FYS inversion, target denoising, and late KV-injection schedule, but replaces the final binary TDM mask with a TDM-attention hybrid mask. The hybrid mask is computed by normalizing the smoothed TDM and target-token attention map, multiplying them as a soft gate, smoothing the product, and binarizing with Otsu thresholding. I compare `part+edit` token attention with `part`-only token attention.

The Oracle ablation keeps the same source inversion, target-prompt trajectory, and late KV-injection schedule. It projects the PartEdit GT mask to the FLUX image-token grid using nearest-neighbor latent-grid resizing followed by `2 x 2` max pooling, then uses that binary grid directly as the Stage-3 injection mask. The saved injection masks match the projected GT masks for all `12/12` cases. This isolates whether localization quality alone is the limiting factor without presenting GT localization as an estimated-mask result.

## Metrics

Localization is evaluated against the PartEdit ground-truth part mask using *binary IoU, soft AP, predicted/GT area ratio*, and *soft inside-GT mass.* Editing and preservation are evaluated for generated images using *outside-mask L1, PSNR, SSIM,* and *LPIPS*. The FLUX attention baseline is localization-only, so image-preservation metrics are not applicable to that baseline.

Oracle localization scores are fixed by construction (`IoU=1`, `AP=1`, area ratio `=1`) and are not included as evidence that one localization estimator outperforms another. The meaningful Oracle comparison is the final image under an exact mask.

I also add a compact qualitative local-edit assessment on the 12 unique seed-0 outputs. This is intentionally separated from mask localization:

- **Local edit success:** `0` = requested part edit absent; `1` = partial, weak, or wrong extent; `2` = requested part edit clearly present.
- **Non-target preservation:** `0` = major object/background drift; `1` = moderate drift; `2` = mostly preserved outside the target part.

## Results

Main quantitative comparison for the editing methods.

Mask localization against GT part masks:

| Method                                | Command runs | Unique outputs | Binary IoU ↑ | Soft AP ↑ | Predicted / GT area ↓ |
| ------------------------------------- | -----------: | -------------: | ------------: | ---------: | ---------------------: |
| Original FYS-TDM                      |           36 |             12 |         0.174 |      0.247 |                   8.04 |
| Attention-gated FYS, part+edit tokens |           36 |             12 |         0.327 |      0.591 |                   2.81 |
| Attention-gated FYS, part-only tokens |           36 |             12 |         0.323 |      0.619 |                   2.51 |

Edited-image preservation outside the GT part mask:

| Method                                | Outside L1 ↓ | Outside PSNR ↑ | Outside SSIM ↑ | Outside LPIPS ↓ |
| ------------------------------------- | ------------: | --------------: | --------------: | ---------------: |
| Original FYS-TDM                      |         0.056 |           20.36 |           0.919 |            0.191 |
| Attention-gated FYS, part+edit tokens |         0.047 |           21.79 |           0.938 |            0.146 |
| Attention-gated FYS, part-only tokens |         0.046 |           22.10 |           0.941 |            0.142 |
| Oracle GT-mask FYS                    |         0.043 |           22.95 |           0.953 |            0.126 |

Full tables:

- `core/results/controlled_revision/localization_comparison.csv`
- `core/results/controlled_revision/fys_run_metrics.csv`
- `core/results/controlled_revision/flux_attention_metrics.csv`
- `core/results/controlled_revision/compact_fys_summary.csv`
- `core/results/attention_gated_fys_eval/attention_gated_fys_summary.csv`
- `core/results/attention_gated_fys_eval/mask_localization_metrics.csv`
- `core/results/attention_gated_fys_eval/image_preservation_metrics.csv`
- `core/results/oracle_mask_eval/oracle_mask_validation.csv`
- `core/results/oracle_mask_eval/oracle_image_preservation_metrics.csv`
- `core/results/oracle_mask_eval/oracle_comparison_summary.csv`
- `core/results/oracle_mask_eval/oracle_per_case_deltas.csv`

The main trend is consistent with the initial diagnosis: original FYS-TDM over-localizes for part-level edits. Attention-gated TDM improves localization substantially, reducing the mean predicted/GT area ratio from `8.04` to `2.51-2.81` and improving mean binary IoU from `0.174` to about `0.32`. Part-only attention gives the sharpest area ratio and highest soft AP, while part+edit attention gives a similar IoU.

However, better masks do not fully solve the editing problem. In difficult cases such as `hair -> curly_hair`, the mask becomes much closer to the hair region, but the face can still change. This suggests that FYS's mask is a late, soft KV-routing constraint rather than a hard spatial edit constraint. Target-prompt trajectory changes can accumulate during unconstrained middle steps and through non-attention pathways, so the bottleneck shifts from mask quality to when and how strongly the trajectory is controlled.

The Oracle result strengthens this interpretation. Projected GT masks produce the best automatic non-target preservation (`L1=0.043`, `PSNR=22.95`, `SSIM=0.953`, `LPIPS=0.126`). Manual review nevertheless gives Oracle a mean local-edit score of only `0.92`, below part+edit gating (`1.08`) and close to original FYS (`1.00`). Oracle therefore confirms that improved localization and pixel-level preservation are not sufficient for successful semantic part editing under the current injection schedule.

Compact per-case local-edit assessment:

| Method                                | Unique outputs | Mean local edit success ↑ | Mean non-target preservation ↑ | Full local-edit cases | Full preservation cases |
| ------------------------------------- | -------------: | -------------------------: | ------------------------------: | --------------------: | ----------------------: |
| Original FYS-TDM                      |             12 |                       1.00 |                            0.92 |                5 / 12 |                  2 / 12 |
| Attention-gated FYS, part+edit tokens |             12 |                       1.08 |                            1.50 |                5 / 12 |                  6 / 12 |
| Attention-gated FYS, part-only tokens |             12 |                       1.00 |                            1.50 |                5 / 12 |                  6 / 12 |
| Oracle GT-mask FYS                    |             12 |                       0.92 |                            1.42 |                4 / 12 |                  5 / 12 |

This human assessment separates two effects that are partially conflated in automatic image metrics. Attention-gated masks improve non-target preservation substantially, but they do not reliably improve the semantic success of the requested part edit. The part+edit variant gives only a small average gain in local edit success (`1.08` vs. `1.00`), while part-only matches the original FYS local-edit score. This suggests that the main benefit of attention gating is spatial preservation, not stronger semantic editing.

By target part size:

| Part size | Method                                | Mean local edit success ↑ | Mean non-target preservation ↑ |
| --------- | ------------------------------------- | -------------------------: | ------------------------------: |
| Small     | Original FYS-TDM                      |                       0.75 |                            1.25 |
| Small     | Attention-gated FYS, part+edit tokens |                       0.75 |                            1.50 |
| Small     | Attention-gated FYS, part-only tokens |                       0.75 |                            1.50 |
| Small     | Oracle GT-mask FYS                    |                       1.00 |                            1.75 |
| Medium    | Original FYS-TDM                      |                       1.00 |                            1.00 |
| Medium    | Attention-gated FYS, part+edit tokens |                       1.00 |                            1.50 |
| Medium    | Attention-gated FYS, part-only tokens |                       1.00 |                            1.50 |
| Medium    | Oracle GT-mask FYS                    |                       0.75 |                            1.00 |
| Large     | Original FYS-TDM                      |                       1.25 |                            0.50 |
| Large     | Attention-gated FYS, part+edit tokens |                       1.50 |                            1.50 |
| Large     | Attention-gated FYS, part-only tokens |                       1.25 |                            1.50 |
| Large     | Oracle GT-mask FYS                    |                       1.00 |                            1.50 |

| Case          | Part edit              | Original FYS local / preserve | Gated part+edit local / preserve | Gated part-only local / preserve | Oracle local / preserve | Note                                                                                                                          |
| ------------- | ---------------------- | ----------------------------: | -------------------------------: | -------------------------------: | ----------------------: | ----------------------------------------------------------------------------------------------------------------------------- |
| `real_0006` | `head -> alien`      |                     `1 / 1` |                        `1 / 1` |                        `1 / 1` |               `2 / 1` | Gating preserves the person and background better, but the alien-head edit is mostly suppressed.                              |
| `real_0008` | `head -> bear`       |                     `0 / 2` |                        `0 / 2` |                        `0 / 2` |               `0 / 2` | Head localization improves, but the head does not clearly become bear-like.                                                   |
| `real_0003` | `head -> cheetah`    |                     `0 / 1` |                        `0 / 1` |                        `0 / 1` |               `0 / 2` | Original FYS changes the animal more visibly; gated versions keep the horse but weaken the cheetah-head edit.                 |
| `real_0002` | `seat -> mesh`       |                     `2 / 1` |                        `2 / 2` |                        `2 / 2` |               `2 / 2` | Gating localizes and preserves the chair/background, but the mesh-seat semantic change is weak.                               |
| `real_0010` | `head -> dragon`     |                     `0 / 0` |                        `0 / 1` |                        `0 / 1` |               `0 / 1` | Attention-gated masks focus near the head and restore some body/road content, but the global cow trajectory remains affected. |
| `real_0004` | `carhood -> rusted`  |                     `0 / 1` |                        `0 / 2` |                        `0 / 2` |               `0 / 1` | The car is preserved better, but rust on the hood is not clear.                                                               |
| `real_0007` | `seat -> leather`    |                     `2 / 2` |                        `2 / 2` |                        `2 / 2` |               `1 / 1` | All methods show the seat-material edit; gated versions better preserve the chair frame/background.                           |
| `real_0001` | `head -> cat`        |                     `2 / 1` |                        `2 / 1` |                        `2 / 1` |               `2 / 1` | The cat-head edit is visible, and attention gating improves non-target preservation.                                          |
| `real_0000` | `torso -> armored`   |                     `2 / 1` |                        `2 / 1` |                        `2 / 1` |               `1 / 2` | The torso is affected, but armor semantics remain partial.                                                                    |
| `real_0011` | `hair -> curly_hair` |                     `2 / 0` |                        `2 / 1` |                        `2 / 1` |               `2 / 1` | Hair localization improves, but face identity still changes.                                                                  |
| `real_0005` | `head -> dog`        |                     `1 / 0` |                        `1 / 2` |                        `1 / 2` |               `0 / 2` | Bear body/background are preserved, but dog-head semantics remain partial.                                                    |
| `real_0009` | `carbody -> rusted`  |                     `0 / 1` |                        `1 / 2` |                        `0 / 2` |               `1 / 1` | The car body is preserved better under gating, but the rusted-body edit is weak.                                              |

The original and gated ratings are saved at `core/results/attention_gated_fys_eval/local_edit_success_per_case.csv`; Oracle ratings are saved at `core/results/oracle_mask_eval/oracle_local_edit_review.csv`.

## Representative Cases

### Mask and Output Comparison

The two aligned rows below compare the **actual mask used for injection** with the corresponding generated output for `real_0007` (`seat -> leather`). The original FYS-TDM covers much of the chair (`3.55x` the GT area, IoU `0.128`). Part+edit gating reduces the support to `2.68x` (IoU `0.321`), part-only gating reduces it to `2.30x` (IoU `0.350`), and the Oracle column uses the projected GT support by construction.

The generated outputs become more source-like as the masks contract, but the relationship is not monotonic: original FYS and both gated variants received `2/2` for local-edit success and preservation, whereas the Oracle result received `1/2` and `1/2`. A sharper mask therefore changes the edit/preservation trade-off, but does not by itself guarantee a stronger semantic edit.

<p align="center">
  <a href="../results/oracle_mask_eval/figures/mask_output_method_comparison.jpg">
    <img src="../results/oracle_mask_eval/figures/mask_output_method_comparison.jpg" width="100%" alt="Aligned comparison of injection masks and generated outputs">
  </a>
</p>

### Representative Failure Case

`real_0010` (`head -> dragon`) is the clearest failure case. The original TDM spreads across the cow and road (`8.51x` the GT area, IoU `0.098`), while part+edit gating contracts the mask to `1.30x` (IoU `0.403`) and the Oracle uses the projected GT head region. The constrained outputs retain more of the source foreground and road than original FYS, confirming that the mask affects preservation. However, neither constrained result produces a convincing dragon head; the Oracle result receives `0/2` for local-edit success and `1/2` for preservation.

<p align="center">
  <a href="../results/oracle_mask_eval/figures/cow_road_failure_analysis.jpg">
    <img src="../results/oracle_mask_eval/figures/cow_road_failure_analysis.jpg" width="100%" alt="Cow-road failure analysis comparing masks and generated outputs">
  </a>
</p>

This failure separates localization from control. The more accurate masks suppress part of the non-target drift, but they cannot undo the global structure established during the earlier unconstrained target trajectory. Because FYS applies the mask only through late-stage KV injection, it behaves as a soft preservation mechanism rather than a hard spatial editing constraint.

The full qualitative overview is split into three panels below so that the generated images and masks remain readable. Together they show all 12 cases at seed 0, including the source, GT part mask, original FYS result, attention-gated outputs, and mask visualizations.

<p align="center">
  <a href="../results/attention_gated_fys_eval/figures/attention_gated_fys_overview_part1.jpg">
    <img src="../results/attention_gated_fys_eval/figures/attention_gated_fys_overview_part1.jpg" width="100%" alt="Attention-gated FYS qualitative overview part 1">
  </a>
</p>

<p align="center">
  <a href="../results/attention_gated_fys_eval/figures/attention_gated_fys_overview_part2.jpg">
    <img src="../results/attention_gated_fys_eval/figures/attention_gated_fys_overview_part2.jpg" width="100%" alt="Attention-gated FYS qualitative overview part 2">
  </a>
</p>

<p align="center">
  <a href="../results/attention_gated_fys_eval/figures/attention_gated_fys_overview_part3.jpg">
    <img src="../results/attention_gated_fys_eval/figures/attention_gated_fys_overview_part3.jpg" width="100%" alt="Attention-gated FYS qualitative overview part 3">
  </a>
</p>

For additional mask diagnostics, the repository also includes `core/results/attention_gated_fys_eval/figures/mask_metric_boxplots.png` and `core/results/controlled_revision/figures/tdm_diagnostic_sheet_part*.jpg`.

The Oracle comparison below shows all 12 seed-0 cases in three readable panels. Each row contains the source, GT part, original FYS result, both attention-gated outputs, Oracle output, and the actual Oracle mask used for injection.

<p align="center">
  <a href="../results/oracle_mask_eval/figures/oracle_comparison_part1.jpg">
    <img src="../results/oracle_mask_eval/figures/oracle_comparison_part1.jpg" width="100%" alt="Oracle GT-mask comparison cases 1 to 4">
  </a>
</p>

<p align="center">
  <a href="../results/oracle_mask_eval/figures/oracle_comparison_part2.jpg">
    <img src="../results/oracle_mask_eval/figures/oracle_comparison_part2.jpg" width="100%" alt="Oracle GT-mask comparison cases 5 to 8">
  </a>
</p>

<p align="center">
  <a href="../results/oracle_mask_eval/figures/oracle_comparison_part3.jpg">
    <img src="../results/oracle_mask_eval/figures/oracle_comparison_part3.jpg" width="100%" alt="Oracle GT-mask comparison cases 9 to 12">
  </a>
</p>

## Conclusion

The controlled revision supports a concrete technical gap: trajectory-guided mask-free editing remains useful for object-level control, but its TDM can be too coarse for part-level edits. Token-aware attention and even GT masks projected to the FLUX token grid improve non-target preservation, but better masks alone do not guarantee stronger semantic part editing under the current FYS injection schedule. The remaining limitation is therefore not only mask estimation; it also concerns when and how the source and target trajectories are constrained.

## Control-Operation Comparison

### Background and hypothesis

The preceding experiments separate two possible bottlenecks. FYS-TDM often produces support broader than the requested part, but replacing it with a projected GT mask still does not reliably realize the requested semantics under the original late image-KV injection schedule. Accurate localization is therefore helpful but not sufficient. The next question is whether a different source/target trajectory control operation can preserve non-target content without suppressing the local edit.

Two oracle-mask controls were evaluated for this purpose. They do not estimate a mask; they assume the GT part support and test what happens after localization has been fixed.

### Shared experimental setting

- The same frozen 12 PartEdit cases are used, with four small, four medium, and four large target parts.
- All outputs use the same source images, part-aware target prompts, FLUX/FYS inversion path, 15-step schedule, and seed 0.
- Both new controls use the same projected oracle mask. Original FYS-TDM remains the native-pipeline baseline and uses its estimated TDM.
- Automatic evaluation uses the same outside-mask L1, PSNR, global-SSIM proxy, and LPIPS implementations. Human evaluation independently scores local-edit success and non-target preservation from 0 to 2.
- Each method uses one globally frozen duration across all cases. No result is selected per image.

Endpoint projection uses its strongest observed global compromise at `N=3`. Residual RK2 uses `N=15`, its best measured setting on the reported aggregate metrics. `N=7` remains the earliest balanced point: it is the first duration reaching the maximum local-edit mean while preservation already exceeds 1.9/2. These operating points were selected from the complete sweeps on this 12-case pilot, not on an independent held-out set.

### Endpoint latent projection

The first strategy completes a normal target-prompt denoising update and then composes its next state with the time-aligned source-inversion state:

$$
z_{i+1}=M_{gt}\odot z^{tgt}_{i+1}+(1-M_{gt})\odot z^{src}_{i+1}.
$$

The target trajectory is retained inside the oracle part mask, while the state outside the mask is projected back to the source trajectory. Control begins at denoising step 2 and lasts for `N` consecutive steps. This directly tests whether state-level source/target composition can replace the original late masked image-KV injection.

### Source-referenced Residual RK2

Endpoint projection constrains only a completed solver step. The second strategy instead represents the edited state $x_i$ as a residual from the time-aligned source state $s_i$:

$$
d_i=x_i-s_i.
$$

Let $h=t_{i+1}-t_i$ be the signed denoising step, $M$ the oracle mask, and $v_1$ and $v_2$ the target-prompt velocities evaluated at the current state and RK2 midpoint. The masked midpoint update is

$$
d_{i+\frac{1}{2}}
=d_i+M\odot\left[\frac{h}{2}v_1-\left(s_{i+\frac{1}{2}}-s_i\right)\right],
\qquad
x_{i+\frac{1}{2}}=s_{i+\frac{1}{2}}+d_{i+\frac{1}{2}},
$$

and the corresponding endpoint update is

$$
d_{i+1}
=d_i+M\odot\left[hv_2-\left(s_{i+1}-s_i\right)\right],
\qquad
x_{i+1}=s_{i+1}+d_{i+1}.
$$

Outside the mask, the residual remains zero and the state follows the aligned source trajectory. Inside the mask, the equations recover the target-prompt midpoint RK2 update. For duration `N`, control applies to the prefix `0..N-1`, and image-KV injection is disabled so the experiment measures this operation directly.

### Numerical comparison

Automatic non-target preservation:

| Method                      | Outside L1 ↓ | Outside PSNR ↑ | Outside SSIM ↑ | Outside LPIPS ↓ |
| --------------------------- | ------------: | --------------: | --------------: | ---------------: |
| Original FYS-TDM            |        0.0555 |           20.36 |          0.9192 |           0.1914 |
| Endpoint projection,`N=3` |        0.0369 |           24.72 |          0.9657 |           0.1615 |
| Residual RK2,`N=15`       |        0.0179 |           30.61 |          0.9914 |           0.0377 |

Human semantic evaluation:

`Joint success` counts a case when both local-edit success and non-target preservation are at least 1, allowing partial success on either dimension. `Strict joint success` requires both scores to equal 2. At Residual RK2 `N=15`, these correspond to 11/12 and 9/12 cases, respectively.

| Method                      | Local edit ↑ | Preservation ↑ | Joint success ↑ | Strict joint ↑ |
| --------------------------- | ------------: | --------------: | ---------------: | --------------: |
| Original FYS-TDM            |         1.000 |           0.917 |            41.7% |            8.3% |
| Endpoint projection,`N=3` |         1.167 |           1.833 |            75.0% |           41.7% |
| Residual RK2,`N=15`       |         1.667 |           2.000 |            91.7% |           75.0% |

Both oracle controls improve non-target preservation over Original FYS-TDM. Endpoint projection gives a useful edit-preservation compromise at `N=3`, but Residual RK2 at `N=15` is stronger on every reported automatic metric and retains substantially more requested edit semantics. Its midpoint-consistent update reaches 91.7% joint success and 75.0% strict joint success.

The two `N` values denote control duration, not identical absolute windows: endpoint projection begins at denoising step 2, whereas Residual RK2 controls a prefix beginning at step 0. The values are therefore not time-aligned, and the comparison evaluates each method at its own globally frozen operating point rather than treating equal `N` as a matched ablation.

### Complete qualitative comparison

The following sheets contain all 12 cases. Every row is aligned by `case_uid` and shows the source, GT part overlay, Original FYS-TDM, endpoint projection at `N=3`, and Residual RK2 at `N=15`.

Regenerate the aligned sheets from the unified metric table with:

```bash
python core/scripts/build_control_operation_comparison.py
```

<p align="center">
  <a href="../results/control_operations_eval/control_operation_comparison/control_comparison_part1.jpg">
    <img src="../results/control_operations_eval/control_operation_comparison/control_comparison_part1.jpg" width="100%" alt="Control-operation comparison cases 1 to 6">
  </a>
</p>

<p align="center">
  <a href="../results/control_operations_eval/control_operation_comparison/control_comparison_part2.jpg">
    <img src="../results/control_operations_eval/control_operation_comparison/control_comparison_part2.jpg" width="100%" alt="Control-operation comparison cases 7 to 12">
  </a>
</p>

The visual comparison supports three observations. First, both controls restore non-target structure in cases such as `real_0011` (`hair -> curly_hair`), where Original FYS changes facial identity, and `real_0004` (`carhood -> rusted`), where both controlled outputs reach human scores of 2 for editing and preservation. Second, endpoint projection can over-constrain semantics: for `real_0005` (`head -> dog`), it improves preservation to 2 but reduces local-edit success to 0, whereas Residual RK2 scores 2 on both criteria. Third, neither operation can create semantics absent from the target trajectory: `real_0010` (`head -> dragon`) reaches preservation 2 under both controls but remains at local-edit score 0.

### Conclusion and scope

Together with the earlier oracle-mask FYS ablation, these results support the hypothesis that the control operation is a major bottleneck after localization is fixed. The direct three-way table is nevertheless a pipeline-level comparison: Original FYS uses its native estimated TDM, while the two new operations receive an oracle mask. The experiment therefore does not by itself attribute the full improvement only to the control formula.

The conclusion is limited to this frozen pilot. It demonstrates that source-referenced state control can improve the edit-preservation trade-off under ideal localization, but it does not establish automatic mask extraction, independent-test-set generalization, or seed uncertainty.

Complete method-internal analyses, including all duration values and qualitative outputs, are available in:

- [`latent_projection_duration_study.md`](latent_projection_duration_study.md)
- [`residual_rk2_prefix_study.md`](residual_rk2_prefix_study.md)

### Reading the Residual RK2 sweep figures

The following figures explain how the operating points were selected rather than serving as unsupported supplementary plots.

**Automatic preservation curves.** All four outside-mask metrics improve monotonically as `N` increases. `N=15` has the lowest L1 and LPIPS and the highest PSNR and SSIM, so it is the best measured preservation setting. The target-region activity curves remain descriptive only; they cannot establish whether the intended semantics were generated.

![Residual RK2 automatic metrics](../results/control_operations_eval/residual_rk2_prefix_sweep/residual_image_metric_curves.png)

**Human-score curves.** Joint success first reaches its maximum of 91.7% at `N=5`, and the local-edit mean first reaches its maximum of 1.667/2 at `N=6`. `N=7` is the earliest point combining that maximum local-edit mean with preservation above 1.9/2. Preservation and strict joint success reach their maxima at `N=9`. Consequently, `N=9..15` are tied on all four human summary metrics. `N=15` is used in the main comparison because the automatic preservation metrics continue to improve through the end of the sweep without any measured human-score reduction; it is not uniquely best under human evaluation alone.

![Residual RK2 human metrics](../results/control_operations_eval/residual_rk2_prefix_sweep/residual_human_metric_curves.png)

**Part-size curves.** At `N=15`, preservation is 2.000/2 for small, medium, and large parts. Local-edit success remains strongest for large parts at 2.000/2 and lower for small and medium parts at 1.500/2, showing that perfect preservation does not remove the semantic difficulty of smaller edits.

![Residual RK2 part-size analysis](../results/control_operations_eval/residual_rk2_prefix_sweep/residual_human_by_part_size.png)

**Per-case heatmaps.** Eleven of the 12 cases achieve joint success at `N=15`. `real_0010` (`head -> dragon`) remains at local-edit score 0 for every duration despite reaching preservation 2, while `real_0003` and `real_0008` remain partial edits with score 1. These failures prevent the preservation curves from being interpreted as universal semantic success.

![Residual RK2 per-case analysis](../results/control_operations_eval/residual_rk2_prefix_sweep/residual_per_case_human_scores.png)

### Exact reproduction commands

Run the following commands from the repository root on the completed experiment branch. Full environment, model, and dataset setup is documented in the repository README.

```bash
git fetch origin --tags
git switch --detach residual-rk2-pilot-v1
git submodule update --init --recursive
```

Generate the complete Endpoint projection sweep:

```bash
python core/scripts/run_latent_projection_duration_sweep.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --all-cases --durations 0-13 --seed 0 --execute
```

Generate the complete Residual RK2 sweep:

```bash
python core/scripts/run_residual_rk2_prefix_sweep.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --all-cases --durations 0-15 --seed 0 --execute
```

Recompute the shared automatic metrics, including LPIPS:

```bash
python core/scripts/evaluate_latent_projection_against_fys.py --lpips require
python core/scripts/evaluate_residual_rk2_prefix_sweep.py --lpips require
```

Validate the completed 192-row Residual RK2 human-score table:

```bash
python core/scripts/build_residual_rk2_manual_review.py \
  --validate core/results/control_operations_eval/residual_rk2_prefix_sweep/manual_review_scores.csv
```

Execute both method-internal analysis notebooks and rebuild the final aligned comparison sheets:

```bash
python -m jupyter nbconvert --execute --to notebook --inplace \
  core/notebooks/09_evaluate_latent_projection_duration_sweep.ipynb
python -m jupyter nbconvert --execute --to notebook --inplace \
  core/notebooks/10_evaluate_residual_rk2_prefix_sweep.ipynb
python core/scripts/build_control_operation_comparison.py
```
