"""Stream full-image IT and compact AV diagnostics without changing model outputs."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import torch

from attention_routing import RoutingRecorder


@torch.no_grad()
def full_image_statistics(q, k, v, text_length, image_mask, valid_positions, groups,
                          chunk_size=32):
    if q.ndim != 4 or q.shape != k.shape or q.shape != v.shape or q.shape[0] != 1:
        raise ValueError('Expected matching single-image Q/K/V')
    mask = torch.as_tensor(image_mask, device=q.device).flatten()
    if not 0 < text_length < q.shape[2] or mask.numel() != q.shape[2] - text_length:
        raise ValueError('Observation grid does not match image sequence')
    if not torch.isfinite(mask).all() or not ((mask == 0) | (mask == 1)).all() or not mask.any():
        raise ValueError('Expected nonempty binary mask')
    valid = list(valid_positions)
    if not valid or len(set(valid)) != len(valid) or any(i < 0 or i >= text_length for i in valid):
        raise ValueError('Invalid valid-text positions')
    if chunk_size < 1:
        raise ValueError('Chunk size must be positive')
    for positions in groups.values():
        if not positions or len(set(positions)) != len(positions) or any(i not in valid for i in positions):
            raise ValueError('Token groups must select distinct valid text positions')
    mask = mask.bool()
    pad = sorted(set(range(text_length)) - set(valid))
    selectors = [torch.arange(text_length, device=q.device),
                 torch.nonzero(mask).flatten() + text_length,
                 torch.nonzero(~mask).flatten() + text_length]
    selectors += [torch.tensor(p, device=q.device, dtype=torch.long) for p in groups.values()]
    chunks = {k: [] for k in ('text_attention', 'padding_mass', 'region_mass', 'entropy',
                              'max_weight', 'av_norms', 'total_av_norm')}
    error = 0.0
    with torch.autocast(device_type=q.device.type, enabled=False):
        keys = k[0].detach().float().transpose(-2, -1)
        values = v[0].detach().float()
        for start in range(text_length, q.shape[2], chunk_size):
            a = torch.softmax(q[0, :, start:start+chunk_size].detach().float() @ keys
                              * q.shape[-1] ** -0.5, dim=-1)
            mass = torch.stack([a.index_select(-1, p).sum(-1) for p in selectors[:3]], -1)
            norms = torch.stack([(a.index_select(-1, p) @ values.index_select(1, p)).norm(dim=-1)
                                 for p in selectors], -1)
            batch = dict(text_attention=a[..., valid], padding_mass=a[..., pad].sum(-1),
                         region_mass=mass, entropy=-(a * a.clamp_min(1e-30).log()).sum(-1),
                         max_weight=a.max(-1).values, av_norms=norms,
                         total_av_norm=(a @ values).norm(dim=-1))
            error = max(error, float((mass.sum(-1)-1).abs().max()))
            for name, array in batch.items():
                if not torch.isfinite(array).all():
                    raise ValueError(f'Nonfinite diagnostic: {name}')
                chunks[name].append(array.cpu().numpy())
    return {**{k: np.concatenate(arrays, axis=1) for k, arrays in chunks.items()},
            'max_row_sum_error': np.asarray(error, dtype=np.float32)}


class RichRoutingRecorder(RoutingRecorder):
    """All blocks, start and midpoint; one compressed file per block evaluation.

    Stored arrays preserve heads and image positions. No full II matrix is retained.
    """

    def __init__(self, model, sampling_info, image_mask, text_length, *, directory, tokens):
        layers = {s: tuple(range(len(getattr(model, f'{s}_blocks')))) for s in ('double', 'single')}
        super().__init__(model, sampling_info, image_mask, text_length, layers=layers)
        self.directory = Path(directory)
        self.tokens = tokens
        self.valid = np.flatnonzero(tokens['valid_positions']).tolist()
        self.phase = None
        self.state_seen = set()
        self.max_error = 0.0
        self.observer_seconds = 0.0
        for name in ('attention', 'states'):
            (self.directory / name).mkdir(parents=True, exist_ok=True)

    def _model_pre(self, module, inputs, kwargs):
        self.layer = self.step = self.phase = None
        info = kwargs.get('info')
        if info is not self.sampling_info or info.get('inverse'):
            return
        if info.get('inject') or info.get('attention_control') is not None:
            raise ValueError('Rich observation requires KV/IT controls disabled')
        trace = info.get('control_trace', [])
        if not trace:
            raise ValueError('Missing explicit control trace')
        self.step = int(trace[-1]['step'])
        self.phase = 'midpoint' if info.get('second_order') else 'start'
        self.t = float(kwargs['timesteps'][0])
        key = (self.step, self.phase)
        if key in self.state_seen:
            raise ValueError(f'Duplicate actual model evaluation: {key}')
        self.state_seen.add(key)
        self._state = kwargs['img'].detach().float().cpu().numpy()

    def _model_post(self, module, inputs, output):
        if self.step is not None:
            path = self.directory / 'states' / f'step_{self.step:02d}_{self.phase}.npz'
            if path.exists():
                raise FileExistsError(path)
            np.savez_compressed(path, latent=self._state,
                                velocity=output[0].detach().float().cpu().numpy(), time=self.t)
            del self._state

    def _attention(self, q, k, v, pe, control=None):
        if self.step is not None and self.layer is not None:
            if control is not None:
                raise ValueError('Unexpected attention intervention')
            from flux.math import apply_rope
            start = time.perf_counter()
            with torch.no_grad():
                qr, kr = apply_rope(q.detach(), k.detach(), pe)
                stats = full_image_statistics(qr, kr, v, self.text_length, self.mask,
                                               self.valid, self.tokens['groups'])
            key = (self.step, self.phase, self.layer)
            if key in self.seen:
                raise ValueError(f'Duplicate attention record: {key}')
            name = f'step_{self.step:02d}_{self.phase}_{self.layer}.npz'
            path = self.directory / 'attention' / name
            if path.exists():
                raise FileExistsError(path)
            np.savez_compressed(path, **stats)
            self.seen.add(key)
            self.max_error = max(self.max_error, float(stats['max_row_sum_error']))
            self.records.append(dict(step=self.step, evaluation=self.phase, layer=self.layer,
                                     time=self.t, file=f'attention/{name}'))
            self.observer_seconds += time.perf_counter() - start
        return self.original_attention(q, k, v, pe=pe, control=control)

    def __enter__(self):
        super().__enter__()
        try:
            self.handles.append(self.model.register_forward_hook(self._model_post))
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def save(self, directory, *, num_steps, tokens):
        expected = {(s, e, f'{stream}_{i}') for s in range(num_steps)
                    for e in ('start', 'midpoint') for stream, ids in self.layers.items() for i in ids}
        if self.seen != expected or len(self.state_seen) != num_steps * 2:
            raise ValueError('Incomplete rich attention/state coverage')
        if len(tokens['token_ids']) != self.text_length:
            raise ValueError('Token length mismatch')
        meta = dict(schema_version=2, mode='rich', records=len(self.records), layers=self.layers,
                    num_steps=num_steps, tokens=tokens, valid_text_positions=self.valid,
                    image_grid_shape=list(self.mask.shape), image_order='flattened row-major',
                    array_axes='head, image_query, text_position_or_group', dtype='float32',
                    mass_columns=['all_text', 'inside_image', 'outside_image'],
                    av_columns=['all_text', 'inside_image', 'outside_image', *tokens['groups']],
                    av_note='Per-head pre-output-projection norms, not semantic attribution; norms do not add.',
                    normalization='Joint softmax over all text and image keys including padding',
                    max_row_sum_error=self.max_error, observer_seconds=self.observer_seconds,
                    coverage=self.records)
        np.save(Path(directory) / 'observation_mask.npy', self.mask)
        (Path(directory) / 'metadata.json').write_text(json.dumps(meta, indent=2) + '\n')
