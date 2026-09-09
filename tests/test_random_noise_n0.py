import importlib.util
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core/scripts'))

class ProtocolTests(unittest.TestCase):
    def test_frozen_parameters(self):
        from run_random_noise_n0 import configuration
        c=configuration()
        self.assertEqual((c['num_steps'],c['guidance'],c['seed'],c['width'],c['height']),(15,2.0,0,1024,1024))
        self.assertEqual(c['initialization'],'random_noise')
        self.assertFalse(c['inversion'])
        self.assertEqual(c['control_duration'],0)

@unittest.skipUnless(importlib.util.find_spec('torch'),'requires server torch')
class SamplingTests(unittest.TestCase):
    def test_noise_reproducible_and_independent_of_global_rng(self):
        import torch
        from run_random_noise_n0 import make_noise
        a=make_noise();torch.manual_seed(918);torch.randn(27);b=make_noise()
        torch.testing.assert_close(a,b,rtol=0,atol=0)
        self.assertEqual(tuple(a.shape),(1,16,128,128))
        self.assertEqual(a.dtype,torch.bfloat16)
        self.assertGreater(a.float().std().item(),.95)

    def test_matches_existing_n0_update_with_same_initial_latent(self):
        import torch
        from test_control_plan_sampling import ControlPlanSamplingTests
        from flux.sampling import denoise_with_TDM
        from run_random_noise_n0 import sample_uncontrolled
        inputs=ControlPlanSamplingTests._residual_inputs(num_steps=2)
        inputs['img']=torch.arange(4).reshape(1,4,1).float()/4
        inputs['info']['inject_step']=100
        class Model:
            def __call__(self, *,img,info,**kw):
                return .1*img.square()+.1*img.mean()+kw['txt'].mean()+kw['y'].mean()+1,info
        inputs['model']=Model()
        expected,_=denoise_with_TDM(**inputs,control_plan=ControlPlanSamplingTests._residual_plan(2,-1),control_spatial_mask=torch.ones(4))
        model_inputs={k:inputs[k] for k in ('img','img_ids','txt','txt_ids','vec')}
        actual,trace=sample_uncontrolled(inputs['model'],model_inputs,inputs['timesteps'],2.0)
        torch.testing.assert_close(actual,expected)
        self.assertEqual(len(trace),4)
        self.assertTrue(all(not r['inject'] and not r['inverse'] for r in trace))
        self.assertEqual([r['second_order'] for r in trace],[False,True,False,True])
