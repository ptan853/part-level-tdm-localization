import sys
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core/scripts'))
sys.path.insert(0, str(ROOT / 'core/third_party/FollowYourShape/src'))


class RichRoutingTests(unittest.TestCase):
    def test_rich_runner_is_opt_in_and_uses_separate_output(self):
        from contextlib import redirect_stdout
        import io
        from run_attention_routing_diagnostic import main
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()) as output:
            main(['--mode', 'rich', '--case-uid', 'synth_0006', '--prepare', '--output-root', tmp])
            self.assertIn('--routing-mode rich', output.getvalue())
            self.assertFalse(list(Path(tmp).glob('recording_*')))

    def test_fp32_proposal_difference_is_not_source_residual(self):
        from analyze_attention_routing_rich import proposal_maps
        current = np.zeros((1, 4, 2), dtype=np.float32)
        velocity = np.ones_like(current)
        actual = np.zeros_like(current)
        actual[:, 0] = -1
        result = proposal_maps(current, velocity, actual, -1, np.zeros_like(current))
        np.testing.assert_allclose(result['proposal_delta_rms'], [1, 1, 1, 1])
        np.testing.assert_allclose(result['actual_minus_proposal_rms'], [0, 1, 1, 1])
        np.testing.assert_allclose(result['actual_source_residual_rms'], [1, 0, 0, 0])

    def test_full_image_weights_and_av_match_dense(self):
        from attention_routing_rich import full_image_statistics
        torch.manual_seed(13)
        q, k, v = [torch.randn(1, 2, 7, 4) for _ in range(3)]
        result = full_image_statistics(q, k, v, 3, np.array([[1, 0], [0, 0]]),
                                       [0, 2], {'edit': [2]}, chunk_size=1)
        a = torch.softmax(q[0, :, 3:] @ k[0].transpose(-2, -1) / 2, -1)
        np.testing.assert_allclose(result['text_attention'], a[:, :, [0, 2]], atol=1e-7)
        np.testing.assert_allclose(result['padding_mass'], a[:, :, 1], atol=1e-7)
        np.testing.assert_allclose(result['region_mass'].sum(-1), 1, atol=1e-6)
        expected = (a[:, :, 2:3] * v[0, :, 2:3]).norm(dim=-1)
        np.testing.assert_allclose(result['av_norms'][..., 3], expected, atol=1e-6)
        np.testing.assert_allclose(result['entropy'], -(a * a.log()).sum(-1), atol=1e-6)

    def test_all_layers_two_evaluations_and_no_output_change(self):
        from attention_routing_rich import RichRoutingRecorder
        from flux.model import Flux, FluxParams
        from flux.modules import layers
        torch.manual_seed(14)
        model = Flux(FluxParams(4, 6, 8, 16, 2, 2, 2, 2, [2, 2, 4], 10000, True, False)).eval()
        info = {'inverse': False, 'second_order': False, 'inject': False,
                'control_trace': [{'step': 0}]}
        tokens = {'token_ids': [1, 2, 0], 'valid_positions': [1, 1, 0], 'groups': {'edit': [1]}}
        args = dict(img=torch.randn(1, 4, 4), img_ids=torch.zeros(1, 4, 3),
                    txt=torch.randn(1, 3, 8), txt_ids=torch.zeros(1, 3, 3),
                    timesteps=torch.tensor([.6]), y=torch.randn(1, 6), info=info)
        attention = layers.attention
        with tempfile.TemporaryDirectory() as tmp, torch.no_grad():
            baseline, _ = model(**args)
            directory = Path(tmp) / 'routing'
            recorder = RichRoutingRecorder(model, info, np.array([[1, 0], [0, 0]]), 3,
                                            directory=directory, tokens=tokens)
            rng = torch.get_rng_state().clone()
            with recorder:
                actual, _ = model(**args)
                model(**{**args, 'info': None})
                info['second_order'] = True
                model(**args)
            self.assertTrue(torch.equal(actual, baseline))
            self.assertTrue(torch.equal(torch.get_rng_state(), rng))
            recorder.save(directory, num_steps=1, tokens=tokens)
            self.assertEqual(len(list((directory / 'attention').glob('*.npz'))), 8)
            self.assertTrue((directory / 'states/step_00_start.npz').is_file())
            self.assertTrue((directory / 'states/step_00_midpoint.npz').is_file())
            np.save(directory / 'final_latent.npy', actual.numpy())
            (directory / 'latent_record.json').write_text(json.dumps({'schedule': [1, 0]}))
            from analyze_attention_routing_rich import audit
            self.assertTrue(audit(Path(tmp))['passed'])
            self.assertEqual(len(list((directory / 'update_diagnostics').glob('*.npz'))), 2)
            with self.assertRaises(ValueError):
                recorder.save(directory, num_steps=2, tokens=tokens)
        self.assertIs(layers.attention, attention)
        self.assertFalse(model._forward_pre_hooks)
        self.assertFalse(model._forward_hooks)


if __name__ == '__main__':
    unittest.main()
