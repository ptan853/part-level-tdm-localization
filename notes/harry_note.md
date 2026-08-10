# Can Trajectory-Guided Mask-Free Editing Support Fine-Grained Object-Preserving Local Edits?

**Working note for Prof. Harry Yang**
**Prepared by:** Peifeng Tan

## Problem

I propose to study a narrow failure mode in controllable image editing: **fine-grained object-preserving local editing**. Recent mask-free editing methods can often change a target object while preserving the background, but it is less clear whether the same mechanisms remain precise when the requested edit affects only a small component attached to or inside the subject, such as a hat, scarf, label, logo, handle, headlight, or shoe lace. The question I want to test is:

> Can trajectory-guided, mask-free region control localize fine-grained object-preserving edits without over-editing the full object?

This is a diagnostic study rather than a proposal to train a new generative model. The goal is to test whether the object-aware region-control mechanism used in Follow-Your-Shape-style editing remains reliable below the object level, when the editable region is much smaller than the full foreground object.

## Closest Related Work

Diffusion-based controllable image editing has recently evolved along two major backbone families: UNet-based diffusion models and Transformer/DiT-based models. In UNet-based models, text conditions are commonly injected through cross-attention layers, making attention maps a natural signal for localizing editable regions. In DiT-based models such as FLUX, image and text information are represented as tokens and interact through transformer attention blocks, so localization and control are often implemented through token-level features, position encodings, attention modulation, or denoising trajectories. Although these architectures differ, they share the same core challenge: how to identify the region that should change while preserving the rest of the image.

