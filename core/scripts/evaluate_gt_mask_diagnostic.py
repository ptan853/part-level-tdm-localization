#!/usr/bin/env python3
"""Audit and evaluate the registered diagnostic, or materialize its blinded review."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from evaluate_heldout_control_comparison import load_protocol_inputs, dilate_mask_by_token_radius
from evaluate_latent_projection_against_fys import OutsideLpips, compute_image_metrics
from prepare_heldout_manual_review import build_blinded_assignments, _copy_blinded_assets
from build_manual_review import build_review_page

PRIMARY = ('endpoint_auto', 'rk2_auto', 'endpoint_gt', 'rk2_gt')
METHODS = PRIMARY + ('rk2_n15_auto', 'rk2_n15_gt')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def comparison_sets(coverage):
    available = coverage[coverage['available']]
    groups = available.groupby('case_uid')['method'].agg(set)
    primary = sorted(c for c, methods in groups.items() if set(PRIMARY) <= methods)
    supplement = sorted(c for c, methods in groups.items() if set(METHODS) <= methods)
    return primary, supplement


def filtered_randomization(source, ids):
    result = source[source['row_uid'].isin(ids)].sort_values(['reviewer_id', 'review_position']).copy()
    result['frozen_review_position'] = result['review_position']
    result['review_position'] = result.groupby('reviewer_id').cumcount()+1
    return result.reset_index(drop=True)


def evaluate(root, output):
    protocol = root/'core/protocols/gt_mask_diagnostic_v2'
    rows = pd.read_csv(protocol/'evaluation_rows.csv')
    assert len(rows) == 360 and not rows['row_uid'].duplicated().any()
    if (output/'automatic_metrics.csv').exists():
        raise FileExistsError('Metrics already exist; use a separate output directory for a rerun')
    output.mkdir(parents=True, exist_ok=True)
    coverage = []
    for row in rows.to_dict('records'):
        path = root/row['edited_image']
        available, reason, digest = False, '', ''
        if path.is_file():
            try:
                with Image.open(path) as im:
                    im.load()
                    if im.size != (1024, 1024):
                        raise ValueError(f'unexpected size {im.size}')
                available, digest = True, sha(path)
            except Exception as exc:
                reason = f'invalid image: {exc}'
        else:
            log = path.parent/'run.log'
            reason = 'safety_filtered' if log.is_file() and 'Your generated image may contain NSFW content.' in log.read_text() else 'missing_output'
        coverage.append({**row, 'available': available, 'reason': reason, 'image_sha256': digest})
    coverage = pd.DataFrame(coverage)
    coverage.to_csv(output/'coverage.csv', index=False)
    metric = OutsideLpips('require')
    scores = []
    for i, row in enumerate(coverage[coverage['available']].to_dict('records')):
        source, edited, gt = load_protocol_inputs(root/row['source_image'], root/row['edited_image'], root/row['gt_mask'])
        values = {}
        for name, region in [('strict', gt), ('buffered', dilate_mask_by_token_radius(gt))]:
            values.update({f'{name}_{k}': v for k, v in compute_image_metrics(source, edited, region).items()})
            values[f'{name}_outside_mask_lpips'] = metric(source, edited, region)
        if not all(np.isfinite(v) for k, v in values.items() if 'psnr' not in k):
            raise ValueError(f'nonfinite metric for {row["row_uid"]}')
        scores.append({**row, **values})
        print(f'evaluated {i+1}/{int(coverage.available.sum())}', flush=True)
    frame = pd.DataFrame(scores)
    frame.to_csv(output/'automatic_metrics.csv', index=False)
    primary, supplement = comparison_sets(coverage)
    columns = [c for c in frame if c.startswith(('strict_', 'buffered_'))]
    for name, cases, methods in [('primary', primary, PRIMARY), ('supplement', supplement, METHODS)]:
        selected = frame[frame.case_uid.isin(cases) & frame.method.isin(methods)]
        selected.groupby('method')[columns].mean().to_csv(output/f'{name}_automatic_means.csv')
    summary = {'registered': 360, 'available': int(coverage.available.sum()),
               'primary_cases': primary, 'supplement_cases': supplement,
               'coverage_by_method': coverage.groupby('method').available.sum().astype(int).to_dict(),
               'primary_size_counts': rows[rows.case_uid.isin(primary)].drop_duplicates('case_uid').part_size.value_counts().to_dict(),
               'bootstrap_status': 'Deferred until new human ratings are available; no previous ratings reused.',
               'evaluator_sha256': sha(__file__), 'metric_implementation_sha256': sha(root/'core/scripts/evaluate_latent_projection_against_fys.py')}
    (output/'evaluation_summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


def review(root, evaluation, output):
    if output.exists():
        raise FileExistsError('Review package already exists; do not overwrite scoring pages')
    protocol = root/'core/protocols/gt_mask_diagnostic_v2'
    assert sha(root/'core/scripts/build_manual_review.py') == json.loads((protocol/'preflight_summary.json').read_text())['review_renderer_sha256']
    summary = json.loads((evaluation/'evaluation_summary.json').read_text())
    metrics = pd.read_csv(evaluation/'automatic_metrics.csv')
    selected = metrics[metrics.case_uid.isin(summary['primary_cases'])].copy()
    frozen = pd.read_csv(protocol/'reviewer_randomization.csv')
    assignments = filtered_randomization(frozen, set(selected.row_uid))
    for key in ['source_image', 'gt_mask', 'edited_image']:
        selected[key] = selected[key].map(lambda p: str(root/p))
    output.mkdir(parents=True)
    for reviewer_id in ['reviewer_1', 'reviewer_2']:
        entries, mapping = build_blinded_assignments(selected, assignments, reviewer_id)
        folder = output/reviewer_id
        entries = _copy_blinded_assets(entries, folder)
        entries.to_csv(folder/'review_template.csv', index=False)
        mapping.to_csv(output/f'{reviewer_id}_private_mapping.csv', index=False)
        config = json.loads((protocol/'review_config_template.json').read_text())
        for key in ['storage_key', 'download_filename']:
            config[key] = config[key].replace('REVIEWER', reviewer_id)
        (folder/'review_config.json').write_text(json.dumps(config, indent=2)+'\n')
        build_review_page(repo_root=root, input_path=folder/'review_template.csv', config_path=folder/'review_config.json', output_path=folder/'review.html')
    hashes = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'review_package_sha256.json').write_text(json.dumps(hashes, indent=2)+'\n')
    print(f'{len(selected)} candidates per reviewer; package frozen at {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['evaluate', 'review'])
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--evaluation', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'evaluate':
        evaluate(args.repo_root.resolve(), args.output.resolve())
    else:
        if args.evaluation is None:
            parser.error('--evaluation is required for review')
        review(args.repo_root.resolve(), args.evaluation.resolve(), args.output.resolve())
