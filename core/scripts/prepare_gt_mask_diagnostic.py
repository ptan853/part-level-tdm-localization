#!/usr/bin/env python3
"""Prepare the separate 2x2 GT-mask diagnostic; never launch GPU generation."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

from heldout_review_randomization import build_frozen_randomization, validate_frozen_randomization
from run_heldout_control_comparison import build_matched_control_plan
from run_control_plan import build_control_command, format_command

METHODS = ('endpoint_auto', 'rk2_auto', 'endpoint_gt', 'rk2_gt')
REVIEW_METHODS = METHODS + ('rk2_n15_auto', 'rk2_n15_gt')
MANIFEST_SHA = '8e69fd42969286ce028c00c285a5a12600a5a4127e18a2c1f03d5ccbc3283147'
REVIEWER_SEEDS = {'reviewer_1': 202609081, 'reviewer_2': 202609082}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze(path, data):
    """Refuse silent changes to an existing pre-generation artifact."""
    path = Path(path)
    data = data.encode() if isinstance(data, str) else data
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f'frozen artifact differs: {path}; create a new protocol revision')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def json_text(value):
    return json.dumps(value, indent=2, ensure_ascii=True) + '\n'


def csv_text(rows):
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def gt_to_token_grid(gt, image_shape):
    """Match edit.py: >0, nearest to H/8 x W/8, then 2x2 max pool.

    NumPy floor-index sampling matches torch interpolate(mode='nearest'),
    rather than PIL's differently aligned nearest-neighbor implementation.
    """
    gt = np.asarray(gt)
    h, w = image_shape
    if gt.ndim != 2 or h % 16 or w % 16 or min(h, w) < 16:
        raise ValueError('require a 2D mask and image dimensions divisible by 16')
    if not np.isfinite(gt).all():
        raise ValueError('non-finite GT')
    lh, lw = h // 8, w // 8
    ys = np.arange(lh, dtype=np.int64) * gt.shape[0] // lh
    xs = np.arange(lw, dtype=np.int64) * gt.shape[1] // lw
    latent = (gt > 0)[ys[:, None], xs[None, :]]
    grid = latent.reshape(lh // 2, 2, lw // 2, 2).max(axis=(1, 3)).astype(np.uint8)
    if not grid.any() or grid.all():
        raise ValueError('GT conversion has empty edit or preservation region')
    return grid


def full_duration_rk2_plan():
    plan = build_matched_control_plan('residual_rk2')
    plan['name'] = 'diagnostic_residual_rk2_n15'
    plan['stages'][0]['end'] = 14
    return plan


def diagnostic_assignments(records):
    rows = [{**r, 'method': m, 'seed': 0,
             'row_uid': f'gt-diagnostic-v2::{m}::{r["case_uid"]}::seed_000'}
            for r in records for m in REVIEW_METHODS]
    assignments = build_frozen_randomization(rows, REVIEWER_SEEDS)
    validate_frozen_randomization(assignments, expected_row_uids={r['row_uid'] for r in rows})
    return assignments


def common_case_ids(rows):
    groups = {}
    for row in rows:
        group = groups.setdefault(row['case_uid'], {})
        if row['method'] in group or row['method'] not in METHODS:
            raise ValueError('duplicate or unknown condition')
        group[row['method']] = row['available']
    return sorted(case for case, group in groups.items()
                  if set(group) == set(METHODS) and all(group.values()))


def prepare(root):
    root = Path(root).resolve()
    old = root / 'core/results/heldout_control_comparison'
    dest = root / 'core/protocols/gt_mask_diagnostic_v2'
    results = root / 'core/results/gt_mask_diagnostic_v2'
    manifest_path = root / 'core/data/partedit_subset/synth_60_frozen_manifest.json'
    if sha(manifest_path) != MANIFEST_SHA:
        raise ValueError('manifest differs from the original frozen split')
    records = sorted(json.loads(manifest_path.read_text()), key=lambda r: r['dataset_index'])
    if len(records) != 60 or [r['dataset_index'] for r in records] != list(range(60)):
        raise ValueError('expected exactly dataset indices 0..59')
    audit, matrix, evaluation = [], [], []
    plans = {}
    from flux.control_schedule import load_control_plan
    for method in ['endpoint_projection', 'residual_rk2']:
        path = dest / 'resolved_plans' / f'{method}_n07.json'
        freeze(path, json_text(build_matched_control_plan(method)))
        plans[method] = path
    n15_plan = dest / 'resolved_plans/residual_rk2_n15.json'
    freeze(n15_plan, json_text(full_duration_rk2_plan()))
    load_control_plan(n15_plan)
    for r in records:
        case = r['case_uid']
        source_path, gt_path = root / r['source_image'], root / r['gt_mask']
        with Image.open(source_path) as image:
            shape = (image.height, image.width)
        if shape != (1024, 1024):
            raise ValueError(f'unexpected native generation resolution: {case}: {shape}')
        with Image.open(gt_path) as image:
            gt = np.asarray(image.convert('L'))
        if gt.shape != shape:
            raise ValueError(f'GT/source geometry mismatch: {case}')
        grid = gt_to_token_grid(gt, shape)
        mask_path = dest / 'gt_masks' / f'{case}.npy'
        buffer = io.BytesIO()
        np.save(buffer, grid, allow_pickle=False)
        freeze(mask_path, buffer.getvalue())
        mask_audit = dict(case_uid=case, source_sha256=sha(source_path), gt_sha256=sha(gt_path),
                          grid_sha256=sha(mask_path), image_height=shape[0], image_width=shape[1],
                          grid_height=grid.shape[0], grid_width=grid.shape[1],
                          gt_pixel_area=int((gt > 0).sum()), gt_token_area=int(grid.sum()),
                          gt_pixel_fraction=float((gt > 0).mean()), gt_token_fraction=float(grid.mean()))
        for base, label in [('endpoint_projection', 'endpoint'), ('residual_rk2', 'rk2')]:
            folder = old / base / case / 'seed_000'
            config = json.loads((folder / 'run_config.json').read_text())
            expected = dict(seed=0, num_steps=15, guidance=2.0, model_name='flux-dev', offload=True,
                            source_prompt=r['source_prompt'], target_prompt=r['target_prompt'],
                            source_image=r['source_image'], mask_source='precomputed')
            if any(config.get(k) != v for k, v in expected.items()):
                raise ValueError(f'cached configuration mismatch: {base}/{case}')
            expected_plan = json.loads(json.dumps(load_control_plan(plans[base]).to_dict()))
            if config['resolved_control_plan'] != expected_plan:
                raise ValueError(f'cached control operation differs: {base}/{case}')
            auto_mask = old / 'attention_mask_scout' / case / 'seed_000/tdm/hybrid_binary_tdm_attention.npy'
            if not config['control_mask_path'].endswith(str(auto_mask.relative_to(old))):
                raise ValueError(f'cached mask path mismatch: {base}/{case}')
            if np.load(auto_mask).shape != grid.shape:
                raise ValueError(f'cached mask grid mismatch: {case}')
            auto_image = folder / 'img_0.jpg'
            if auto_image.exists() == (case == 'synth_0014'):
                raise ValueError(f'cached coverage changed: {base}/{case}')
            command = build_control_command(r, plan_path=plans[base], repo_root=root,
                python_executable='python', seed=0, offload=True,
                output_root=results / f'{label}_gt', control_mask_path=mask_path)
            if command.output_dir.exists() and any(command.output_dir.iterdir()):
                raise ValueError(f'new output is not empty: {command.output_dir}')
            # Commands are portable after replacing this one repository-root placeholder.
            portable = format_command(command).replace(str(root), '${REPO_ROOT}')
            matrix.append(dict(case_uid=case, condition=f'{label}_gt', seed=0,
                output_dir=str(command.output_dir.relative_to(root)),
                control_mask_path=str(mask_path.relative_to(root)), command=portable))
            mask_audit[f'{label}_config_sha256'] = sha(folder / 'run_config.json')
            mask_audit[f'{label}_auto_image_sha256'] = sha(auto_image) if auto_image.exists() else None
            mask_audit['auto_mask_sha256'] = sha(auto_mask)
            for suffix, image_path in [('auto', auto_image), ('gt', command.output_dir / 'img_0.jpg')]:
                condition = f'{label}_{suffix}'
                evaluation.append(dict(row_uid=f'gt-diagnostic-v2::{condition}::{case}::seed_000',
                    case_uid=case, seed=0, method=condition, part=r['part'], edit=r['edit'],
                    part_size=r['part_size'], footprint_change=r['footprint_change'],
                    source_prompt=r['source_prompt'], target_prompt=r['target_prompt'],
                    source_image=r['source_image'], gt_mask=r['gt_mask'],
                    edited_image=str(image_path.relative_to(root))))
        for suffix, selected_mask in [('auto', auto_mask), ('gt', mask_path)]:
            condition = f'rk2_n15_{suffix}'
            command = build_control_command(r, plan_path=n15_plan, repo_root=root,
                python_executable='python', seed=0, offload=True,
                output_root=results / condition, control_mask_path=selected_mask)
            if command.output_dir.exists() and any(command.output_dir.iterdir()):
                raise ValueError(f'new output is not empty: {command.output_dir}')
            matrix.append(dict(case_uid=case, condition=condition, seed=0,
                output_dir=str(command.output_dir.relative_to(root)),
                control_mask_path=str(selected_mask.relative_to(root)),
                command=format_command(command).replace(str(root), '${REPO_ROOT}')))
            evaluation.append(dict(row_uid=f'gt-diagnostic-v2::{condition}::{case}::seed_000',
                case_uid=case, seed=0, method=condition, part=r['part'], edit=r['edit'],
                part_size=r['part_size'], footprint_change=r['footprint_change'],
                source_prompt=r['source_prompt'], target_prompt=r['target_prompt'],
                source_image=r['source_image'], gt_mask=r['gt_mask'],
                edited_image=str((command.output_dir / 'img_0.jpg').relative_to(root))))
        audit.append(mask_audit)
    assignments = diagnostic_assignments(records)
    assert len(matrix) == 240 and len(evaluation) == 360 and len(assignments) == 720
    freeze(dest / 'mask_and_cache_audit.json', json_text(audit))
    freeze(dest / 'run_matrix.csv', csv_text(matrix))
    freeze(dest / 'evaluation_rows.csv', csv_text(evaluation))
    freeze(dest / 'reviewer_randomization.csv', csv_text(assignments))
    # Freeze the already-used rubric and renderer as the review contract.
    old_review = old / 'blinded_review_available_outputs/reviewer_1'
    configs = list(old_review.glob('*config*.json'))
    if not configs:
        raise FileNotFoundError('original review-page configuration not found')
    config_path = next((p for p in configs if 'core' in p.name), configs[0])
    review_config = json.loads(config_path.read_text())
    review_config['storage_key'] = 'gt-mask-diagnostic-v2-REVIEWER'
    review_config['download_filename'] = 'gt_mask_diagnostic_REVIEWER_scores.csv'
    freeze(dest / 'review_config_template.json', json_text(review_config))
    summary = dict(protocol='gt-mask-diagnostic-v2', manifest_sha256=MANIFEST_SHA,
        primary_conditions=list(METHODS), supplemental_conditions=list(REVIEW_METHODS[4:]),
        registered_cases=60, new_generation_runs=240, cached_available_images=118,
        total_condition_records=360, planned_reviewer_assignments=720,
        common_case_upper_bound=59, known_missing_case='synth_0014',
        all_gt_masks_nonempty=True, gt_grid_shape=[64, 64],
        review_renderer_sha256=sha(root / 'core/scripts/build_manual_review.py'),
        runtime_environment_status='server check required before generation',
        generation_started=False)
    freeze(dest / 'preflight_summary.json', json_text(summary))
    print(json_text(summary))
    return summary


if __name__ == '__main__':
    if len(sys.argv) != 1:
        raise SystemExit('This preparation-only entry point accepts no arguments and never generates images.')
    prepare(Path(__file__).resolve().parents[2])
