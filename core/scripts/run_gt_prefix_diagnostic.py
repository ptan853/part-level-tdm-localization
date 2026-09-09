#!/usr/bin/env python3
"""Prepare, run, or evaluate the frozen six-case GT prefix diagnostic."""
from __future__ import annotations

import argparse
import csv
import html
import math
import json
import os
from pathlib import Path
import subprocess
import shutil

from run_residual_rk2_prefix_sweep import build_sweep_commands, build_prefix_plan
from prepare_gt_mask_diagnostic import freeze, sha, json_text, csv_text, gt_to_token_grid, MANIFEST_SHA
from heldout_review_randomization import build_frozen_randomization, validate_frozen_randomization
from run_control_plan import execute_command, format_command

CASES = ('synth_0028', 'synth_0032', 'synth_0033', 'synth_0038', 'synth_0043', 'synth_0036')
PROTOCOL = 'gt_prefix_diagnostic_v1'
BASE = '3f8581894eabacf7a30ee08168923bef1a89d7ba'
DURATIONS = tuple(range(14))


def selection_evidence(rows):
    evidence = []
    for case in CASES:
        for method in ('original_fys_tdm', 'endpoint_projection', 'residual_rk2'):
            selected = [r for r in rows if r['case_uid'] == case and r['method'] == method]
            if len(selected) != 2 or {r['reviewer_id'] for r in selected} != {'reviewer_1', 'reviewer_2'}:
                raise ValueError(f'expected both old reviewers: {case}/{method}')
            scores = {r['reviewer_id']: float(r['local_edit_success_0_2']) for r in selected}
            expected = 2 if case == 'synth_0036' and method == 'original_fys_tdm' else 0
            if any(v != expected for v in scores.values()):
                raise ValueError(f'old selection evidence changed: {case}/{method}')
            evidence.append(dict(case_uid=case, method=method, **scores, mean=expected))
    return evidence


def commands(root, data_root, records, python):
    dest = root / 'core/protocols' / PROTOCOL
    plans = []
    for n in DURATIONS:
        path = dest / 'plans' / f'duration_{n:02d}.json'
        freeze(path, json_text(build_prefix_plan(n)))
        plans.append(path)
    # Relative paths retain the evaluator's repository-visible path contract.
    runtime = [{**r, **{k: os.path.relpath(data_root / r[k], root)
                           for k in ('source_image', 'gt_mask')}} for r in records]
    return build_sweep_commands(records=runtime, plan_paths=plans, repo_root=root,
        python_executable=python, seed=0, offload=True, guidance=2.0,
        output_root=root / 'core/results' / PROTOCOL)


