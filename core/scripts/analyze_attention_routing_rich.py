#!/usr/bin/env python3
"""Audit rich recordings and derive spatial update diagnostics locally."""

import argparse
import json
from pathlib import Path

import numpy as np


def proposal_maps(current, velocity, actual, dt, source=None):
    proposal = current.astype(np.float32) + np.float32(dt) * velocity.astype(np.float32)
    def rms(value):
        return np.sqrt(np.mean(np.square(value.astype(np.float32)), axis=-1))[0]
    result = {'proposal_delta_rms': rms(proposal-current),
              'actual_delta_rms': rms(actual-current),
              'actual_minus_proposal_rms': rms(actual-proposal)}
    if source is not None:
        result.update(proposal_source_residual_rms=rms(proposal-source),
                      actual_source_residual_rms=rms(actual-source))
    return result


def audit(run):
    directory = run / 'routing'
    meta = json.loads((directory / 'metadata.json').read_text())
    if meta.get('schema_version') != 2:
        raise ValueError('Expected rich schema v2')
    n = meta['num_steps']
    expected = {(s, e, f'{stream}_{i}') for s in range(n) for e in ('start', 'midpoint')
                for stream, ids in meta['layers'].items() for i in ids}
    seen = set()
    positions = meta['valid_text_positions']
    pixels = int(np.prod(meta['image_grid_shape']))
    worst = 0.0
    for record in meta['coverage']:
        key = (record['step'], record['evaluation'], record['layer'])
        if key in seen:
            raise ValueError('Duplicate record')
        seen.add(key)
        with np.load(directory / record['file'], allow_pickle=False) as data:
            a, mass = data['text_attention'], data['region_mass']
            if a.ndim != 3 or a.shape[1:] != (pixels, len(positions)) or mass.shape != (*a.shape[:2], 3):
                raise ValueError('Invalid array dimensions')
            if any(not np.isfinite(data[k]).all() for k in data.files):
                raise ValueError('Nonfinite diagnostic')
            error = max(float(np.max(np.abs(mass.sum(-1)-1))),
                        float(np.max(np.abs(a.sum(-1)+data['padding_mass']-mass[...,0]))))
            worst = max(worst, error)
            if error > 1e-5 or (a < 0).any() or (mass < 0).any():
                raise ValueError('Invalid joint attention probabilities')
    if seen != expected:
        raise ValueError('Missing or extra block evaluations')
    schedule = json.loads((directory / 'latent_record.json').read_text())['schedule']
    source_files = {}
    for name in ('source_latents', 'source_midpoints'):
        path = directory / f'{name}.npz'
        if path.exists():
            with np.load(path) as data:
                source_files[name] = {k: data[k] for k in data.files}
    out = directory / 'update_diagnostics'
    out.mkdir(exist_ok=True)
    for s in range(n):
        with np.load(directory / f'states/step_{s:02d}_start.npz') as data:
            current, start_v = data['latent'], data['velocity']
        with np.load(directory / f'states/step_{s:02d}_midpoint.npz') as data:
            midpoint, mid_v = data['latent'], data['velocity']
        if s+1 < n:
            with np.load(directory / f'states/step_{s+1:02d}_start.npz') as data:
                endpoint = data['latent']
        else:
            endpoint = np.load(directory / 'final_latent.npy')
        for phase, velocity, actual, fraction, field, index in (
            ('midpoint', start_v, midpoint, .5, 'source_midpoints', s),
            ('endpoint', mid_v, endpoint, 1., 'source_latents', s+1),
        ):
            values = proposal_maps(current, velocity, actual, fraction*(schedule[s+1]-schedule[s]),
                                   source_files.get(field, {}).get(str(index)))
            np.savez_compressed(out / f'step_{s:02d}_{phase}.npz',
                                **{k: v.reshape(meta['image_grid_shape']) for k,v in values.items()})
    summary = dict(passed=True, records=len(seen), states=n*2, max_probability_error=worst,
                   observer_seconds=meta['observer_seconds'],
                   bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),
                   update_note='FP32 unconstrained Euler/midpoint proposals versus actual saved states. '
                               'Differences also include solver floating-point arithmetic; not semantic attribution.',
                   source_references=list(source_files))
    (directory / 'rich_audit.json').write_text(json.dumps(summary, indent=2)+'\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    print(json.dumps(audit(parser.parse_args().run), indent=2))
