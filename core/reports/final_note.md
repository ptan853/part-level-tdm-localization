# Controlled Revision Note: Part-Level Localization in Follow-Your-Shape

Code and artifacts: `https://github.com/ptan853/part-level-tdm-localization`

## Problem

This mini-project tests a narrow controllable image-editing question: when the requested edit targets a local object part, does Follow-Your-Shape's trajectory divergence map (TDM) localize the intended part, or does it expand to a broader object/background region?

The motivating gap is that Follow-Your-Shape is effective for shape-aware object editing, but its TDM is derived from denoising trajectory divergence rather than explicit part-token localization. For small local components such as a head, hair, seat, hood, torso, or car body, this signal may capture broader edit-induced change instead of the intended part boundary.

## Experimental Setup

I used a fixed PartEdit-Bench subset of 12 cases, balanced by target part size: 4 small, 4 medium, and 4 large cases. Each case was run with three fixed seeds, `0, 1, 2`, for 36 Follow-Your-Shape runs. The target prompt uses PartEdit's part-aware `p2p_prompt`, such as

```
"a dog with bear head standing in a field with grass and water"
```

because the original changed prompt can imply whole-object replacement.

The FYS configuration is fixed as `flux-dev`, guidance `2.0`, `15` denoising steps, `front=2`, `inject=4`, no ControlNet, no oracle mask, and offload enabled. The pinned Follow-Your-Shape submodule revision is `a323456378b0e70f0368c713d4a343c5a41d5a21`.

## Baseline

I added a simple FLUX target-token attention localization baseline. For each case and seed, the baseline encodes the source image, performs source-prompt inversion, and then runs plain target-prompt FLUX denoising from the same inverted latent, without FYS KV injection or oracle masks. For localization, it records the softmax attention mass from image-token queries to the selected target part/edit T5 tokens. I use late FLUX single-stream blocks `28-37` and the same middle denoising window as FYS-TDM, i.e. step indices `2-8` under the 15-step schedule. The maps are averaged over selected tokens, heads, layers, and recorded steps, reshaped to the `32 x 32` image-token grid, smoothed, and binarized with Otsu thresholding. This baseline is localization-only; it does not edit the image.

## Metrics

Localization is evaluated against the PartEdit ground-truth part mask using *binary IoU, soft AP, predicted/GT area ratio*, and *soft inside-GT mass.* Editing and preservation are evaluated only for FYS edited images using manual local-edit success, manual outside-preservation scores, and *outside-mask PSNR/SSIM/LPIPS*. The FLUX attention baseline does not generate edited images, so image-preservation metrics are not applicable.

## Results

Main quantitative comparison:

| Method                      | Part size |     Binary IoU |        Soft AP | Predicted / GT area |
| --------------------------- | --------: | -------------: | -------------: | ------------------: |
| FYS TDM                     |     large | 0.308 ± 0.138 | 0.371 ± 0.186 |        3.19 ± 1.63 |
| FYS TDM                     |    medium | 0.161 ± 0.066 | 0.225 ± 0.133 |        5.40 ± 2.03 |
| FYS TDM                     |     small | 0.048 ± 0.014 | 0.124 ± 0.086 |      16.98 ± 10.69 |
| FLUX target-token attention |     large | 0.425 ± 0.174 | 0.609 ± 0.196 |        2.38 ± 1.26 |
| FLUX target-token attention |    medium | 0.267 ± 0.108 | 0.338 ± 0.146 |        3.43 ± 1.14 |
| FLUX target-token attention |     small | 0.240 ± 0.276 | 0.501 ± 0.415 |      13.09 ± 15.09 |

Full tables:

- `core/results/controlled_revision/localization_comparison.csv`
- `core/results/controlled_revision/fys_run_metrics.csv`
- `core/results/controlled_revision/flux_attention_metrics.csv`
- `core/results/controlled_revision/compact_fys_summary.csv`

The main trend is consistent with the initial diagnosis: FYS-TDM over-localizes most strongly for small parts. The small-part FYS IoU is low, and the predicted region is much larger than the GT part mask. The simple FLUX target-token attention signal is often more spatially concentrated, suggesting that part-token attention can provide a sharper localization cue than trajectory divergence alone.

The outside-mask preservation scores are not the main failure signal. FYS outside-mask SSIM remains around `0.90-0.93` across part sizes, and outside-mask LPIPS is around `0.18-0.20`. The more diagnostic issue is localization granularity: the TDM can expand from the target part to the whole object or adjacent background.

## Representative Cases

The focused qualitative comparison below shows four representative cases. Each row includes the source image, GT part mask, FYS edited image, soft TDM, binary TDM, and FLUX target-token attention map. This view is intended to make both image quality and localization-mask differences visible.

![Focused comparison of FYS edits, TDM masks, and FLUX attention masks](../results/controlled_revision/figures/final_note_mask_quality_comparison.jpg)

- `real_0009_seed_002`: best FYS localization, a large car-body edit.
- `real_0006_seed_000`: worst FYS over-localization, a small head edit.
- `real_0003_seed_000`: weak FYS localization, where FLUX target-token attention is much sharper.
- `real_0004_seed_000`: possible preservation drift, selected by lowest outside-mask SSIM.

For full mask diagnostics across all 36 runs, the repository also includes three supporting sheets at `core/results/controlled_revision/figures/tdm_diagnostic_sheet_part*.jpg`.

## Conclusion

The controlled revision supports a concrete technical gap: trajectory-guided mask-free editing remains useful for object-level control, but its TDM can be too coarse for part-level edits. A useful next direction would be to combine FYS-style trajectory control with token-aware or part-aware localization, rather than replacing FYS with attention alone.
