# Controlled Revision Note: Attention-Gated Part Localization in Follow-Your-Shape

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

The FYS configuration is fixed as `flux-dev`, guidance `2.0`, `15` denoising steps, `front=2`, `inject=4`, no ControlNet, no oracle mask, and offload enabled. The pinned Follow-Your-Shape submodule revision is `1d01f0d3a5fde5c11e8630808d1d59243894625d`.

One exact command for reproducing the main attention-gated FYS run is:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --tdm-mask-mode attention_gated \
  --attention-token-mode part_edit \
  --execute
```

The repository README provides the full environment setup, dataset extraction, baseline commands, and notebook evaluation commands.

## Baseline And Variant

I added a simple FLUX target-token attention localization baseline. For each case and seed, the baseline encodes the source image, performs source-prompt inversion, and then runs plain target-prompt FLUX denoising from the same inverted latent, without FYS KV injection or oracle masks. For localization, it records the softmax attention mass from image-token queries to the selected target part/edit T5 tokens. I use late FLUX single-stream blocks `28-37` and the same middle denoising window as FYS-TDM, i.e. step indices `2-8` under the 15-step schedule. The maps are averaged over selected tokens, heads, layers, and recorded steps, reshaped to the `32 x 32` image-token grid, smoothed, and binarized with Otsu thresholding. This baseline is localization-only; it does not edit the image.

The main tested variant is attention-gated FYS. It keeps the original FYS inversion, target denoising, and late KV-injection schedule, but replaces the final binary TDM mask with a TDM-attention hybrid mask. The hybrid mask is computed by normalizing the smoothed TDM and target-token attention map, multiplying them as a soft gate, smoothing the product, and binarizing with Otsu thresholding. I compare `part+edit` token attention with `part`-only token attention.

## Metrics

Localization is evaluated against the PartEdit ground-truth part mask using *binary IoU, soft AP, predicted/GT area ratio*, and *soft inside-GT mass.* Editing and preservation are evaluated for generated images using *outside-mask L1, PSNR, SSIM,* and *LPIPS*. The FLUX attention baseline is localization-only, so image-preservation metrics are not applicable to that baseline.

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

Full tables:

- `core/results/controlled_revision/localization_comparison.csv`
- `core/results/controlled_revision/fys_run_metrics.csv`
- `core/results/controlled_revision/flux_attention_metrics.csv`
- `core/results/controlled_revision/compact_fys_summary.csv`
- `core/results/attention_gated_fys_eval/attention_gated_fys_summary.csv`
- `core/results/attention_gated_fys_eval/mask_localization_metrics.csv`
- `core/results/attention_gated_fys_eval/image_preservation_metrics.csv`

The main trend is consistent with the initial diagnosis: original FYS-TDM over-localizes for part-level edits. Attention-gated TDM improves localization substantially, reducing the mean predicted/GT area ratio from `8.04` to `2.51-2.81` and improving mean binary IoU from `0.174` to about `0.32`. Part-only attention gives the sharpest area ratio and highest soft AP, while part+edit attention gives a similar IoU.

However, better masks do not fully solve the editing problem. In difficult cases such as `hair -> curly_hair`, the mask becomes much closer to the hair region, but the face can still change. This suggests that FYS's mask is a late, soft KV-routing constraint rather than a hard spatial edit constraint. Target-prompt trajectory changes can accumulate during unconstrained middle steps and through non-attention pathways, so the bottleneck shifts from mask quality to when and how strongly the trajectory is controlled.

Compact per-case local-edit assessment:

| Method | Unique outputs | Mean local edit success ↑ | Mean non-target preservation ↑ | Full local-edit cases | Full preservation cases |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original FYS-TDM | 12 | 1.00 | 0.92 | 5 / 12 | 2 / 12 |
| Attention-gated FYS, part+edit tokens | 12 | 1.08 | 1.50 | 5 / 12 | 6 / 12 |
| Attention-gated FYS, part-only tokens | 12 | 1.00 | 1.50 | 5 / 12 | 6 / 12 |

This human assessment separates two effects that are partially conflated in automatic image metrics. Attention-gated masks improve non-target preservation substantially, but they do not reliably improve the semantic success of the requested part edit. The part+edit variant gives only a small average gain in local edit success (`1.08` vs. `1.00`), while part-only matches the original FYS local-edit score. This suggests that the main benefit of attention gating is spatial preservation, not stronger semantic editing.

By target part size:

| Part size | Method | Mean local edit success ↑ | Mean non-target preservation ↑ |
| --- | --- | ---: | ---: |
| Small | Original FYS-TDM | 0.75 | 1.25 |
| Small | Attention-gated FYS, part+edit tokens | 0.75 | 1.50 |
| Small | Attention-gated FYS, part-only tokens | 0.75 | 1.50 |
| Medium | Original FYS-TDM | 1.00 | 1.00 |
| Medium | Attention-gated FYS, part+edit tokens | 1.00 | 1.50 |
| Medium | Attention-gated FYS, part-only tokens | 1.00 | 1.50 |
| Large | Original FYS-TDM | 1.25 | 0.50 |
| Large | Attention-gated FYS, part+edit tokens | 1.50 | 1.50 |
| Large | Attention-gated FYS, part-only tokens | 1.25 | 1.50 |

| Case | Part edit | Original FYS local / preserve | Gated part+edit local / preserve | Gated part-only local / preserve | Note |
| --- | --- | ---: | ---: | ---: | --- |
| `real_0006` | `head -> alien` | `1 / 1` | `1 / 1` | `1 / 1` | Gating preserves the person and background better, but the alien-head edit is mostly suppressed. |
| `real_0008` | `head -> bear` | `0 / 2` | `0 / 2` | `0 / 2` | Head localization improves, but the head does not clearly become bear-like. |
| `real_0003` | `head -> cheetah` | `0 / 1` | `0 / 1` | `0 / 1` | Original FYS changes the animal more visibly; gated versions keep the horse but weaken the cheetah-head edit. |
| `real_0002` | `seat -> mesh` | `2 / 1` | `2 / 2` | `2 / 2` | Gating localizes and preserves the chair/background, but the mesh-seat semantic change is weak. |
| `real_0010` | `head -> dragon` | `0 / 0` | `0 / 1` | `0 / 1` | Attention-gated masks focus near the head and restore some body/road content, but the global cow trajectory remains affected. |
| `real_0004` | `carhood -> rusted` | `0 / 1` | `0 / 2` | `0 / 2` | The car is preserved better, but rust on the hood is not clear. |
| `real_0007` | `seat -> leather` | `2 / 2` | `2 / 2` | `2 / 2` | All methods show the seat-material edit; gated versions better preserve the chair frame/background. |
| `real_0001` | `head -> cat` | `2 / 1` | `2 / 1` | `2 / 1` | The cat-head edit is visible, and attention gating improves non-target preservation. |
| `real_0000` | `torso -> armored` | `2 / 1` | `2 / 1` | `2 / 1` | The torso region is affected, but the armor semantics are partial; gating reduces non-target drift. |
| `real_0011` | `hair -> curly_hair` | `2 / 0` | `2 / 1` | `2 / 1` | Hair localization improves, but face identity still changes. |
| `real_0005` | `head -> dog` | `1 / 0` | `1 / 2` | `1 / 2` | Bear body/background are preserved, but dog-head semantics remain partial. |
| `real_0009` | `carbody -> rusted` | `0 / 1` | `1 / 2` | `0 / 2` | The car body is preserved better under gating, but the rusted-body edit is weak. |

The full CSV version is saved at `core/results/attention_gated_fys_eval/local_edit_success_per_case.csv`, and the compact summary is saved at `core/results/attention_gated_fys_eval/local_edit_success_summary.csv`.

## Representative Cases

The focused qualitative comparison below shows `real_0010` (`head -> dragon`). The original TDM expands over the cow body and road, while attention-gated masks focus closer to the head. The gated output partially restores non-target cow/street appearance, but the final edit remains globally affected. This supports the main interpretation: better masks help localization, but FYS's late masked KV injection is not a hard local-edit constraint.

<p align="center">
  <a href="../results/attention_gated_fys_eval/figures/cow_road_case_analysis.jpg">
    <img src="../results/attention_gated_fys_eval/figures/cow_road_case_analysis.jpg" width="100%" alt="Representative cow road attention-gated FYS case analysis">
  </a>
</p>

- `real_0010_seed_000`: original FYS IoU `0.10`; gated part+edit IoU `0.40`; gated part-only IoU `0.41`.
- The body becoming partially transparent/restored under gated masks is evidence that the mask has real effect.
- The remaining global drift is evidence that the target trajectory has already shaped the latent before late-stage masking.

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

## Conclusion

The controlled revision supports a concrete technical gap: trajectory-guided mask-free editing remains useful for object-level control, but its TDM can be too coarse for part-level edits. Token-aware attention can sharpen the mask and improve non-target preservation, but sharper masks alone do not guarantee stronger semantic part editing under the current FYS injection schedule.
