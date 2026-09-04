# Data

This directory stores fixed PartEdit-Bench manifests and the portable case
archive used by the experiments.

The held-out comparison uses every record in the PartEdit-Bench `synth` split
at dataset revision `v1.1` (commit
`e6e132f8bb32bec49269ae979659f2bab341e813`). Its tracked inputs are:

- `partedit_subset/synth_60_frozen_manifest.json`: all dataset indices `0..59`.
- `partedit_subset/synth_60_frozen_manifest.meta.json`: source Parquet and
  manifest SHA-256 checksums.
- `partedit_subset/synth_60_footprint_labels.csv`: pre-output footprint labels.

The footprint labels were assigned from prompts, part/edit labels, and source
images only, then manually reviewed on 2026-09-04 before formal generation.
Their frozen distribution is 1 contraction, 46 comparable, and 13 expansion
cases. After any output is inspected, the frozen protocol prohibits changing
them.

Build the local pre-generation review page from the frozen manifest and current
labels:

```bash
python core/scripts/build_footprint_review.py
```

Open
`core/results/heldout_control_comparison/footprint_label_review.html` to audit
the frozen labels or repeat the review. The page shows only source images and
prompt metadata; it intentionally excludes GT masks, PartEdit references, and
generated outputs.

The main experiment uses a fixed 12-case subset balanced by target part size:

- 4 small-part cases.
- 4 medium-part cases.
- 4 large-part cases.

The 12-case subset is derived from the reviewed 20-case manifest without
changing source images, masks, or prompts.

Tracked contents:

- `partedit_subset/pilot_manifest.json`: original 20-case reviewed pilot.
- `partedit_subset/pilot_12_manifest.json`: fixed controlled-revision subset.
- `partedit_subset/pilot_12_manifest.csv`: tabular copy of the same 12 cases.
- `../artifacts/partedit_pilot_12_cases_strict.tar.gz`: portable archive of
  the exact selected case files required by the 12-case manifest.

Runtime-only contents, created when preparing data:

- `images/`: local source images, ignored by git.
- `masks/`: local ground-truth part masks, ignored by git.
- `partedit_subset/cases/`: extracted source images, GT masks, PartEdit
  references, and metadata for the selected cases. This directory is ignored
  to avoid duplicating the tracked archive.

To restore the selected case files from a fresh clone, run from the project
root:

```bash
tar -xzf core/artifacts/partedit_pilot_12_cases_strict.tar.gz
```

To export the held-out synth split from the fixed Hugging Face Parquet shard:

```bash
curl -L --fail -o /tmp/partedit-synth-v1.1.parquet \
  https://huggingface.co/datasets/Aleksandar/PartEdit-Bench/resolve/v1.1/data/synth-00000-of-00001.parquet

uv run --with pyarrow python core/scripts/prepare_partedit_synth60.py \
  --parquet /tmp/partedit-synth-v1.1.parquet \
  --footprint-labels core/data/partedit_subset/synth_60_footprint_labels.csv \
  --footprint-labels-reviewed \
  --manifest core/data/partedit_subset/synth_60_frozen_manifest.json
```
