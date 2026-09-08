#!/usr/bin/env python3
"""Offline, explicitly available-case analysis of the completed held-out run.

Reads GPU-computed metrics and two blinded core-method reviews. Does not change
the frozen generation protocol or impute the missing output's human ratings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_heldout_reviews import (
    SCORE_FIELDS, add_derived_outcomes, evaluate_registered_success,
    weighted_cohen_kappa,
)

CORE_METHODS = ('original_fys_tdm', 'endpoint_projection', 'residual_rk2')


def bootstrap_table(frame, metrics, methods, iterations=10_000, seed=20260903):
    """Match the frozen RNG order, with array indexing instead of pandas iloc."""
    if iterations < 1:
        raise ValueError('iterations must be positive')
    strata = frame.drop_duplicates('case_uid').set_index('case_uid')['part_size']
    if frame.groupby('case_uid')['part_size'].nunique().ne(1).any():
        raise ValueError('inconsistent case strata')
    output = []
    for a, b in combinations(methods, 2):
        for metric in metrics:
            p = frame.groupby(['case_uid', 'method'])[metric].mean().unstack()
            p = p[[a, b]].dropna().join(strata)
            if p.empty or p.part_size.isna().any():
                raise ValueError(f'no valid paired cases for {a}, {b}, {metric}')
            groups = [(g[a] - g[b]).to_numpy() for _, g in p.groupby('part_size', sort=True)]
            rng = np.random.default_rng(seed)
            samples = np.empty(iterations)
            for i in range(iterations):
                samples[i] = np.concatenate([
                    g[rng.integers(0, len(g), size=len(g))] for g in groups
                ]).mean()
            output.append(dict(metric=metric, method_a=a, method_b=b,
                               difference=float((p[a] - p[b]).mean()),
                               ci_low=float(np.quantile(samples, .025)),
                               ci_high=float(np.quantile(samples, .975)),
                               iterations=iterations, paired_cases=len(p)))
    return pd.DataFrame(output)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(repo_root: Path, results: Path, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = repo_root / 'core/data/partedit_subset/synth_60_frozen_manifest.json'
    manifest = pd.DataFrame(json.loads(manifest_path.read_text()))
    metric_path = results / 'available_output_evaluation/evaluation_metrics.csv'
    all_path = results / 'available_output_evaluation/evaluation_metrics_all_records.csv'
    auto = pd.read_csv(metric_path)
    all_rows = pd.read_csv(all_path)
    expected = set(manifest.case_uid) - {'synth_0014'}
    methods = (*CORE_METHODS, 'endpoint_projection_n3')
    if len(manifest) != 60 or len(auto) != 236 or len(all_rows) != 240:
        raise ValueError('unexpected coverage; review before changing this analysis')
    if auto.row_uid.duplicated().any() or all_rows.row_uid.duplicated().any():
        raise ValueError('duplicate automatic records')
    for method in methods:
        if set(auto.loc[auto.method == method, 'case_uid']) != expected:
            raise ValueError(f'incomplete paired coverage: {method}')
    metric_columns = [c for c in auto if c.startswith(('strict_', 'buffered_'))]
    if not np.isfinite(auto[metric_columns].to_numpy()).all():
        raise ValueError('automatic metrics contain non-finite values')
    missing = all_rows[all_rows.status != 'evaluated']
    if len(missing) != 4 or set(missing.case_uid) != {'synth_0014'}:
        raise ValueError('unexpected missing output records')
    if not missing[metric_columns].isna().all().all():
        raise ValueError('missing images must not have imputed automatic metrics')
    frames, audit, inputs = [], [], [manifest_path, metric_path, all_path]
    for reviewer in ('reviewer_1', 'reviewer_2'):
        scores_path = results / f'two_reviewer_core_analysis/{reviewer}_core_scores.csv'
        map_path = results / f'blinded_review_available_outputs/{reviewer}_core_private_mapping.csv'
        scores, mapping = pd.read_csv(scores_path), pd.read_csv(map_path)
        inputs.extend([scores_path, map_path])
        if (len(scores) != 177 or scores.review_uid.duplicated().any()
                or mapping.review_uid.duplicated().any()
                or set(scores.review_uid) != set(mapping.review_uid)):
            raise ValueError(f'invalid reviewer mapping: {reviewer}')
        if not scores[list(SCORE_FIELDS)].isin([0, 1, 2]).all().all():
            raise ValueError(f'incomplete or invalid ratings: {reviewer}')
        d = add_derived_outcomes(scores.merge(mapping, on='review_uid', validate='one_to_one'))
        if set(d.method) != set(CORE_METHODS) or set(d.reviewer_id) != {reviewer}:
            raise ValueError('unexpected methods or reviewer identity')
        for method in CORE_METHODS:
            if set(d.loc[d.method == method, 'case_uid']) != expected:
                raise ValueError('incomplete human pairing')
        for row in d.to_dict('records'):
            m = manifest.set_index('case_uid').loc[row['case_uid']]
            folder = results / f'blinded_review_available_outputs/{reviewer}'
            source = repo_root / m.source_image
            candidate = results / row['method'] / row['case_uid'] / 'seed_000/img_0.jpg'
            checks = [digest(folder / row['source_image']) == digest(source),
                      digest(folder / row['candidate_image']) == digest(candidate),
                      row['source_prompt'] == m.source_prompt,
                      row['target_prompt'] == m.target_prompt]
            if not all(checks):
                raise ValueError(f'display mismatch: {row["review_uid"]}')
            audit.append(dict(reviewer_id=reviewer, review_uid=row['review_uid'],
                              case_uid=row['case_uid'], method=row['method'],
                              source_sha256=digest(source), candidate_sha256=digest(candidate),
                              display_verified=True))
        frames.append(d)
    human = pd.concat(frames, ignore_index=True)
    human_metrics = [*SCORE_FIELDS, 'joint_success', 'strict_joint_success']
    human.to_csv(output / 'reviewer_level_scores.csv', index=False)
    pd.DataFrame(audit).to_csv(output / 'display_audit.csv', index=False)
    human_summary = human.groupby('method')[human_metrics].mean().reindex(CORE_METHODS)
    human_summary.to_csv(output / 'human_summary.csv')
    auto.groupby('method')[metric_columns].mean().reindex(methods).to_csv(output / 'automatic_summary.csv')
    for label in ('part_size', 'footprint_change'):
        human.groupby([label, 'method'])[human_metrics].mean().to_csv(output / f'human_by_{label}.csv')
        auto.groupby([label, 'method'])[metric_columns].mean().to_csv(output / f'automatic_by_{label}.csv')
        manifest.groupby(label).size().rename('registered').to_frame().join(
            manifest[manifest.case_uid.isin(expected)].groupby(label).size().rename('available')
        ).fillna(0).to_csv(output / f'coverage_by_{label}.csv')
    human.groupby(['reviewer_id', 'method'])[human_metrics].mean().to_csv(output / 'per_reviewer_summary.csv')
    paired_human = bootstrap_table(human, human_metrics, CORE_METHODS)
    paired_human.to_csv(output / 'human_paired_bootstrap.csv', index=False)
    bootstrap_table(auto, metric_columns, methods).to_csv(output / 'automatic_paired_bootstrap.csv', index=False)
    consensus = human.groupby(['case_uid', 'method', 'part_size'])[
        ['joint_success', 'strict_joint_success']].min().reset_index()
    consensus.groupby('method')[['joint_success', 'strict_joint_success']].mean().to_csv(output / 'consensus_joint_summary.csv')
    left = frames[0].set_index('row_uid')
    right = frames[1].set_index('row_uid').loc[left.index]
    agreement = []
    distributions = []
    for metric in SCORE_FIELDS:
        agreement.append(dict(criterion=metric,
                              weighted_kappa=weighted_cohen_kappa(left[metric], right[metric]),
                              exact_agreement=float((left[metric] == right[metric]).mean())))
        for reviewer, group in human.groupby('reviewer_id'):
            for score in (0, 1, 2):
                distributions.append(dict(reviewer_id=reviewer, metric=metric, score=score,
                                          count=int((group[metric] == score).sum())))
    pd.DataFrame(agreement).to_csv(output / 'interrater_agreement.csv', index=False)
    pd.DataFrame(distributions).to_csv(output / 'score_distributions.csv', index=False)
    localization = auto.drop_duplicates(['case_uid', 'seed'])
    loc_cols = ['mask_iou', 'mask_ap', 'mask_area_over_gt']
    localization[['case_uid', 'part_size', 'footprint_change', *loc_cols]].to_csv(output / 'localization_per_case.csv', index=False)
    localization[loc_cols].agg(['mean', 'median']).to_csv(output / 'localization_summary.csv')
    verdict = evaluate_registered_success(human_summary, paired_human)
    verdict['scope'] = 'Available-case criteria check only; not the complete frozen 60-case primary analysis.'
    (output / 'available_case_criteria.json').write_text(json.dumps(verdict, indent=2) + '\n')
    coverage = dict(registered_cases=60, available_cases=59, registered_outputs=240,
                    available_outputs=236, core_reviewed_outputs=177, ratings=354,
                    missing_case='synth_0014', bootstrap_iterations=10000, bootstrap_seed=20260903,
                    execution_commit='085e8a3b930bfdf85da4bbbb198e83aede532e37',
                    manifest_sha256=digest(manifest_path),
                    limitations=['Available-case resampling uses 20 small, 19 medium, 20 large cases.',
                                 'No missing-output score imputation; N3 human evaluation deferred.',
                                 'Source prompt and Chinese rubric added to review display after generation.',
                                 'Two supplied reviewers; independence cannot be verified from CSV files.',
                                 'CIs resample cases while retaining both reviewers, not a reviewer population.',
                                 'Metric-specific percentile intervals have no multiplicity correction.'])
    (output / 'coverage.json').write_text(json.dumps(coverage, indent=2) + '\n')
    provenance = {str(p.relative_to(repo_root)): digest(p) for p in inputs}
    provenance[str(Path(__file__).resolve().relative_to(repo_root))] = digest(Path(__file__))
    (output / 'input_sha256.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(human_summary.to_string())
    print(json.dumps(verdict, indent=2))
    print(f'Analysis saved: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--results', type=Path, default=Path('core/results/heldout_control_comparison'))
    parser.add_argument('--output', type=Path, default=Path('core/results/heldout_control_comparison/final_analysis'))
    args = parser.parse_args()
    root = args.repo_root.resolve()
    summarize(root, root / args.results, root / args.output)