**PartEdit: Fine-Grained Image Editing using Pre-Trained Diffusion Models** ([paper](https://arxiv.org/abs/2502.04050), [project](https://gorluxor.github.io/part-edit/), [code](https://github.com/Gorluxor/partedit)) represents the UNet-based localization approach. It keeps the base diffusion model frozen and optimizes special part tokens, such as `<car-hood>` or `<animal-head>`, whose attention maps correspond to object parts. These token-induced masks are then used to blend source and edited features. This directly addresses part-level editing, but its localization depends on learned part tokens and mask supervision, which may limit generalization to unseen or user-defined parts without additional token optimization.

**OminiControl: Minimal and Universal Control for Diffusion Transformer** ([paper](https://arxiv.org/abs/2411.15098), [code](https://github.com/Yuanshi9815/OminiControl)) represents a trained DiT-control approach. It adapts a FLUX-style DiT to accept additional image conditions together with text prompts by combining condition tokens and image tokens. It uses dynamic position encoding to distinguish spatially aligned controls from non-aligned subject controls, and attention-bias control to adjust how strongly the condition influences generation. This shows that DiT models can support flexible conditional control, but the control mechanism is learned through training rather than discovered from a source/edit trajectory at inference time.

**Follow-Your-Shape / EditAnyShape** ([project](https://follow-your-shape.github.io/), [code](https://github.com/mayuelala/FollowYourShape)) is closest to this project because it is training-free and mask-free. It computes a Trajectory Divergence Map from token-wise velocity differences between the source-prompt inversion trajectory and the target-prompt denoising trajectory. This TDM acts as a soft edit-region estimate and guides KV injection for shape-aware editing. However, its benchmark mainly evaluates object-level or foreground-level transformations, leaving open whether this trajectory-derived soft mask is precise enough for local edits inside or attached to the same object.

**Rethinking Where to Edit: Task-Aware Localization for Instruction-Based Image Editing** ([paper](https://arxiv.org/abs/2604.20258)) and recent mask-free local editing work such as **AdaptEdit / Edit Where You Mean** ([paper](https://arxiv.org/abs/2604.23763)) mainly motivate the evaluation side of this project. They argue that modern DiT editors can follow global instructions while leaking local edits into irrelevant regions, and that localization should be evaluated separately from global image quality or text-image alignment. This supports the need for a focused diagnostic benchmark for fine-grained over-editing within an otherwise preserved object.

## Technical Gap

The related work suggests three different ways to localize edits: learned part-token masks in UNet models, trained conditional control in DiT models, and training-free trajectory-derived soft masks. However, these lines leave a specific question unanswered for Follow-Your-Shape-style editing.

Follow-Your-Shape uses the divergence between source and target denoising trajectories to infer where an edit should happen. This is effective for foreground or object-level shape transformations, where the semantic change usually corresponds to a large visible region. Fine-grained object-preserving edits are different: the target region may occupy only a small area of the object or an accessory attached to it, while the rest of the same object should remain unchanged. In this setting, the trajectory divergence signal may either over-expand to the whole object or become too weak to isolate the intended local change.

The technical gap is therefore not whether Follow-Your-Shape is object-aware, but whether its object-aware localization is precise enough below the object level, without learned part tokens, user masks, or retraining.

## Proposed Experiment

I propose a small diagnostic experiment that can be completed in 2-3 weeks. The experiment treats Follow-Your-Shape as the method under diagnosis rather than only as a black-box baseline. The goal is to test whether its trajectory-derived TDM remains localized when the desired change is below object level.

### Dataset

The experiment has two complementary subsets.

**PartEdit-Bench mask diagnostic subset** ([dataset](https://huggingface.co/datasets/Aleksandar/PartEdit-Bench)). I will select 10-20 cases from PartEdit-Bench where the provided ground-truth part mask corresponds to a visible local region, such as animal head, human hair, car hood, or chair seat. These cases allow direct evaluation of whether Follow-Your-Shape's TDM or thresholded edit mask matches a benchmark part mask. Each case will be converted into the Follow-Your-Shape input format using the provided original prompt as the source prompt and the changed prompt as the target prompt.

**ReShapeBench-derived local-edit subset** ([dataset](https://huggingface.co/datasets/3087richard/ReShapeBench)). I will start from the 70 single-object images in ReShapeBench, since this is the native evaluation style of Follow-Your-Shape. I will select 20-30 images where the foreground object is large enough to support a visible local edit. For each image, I will keep the source image and source prompt, then create a new target prompt that changes only a small component inside or attached to the same object. Following the ReShapeBench construction style, a VLM such as Qwen may be used to draft candidate target prompts, but all prompts will be manually checked and revised. The original ReShapeBench masks are object-level and will be used only as reference preservation regions. For the new local edits, I will create rough local-region masks manually for evaluation only; these masks will not be used as model input.

The ReShapeBench-derived cases will cover three edit types: accessory addition/removal/replacement, surface or label/logo/text editing, and small functional-part editing. I will also keep a few original ReShapeBench object-level cases as sanity checks.

Example prompt pair:

**Source prompt:** A brown teddy bear sits on a wooden chair in a softly lit bedroom. The teddy bear has round ears, brown fur, black eyes, and a stitched smile. The chair, bed, and warm background lighting remain visible.
**Target prompt:** A brown teddy bear sits on a wooden chair in a softly lit bedroom, wearing a red scarf around its neck. The teddy bear has round ears, brown fur, black eyes, and a stitched smile. The chair, bed, and warm background lighting remain visible.
**Instruction:** Add a red scarf around the teddy bear's neck.

### Methods And Baselines

Because editing methods use different input formats, I will separate matched baselines from reference baselines rather than treat the experiment as a single leaderboard.

**Follow-Your-Shape / EditAnyShape** ([code](https://github.com/mayuelala/FollowYourShape)) is the primary method under diagnosis. Its input format is the main setting of this study: source image, source prompt, and target/edit prompt. I will evaluate both its final edited image and, if accessible from the code, its intermediate TDM or thresholded edit mask.

**Matched editing baselines from Follow-Your-Shape.** I will first attempt one or two baselines used in the Follow-Your-Shape paper, prioritizing methods with public code, compatible image-editing inputs, and feasible compute, such as FlowEdit, KV-Edit, or PnPInversion. These are preferable to generic instruction-editing models because they are closer to the source-image/source-prompt/target-prompt setting.

**Reference baselines.** If matched baselines are not runnable within the 2-3 week window, I will use **InstructPix2Pix** ([code](https://github.com/timothybrooks/instruct-pix2pix)) as a lightweight no-mask instruction-editing reference, using the concise instruction derived from the same source/target prompt pair. I will also use oracle-mask inpainting as an upper-bound reference, where the rough local mask is provided to test whether the edit is feasible when localization is known. This is not a fair mask-free baseline, but it helps separate localization failure from generation failure.

**PartEdit** ([code](https://github.com/Gorluxor/partedit)) will be evaluated only on a small compatible subset if its released part-token categories overlap with the selected cases. It will not be used as a full baseline for accessories, labels, or logos because those local regions are outside its fixed part categories.

### Evaluation Metrics

For the PartEdit-Bench mask diagnostic subset, I will evaluate the TDM as a localization signal:

- **Mask IoU:** IoU between the thresholded TDM/edit mask and the ground-truth part mask.
- **Soft-mask AUC/AP:** ranking quality of the continuous TDM against the part mask, avoiding dependence on one threshold.
- **Mask size ratio:** area of the predicted edit mask divided by area of the ground-truth local mask, to detect over-expansion to the whole object.

For the edited images, I will evaluate three regions: the target local region, the remaining object region, and the background.

- **Semantic alignment:** CLIP similarity for the full edited image/target prompt, plus an auxiliary padded local-crop CLIP score; both are treated as supporting signals rather than primary judgments.
- **Human local edit success:** a 0-2 score for whether the requested local component is correctly edited.
- **Object preservation:** LPIPS/SSIM on the non-edited object region (`object mask - local mask`), with optional DINO similarity for structural consistency.
- **Background preservation:** LPIPS/SSIM on the region outside the object mask, following the preservation metrics used in Follow-Your-Shape.
- **Change localization ratio:** fraction of source-to-edit visual change that lies inside the local edit mask, reported together with local edit success to avoid rewarding no-change outputs.
- **Failure category:** over-expanded localization, weak localization, generation failure, boundary leakage, or object/background drift.

### Representative Results And Failure Cases

I will include real pilot outputs rather than assumed results. The report will select representative successful and failed cases based on the measured localization and preservation scores. For each example, I will show the source image, source prompt, target prompt, edited result, and the available localization evidence, such as the TDM, thresholded edit mask, PartEdit-Bench ground-truth mask, or manually annotated rough local mask. The failure analysis will focus on whether errors come from over-expanded localization, weak localization where the local component is not edited, reasonable localization but poor generation quality, or boundary leakage into nearby object or background regions.

### Success Criterion

The 2-3 week pilot succeeds if it produces:

- a reproducible diagnostic set with 10-20 PartEdit-Bench mask cases and 10-20 ReShapeBench-derived local-edit cases;
- Follow-Your-Shape results on at least 5-10 pilot cases, including final edited images and TDM/edit masks if accessible;
- at least one comparison result from either a matched Follow-Your-Shape baseline, if runnable, or a clearly labeled reference baseline such as InstructPix2Pix or oracle-mask inpainting;
- a compact table reporting TDM localization quality, local edit success, object preservation, background preservation, and failure category;
- representative success and failure cases showing whether errors come from over-expanded localization, weak localization, or generation failure.

A useful outcome does not require showing that Follow-Your-Shape fails. The project succeeds if it measures whether trajectory-guided object-aware localization remains precise below the object level and identifies the main failure modes.
