# Part-Level Over-Editing Research Plan

## Final Research Direction

**A Diagnostic Study of Part-Level Over-Editing in Trajectory-Guided Mask-Free Image Editing**

Core question:

> Can Follow-Your-Shape-style trajectory-guided region control localize small part-level edits without over-editing the full object?

## Mapping To Harry Yang's Email

### 1. One Narrow Problem

Part-level over-editing in mask-free image editing.

The project focuses on cases where the user wants to modify only a small component of a subject, such as a hat, label, logo, handle, headlight, or shoe lace, while preserving the rest of the subject and the background.

### 2. Closest Related Work

Use three core papers:

- **Follow-Your-Shape / EditAnyShape:** closest to Harry's current research and the target mechanism being diagnosed.
- **PartEdit:** closest work on part-level editing.
- **Task-Aware Localization or AdaptEdit:** closest work on local edit leakage and over-editing.

Use InstructPix2Pix and SAM/inpainting as baseline references, not as the main related-work argument.

### 3. Precise Technical Gap

Follow-Your-Shape evaluates trajectory-guided region control mainly on object-level and foreground-level shape transformations. PartEdit studies part-level editing through optimized part tokens and localization masks. What remains under-tested is whether a training-free TDM/KV mechanism can localize small part-level edits without expanding the editable region to the whole object.

### 4. 2-3 Week Experiment

Build a small diagnostic benchmark of 20-40 part-level editing cases and run at least one feasible baseline.

Case groups:

- Accessory removal/replacement.
- Label/logo/text replacement.
- Small functional part replacement.
- Full-object replacement sanity checks.

### 5. Dataset

Construct a small prompt-pair dataset using the Follow-Your-Shape format:

- source image.
- source prompt.
- target prompt.
- concise instruction.
- intended part category.
- optional rough part mask or manual evaluation region.

If useful, reuse public images from ReShapeBench or other permissive sources, but the part-level cases should be newly curated because ReShapeBench is mostly object-level.

### 6. Baseline

Primary:

- Follow-Your-Shape, if compute permits.

Fallback:

- InstructPix2Pix for low-cost instruction editing.
- SAM + Stable Diffusion inpainting as oracle-mask reference.
- PartEdit if the inference path is feasible.

### 7. Evaluation Metrics

Manual rubric:

- Part edit success.
- Whole-object preservation.
- Over-editing rate.
- Background preservation.
- Failure category.

Optional automatic metrics:

- LPIPS/SSIM outside a rough part mask.
- CLIP similarity between cropped edited part and target description.
- Change-area ratio inside vs outside the intended part region.

### 8. Success Criterion

The mini-project succeeds if it produces:

- A reproducible 20-40 case diagnostic set.
- At least one runnable baseline evaluation.
- A compact result table.
- At least two stable failure modes with representative success and failure cases.
- A 1-2 page English note that clearly states the gap and feasible next experiment.

## Execution Checklist

- [ ] Read Follow-Your-Shape sections on ReShapeBench, metrics, TDM, limitations, and code requirements.
- [ ] Read PartEdit abstract, method overview, benchmark, and code feasibility.
- [ ] Read Task-Aware Localization or AdaptEdit for over-editing/localization framing.
- [ ] Finalize `related_work.md` into 3 concise paragraphs.
- [ ] Build `cases/part_level_cases_v0.jsonl` with 20-40 cases.
- [ ] Select one baseline that can realistically run.
- [ ] Run 5-10 pilot cases if feasible.
- [ ] Save outputs and failure examples under `results/`.
- [ ] Draft `harry_note.md`.
- [ ] Draft `reply_email.md`.

## Do Not Claim

- Do not claim Follow-Your-Shape cannot handle part-level editing.
- Do not claim part-level editing is unexplored.
- Do not claim results before running a baseline.
- Do not frame the project as training a new large model.

## Safe One-Sentence Pitch

I propose a lightweight diagnostic benchmark to test whether trajectory-guided, mask-free image editing can localize part-level edits, such as labels, accessories, and small functional components, without over-editing the whole object.
