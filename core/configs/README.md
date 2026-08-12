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
- Follow-Your-Shape submodule revision:
  `a323456378b0e70f0368c713d4a343c5a41d5a21`.

Use `core/scripts/run_fys_pilot.py` to execute this configuration. The JSON
file is a reproducibility record rather than a separate executable format.
