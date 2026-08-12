# Configs

This directory holds experiment configuration files, including case lists,
fixed seeds, Follow-Your-Shape parameters, output paths, and evaluation
settings.

## Controlled Revision

`fys_controlled_revision.json` records the setup:

- Manifest: `core/data/partedit_subset/pilot_12_manifest.json`.
- Seeds: `0, 1, 2`.
- FYS parameters: `flux-dev`, `guidance=2.0`, `num_steps=15`, `front=2`,
  `inject=4`, no ControlNet, no oracle mask.
- Follow-Your-Shape submodule base revision:
  `47b574cee0aa72466576a834f4e24d5999816f26`.
- Local FYS patch: `src/edit.py` adds `--seed` support and seeds Python,
  NumPy, PyTorch, and CUDA RNGs. Commit this patch in the FollowYourShape fork
  before remote reproduction, then update the pinned revision.

Use `core/scripts/run_fys_pilot.py` to execute this configuration. The JSON
file is a reproducibility record rather than a separate executable format.
