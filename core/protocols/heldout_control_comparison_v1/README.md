# Held-Out Control Comparison v1

This directory is the pre-generation evidence bundle for the frozen 60-case
comparison.

- `command_matrix.csv`: portable 300-row command matrix. `${REPO_ROOT}` denotes
  the checked-out repository root.
- `reviewer_randomization.csv`: two fixed, independently ordered 240-item
  reviewer assignments generated before any held-out output.
- `resolved_plans/`: the exact endpoint N=7, residual RK2 N=7, and supplemental
  endpoint N=3 control plans.
- `environment_lock.json`: checksums for the repository package metadata and
  the pinned FollowYourShape revision.
- `preflight_summary.json`: manifest, matrix, randomization, environment, and
  row-count checksums.

The committed `execution_commit` field is `null` because a Git commit cannot
contain its own final hash. The exact full commit SHA is supplied in the
pre-launch record and passed through `--execution-commit`; the runner verifies
that it equals the current `HEAD` before starting the first model command.
With `--execute`, `runtime_environment.json` is captured before generation.
