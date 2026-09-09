from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core/scripts'))
import run_gt_prefix_diagnostic as diagnostic

METRICS = dict(mask_area_ratio=.5, midpoint_outside_residual_mae_after=0.,
    midpoint_outside_residual_max_after=0., outside_residual_mae_before=0.,
    outside_residual_mae_after=0., outside_residual_max_after=0.)


class DiagnosticTests(unittest.TestCase):
    def test_fixed_matrix_uses_new_code_and_external_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'code'
            data = Path(tmp) / 'old'
            records = [dict(case_uid=uid, source_image=f'core/data/{uid}.png',
                            gt_mask=f'core/data/{uid}_mask.png', source_prompt='source',
                            target_prompt='target') for uid in diagnostic.CASES]
            commands = diagnostic.commands(root, data, records, 'python')
            self.assertEqual(len(commands), 84)
            self.assertEqual(len({c.output_dir for c in commands}), 84)
            for c in commands:
                self.assertTrue(c.cwd.is_relative_to(root))
                self.assertTrue(c.output_dir.is_relative_to(root))
                self.assertEqual(Path(c.args[c.args.index('--source_img_dir') + 1]).resolve().parent,
                                 (data / 'core/data').resolve())
                self.assertEqual(c.plan.num_steps, 15)
                self.assertEqual(c.plan.image_kv_layers, ())
                self.assertEqual(c.plan.it_gate_layers, ())
                self.assertEqual(c.run_config['seed'], 0)
                self.assertEqual(c.run_config['guidance'], 2.0)
                for stage in c.plan.stages:
                    self.assertEqual(stage.image_kv, 'none')
                    self.assertEqual(stage.it_gate, 'none')
                    self.assertEqual(stage.prompt, 'target')
            self.assertFalse(commands[0].plan.stages)
            self.assertEqual(commands[-1].plan.stages[0].end, 12)

    def test_selection_requires_two_old_reviewers_and_exact_scores(self):
        rows = [dict(case_uid=uid, method=method, reviewer_id=reviewer,
                     local_edit_success_0_2=str(2 if uid == 'synth_0036' and method == 'original_fys_tdm' else 0))
                for uid in diagnostic.CASES for method in ('original_fys_tdm', 'endpoint_projection', 'residual_rk2')
                for reviewer in ('reviewer_1', 'reviewer_2')]
        self.assertEqual(len(diagnostic.selection_evidence(rows)), 18)
        with self.assertRaises(ValueError):
            diagnostic.selection_evidence(rows[:-1])
        rows[0]['local_edit_success_0_2'] = '1'
        with self.assertRaises(ValueError):
            diagnostic.selection_evidence(rows)

    def test_trace_rejects_hidden_control_and_wrong_indices(self):
        trace = {'trace': [dict(step=i, image_kv='none', it_gate='none',
                  latent_projection='none', residual_control='source_referenced_rk2' if i < 1 else None)
                  for i in range(15)],
                 'residual_control_trace': [dict(**METRICS, step=0, source_current_index=0,
                    source_midpoint_index=0, source_next_index=1, timestep=1., next_timestep=.9)]}
        diagnostic.validate_trace(trace, 1)
        trace['trace'][10]['image_kv'] = 'source_all'
        with self.assertRaises(ValueError):
            diagnostic.validate_trace(trace, 1)
        trace['trace'][10]['image_kv'] = 'none'
        trace['residual_control_trace'][0]['outside_residual_max_after'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            diagnostic.validate_trace(trace, 1)



class MathematicalAuditTests(unittest.TestCase):
    def test_reverse_midpoint_is_not_forward_midpoint(self):
        # dx/dt=x, reverse interval 0 -> 0.5, x(0)=1.
        reverse_mid = 1 + .25 * 1
        source_high = 1 + .5 * reverse_mid
        forward_mid = source_high - .25 * source_high
        self.assertEqual(reverse_mid, 1.25)
        self.assertEqual(forward_mid, 1.21875)
        self.assertNotEqual(reverse_mid, forward_mid)

    def test_residual_scheme_matches_increment_form_with_negative_steps(self):
        import numpy as np
        rng = np.random.default_rng(81)
        for mask in (np.zeros((1, 4, 1)), np.ones((1, 4, 1)), np.array([1, 0, 1, 0]).reshape(1, 4, 1)):
            x, source, midpoint, endpoint, velocity = rng.normal(size=(5, 1, 4, 1))
            for h in (-.03, -.7):
                residual = x - source
                controlled_mid = midpoint + residual + mask * (h/2 * velocity - (midpoint-source))
                np.testing.assert_allclose(controlled_mid,
                    x + mask*h/2*velocity + (1-mask)*(midpoint-source))
                # Nonlinear, cross-token-coupled field responds to controlled midpoint.
                mid_v = controlled_mid**2 + controlled_mid.mean()
                controlled_end = endpoint + residual + mask * (h*mid_v - (endpoint-source))
                np.testing.assert_allclose(controlled_end,
                    x + mask*h*mid_v + (1-mask)*(endpoint-source))
                np.testing.assert_allclose((1-mask)*(controlled_end-endpoint), (1-mask)*residual)


class EvaluationSmokeTests(unittest.TestCase):
    def test_full_small_image_evaluation_and_review_assets(self):
        import json
        import numpy as np
        import pandas as pd
        from PIL import Image
        from heldout_review_randomization import build_frozen_randomization
        from prepare_gt_mask_diagnostic import json_text, csv_text
        with tempfile.TemporaryDirectory() as tmp:
            root, data = (Path(tmp)/'code').resolve(), (Path(tmp)/'data').resolve()
            data.mkdir()
            records = []
            for uid in diagnostic.CASES:
                Image.fromarray(np.full((16,16,3), 100, dtype=np.uint8)).save(data / f'{uid}.png')
                mask = np.zeros((16,16), dtype=np.uint8); mask[:8] = 255
                Image.fromarray(mask).save(data / f'{uid}_gt.png')
                records.append(dict(case_uid=uid, part='head', edit='dragon', part_size='small',
                    footprint_change='expansion', source_prompt='source', target_prompt='target',
                    source_image=f'{uid}.png', gt_mask=f'{uid}_gt.png'))
            runs = diagnostic.commands(root, data, records, 'python')
            for c in runs:
                c.output_dir.mkdir(parents=True)
                (c.output_dir/'tdm').mkdir()
                Image.open(data / f'{c.case_uid}.png').save(c.output_dir/'img_0.jpg')
                (c.output_dir/'run_config.json').write_text(json_text(c.run_config))
                (c.output_dir/'resolved_control_plan.json').write_text(json_text(c.plan.to_dict()))
                n = int(c.plan.name.rsplit('_',1)[1])
                trace = dict(trace=[dict(step=i, image_kv='none', it_gate='none', latent_projection='none',
                    residual_control='source_referenced_rk2' if i<n else None) for i in range(15)],
                    residual_control_trace=[dict(**METRICS, step=i, source_current_index=i, source_midpoint_index=i,
                        source_next_index=i+1, timestep=1-i/15, next_timestep=1-(i+1)/15) for i in range(n)])
                (c.output_dir/'tdm/control_trace.json').write_text(json_text(trace))
            dest = root/'core/protocols'/diagnostic.PROTOCOL
            assignments = build_frozen_randomization([{**r, 'seed':0, 'method':f'N{n:02d}',
                'row_uid':f'{diagnostic.PROTOCOL}::{r["case_uid"]}::N{n:02d}'} for r in records for n in range(14)])
            (dest/'reviewer_randomization.csv').write_text(csv_text(assignments))
            (dest/'review_config.json').write_text((ROOT/'core/protocols/gt_mask_diagnostic_v2/review_config_template.json').read_text())
            diagnostic.evaluate(root, data, records, 'off')
            result = root/'core/results'/diagnostic.PROTOCOL/'evaluation'
            metrics = pd.read_csv(result/'image_metrics.csv')
            self.assertEqual(len(metrics),84)
            self.assertIn('buffered_outside_mask_l1_aux',metrics)
            self.assertIn('strict_outside_mask_lpips',metrics)
            self.assertEqual((result/'comparison.html').read_text().count('<figure>'),96)
            for reviewer in ('reviewer_1','reviewer_2'):
                template = pd.read_csv(result/reviewer/'template.csv')
                self.assertEqual(len(template),84)
                self.assertNotIn('duration',template)
                self.assertFalse(template['candidate_image'].str.contains('duration_').any())
                self.assertTrue((result/reviewer/'review.html').is_file())
            cfg_path = runs[0].output_dir/'run_config.json'
            wrong = json.loads(cfg_path.read_text()); wrong['gt_mask'] = 'wrong.png'
            cfg_path.write_text(json_text(wrong))
            with self.assertRaisesRegex(ValueError, 'run input mismatch'):
                diagnostic.evaluate(root, data, records, 'off')


if __name__ == '__main__':
    unittest.main()
