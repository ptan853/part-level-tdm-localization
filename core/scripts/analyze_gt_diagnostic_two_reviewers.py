"""Paired two-reviewer update; preserve original exports and single-reviewer results."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_gt_diagnostic_single_reviewer import METHODS, CONTRASTS, paired_intervals

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'core/results/gt_mask_diagnostic_v2'
OUT = BASE / 'two_reviewer_analysis'
REPORT = ROOT / 'core/reports/gt_mask_diagnostic_closeout/two_reviewer_update'
RUBRIC = ['local_edit_success_0_2', 'non_target_preservation_0_2',
          'overall_prompt_adherence_0_2', 'visual_quality_0_2']
METRICS = RUBRIC + ['joint_success', 'strict_joint_success']


def agreement(a, b):
    counts = np.zeros((3, 3), dtype=int)
    np.add.at(counts, (np.asarray(a, int), np.asarray(b, int)), 1)
    observed = counts / counts.sum()
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0))
    distance = np.abs(np.arange(3)[:, None] - np.arange(3)[None, :]) / 2
    denom = (distance * expected).sum()
    kappa = 1 - (distance * observed).sum() / denom if denom else np.nan
    return kappa, np.trace(observed), counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archived-inputs', action='store_true', help='Recompute from the report input archive without local generation assets')
    args = parser.parse_args()
    source = REPORT / 'inputs' if args.archived_inputs else BASE
    inputs = [Path(__file__), Path(__file__).with_name('analyze_gt_diagnostic_single_reviewer.py')]
    frames = []
    corrections_path = source / 'human_ratings/reviewer_2_corrections.json'
    corrections = json.loads(corrections_path.read_text())
    inputs.append(corrections_path)
    attestation_path = source / 'human_ratings/reviewer_2_review_attestation.json'
    attestation = json.loads(attestation_path.read_text())
    assert attestation['reviewer_id'] == 'reviewer_2' and attestation['independent_scoring']
    assert not any(attestation['exposure_before_or_during_review'].values())
    inputs.append(attestation_path)
    for reviewer in ['reviewer_1', 'reviewer_2']:
        filename = 'reviewer_1_scores.csv' if reviewer == 'reviewer_1' else 'reviewer_2_original.csv'
        score_path = source / 'human_ratings' / filename
        mapping_path = source / 'blinded_review' / f'{reviewer}_private_mapping.csv'
        template_path = source / 'blinded_review' / reviewer / 'review_template.csv'
        inputs.extend([score_path, mapping_path, template_path])
        scores = pd.read_csv(score_path, keep_default_na=False)
        assert len(scores) == 354 and scores.review_uid.is_unique
        if reviewer == 'reviewer_2':
            seen = set()
            for correction in corrections['corrections']:
                uid, field = correction['review_uid'], correction['field']
                assert (uid, field) not in seen
                seen.add((uid, field))
                assert correction['reviewer_identity_user_confirmed']
                index = scores.index[scores.review_uid.eq(uid)].item()
                assert index + 1 == correction['review_position']
                assert scores.loc[index, field] == correction['original_value'] == ''
                scores.loc[index, field] = str(correction['corrected_value'])
            assert len(seen) == 10
        scores[RUBRIC] = scores[RUBRIC].apply(pd.to_numeric)
        assert scores[RUBRIC].isin([0, 1, 2]).all().all()
        template = pd.read_csv(template_path).set_index('review_uid')
        mapping = pd.read_csv(mapping_path)
        assert set(scores.review_uid) == set(mapping.review_uid) == set(template.index)
        for row in scores.to_dict('records'):
            expected = template.loc[row['review_uid']]
            for field in ['part', 'edit', 'source_prompt', 'target_prompt']:
                assert row[field] == expected[field]
            for field in ['source_image', 'candidate_image']:
                if args.archived_inputs:
                    assert Path(row[field]).parts[-2:] == Path(expected[field]).parts[-2:]
                else:
                    assert (BASE / 'blinded_review' / reviewer / row[field]).resolve() == Path(expected[field]).resolve()
        frame = scores.merge(mapping, on='review_uid', validate='one_to_one')
        assert frame.reviewer_id.eq(reviewer).all()
        assert not frame.duplicated(['case_uid', 'method']).any()
        assert frame.groupby('case_uid').method.agg(set).map(lambda x: x == set(METHODS)).all()
        frame['joint_success'] = (frame[RUBRIC[0]].ge(1) & frame[RUBRIC[1]].ge(1)).astype(int)
        frame['strict_joint_success'] = (frame[RUBRIC[0]].eq(2) & frame[RUBRIC[1]].eq(2)).astype(int)
        frames.append(frame)
    frame = pd.concat(frames, ignore_index=True)
    assert frame.case_uid.nunique() == 59 and len(frame) == 708
    assert frame.groupby('row_uid').size().eq(2).all()
    assert frame.groupby('case_uid').part_size.nunique().eq(1).all()
    # Compute joint per reviewer before averaging, not by thresholding average scores.
    pooled = frame.groupby(['case_uid', 'method', 'part_size', 'part', 'footprint_change'])[METRICS].mean().reset_index()
    assert len(pooled) == 354
    summary = pooled.groupby('method')[METRICS].mean().reindex(METHODS)
    intervals = paired_intervals(pooled, METRICS)
    reviewer_intervals = pd.concat([paired_intervals(f, METRICS).assign(reviewer_id=f.reviewer_id.iloc[0]) for f in frames])
    paired = frames[0].merge(frames[1], on=['case_uid', 'method', 'row_uid'], suffixes=('_r1', '_r2'), validate='one_to_one')
    rows, disagreements, confusion = [], [], {}
    for field in RUBRIC:
        a, b = paired[field + '_r1'], paired[field + '_r2']
        kappa, exact, counts = agreement(a, b)
        rows.append(dict(criterion=field, linear_weighted_kappa=kappa, exact_agreement=exact, pairs=len(a)))
        confusion[field] = counts.tolist()
        for _, r in paired.loc[a.ne(b)].iterrows():
            disagreements.append(dict(case_uid=r.case_uid, method=r.method, criterion=field,
                                      reviewer_1=r[field+'_r1'], reviewer_2=r[field+'_r2'],
                                      absolute_difference=abs(r[field+'_r1']-r[field+'_r2'])))
    agreements = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    tables = {'reviewer_level_scores': frame, 'case_method_mean_scores': pooled,
              'human_summary': summary.reset_index(), 'human_paired_bootstrap': intervals,
              'reviewer_paired_bootstrap': reviewer_intervals,
              'reviewer_summary': frame.groupby(['reviewer_id', 'method'])[METRICS].mean().reset_index(),
              'agreement': agreements, 'disagreements': pd.DataFrame(disagreements)}
    for group in ['part', 'part_size', 'footprint_change']:
        grouped = pooled.groupby([group, 'method'])
        tables['human_by_'+group] = grouped[METRICS].mean().join(grouped.size().rename('cases')).reset_index()
    auto_path = source / 'evaluation/automatic_metrics.csv'
    inputs.append(auto_path)
    auto = pd.read_csv(auto_path)
    auto = auto[auto.row_uid.isin(frame.row_uid)].copy()
    assert len(auto) == 354 and auto.row_uid.is_unique
    auto_metrics = [c for c in auto if c.startswith(('strict_', 'buffered_'))]
    tables['automatic_summary'] = auto.groupby('method')[auto_metrics].mean().reindex(METHODS).reset_index()
    tables['automatic_paired_bootstrap'] = paired_intervals(auto, auto_metrics)
    for name, table in tables.items():
        table.to_csv(OUT / (name+'.csv'), index=False)
        table.to_csv(REPORT / (name+'.csv'), index=False)
    record = dict(cases=59, ratings=708, reviewers=2, corrections=10, draws=10000, seed=20260908,
                  size_counts=pooled.drop_duplicates('case_uid').part_size.value_counts().to_dict(),
                  uncertainty='Size-stratified paired case percentile CI; both reviewers and all conditions retained together. Conditional on these reviewers, not reviewer-population uncertainty. No multiplicity adjustment.',
                  reviewer_2_attestation=attestation,
                  limitations='Second-reviewer independence and absence of prior/during-review exposure are user-attested, not independently verified. Second review does not erase earlier single-reviewer reporting deviation or reviewer-1 comparative exposure.',
                  confusion_matrices=confusion,
                  input_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    for directory in [OUT, REPORT]:
        (directory/'analysis_record.json').write_text(json.dumps(record, indent=2)+'\n')
    labels = ['Endpoint auto N7', 'RK2 auto N7', 'Endpoint GT N7', 'RK2 GT N7', 'RK2 auto N15', 'RK2 GT N15']
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, metric, title in zip(axes, [RUBRIC[0], RUBRIC[1], 'joint_success'], ['Local edit (0-2)', 'Preservation (0-2)', 'Joint success (%)']):
        scale = 100 if metric == 'joint_success' else 1
        ax.barh(labels, summary[metric]*scale, color=['#327ba8']*4+['#888888']*2)
        for reviewer, marker in [('reviewer_1','o'), ('reviewer_2','x')]:
            vals = frame[frame.reviewer_id.eq(reviewer)].groupby('method')[metric].mean().reindex(METHODS)
            ax.scatter(vals*scale, np.arange(6), marker=marker, color='black', label=reviewer, zorder=3)
        ax.invert_yaxis(); ax.set_title(title); ax.set_xlim(0, 100 if scale==100 else 2)
        ax.grid(axis='x', alpha=.2)
    axes[0].legend(loc='upper center', bbox_to_anchor=(0.5, -0.10), ncol=2); fig.tight_layout()
    fig.savefig(REPORT/'human_results.png', dpi=160); plt.close(fig)
    lines = ['# GT-mask diagnostic: two-reviewer update', '',
             '## Scope', '',
             '59 paired cases, six conditions and two reviewers (708 image ratings). N=7 remains primary; RK2 N=15 remains supplementary. The unavailable synth_0014 case remains excluded. Generation outputs, frozen protocol and the original single-reviewer report are unchanged.', '',
             'Ten initially missing scores across seven images were subsequently completed by the same second reviewer. No scores were imputed. Original exports and amendment records were retained.', '',
             'Joint success means local edit >=1 AND preservation >=1 for an individual reviewer. Strict joint means both equal 2. These binary outcomes are computed before averaging reviewers.', '',
             '## Human results', '', '| Method | Local edit | Preservation | Prompt | Quality | Joint % | Strict joint % |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for method, r in summary.iterrows():
        values = [r[c] for c in RUBRIC]+[r[c]*100 for c in METRICS[-2:]]
        lines.append('| '+method+' | '+' | '.join(f'{v:.3f}' for v in values)+' |')
    lines += ['', '![Human results with separate reviewer markers](human_results.png)', '',
              'Bars show the two-reviewer average; circles and crosses show reviewer-specific means. These markers show disagreement, not confidence intervals.', '',
              '## Paired contrasts', '',
              '10,000 paired case draws, seed 20260908, within size strata 20/19/20. Both reviewers and all methods stay together within each sampled case. Percentile 95% intervals are conditional on these two reviewers and are not multiplicity-adjusted. Joint differences are proportions.', '',
              '| Contrast | Local edit [95% CI] | Preservation [95% CI] | Joint [95% CI] |', '| --- | --- | --- | --- |']
    for contrast in CONTRASTS:
        sub = intervals[intervals.contrast.eq(contrast)].set_index('metric')
        cells = [f'{sub.loc[m,"difference"]:.3f} [{sub.loc[m,"ci_low"]:.3f}, {sub.loc[m,"ci_high"]:.3f}]' for m in [RUBRIC[0], RUBRIC[1], 'joint_success']]
        lines.append('| '+contrast+' | '+' | '.join(cells)+' |')
    lines += ['', '## Reviewer agreement', '', '| Criterion | Linear weighted kappa | Exact agreement |', '| --- | ---: | ---: |']
    for r in rows:
        lines.append(f'| {r["criterion"]} | {r["linear_weighted_kappa"]:.3f} | {100*r["exact_agreement"]:.1f}% |')
    lines += ['', 'Agreement is descriptive over 354 paired outputs. Outputs share cases, so they are not 354 independent cases. Reviewer-level results and all disagreements are retained in reviewer_summary.csv, reviewer_paired_bootstrap.csv and disagreements.csv.', '',
              '## Interpretation and limitations', '',
              'At N=7, GT improves preservation versus auto for both controllers: Endpoint +0.364 [0.220, 0.517]; RK2 +0.305 [0.186, 0.432]. Local-edit differences remain uncertain: Endpoint +0.059 [-0.068, 0.186]; RK2 +0.008 [-0.127, 0.153]. Thus better mask quality helps preservation but does not, by itself, resolve semantic editing failures.', '',
              'Endpoint GT increases joint success by 11.86 percentage points [2.54, 22.03]; RK2 GT increases it by 7.63 points [-1.69, 16.95]. RK2-versus-Endpoint intervals span zero for local edit, preservation and joint success under both mask types. These results do not establish RK2 superiority or equivalence.', '',
              'Supplementary N=15 improves RK2 preservation with either mask. With auto masks, local edit decreases by 0.102 [-0.195, -0.008], while joint-success change remains uncertain. With GT, local-edit and joint-success changes also remain uncertain. Longer control is therefore not an established general improvement in joint editing utility.', '',
              'Visual quality has 99.4% exact agreement but kappa=0: reviewer 2 assigns 2 to every output and reviewer 1 differs on only two. With such a ceiling, expected agreement is already very high. Kappa=0 here should not be read as widespread disagreement or used as strong evidence of a discriminative quality rubric.', '',
              'The second reviewer evaluated the frozen outputs independently using the fixed rubric, with method identities concealed and without access to comparative montages, analysis reports, or the first reviewer\'s scores before or during evaluation. The first reviewer\'s prior exposure to comparative montages remains a potential source of bias. The initial single-reviewer analysis is retained as a documented deviation from the planned two-reviewer evaluation; the additional review does not remove these limitations.', '',
              'GT marks the source part, not necessarily the required target footprint. Better preservation alone does not establish successful target semantics. Intervals spanning zero do not prove equivalence. Part and size analyses are descriptive, not independently powered subgroup claims.', '',
              'Automatic measurements are reused without new GPU generation. Their summaries and paired intervals are included; adding a reviewer does not alter automatic measurements.', '',
              '## Reproduce', '', 'From the repository root, in a Python environment with numpy, pandas and matplotlib:', '', '```bash', 'python core/scripts/analyze_gt_diagnostic_two_reviewers.py --archived-inputs', '```', '',
              'The input archive supports statistical reproduction without GPU models or generated images. Archived mode checks image-role identifiers rather than machine-specific absolute paths; the original local analysis checked full path matches. To rerun against the original local review package, omit --archived-inputs. Source data and rating amendments are retained under inputs/.', '',
              'Input hashes and confusion matrices: [analysis_record.json](analysis_record.json). Original report: [single-reviewer closeout](../README.md).', '']
    (REPORT/'two_reviewer_report.md').write_text('\n'.join(lines))
    print(summary.to_string())
    print(intervals[intervals.metric.isin([RUBRIC[0], RUBRIC[1], 'joint_success'])].to_string(index=False))
    print(agreements.to_string(index=False))


if __name__ == '__main__':
    main()
