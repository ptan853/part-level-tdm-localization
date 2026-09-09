"""Actual torch sampler checks; skipped explicitly when torch is unavailable."""
import importlib.util
from pathlib import Path
import sys
import unittest


@unittest.skipUnless(importlib.util.find_spec('torch'), 'requires torch; run on the GPU server before generation')
class PrefixSamplingAudit(unittest.TestCase):
    def test_nonlinear_velocity_uses_controlled_midpoint_and_releases_prefix(self):
        import torch
        from test_control_plan_sampling import ControlPlanSamplingTests
        from flux.sampling import denoise_with_TDM
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core/scripts'))
        from run_residual_rk2_prefix_sweep import build_prefix_plan
        from flux.control_schedule import ControlPlan
        from flux.latent_control import build_residual_midpoint, build_residual_endpoint

        calls = []
        class Model:
            def __call__(self, *, img, txt, y, timesteps, info, **kwargs):
                velocity = .01 * img.square() + .1 * img + .03 * img.mean() + txt.mean() + y.mean() + timesteps.view(-1,1,1)
                if info is not None:
                    calls.append((img.clone(), velocity.clone(), dict(info), txt.clone(), y.clone()))
                return velocity, info
        inputs = ControlPlanSamplingTests._residual_inputs(num_steps=15)
        inputs['model'] = Model()
        inputs['txt'].fill_(.2)
        inputs['vec'].fill_(.3)
        for i in range(16):
            inputs['info']['source_latents'][i] = torch.arange(4).reshape(1,4,1).float() + i*.1
        for i in range(15):
            inputs['info']['source_midpoints'][i] = torch.arange(4).reshape(1,4,1).float() + i*.1+.08
        inputs['img'] = inputs['info']['source_latents'][0].clone()
        mask = torch.tensor([1.,0.,1.,0.])
        output, info = denoise_with_TDM(**inputs, control_plan=ControlPlan.from_dict(build_prefix_plan(13)), control_spatial_mask=mask)
        self.assertEqual(len(calls),30)  # Two updating calls; diagnostic calls have info=None.
        for i in range(15):
            x,v,first,txt,vec = calls[2*i]
            mid,mv,second,_,_ = calls[2*i+1]
            torch.testing.assert_close(txt, inputs['txt'])
            torch.testing.assert_close(vec, inputs['vec'])
            for control in (first,second):
                self.assertFalse(control['inject'])
                self.assertNotIn('attention_control',control)
                self.assertEqual(control['image_kv_layers'],())
            h=inputs['timesteps'][i+1]-inputs['timesteps'][i]
            if i<13:
                expected_mid,_=build_residual_midpoint(current=x, source_current=inputs['info']['source_latents'][i],
                    source_midpoint=inputs['info']['source_midpoints'][i],target_velocity=v,step_size=h,spatial_mask=mask)
                expected_end,_=build_residual_endpoint(current=x,source_current=inputs['info']['source_latents'][i],
                    source_next=inputs['info']['source_latents'][i+1],target_mid_velocity=mv,step_size=h,spatial_mask=mask)
            else:
                expected_mid=x+h/2*v
                expected_end=x+h*mv
            torch.testing.assert_close(mid,expected_mid)
            torch.testing.assert_close(calls[2*i+2][0] if i<14 else output,expected_end)
        self.assertEqual(len(info['residual_control_trace']),13)

    def test_n0_starts_at_inversion_output_and_all_one_matches_n0(self):
        import torch
        from test_control_plan_sampling import ControlPlanSamplingTests
        from flux.sampling import denoise, denoise_with_TDM
        inputs=ControlPlanSamplingTests._residual_inputs(num_steps=2)
        source=torch.arange(4).float().reshape(1,4,1)+3
        z,cache=denoise(inputs['model'],img=source,img_ids=inputs['img_ids'],txt=inputs['txt'],
            txt_ids=inputs['txt_ids'],vec=inputs['vec'],timesteps=inputs['timesteps'],inverse=True,
            info={},inject_list=[False,False],record_source_latents=True)
        torch.testing.assert_close(z,cache['source_latents'][0])
        inputs['img']=z.clone()
        inputs['info'].update(cache)
        inputs['info']['inject_step']=100  # Disable irrelevant TDM thresholding for this two-step toy.
        n0,_=denoise_with_TDM(**inputs,control_plan=ControlPlanSamplingTests._residual_plan(2,-1),control_spatial_mask=torch.ones(4))
        inputs['img']=z.clone()
        one,_=denoise_with_TDM(**inputs,control_plan=ControlPlanSamplingTests._residual_plan(2,1),control_spatial_mask=torch.ones(4))
        torch.testing.assert_close(n0,source)
        torch.testing.assert_close(one,n0)
