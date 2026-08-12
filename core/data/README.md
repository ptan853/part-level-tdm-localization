# Data

This project uses small selected subsets of PartEdit-Bench for execution-focused
Follow-Your-Shape diagnostics.

The original pilot subset contains 20 cases. The controlled revision requested
by Harry Yang uses a fixed 12-case subset balanced by target part size:

- 4 small-part cases.
- 4 medium-part cases.
- 4 large-part cases.

The 12-case subset is derived from the reviewed 20-case manifest without
changing source images, masks, or prompts. It is intentionally fixed before
rerunning the model, so later analysis does not cherry-pick cases based on
new results.

Tracked contents:

- `partedit_subset/pilot_manifest.json`: original 20-case reviewed pilot.
- `partedit_subset/pilot_12_manifest.json`: fixed controlled-revision subset.
- `partedit_subset/pilot_12_manifest.csv`: tabular copy of the same 12 cases.

Runtime-only contents, created when preparing data:

- `images/`: local source images, ignored by git.
- `masks/`: local ground-truth part masks, ignored by git.
