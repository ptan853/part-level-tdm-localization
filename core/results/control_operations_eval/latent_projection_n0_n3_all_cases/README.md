# Latent-Projection Duration Sweep: 12-Case Result

## Scope

This experiment compares projection durations `N=0,1,2,3` on the locked
12-case manifest at seed 0. `N=0` is the no-projection control. The remaining
settings project the latent state outside the oracle GT mask for the first
`N` controlled denoising steps.

All 48 runs passed artifact validation: each run has a generated image,
configuration, log, and control trace, with no recorded traceback.

## Aggregate Results

| N | Mean change inside GT | Retained inside change vs N=0 | Mean change outside GT | Reduced outside change vs N=0 |
|---:|---:|---:|---:|---:|
| 0 | 0.1215 | 100.0% | 0.0679 | 0.0% |
| 1 | 0.1045 | 86.0% | 0.0502 | 26.1% |
| 2 | 0.0927 | 76.3% | 0.0418 | 38.5% |
| 3 | 0.0895 | 73.7% | 0.0369 | 45.7% |

The automatic measurements show a monotonic preservation/edit-activity
tradeoff. Longer projection consistently reduces non-target pixel drift, but
also suppresses change inside the requested region. `N=2` is a plausible
middle setting, but these measurements do not establish it as a universally
best setting. Compared with `N=2`, `N=3` provides another 7.2 percentage points
of outside-change reduction while retaining 2.6 percentage points less inside
change.

## Interpretation

Inside-mask RGB change is an edit-activity proxy, not a semantic-success
metric. A method can retain substantial inside change while producing the
wrong concept, or produce little change because projection suppresses the
requested edit. The qualitative sheet shows this limitation for several
head-replacement cases. A final default duration should therefore be selected
using manual local-edit success together with these preservation measurements.

The current evidence supports three conclusions:

1. Latent projection is functioning as implemented: outside-mask drift falls
   as the controlled interval grows.
2. Projection alone does not guarantee target semantics; stronger projection
   can restore source structure while weakening the requested edit.
3. `N=2` should be treated as a candidate compromise for follow-up evaluation,
   not as a proven optimum.

## Artifacts

- `duration_sweep_metrics.csv`: one row per case and duration.
- `duration_sweep_summary.csv`: aggregate statistics across 12 cases.
- `duration_sweep_summary_by_part_size.csv`: small/medium/large breakdown.
- `duration_sweep_comparison.jpg`: source, GT visualization, N=0..3 outputs,
  and the prior long-control reference.
- `duration_sweep_change_curve.png`: per-case inside/outside pixel-change curves.
