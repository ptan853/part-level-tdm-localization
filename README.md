# Part-Level TDM Localization in Shape-Aware Image Editing

## Working Title

**Part-Level TDM Localization in Trajectory-Guided Mask-Free Image Editing**

## One-Sentence Research Question

When a prompt asks for a small part-level edit inside an object, does the trajectory divergence signal used by Follow-Your-Shape precisely localize the intended part, or does it spread to the full object?

## Motivation

Follow-Your-Shape / EditAnyShape studies training-free, mask-free shape-aware image editing. Its core idea is to infer editable regions from the difference between the source-prompt inversion trajectory and the target-prompt denoising trajectory, then use scheduled KV injection to preserve non-target regions while changing the intended object.

The open question for this project is not whether object-level shape editing works. The narrow question is whether the same trajectory-guided region control can remain precise when the intended edit affects only a small component of an object, such as a hat, label, logo, handle, light, strap, or accessory.

## Technical Gap

Existing shape-aware image editing work primarily evaluates object-level structural transformation, where the edited region is usually the whole foreground object or a clearly designated object. It does not appear to systematically isolate part-level edits where only a small component inside the object should change while the rest of the object remains fixed. In these cases, the trajectory divergence map may spread from the intended part to the full object, causing over-editing.

This project will treat that as a diagnostic gap rather than proposing a new large model.

## Current Execution Scope

The next execution step follows Harry Yang's latest feedback:

- Image editing, not video generation.
- 10-15 PartEdit-Bench cases, balanced across target part sizes.
- Follow-Your-Shape as the main method.
- Several fixed seeds.
- Per-step TDMs, aggregated soft TDM, final binary mask, and edited result saved for every run.
- Localization analysis versus part size.
- One lightweight localization comparison, such as the corresponding FLUX attention signal.
- No new model training.
- No broad baseline sweep in the first submission.

## Example Tasks

### Remove Or Change An Accessory

- Source: a teddy bear wearing a red hat.
- Edit: remove the red hat; keep the teddy bear unchanged.

### Change A Product Label

- Source: a Coca-Cola can on a table.
- Edit: change the label into a plain white label; keep the can shape and background unchanged.

### Change A Small Functional Part

- Source: a car parked on a street.
- Edit: change only the headlights into round headlights; keep the car body unchanged.

### Change A Logo Or Pattern

- Source: a mug with a star logo.
- Edit: replace the star logo with a heart logo; keep the mug unchanged.

## Expected Failure Modes

- The whole object changes when only one part should change.
- The intended part is not changed.
- The part is changed but the object's shape, color, or identity drifts.
- Background or neighboring regions are damaged.
- The inferred edit mask is too large, too small, or spatially fragmented.

## Metrics

- **Average precision:** soft TDM localization quality against the PartEdit-Bench target mask.
- **IoU:** overlap between the final binary mask and the target part mask.
- **Predicted-to-GT area ratio:** whether the predicted editable region is too large or too small.
- **Local edit success:** whether the requested part edit is visible in the edited image.
- **Outside-part preservation:** whether regions outside the target part remain stable.
- **Failure category:** over-expanded localization, under-localization, boundary leakage, edit failure, or object/background drift.

## Planned Execution

1. Set up a reproducible GitHub repository.
2. Fork or clone Follow-Your-Shape under `third_party/`.
3. Select 10-15 PartEdit-Bench cases by target mask area.
4. Patch Follow-Your-Shape only to save required TDM artifacts.
5. Run a one-case smoke test on rented GPU.
6. Run the full 10-15 case pilot once the pipeline is stable.
7. Produce a compact quantitative table and representative success/failure cases.

## Project Files

- `README.md`: current project definition and execution scope.
- `REPOSITORY_PLAN.md`: GitHub-ready repository plan.
- `related_work.md`: closest related papers and what gap remains.
- `experiment_plan.md`: dataset, prompts, baseline, metrics, and success criterion.
- `harry_note.md`: final 1-2 page English note draft.
- `reply_email.md`: concise email to Harry attaching or linking the note.
- `configs/`: planned experiment settings.
- `data/`: PartEdit-Bench subset metadata and local data placeholders.
- `third_party/`: future Follow-Your-Shape fork/submodule.
- `results/`: generated outputs, ignored by git by default.
- `reports/`: compact final tables and representative examples.
