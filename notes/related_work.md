# Related Work Notes

## Research Question

This project asks whether trajectory-guided, mask-free image editing can support **part-level object edits** without over-editing the full object.

The target failure mode is not general text-image mismatch. It is local control failure:

> the requested small part changes, but the rest of the object also drifts in shape, identity, texture, or color.

## Core Related Work

### 1. Follow-Your-Shape / EditAnyShape

- Project: https://follow-your-shape.github.io/
- Paper: https://arxiv.org/abs/2508.08134
- Code: https://github.com/mayuelala/FollowYourShape
- Dataset: https://huggingface.co/datasets/3087richard/ReShapeBench

Why it is closest:

- It is Harry Yang's directly relevant work.
- It proposes trajectory-guided region control for mask-free shape-aware image editing.
- It computes a Trajectory Divergence Map (TDM) from source/edit trajectory differences and uses scheduled KV injection in a FLUX/DiT backbone.

What it covers:

- Object-level shape transformation.
- Foreground object or foreground group replacement.
- Background and non-target preservation.
- Single-object and multi-object scenes in ReShapeBench.

What remains open for this project:

- ReShapeBench primarily evaluates full-object or foreground-level transformation.
- It does not systematically isolate edits where only a small component of the subject should change.
- Its metrics, such as Aesthetic Score, PSNR, LPIPS, and CLIP similarity, do not directly measure whether the edit stayed within the intended part.

### 2. PartEdit

- Project: https://gorluxor.github.io/part-edit/
- Paper: https://arxiv.org/abs/2502.04050
- Code: https://github.com/Gorluxor/partedit
- Benchmark: https://huggingface.co/datasets/Aleksandar/PartEdit-Bench

Why it matters:

- It directly studies object-part image editing.
- It shows that part-level editing is a real and measurable problem.
- It provides task inspiration for edits such as changing small object components while preserving the rest of the object.

Difference from this project:

- PartEdit uses optimized part tokens and localization masks in a diffusion editing pipeline.
- This project does not claim to invent part-level editing.
- The narrow question is whether Follow-Your-Shape-style TDM/KV region control can handle similar part-level locality without expanding to the full object.

### 3. Task-Aware Localization / Local Over-Editing Work

- Task-Aware Localization paper: https://arxiv.org/abs/2604.20258
- AdaptEdit paper: https://arxiv.org/abs/2604.23763

Why they matter:

- They study where-to-edit failures, local edit leakage, and over-editing in modern image editors.
- They support the claim that localization should be evaluated directly, not only through global text-image alignment or image quality.

Difference from this project:

- These works focus on instruction-based editing and/or trained localization/adaptation modules.
- They do not directly evaluate Follow-Your-Shape's training-free TDM and scheduled KV injection mechanism on part-level edits.

## Baseline-Related Work

### InstructPix2Pix

- Code: https://github.com/timothybrooks/instruct-pix2pix
- Diffusers docs: https://huggingface.co/docs/diffusers/v0.35.0/en/training/instructpix2pix

Use in this project:

- Candidate low-cost instruction-editing baseline if Follow-Your-Shape cannot be run locally.
- Not closest related work, because it is not a part-localization or trajectory-guided method.

### SAM + Inpainting

- Inpaint Anything: https://github.com/geekyutao/Inpaint-Anything
- Grounded Segment Anything: https://github.com/IDEA-Research/Grounded-Segment-Anything

Use in this project:

- Candidate oracle/local-mask reference.
- It is not mask-free, so it should be framed as an upper-bound reference rather than the main comparison.

## Safe Gap Statement

Follow-Your-Shape demonstrates that trajectory divergence maps can localize object-level shape transformations without user-provided masks. PartEdit shows that part-level editing is a meaningful and measurable task, and recent localization work studies local edit leakage and over-editing. However, it remains unclear whether Follow-Your-Shape-style TDM/KV region control is precise enough for part-level edits, where only a small component of the subject, such as a hat, label, logo, handle, headlight, or lace, should change while the rest of the object remains fixed.
