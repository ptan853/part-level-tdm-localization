# Repository Plan

## Project Goal

This repository will support a small reproducible diagnostic study requested by Professor Harry Yang:

> Does the trajectory divergence signal used by Follow-Your-Shape remain reliable below the object level, especially for part-level image edits?

The repository is intended to contain the experiment configuration, selected PartEdit-Bench cases, Follow-Your-Shape integration notes, evaluation protocol, and compact results.

## Current Scope

The immediate scope follows Harry's latest feedback:

- Use only 10-15 PartEdit-Bench cases.
- Balance cases across different part sizes.
- Run Follow-Your-Shape with several fixed seeds.
- Save per-step TDMs, aggregated soft TDM, final binary mask, and edited result.
- Evaluate localization quality versus part size.
- Include one simple localization comparison, such as the corresponding FLUX attention signal.
- Defer the second dataset and broad editing baselines.

## Repository Layout

```text
part-level-overediting/
  third_party/
    FollowYourShape/        # future fork/submodule of the original implementation
  configs/
    README.md               # experiment configuration notes
  data/
    partedit_subset/         # selected case manifest and metadata
    images/                  # local source images, ignored by git
    masks/                   # local GT masks, ignored by git
  docs/
    README.md                # research notes and method documentation
  reports/
    README.md                # final tables and representative cases
  results/
    .gitkeep                 # generated outputs, ignored by git by default
  scripts/
    README.md                # future runner/evaluation scripts
```

## Planned Deliverables

- A fixed PartEdit-Bench subset manifest.
- Exact environment and command documentation.
- Follow-Your-Shape patch notes for saving TDM artifacts.
- Quantitative table with AP, IoU, predicted-to-GT area ratio, local edit success, and outside-part preservation.
- Representative successful and failed examples.
- A compact follow-up note/email for Harry.

## Non-Goals For The First Submission

- Training a new model.
- Building a new dataset from scratch.
- Running broad image editing baselines.
- Extending to video generation.
