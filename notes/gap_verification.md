# Gap Verification: Follow-Your-Shape / ReShapeBench

Date: 2026-08-05

## Sources Checked

- Follow-Your-Shape project page: https://follow-your-shape.github.io/
- Paper HTML: https://arxiv.org/html/2508.08134v4
- Paper abstract page: https://arxiv.org/abs/2508.08134
- Official code: https://github.com/mayuelala/FollowYourShape
- ReShapeBench dataset: https://huggingface.co/datasets/3087richard/ReShapeBench
- ReShapeBench metadata files:
  - `single_object/metadata.jsonl`
  - `multi_object/metadata.jsonl`

## What Follow-Your-Shape Already Covers

Follow-Your-Shape is directly relevant to the proposed topic. It is a training-free and mask-free shape-aware image editing method. Its main mechanism is trajectory-guided region control: it computes a Trajectory Divergence Map (TDM) from source/edit trajectory differences and uses scheduled KV injection to preserve non-target content while editing the target region.

The paper does cover multi-object editing:

- The abstract/project page state that the examples include both single-object and multi-object cases.
- ReShapeBench contains 120 new images:
  - 70 single-object scenes.
  - 50 multi-object scenes.
- Each new image has two edit cases, giving 240 cases across the single- and multi-object subsets.
- The Hugging Face dataset states that `multi_object` contains images with multiple salient objects where only one object should be edited while the remaining scene stays consistent.

Therefore, the proposed project must not claim that Follow-Your-Shape ignores multi-object editing.

## What The Dataset Actually Looks Like

The `multi_object/metadata.jsonl` file contains 100 entries. The `num_objects` distribution is:

- 1 object: 4 entries.
- 2 objects: 34 entries.
- 3 objects: 34 entries.
- 4 objects: 20 entries.
- 5 objects: 6 entries.
- 6 objects: 2 entries.

The multi-object set is mostly "one chosen foreground object plus other surrounding objects." Examples include:

- Change the cat-face pillow into a round striped cushion, while a real cat and another pillow remain in the scene.
- Change the metal sugar bowl into a ceramic jar, while other tableware and hands remain.
- Change the large striped hot air balloon into a blimp, while other balloons remain in the background.
- Change the empty blue coffee grinder, while another blue coffee grinder remains.

This means the benchmark does include some target selection among multiple objects, including a few cases with same-category distractors.

## What It Does Not Systematically Isolate

The paper and dataset do not appear to systematically isolate part-level region control as a primary evaluation factor.

Specific missing or under-isolated cases:

- Removing or changing a small accessory while preserving the main object.
- Changing a product label, logo, or printed pattern while preserving the object shape and material.
- Changing a small functional part, such as headlights, laces, handles, or buttons.
- Measuring whether the edit spreads from the intended part to the whole object.
- Measuring part-level edit success separately from whole-object preservation.

The existing ReShapeBench metrics are:

- Aesthetic Score for image quality.
- PSNR and LPIPS for background preservation.
- CLIP similarity for text-image alignment.

These metrics do not directly answer whether only the intended object part was edited.

## Important Limitation Mentioned By The Paper

The paper explicitly states that the method can be sensitive to prompt ambiguity and imprecise editing instructions. It says vague or low-specificity prompts can lead to weak, diffuse, or inconsistent edits, and that clear descriptions are important for reliable performance.

This supports our proposed topic, but it also means the gap should be framed as a follow-up diagnostic study of a boundary condition, not as a completely undiscovered weakness.

## Code / Experiment Feasibility

The official GitHub repository provides command-line editing scripts and toy tests. The README recommends running experiments on a single A100 GPU. The provided toy tests mainly cover simple replacement examples, including some two-object cases, but they do not provide a ready-made crowded 4-5 similar-object target-selection benchmark.

This implies:

- The official code is relevant and reproducible in principle.
- Full reproduction may be compute-heavy.
- A 2-3 week mini-project should be framed as a small diagnostic benchmark and pilot evaluation, not as full reproduction or new model training.

## Verified Gap Statement

Safe version:

> Follow-Your-Shape introduces a strong training-free mechanism for mask-free shape-aware image editing and evaluates it on ReShapeBench, including multi-object scenes where one designated object is edited. However, its benchmark primarily targets object-level shape transformations rather than part-level edits inside an object. I propose a lightweight diagnostic benchmark to evaluate whether trajectory-guided region control can localize small part-level changes, such as accessories, labels, logos, and functional components, without over-editing the whole object.

Unsafe version to avoid:

> Follow-Your-Shape does not handle multi-object editing.

This is false because the paper and ReShapeBench explicitly include multi-object cases.

Also avoid:

> Follow-Your-Shape cannot do part-level editing.

This has not been proven. The safe claim is that part-level localization is not systematically evaluated as the main benchmark factor.
