# Part-Level TDM Localization in Shape-Aware Image Editing

## Research Question

When a prompt asks for a small part-level edit inside an object, does the trajectory divergence signal used by Follow-Your-Shape precisely localize the intended part, or does it spread to the full object?

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

## Layout

- `core/`: experiment code, configuration, data manifests, third-party code, results, and final reports.
- `notes/`: background notes, prior email drafts, related-work summaries, and planning documents.

## Local Analysis Environment

Use `uv` for lightweight local analysis:

```bash
uv sync
uv run python -m ipykernel install --user --name part-level-tdm-localization --display-name "part-level-tdm-localization"
uv run jupyter lab
```

This environment is for notebooks, dataset inspection, subset selection, and evaluation utilities. GPU inference dependencies for Follow-Your-Shape should be installed separately on the rented GPU server.

## Core Workflow

1. Add a Follow-Your-Shape fork or submodule under `core/third_party/`.
2. Select the PartEdit-Bench pilot subset under `core/data/partedit_subset/`.
3. Add run configuration under `core/configs/`.
4. Save generated artifacts under `core/results/`.
5. Summarize quantitative tables and representative cases under `core/reports/`.

## Status

Scaffold only. No experiment code has been added yet.
