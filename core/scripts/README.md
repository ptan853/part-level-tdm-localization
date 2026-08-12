# Scripts

This directory contains runner and evaluation scripts for the PartEdit pilot.

## Follow-Your-Shape Pilot Runner

Preview the first manifest case without launching the model:

```bash
python core/scripts/run_fys_pilot.py --limit 1
```

Run the first case on a GPU machine:

```bash
python core/scripts/run_fys_pilot.py --limit 1 --execute
```

Preview Harry Yang's controlled-revision run matrix without launching the model:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2
```

Run the controlled revision:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --execute
```

Run a specific case:

```bash
python core/scripts/run_fys_pilot.py --case-uid real_0008 --execute
```

Run the oracle-mask variant:

```bash
python core/scripts/run_fys_pilot.py --case-uid real_0008 --oracle-mask --execute
```

The runner reads `core/data/partedit_subset/pilot_manifest.json` by default,
writes model outputs under `core/results/follow_your_shape/`, and keeps a
`run.log` per case. When `--seeds` is provided, each run is written to a
separate `seed_XXX` directory and gets its own `run_config.json`.

The runner also writes a command/config matrix to
`core/results/run_matrices/<manifest>_multi_seed.csv`. This table is intended
for reproducibility and should be the source for later evaluation tables.
