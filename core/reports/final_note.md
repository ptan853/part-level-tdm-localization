# Controlled Revision Note: Part-Level Localization in Follow-Your-Shape

## Problem

This mini-project tests a narrow controllable image-editing question: when the requested edit targets a local object part, does Follow-Your-Shape's trajectory divergence map (TDM) localize the intended part, or does it expand to a broader object/background region?

The motivating gap is that Follow-Your-Shape is effective for shape-aware object editing, but its TDM is derived from denoising trajectory divergence rather than explicit part-token localization. For small local components such as a head, hair, seat, hood, torso, or car body, this signal may capture broader edit-induced change instead of the intended part boundary.

## Experimental Setup

I used a fixed PartEdit-Bench subset of 12 cases, balanced by target part size: 4 small, 4 medium, and 4 large cases. Each case was run with three fixed seeds, `0, 1, 2`, for 36 Follow-Your-Shape runs. The target prompt uses PartEdit's part-aware `p2p_prompt`, such as "a dog with bear head standing in a field with grass and water", because the original changed prompt can imply whole-object replacement.

The FYS configuration is fixed as `flux-dev`, guidance `2.0`, `15` denoising steps, `front=2`, `inject=4`, no ControlNet, no oracle mask, and offload enabled. The pinned Follow-Your-Shape submodule revision is `a323456378b0e70f0368c713d4a343c5a41d5a21`.

## Baseline

I added a simple FLUX target-token attention localization baseline. For each case and seed, the baseline encodes the source image, runs source-prompt inversion to obtain the same kind of starting latent used by FYS, then runs plain target-prompt FLUX denoising without KV injection. It records true softmax attention mass from image-token queries to selected target part/edit T5 tokens in late single-stream blocks, restricted to the same middle denoising steps used by the FYS TDM construction. This is a diagnostic localization baseline, not a competing editing method.

## Metrics

Localization is evaluated against the PartEdit ground-truth part mask using binary IoU, soft AP, predicted/GT area ratio, and soft inside-GT mass. Editing and preservation are evaluated only for FYS edited images using manual local-edit success, manual outside-preservation scores, and outside-mask PSNR/SSIM/LPIPS. The FLUX attention baseline does not generate edited images, so image-preservation metrics are not applicable.

## Results

| Method | Part size | Binary IoU | Soft AP | Predicted / GT area |
|---|---:|---:|---:|---:|
| FYS TDM | large | 0.308 ± 0.138 | 0.371 ± 0.186 | 3.19 ± 1.63 |
| FYS TDM | medium | 0.161 ± 0.066 | 0.225 ± 0.133 | 5.40 ± 2.03 |
| FYS TDM | small | 0.048 ± 0.014 | 0.124 ± 0.086 | 16.98 ± 10.69 |
| FLUX target-token attention | large | 0.425 ± 0.174 | 0.609 ± 0.196 | 2.38 ± 1.26 |
| FLUX target-token attention | medium | 0.267 ± 0.108 | 0.338 ± 0.146 | 3.43 ± 1.14 |
| FLUX target-token attention | small | 0.240 ± 0.276 | 0.501 ± 0.415 | 13.09 ± 15.09 |

The main trend is consistent with the initial diagnosis: FYS-TDM over-localizes most strongly for small parts. The small-part FYS IoU is low, and the predicted region is much larger than the GT part mask. The simple FLUX target-token attention signal is often more spatially concentrated, suggesting that part-token attention can provide a sharper localization cue than trajectory divergence alone.

The outside-mask preservation scores are not the main failure signal. FYS outside-mask SSIM remains around `0.90-0.93` across part sizes, and outside-mask LPIPS is around `0.18-0.20`. The more diagnostic issue is localization granularity: the TDM can expand from the target part to the whole object or adjacent background.

## Representative Cases

The repository includes four representative cases in `core/results/controlled_revision/figures/representative_case_candidates_sheet.jpg`:

- `real_0009_seed_002`: best FYS localization, a large car-body edit.
- `real_0006_seed_000`: worst FYS over-localization, a small head edit.
- `real_0003_seed_000`: weak FYS localization, where FLUX target-token attention is much sharper.
- `real_0004_seed_000`: possible preservation drift, selected by lowest outside-mask SSIM.

Full diagnostic sheets are stored in `core/results/controlled_revision/figures/tdm_diagnostic_sheet_part*.jpg`.

## Conclusion

The controlled revision supports a concrete technical gap: trajectory-guided mask-free editing remains useful for object-level control, but its TDM can be too coarse for part-level edits. A useful next direction would be to combine FYS-style trajectory control with token-aware or part-aware localization, rather than replacing FYS with attention alone.

The project succeeds as a reproducible diagnostic study: it fixes the dataset and seeds, records configurations and logs, adds a simple localization baseline, reports local-edit and preservation evidence, and identifies representative success and failure cases.
