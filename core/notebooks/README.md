# Notebooks

This directory contains lightweight, reader-facing notebooks for local dataset inspection and experiment planning.

## Current Notebook

- `01_inspect_partedit_bench.ipynb`: inspect PartEdit-Bench fields, mask formats, and candidate case sizes before running Follow-Your-Shape.

## Environment

From the repository root:

```bash
uv sync
uv run python -m ipykernel install --user --name part-level-tdm-localization --display-name "part-level-tdm-localization"
uv run jupyter lab
```

The notebook environment is intentionally lightweight. GPU inference dependencies for Follow-Your-Shape should be installed separately on the rented GPU server.
