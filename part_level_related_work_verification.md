# Part-Level Localized Editing: Related Work Verification

Date: 2026-08-05

## Question

Does the proposed gap stand after checking part-level localized image editing and over-editing related work?

## Short Answer

Yes, but the gap must be stated carefully.

Part-level image editing itself is already studied, especially by PartEdit. Local-edit over-editing/leakage is also studied by recent instruction-based and DiT-based editors. Therefore, the project should not claim that part-level editing is unexplored.

The safer gap is:

> Existing work studies part-level editing and local edit leakage, while Follow-Your-Shape studies trajectory-guided object-level shape editing. What remains under-tested is whether Follow-Your-Shape-style TDM/KV region control can localize part-level edits without expanding the edit region to the full object.

## Core Related Work

### 1. Follow-Your-Shape / EditAnyShape

- Project: https://follow-your-shape.github.io/
- Paper: https://arxiv.org/abs/2508.08134
- Code: https://github.com/mayuelala/FollowYourShape
- Dataset: https://huggingface.co/datasets/3087richard/ReShapeBench

Role in our project:

- Closest to Harry Yang's research direction.
- Provides the trajectory-guided TDM and scheduled KV injection mechanism.
- Evaluates object-level and foreground-level shape transformation, including multi-object scenes.

Not enough for our question:

- ReShapeBench mainly changes full foreground objects or object groups.
- It does not systematically isolate small object-part edits such as labels, logos, hats, handles, headlights, or laces.
- Its metrics focus on image quality, background preservation, and text alignment, not part-level over-editing.

### 2. PartEdit: Fine-Grained Image Editing using Pre-Trained Diffusion Models

- Project: https://gorluxor.github.io/part-edit/
- Paper: https://arxiv.org/abs/2502.04050
- Code: https://github.com/Gorluxor/partedit
- Benchmark: https://huggingface.co/datasets/Aleksandar/PartEdit-Bench

What it does:

- Directly studies text-based object-part editing.
- Learns special textual tokens corresponding to object parts.
- Uses optimized part tokens to produce localization masks at each inference step.
- Applies feature blending and adaptive thresholding for localized part edits.
- Provides PartEdit-Synth and PartEdit-Real benchmarks.

Why it does not kill our gap:

- It is the direct part-editing related work and must be cited.
- However, it is built around UNet-based diffusion and optimized part tokens.
- It does not answer whether FLUX/DiT trajectory divergence maps from Follow-Your-Shape can localize small part-level changes without over-editing the larger object.

Compute note:

- The GitHub README says training can take about 64GB memory with fp32 and 8 selected layers on 100 images for 2000 steps, around 1.5 hours on an A100 80GB.
- The demo/inference path may be easier, but full token optimization is not a low-compute baseline.

### 3. AdaptEdit / Edit Where You Mean

- Paper: https://arxiv.org/abs/2604.23763

What it does:

- Studies mask-free local image editing in large DiT editors.
- Identifies edit leakage as a problem in DiT models.
- Uses trainable region-aware adapters, a SpatialGate, and a MaskPredictor to ground local edit regions from instruction and source image.

Why it matters:

- Confirms that local edit leakage in DiT editors is a real current research problem.
- The wording is highly relevant to Harry's controllable generation direction.

Why it does not kill our gap:

- It is a trained adapter framework, not a training-free TDM/KV diagnostic.
- It is not specifically evaluating Follow-Your-Shape or ReShapeBench-style trajectory divergence masks.

### 4. Rethinking Where to Edit: Task-Aware Localization for Instruction-Based Image Editing

- Paper: https://arxiv.org/abs/2604.20258

What it does:

- Studies over-editing in instruction-based image editing.
- Argues that different edit operations, such as addition, removal, and replacement, require different localization patterns.
- Proposes a training-free task-aware localization framework using source and target image streams.

Why it matters:

- Strong support for our metric design: over-editing and localization need to be measured directly, not only through CLIP or image quality.
- Suggests that our prompt groups should separate removal, replacement, and attribute/part changes.

Why it does not kill our gap:

- It focuses on instruction-based editing backbones such as Step1X-Edit and Qwen-Image-Edit.
- It does not study Follow-Your-Shape's TDM or scheduled KV injection.

### 5. MIRAGE: Benchmarking and Aligning Multi-Instance Image Editing

- Paper: https://arxiv.org/abs/2604.05180
- Code link from arXiv: https://github.com/ZiqianLiu666/MIRAGE

What it does:

- Studies over-editing and spatial misalignment in multi-instance editing.
- Introduces a benchmark for 3-5 similar instances and composite instructions.
- Uses VLM parsing, regional subsets, and multi-branch parallel denoising.

Why it matters:

- Confirms that our earlier same-class target-selection idea is also a real research direction.

Why it is now secondary:

- It is more about instance-level grounding and compositional multi-instruction editing.
- Our main direction is now part-level over-editing inside one object, which is closer to testing the spatial precision of TDM.

### 6. InstructPix2Pix

- Code: https://github.com/timothybrooks/instruct-pix2pix
- Diffusers docs: https://huggingface.co/docs/diffusers/v0.35.0/en/training/instructpix2pix

Role:

- Practical low-compute-ish instruction editing baseline.
- Useful for pilot comparisons if Follow-Your-Shape is too expensive to run.

Limitation:

- Not a precise local/part editing method.
- Original repo says examples were tested on GPU with more than 18GB VRAM.

### 7. Inpaint Anything / SAM + Inpainting

- Code: https://github.com/geekyutao/Inpaint-Anything

Role:

- Useful oracle-mask baseline.
- If a human/SAM mask is provided for the part, inpainting should preserve the rest of the object better.

Limitation:

- Not mask-free, so it should not be compared as the same setting.
- Best used as an upper-bound/local-mask reference.

## Gap After Verification

The original broad claim:

> Part-level localized image editing has not been studied.

is false.

The refined claim:

> Part-level editing has been studied by methods such as PartEdit, and local edit leakage is actively studied in DiT instruction editors. However, Follow-Your-Shape-style trajectory-guided region control has not been systematically stress-tested on part-level edits, where the desired change occupies only a small component of an object. A lightweight diagnostic benchmark can test whether TDM masks stay localized or expand to the whole object.

is defensible.

## Recommended Mini-Project Framing

Title:

**A Diagnostic Study of Part-Level Over-Editing in Trajectory-Guided Mask-Free Image Editing**

Closest related work:

- Follow-Your-Shape / EditAnyShape.
- PartEdit.
- AdaptEdit or Task-Aware Localization as local-over-editing references.

Technical gap:

- Existing trajectory-guided shape editing is evaluated mainly at object/foreground level.
- Existing part-level methods use part-token optimization or trained region-aware modules.
- It remains unclear whether training-free TDM/KV region control can support part-level edit locality.

Feasible experiment:

- Build 20-40 part-level cases.
- Use Follow-Your-Shape if compute permits.
- Use InstructPix2Pix and/or SAM+inpainting as low-compute pilot baselines.
- Evaluate part success, object preservation, over-editing, and background preservation.

Success criterion:

- Identify and quantify at least two stable part-level failure modes, such as whole-object drift and under-localized/over-localized masks, with representative successes and failures.
