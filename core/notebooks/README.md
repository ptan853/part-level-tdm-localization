# Notebooks

This directory contains the dataset inspection and final evaluation notebooks.

## Notebooks

- `01_inspect_partedit_bench.ipynb`: inspect PartEdit-Bench fields, mask formats, and candidate case sizes before running Follow-Your-Shape.
- `02_evaluate_fys_tdm_localization.ipynb`: early single-seed TDM exploration, kept for audit trail.
- `03_evaluate_controlled_revision.ipynb`: final 12-case x 3-seed evaluation, metric tables, and qualitative figures.

## Environment

From the repository root:

```bash
uv sync
uv run python -m ipykernel install --user --name part-level-tdm-localization --display-name "part-level-tdm-localization"
uv run jupyter lab
```

GPU inference dependencies for Follow-Your-Shape should be installed separately on the GPU machine.
