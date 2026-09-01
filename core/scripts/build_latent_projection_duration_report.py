#!/usr/bin/env python3
"""Build the latent-state projection duration report from notebook 09 tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def format_value(value: float, digits: int = 3) -> str:
    return "NA" if pd.isna(value) else f"{value:.{digits}f}"


def build_report(repo_root: Path) -> str:
    eval_dir = repo_root / "core/results/control_operations_eval/latent_projection_all_cases_n0_n13"
    compact = pd.read_csv(eval_dir / "fys_vs_projection_key_durations.csv")
    localization = pd.read_csv(eval_dir / "fys_localization_summary.csv", index_col=0)

    table_rows = []
    for row in compact.itertuples():
        table_rows.append(
            "| {method} | {l1} | {psnr} | {ssim} | {lpips} | {inside} | {local} | {preserve} | {joint} |".format(
                method=row.method,
                l1=format_value(row.outside_mask_l1_aux),
                psnr=format_value(row.outside_mask_psnr, 2),
                ssim=format_value(row.outside_mask_global_ssim),
                lpips=format_value(row.outside_mask_lpips),
                inside=format_value(row.inside_mask_l1_aux),
                local=format_value(row.local_edit_mean),
                preserve=format_value(row.preservation_mean),
                joint="NA" if pd.isna(row.joint_success_rate) else f"{row.joint_success_rate:.1%}",
            )
        )

    n0 = compact[compact["method"] == "Oracle projection N=0"].iloc[0]
    n3 = compact[compact["method"] == "Oracle projection N=3"].iloc[0]
    n13 = compact[compact["method"] == "Oracle projection N=13"].iloc[0]
    outside_l1_reduction = 1 - n13.outside_mask_l1_aux / n0.outside_mask_l1_aux

    return f"""# Latent-State Projection Duration Study

## Objective

This experiment tests whether the control operation, rather than mask estimation alone, is a bottleneck in part-level editing. It compares the original FYS-TDM pipeline with an oracle-mask latent-state projection sweep over 12 locked cases.

## Control Strategy

The source image is inverted once to obtain aligned source states. Target-prompt denoising then follows the same 15-step schedule. For projection duration `N`, beginning at denoising step 2 and continuing for `N` consecutive steps:

```text
z_next = M_gt * z_target_next + (1 - M_gt) * z_source_aligned
```

Inside the GT part mask, the target trajectory is retained. Outside the mask, the state is projected back to the aligned source inversion state. `N=0` is the unprojected target-trajectory control. The experiment varies only `N`; the manifest, prompts, model, guidance, step count, and seed are fixed.

This is an oracle control-operation study. It does not claim automatic mask estimation.

## Evaluation Protocol

- 12 unique cases balanced across small, medium, and large parts.
- Original FYS is evaluated on 12 unique seed-0 outputs; the three stored seeds are identical and are not independent samples.
- Projection is evaluated at all durations `N=0..13`, producing 168 unique outputs.
- Image metrics use the exact implementation shared with notebooks 03 and 05.
- Human evaluation separates local semantic success from non-target preservation on a 0-2 rubric.

### Localization Diagnostic

Original FYS-TDM has mean IoU `{localization.loc['binary_iou', 'mean']:.3f}`, mean AP `{localization.loc['soft_ap', 'mean']:.3f}`, and mean predicted/GT area ratio `{localization.loc['pred_to_gt_area_ratio', 'mean']:.2f}`. Localization metrics are not assigned to oracle projection because its GT support is given rather than predicted.

## Quantitative Comparison

| Method | outside L1 ↓ | outside PSNR ↑ | outside SSIM ↑ | outside LPIPS ↓ | inside L1 | local edit ↑ | preservation ↑ | joint success ↑ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(table_rows)}

Inside L1 is descriptive edit activity, not semantic quality. Human local-edit scores determine whether a visible change realizes the requested edit.

![Unified image metrics](../results/control_operations_eval/latent_projection_all_cases_n0_n13/unified_image_metric_curves.png)

## Human Semantic Evaluation

![Human metric curves](../results/control_operations_eval/latent_projection_all_cases_n0_n13/unified_human_metric_curves.png)

N=3 gives the strongest observed compromise: local-edit score `{n3.local_edit_mean:.3f}/2`, preservation `{n3.preservation_mean:.3f}/2`, and joint success `{n3.joint_success_rate:.1%}`. Longer projection continues to improve pixel and perceptual preservation, but does not improve semantic realization. From N=0 to N=13, outside L1 falls by `{outside_l1_reduction:.1%}`, while the human local-edit mean falls from `{n0.local_edit_mean:.3f}` to `{n13.local_edit_mean:.3f}`.

## Qualitative Results

### Small parts

![Small-part comparison](../results/control_operations_eval/latent_projection_all_cases_n0_n13/unified_qualitative_small.jpg)

### Medium parts

![Medium-part comparison](../results/control_operations_eval/latent_projection_all_cases_n0_n13/unified_qualitative_medium.jpg)

### Large parts

![Large-part comparison](../results/control_operations_eval/latent_projection_all_cases_n0_n13/unified_qualitative_large.jpg)

## Findings

1. State projection provides substantially stronger non-target preservation than N=0 and, from N=2 onward, improves the mean outside-region metrics over original FYS.
2. The gain is monotonic for preservation but not for semantic editing. Stronger/longer projection can suppress the requested local transformation.
3. N=2 and N=3 are the useful pilot candidates; N=5 is a preservation-dominant ablation.
4. A correct oracle support mask is not sufficient for reliable part semantics. The remaining failures implicate the target generation/control dynamics, not only localization.

## Limitations

- 12 cases and one human reviewer.
- Human assessments are complete for all 168 projection outputs.
- The deterministic path provides no seed uncertainty despite three configured seed labels in earlier experiments.
- The repository's global SSIM is a selected-pixel proxy, not windowed SSIM.
- Outside LPIPS neutralizes the GT interior to match the established project protocol.

## Reproduction

Generate the complete duration sweep:

```bash
python core/scripts/run_latent_projection_duration_sweep.py \\
  --manifest core/data/partedit_subset/pilot_12_manifest.json \\
  --all-cases \\
  --durations 0-13 \\
  --execute
```

Compute all image metrics, requiring GPU LPIPS:

```bash
TORCH_HOME=/path/to/torch_cache python core/scripts/evaluate_latent_projection_against_fys.py --lpips require
```

Then execute [`09_evaluate_latent_projection_duration_sweep.ipynb`](../notebooks/09_evaluate_latent_projection_duration_sweep.ipynb). Full environment and model setup remain in the repository README.
"""


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    output = repo_root / "core/reports/latent_projection_duration_study.md"
    output.write_text(build_report(repo_root))
    print(output)


if __name__ == "__main__":
    main()
