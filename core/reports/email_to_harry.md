Subject: Controlled revision for part-level FYS localization

Dear Professor Yang,

Thank you for the concrete feedback. I completed the controlled revision following your requested protocol.

I fixed a 12-case PartEdit-Bench subset balanced by part size, ran three fixed seeds per case, recorded the seeds/configurations/logs, and added a simple FLUX target-token attention localization baseline. I also added local-edit success and outside-target preservation evaluation instead of relying only on image-difference mass inside the GT mask.

The main result is that FYS-TDM still shows the same over-localization trend, especially for small parts. In the controlled 12-case x 3-seed run, small-part FYS-TDM has low IoU and high predicted/GT area ratio, while the simple FLUX target-token attention signal is often more spatially concentrated. This suggests that trajectory divergence is useful but can be too coarse for part-level localization.

I have included the compact comparison table, representative successful and failed cases, and reproducibility instructions in the repository:

https://github.com/ptan853/part-level-tdm-localization

The main files are:

- `core/reports/final_note.md`
- `core/notebooks/03_evaluate_controlled_revision.ipynb`
- `core/results/controlled_revision/compact_fys_summary_for_harry.csv`
- `core/results/controlled_revision/figures/representative_case_candidates_sheet.jpg`

Best regards,
Peifeng Tan