def prepare(root, data_root):
    import numpy as np
    from PIL import Image
    dest = root / 'core/protocols' / PROTOCOL
    manifest = data_root / 'core/data/partedit_subset/synth_60_frozen_manifest.json'
    if sha(manifest) != MANIFEST_SHA:
        raise ValueError('original frozen manifest changed')
    all_records = {r['case_uid']: r for r in json.loads(manifest.read_text())}
    records = [all_records[uid] for uid in CASES]
    scores_path = data_root / 'core/results/heldout_control_comparison/final_analysis/reviewer_level_scores.csv'
    with scores_path.open() as f:
        evidence = selection_evidence(list(csv.DictReader(f)))
    audit = []
    for r in records:
        with Image.open(data_root / r['source_image']) as im:
            shape = im.height, im.width
        with Image.open(data_root / r['gt_mask']) as im:
            gt = np.asarray(im.convert('L'))
        if shape != (1024, 1024) or gt.shape != shape:
            raise ValueError(f'unexpected image geometry: {r["case_uid"]}')
        grid = gt_to_token_grid(gt, shape)
        config_hashes = {}
        for method in ('endpoint_projection', 'residual_rk2'):
            p = data_root / 'core/results/heldout_control_comparison' / method / r['case_uid'] / 'seed_000/run_config.json'
            cfg = json.loads(p.read_text())
            expected = dict(seed=0, guidance=2.0, num_steps=15, model_name='flux-dev', offload=True,
                source_prompt=r['source_prompt'], target_prompt=r['target_prompt'], source_image=r['source_image'])
            if any(cfg.get(k) != v for k, v in expected.items()):
                raise ValueError(f'frozen run config mismatch: {p}')
            config_hashes[method] = sha(p)
        audit.append(dict(case_uid=r['case_uid'], source_sha256=sha(data_root / r['source_image']),
            gt_sha256=sha(data_root / r['gt_mask']), image_shape=list(shape), grid_shape=list(grid.shape),
            gt_pixels=int((gt > 0).sum()), gt_tokens=int(grid.sum()), config_sha256=config_hashes))
    freeze(dest / 'manifest.json', json_text(records))
    freeze(dest / 'selection_scores.csv', csv_text(evidence))
    freeze(dest / 'input_audit.json', json_text(audit))
    runs = commands(root, data_root, records, '${PYTHON}')
    matrix = []
    for c in runs:
        n = int(c.plan.name.rsplit('_', 1)[1])
        matrix.append(dict(case_uid=c.case_uid, duration=n, seed=0, guidance=2.0,
            num_steps=15, plan_path=str(Path(c.run_config['plan_path'])), plan_sha256=c.run_config['plan_sha256'],
            output_dir=c.run_config['output_dir'], source_prompt=c.run_config['source_prompt'],
            target_prompt=c.run_config['target_prompt'], mask_source='oracle', image_kv='none', it_gate='none'))
    freeze(dest / 'run_matrix.csv', csv_text(matrix))
    assignments = build_frozen_randomization([
        {**r, 'seed': 0, 'method': f'N{n:02d}', 'row_uid': f'{PROTOCOL}::{r["case_uid"]}::N{n:02d}'}
        for r in records for n in DURATIONS], {'reviewer_1': 202609091, 'reviewer_2': 202609092})
    validate_frozen_randomization(assignments, expected_row_uids={a['row_uid'] for a in assignments})
    freeze(dest / 'reviewer_randomization.csv', csv_text(assignments))
    review = json.loads((root / 'core/protocols/gt_mask_diagnostic_v2/review_config_template.json').read_text())
    review['storage_key'] = PROTOCOL + '-REVIEWER'
    review['download_filename'] = PROTOCOL + '_REVIEWER_scores.csv'
    freeze(dest / 'review_config.json', json_text(review))
    freeze(dest / 'protocol.json', json_text(dict(protocol=PROTOCOL, base_commit=BASE,
        fys_commit='b096e8f7736b0f44d820933d5046fe252059a5eb', manifest_sha256=MANIFEST_SHA,
        selection_scores_sha256=sha(scores_path), cases=list(CASES), durations=list(DURATIONS),
        runs=84, seed=0, guidance=2.0, inversion_guidance=1.0, num_steps=15,
        selection='Observed old failures; no new GT diagnostic scores used',
        inference='Exploratory selected-case diagnostic; not a frozen-comparison replacement or FLUX impossibility test')))
    return records


def validate_trace(trace, n):
    steps = trace.get('trace', [])
    residual = trace.get('residual_control_trace', [])
    if [s['step'] for s in steps] != list(range(15)) or [s['step'] for s in residual] != list(range(n)):
        raise ValueError('incorrect control trace coverage')
    for i, s in enumerate(steps):
        if any(s.get(k) not in (None, 'none') for k in ('image_kv', 'it_gate', 'latent_projection')):
            raise ValueError('unexpected extra control')
        if s.get('residual_control') != ('source_referenced_rk2' if i < n else None):
            raise ValueError('incorrect residual prefix')
    for i, s in enumerate(residual):
        for key in ('mask_area_ratio', 'midpoint_outside_residual_mae_after', 'midpoint_outside_residual_max_after',
                    'outside_residual_mae_before', 'outside_residual_mae_after', 'outside_residual_max_after'):
            if not math.isfinite(float(s.get(key, float('nan')))):
                raise ValueError(f'missing or non-finite residual metric: {key}')
        if (s['source_current_index'], s['source_midpoint_index'], s['source_next_index']) != (i, i, i+1):
            raise ValueError('misaligned source indices')
        if not s['next_timestep'] < s['timestep']:
            raise ValueError('nonnegative denoising step')


