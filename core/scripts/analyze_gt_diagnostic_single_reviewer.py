"""Analyze the user-authorized single-reviewer diagnostic without changing the protocol."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


METHODS = ['endpoint_auto', 'rk2_auto', 'endpoint_gt', 'rk2_gt',
           'rk2_n15_auto', 'rk2_n15_gt']
CONTRASTS = {
    'Endpoint GT - auto': {'endpoint_gt': 1, 'endpoint_auto': -1},
    'RK2 GT - auto': {'rk2_gt': 1, 'rk2_auto': -1},
    'RK2 - Endpoint (auto)': {'rk2_auto': 1, 'endpoint_auto': -1},
    'RK2 - Endpoint (GT)': {'rk2_gt': 1, 'endpoint_gt': -1},
    'Mask-by-controller interaction': {'rk2_gt': 1, 'rk2_auto': -1,
                                      'endpoint_gt': -1, 'endpoint_auto': 1},
    'RK2 N15 - N7 (auto)': {'rk2_n15_auto': 1, 'rk2_auto': -1},
    'RK2 N15 - N7 (GT)': {'rk2_n15_gt': 1, 'rk2_gt': -1},
}


def paired_intervals(frame, metrics, draws=10000, seed=20260908):
    cases = sorted(frame.case_uid.unique())
    info = frame.drop_duplicates('case_uid').set_index('case_uid').loc[cases]
    rng = np.random.default_rng(seed)
    strata = [np.flatnonzero(info.part_size.to_numpy() == size)
              for size in ['small', 'medium', 'large']]
    samples = np.concatenate([rng.choice(ids, (draws, len(ids)), replace=True)
                              for ids in strata if len(ids)], axis=1)
    records = []
    for metric in metrics:
        values = frame.pivot(index='case_uid', columns='method', values=metric).loc[cases, METHODS]
        assert np.isfinite(values.to_numpy(dtype=float)).all(), metric
        for name, weights in CONTRASTS.items():
            delta = sum(values[m].to_numpy(dtype=float) * w for m, w in weights.items())
            lo, hi = np.quantile(delta[samples].mean(axis=1), [0.025, 0.975])
            records.append(dict(contrast=name, metric=metric, difference=delta.mean(),
                                ci_low=lo, ci_high=hi, cases=len(cases)))
    return pd.DataFrame(records)


def main():
    root = Path(__file__).resolve().parents[2]
    base = root / 'core/results/gt_mask_diagnostic_v2'
    output = base / 'single_reviewer_analysis'
    score_path = base / 'human_ratings/reviewer_1_scores.csv'
    mapping_path = base / 'blinded_review/reviewer_1_private_mapping.csv'
    scores = pd.read_csv(score_path)
    mapping = pd.read_csv(mapping_path)
    rubric = ['local_edit_success_0_2', 'non_target_preservation_0_2',
              'overall_prompt_adherence_0_2', 'visual_quality_0_2']
    assert len(scores) == 354 and scores.review_uid.is_unique
    assert scores[rubric].isin([0, 1, 2]).all().all()
    assert set(scores.review_uid) == set(mapping.review_uid)
    frame = scores.merge(mapping, on='review_uid', validate='one_to_one')
    template = pd.read_csv(base / 'blinded_review/reviewer_1/review_template.csv').set_index('review_uid')
    for row in scores.to_dict('records'):
        expected = template.loc[row['review_uid']]
        for field in ['part', 'edit', 'source_prompt', 'target_prompt']:
            assert row[field] == expected[field]
        for field in ['source_image', 'candidate_image']:
            assert (base / 'blinded_review/reviewer_1' / row[field]).resolve() == Path(expected[field]).resolve()
    assert not frame.duplicated(['case_uid', 'method']).any()
    assert frame.groupby('case_uid').method.agg(set).map(lambda x: x == set(METHODS)).all()
    frame['joint_success'] = ((frame[rubric[0]] >= 1) & (frame[rubric[1]] >= 1)).astype(int)
    frame['strict_joint_success'] = ((frame[rubric[0]] == 2) & (frame[rubric[1]] == 2)).astype(int)
    metrics = rubric + ['joint_success', 'strict_joint_success']
    automatic_path = base / 'evaluation/automatic_metrics.csv'
    automatic = pd.read_csv(automatic_path)
    automatic = automatic[automatic.row_uid.isin(frame.row_uid)].copy()
    assert len(automatic) == 354 and automatic.row_uid.is_unique
    auto_metrics = [c for c in automatic if c.startswith(('strict_', 'buffered_'))]
    intervals = paired_intervals(frame, metrics)
    auto_intervals = paired_intervals(automatic, auto_metrics)
    summary = frame.groupby('method')[metrics].mean().reindex(METHODS)
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / 'reviewer_level_scores.csv', index=False)
    summary.to_csv(output / 'human_summary.csv')
    intervals.to_csv(output / 'human_paired_bootstrap.csv', index=False)
    auto_intervals.to_csv(output / 'automatic_paired_bootstrap.csv', index=False)
    automatic.groupby('method')[auto_metrics].mean().reindex(METHODS).to_csv(output / 'automatic_summary.csv')
    for group in ['footprint_change', 'part_size']:
        grouped = frame.groupby([group, 'method'])[metrics].mean()
        grouped['cases'] = frame.groupby([group, 'method']).size()
        grouped.to_csv(output / f'human_by_{group}.csv')
    manifest = pd.DataFrame(json.loads((root / 'core/data/partedit_subset/synth_60_frozen_manifest.json').read_text()))
    detailed = frame.merge(manifest[['case_uid', 'class_name']], on='case_uid', validate='many_to_one')
    detailed['edit_at_least_partial'] = detailed[rubric[0]].ge(1).astype(int)
    detailed['edit_complete'] = detailed[rubric[0]].eq(2).astype(int)
    for group, selected in [('part', detailed), ('head_class', detailed[detailed.part.eq('head')].rename(columns={'class_name': 'head_class'}))]:
        grouped = selected.groupby([group, 'method'])
        table = grouped[metrics + ['edit_at_least_partial', 'edit_complete']].mean()
        table['cases'] = grouped.size()
        for outcome in ['edit_at_least_partial', 'edit_complete', 'joint_success', 'strict_joint_success']:
            table[outcome + '_count'] = grouped[outcome].sum()
        table.to_csv(output / f'human_by_{group}.csv')
    provenance = {
        'reviewers': ['reviewer_1'], 'cases': frame.case_uid.nunique(),
        'ratings': len(frame), 'draws': 10000, 'seed': 20260908,
        'size_counts': frame.drop_duplicates('case_uid').part_size.value_counts().to_dict(),
        'deviation': 'User requested one reviewer after reviewer_1 ratings were supplied. Original protocol required two; no advisor approval of this change is asserted.',
        'uncertainty': 'Size-stratified paired case percentile intervals, conditional on reviewer_1. No reviewer-population inference or multiplicity correction.',
        'exposure': 'Anonymous side-by-side montages were supplied and inspected during the review period; order and influence on individual ratings cannot be reconstructed.',
        'interrater_agreement': 'Not estimable with one reviewer.',
        'input_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [score_path, mapping_path, automatic_path, Path(__file__)]},
    }
    (output / 'analysis_record.json').write_text(json.dumps(provenance, indent=2) + '\n')
    lines = ['# GT-mask diagnostic: single-reviewer analysis', '',
             '## Scope and deviation', '',
             'This is an exploratory analysis of 59 paired cases, six conditions and one reviewer (354 ratings). The user elected to stop at one reviewer after supplying scores. This deviates from the frozen two-reviewer plan and must be disclosed; it is not claimed to have advisor approval. The original protocol, old ratings and generation outputs are unchanged.', '',
             'Anonymous multi-output montages were available and inspected during the review period. Possible comparative exposure is an additional limitation. Inter-rater kappa cannot be calculated.', '',
             'The primary analysis remains the four N=7 controller-by-mask conditions; N=15 is supplementary. synth_0014 remains outside the paired set due to unavailable conditions. No score is imputed. One initially missing score was explicitly supplied by the user; the correction and raw export are retained.', '',
             '## Human results', '',
             '| Method | Local edit | Preservation | Prompt | Quality | Joint (%) | Strict joint (%) |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for method, row in summary.iterrows():
        nums = [row[c] for c in rubric] + [100*row[c] for c in metrics[-2:]]
        lines.append('| ' + method + ' | ' + ' | '.join(f'{v:.3f}' for v in nums) + ' |')
    lines += ['', '## Paired differences', '',
              '10,000 paired case bootstrap draws, seed 20260908, stratified by part size (20/19/20). All six conditions remain paired. Intervals are conditional on this reviewer, percentile 95%, and not multiplicity-adjusted. Joint differences are proportions, not points on the 0-2 rubric.', '',
              '| Contrast | Local edit [95% CI] | Preservation [95% CI] | Joint [95% CI] |',
              '| --- | --- | --- | --- |']
    for name in CONTRASTS:
        selected = intervals[intervals.contrast == name].set_index('metric')
        cells = []
        for metric in [rubric[0], rubric[1], 'joint_success']:
            r = selected.loc[metric]
            cells.append(f'{r.difference:.3f} [{r.ci_low:.3f}, {r.ci_high:.3f}]')
        lines.append('| ' + name + ' | ' + ' | '.join(cells) + ' |')
    lines += ['', '## Interpretation limits', '',
              'Source-part GT is not necessarily the target edit footprint. Improved preservation alone does not establish semantic success. These results do not establish general model incapability, an optimal duration, controller equivalence, or superiority across reviewers. Footprint-specific results (including expansion) and all four human criteria are retained in the accompanying CSVs.', '',
              'Automatic metrics reuse the completed evaluation without GPU recomputation. Strict and buffered regions remain fixed across methods; inside-region similarity is descriptive, not semantic success. See automatic_summary.csv and automatic_paired_bootstrap.csv.', '',
              '## Reproduce', '', 'From the repository root:', '',
              '```bash', '.venv/bin/python core/scripts/analyze_gt_diagnostic_single_reviewer.py', '```', '',
              'Input hashes and deviations: [analysis_record.json](analysis_record.json).', '']
    (output / 'README.md').write_text('\n'.join(lines))
    print(summary.to_string())
    print(intervals[intervals.metric.isin([rubric[0], rubric[1]])].to_string(index=False))
    print(output)


if __name__ == '__main__':
    main()
