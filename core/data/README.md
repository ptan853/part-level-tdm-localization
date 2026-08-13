# Data

This directory stores the fixed PartEdit-Bench manifests and the portable case
archive used by the experiment.

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