def evaluate(root, data_root, records, lpips):
    import pandas as pd
    from evaluate_residual_rk2_prefix_sweep import build_residual_evaluation_rows
    from evaluate_latent_projection_against_fys import OutsideLpips, compute_image_metrics
    from evaluate_heldout_control_comparison import load_protocol_inputs, dilate_mask_by_token_radius
    from build_manual_review import build_review_page
    dest = root / 'core/protocols' / PROTOCOL
    output = root / 'core/results' / PROTOCOL
    runs = commands(root, data_root, records, 'python')
    provenance_path = output / 'execution_provenance.json'
    provenance = json.loads(provenance_path.read_text()) if provenance_path.exists() else {}
    origin_code = Path(provenance.get('code_root', str(root)))
    origin_data = Path(provenance.get('data_root', str(data_root)))
    canonical = {r['case_uid']: r for r in records}
    for c in runs:
        config = json.loads((c.output_dir / 'run_config.json').read_text())
        for k in ('seed', 'guidance', 'num_steps', 'model_name', 'source_prompt', 'target_prompt', 'plan_sha256', 'mask_source', 'case_uid', 'offload'):
            if config.get(k) != c.run_config[k]:
                raise ValueError(f'run provenance mismatch: {c.run_uid}/{k}')
        for key in ('source_image', 'gt_mask'):
            if os.path.normpath(origin_code / config[key]) != os.path.normpath(origin_data / canonical[c.case_uid][key]):
                raise ValueError(f'run input mismatch: {c.run_uid}/{key}')
        if json.loads((c.output_dir / 'resolved_control_plan.json').read_text()) != json.loads(json_text(c.plan.to_dict())):
            raise ValueError(f'resolved plan mismatch: {c.run_uid}')
        validate_trace(json.loads((c.output_dir / 'tdm/control_trace.json').read_text()),
                       int(c.plan.name.rsplit('_', 1)[1]))
    runtime = [c.case_record for c in runs[:6]]
    rows = build_residual_evaluation_rows(root, runtime, output, durations=DURATIONS)
    rows['row_uid'] = rows.apply(lambda r: f'{PROTOCOL}::{r.case_uid}::N{int(r.duration):02d}', axis=1)
    metric = OutsideLpips(lpips)
    measured = []
    buffered_cache = {}
    for row in rows.to_dict('records'):
        source, edited, gt = load_protocol_inputs(root / row['source_image'], root / row['edited_image'], root / row['gt_mask'])
        if row['case_uid'] not in buffered_cache:
            buffered_cache[row['case_uid']] = dilate_mask_by_token_radius(gt)
        values = {}
        for label, mask in (('strict', gt), ('buffered', buffered_cache[row['case_uid']])):
            values.update({f'{label}_{k}': v for k, v in compute_image_metrics(source, edited, mask).items()})
            value = metric(source, edited, mask)
            if lpips == 'require' and not math.isfinite(value):
                raise ValueError('required LPIPS result is non-finite')
            values[f'{label}_outside_mask_lpips'] = value
        measured.append({**row, **values})
    evaluated = pd.DataFrame(measured)
    result = output / 'evaluation'
    result.mkdir(parents=True, exist_ok=True)
    evaluated.to_csv(result / 'image_metrics.csv', index=False)
    assignments = pd.read_csv(dest / 'reviewer_randomization.csv')
    for reviewer, group in assignments.groupby('reviewer_id', sort=True):
        review_dir = result / reviewer
        review_dir.mkdir(exist_ok=True)
        joined = group.merge(evaluated, on=['row_uid', 'case_uid'], validate='one_to_one').sort_values('review_position')
        # Do not expose duration/method or the randomization key in the scoring CSV/page.
        review_rows = joined[['review_uid', 'part', 'edit', 'target_prompt', 'source_image', 'edited_image']].rename(columns={'edited_image':'candidate_image'})
        assets = review_dir / 'assets'
        assets.mkdir(exist_ok=True)
        for idx, row in review_rows.iterrows():
            for key in ('source_image', 'candidate_image'):
                source = root / row[key]
                opaque = assets / (row['review_uid'] + '_' + key + source.suffix)
                shutil.copy2(source, opaque)
                review_rows.at[idx, key] = os.path.relpath(opaque, root)
        cfg = json.loads((dest / 'review_config.json').read_text())
        cfg['storage_key'] = cfg['storage_key'].replace('REVIEWER', reviewer)
        cfg['download_filename'] = cfg['download_filename'].replace('REVIEWER', reviewer)
        for field in cfg['score_fields']:
            review_rows[field['key']] = ''
        review_rows['short_note'] = ''
        review_rows.to_csv(review_dir / 'template.csv', index=False)
        (review_dir / 'config.json').write_text(json_text(cfg))
        build_review_page(repo_root=root, input_path=review_dir / 'template.csv',
            config_path=review_dir / 'config.json', output_path=review_dir / 'review.html')
    # Durable comparison evidence; no raster collage or notebook-generation script.
    body = ['<!doctype html><meta charset="utf-8"><title>GT prefix diagnostic</title>',
            '<style>body{font-family:system-ui}section{display:flex;overflow:auto}figure{margin:6px}img{width:256px}figcaption{font-weight:bold}</style>',
            '<h1>Exploratory GT prefix diagnostic</h1><p>Source, GT mask, N=0..13. Review blinded outputs before using this comparison.</p>']
    for r in runtime:
        body.append('<h2>' + html.escape(r['case_uid'] + ': ' + r['target_prompt']) + '</h2><section>')
        images = [('Source', root / r['source_image']), ('GT mask', root / r['gt_mask'])]
        images += [(f'N={n}', output / f'duration_{n:02d}' / r['case_uid'] / 'seed_000/img_0.jpg') for n in DURATIONS]
        for label, path in images:
            body.append(f'<figure><figcaption>{label}</figcaption><img src="{html.escape(os.path.relpath(path, result), quote=True)}"></figure>')
        body.append('</section>')
    (result / 'comparison.html').write_text('\n'.join(body))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'run', 'evaluate'))
    p.add_argument('--data-root', required=True, type=Path, help='Read-only original repository/data root')
    p.add_argument('--python', default='/root/miniconda3/bin/python')
    p.add_argument('--lpips', choices=('off', 'auto', 'require'), default='require')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    data = args.data_root.resolve()
    records = prepare(root, data)
    if args.action == 'run':
        if root == data:
            raise ValueError('run requires an independent code checkout and external data root')
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip():
            raise ValueError('commit the reviewed experiment before generation')
        fys_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
            cwd=root / 'core/third_party/FollowYourShape', text=True).strip()
        if fys_commit != 'b096e8f7736b0f44d820933d5046fe252059a5eb':
            raise ValueError('audited FYS revision changed')
        subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, commit], cwd=root, check=True)
        runtime = subprocess.check_output([args.python, '-c',
            'import json,sys,torch; assert torch.cuda.is_available(); print(json.dumps(dict(python=sys.version,torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0))))'],
            cwd=root, text=True).strip()
        for test in ('test_latent_control.py', 'test_control_plan_sampling.py',
                     'test_inversion_step_observer.py', 'test_gt_prefix_sampling.py'):
            subprocess.run([args.python, '-m', 'unittest', 'discover', '-s', 'tests', '-p', test],
                           cwd=root, check=True)
        output = root / 'core/results' / PROTOCOL
        freeze(output / 'execution_provenance.json', json_text(dict(commit=commit,
            data_root=str(data), code_root=str(root), python=args.python,
            fys_commit=fys_commit, runtime=json.loads(runtime),
            protocol_sha256=sha(root / 'core/protocols' / PROTOCOL / 'protocol.json'))))
        for command in commands(root, data, records, args.python):
            print(format_command(command), flush=True)
            code = execute_command(command, overwrite=False)
            if code:
                return code
    elif args.action == 'evaluate':
        evaluate(root, data, records, args.lpips)
    print(f'{args.action}: {len(records)} cases, 84 conditions; {PROTOCOL}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
