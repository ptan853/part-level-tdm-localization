import importlib
import importlib.util
from importlib.machinery import ModuleSpec
import types
from pathlib import Path
import sys
import unittest

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLING_PATH = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src" / "flux" / "sampling.py"
PROBE_PATH = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src" / "flux" / "same_state_probe.py"
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"


def load_sampling_module():
    sys.path.insert(0, str(FYS_SRC))
    spec = importlib.util.spec_from_file_location("flux.sampling", SAMPLING_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_probe_module():
    sys.path.insert(0, str(FYS_SRC))
    spec = importlib.util.spec_from_file_location("flux.same_state_probe", PROBE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_flux_model_module():
    sys.path.insert(0, str(FYS_SRC))
    return importlib.import_module("flux.model")


def build_tiny_flux():
    flux_model = load_flux_model_module()
    params = flux_model.FluxParams(
        in_channels=2,
        vec_in_dim=4,
        context_in_dim=3,
        hidden_size=4,
        mlp_ratio=1.0,
        num_heads=1,
        depth=0,
        depth_single_blocks=1,
        axes_dim=[2, 2],
        theta=10000,
        qkv_bias=False,
        guidance_embed=False,
    )
    return flux_model.Flux(params)


def install_optional_dependency_stubs():
    def make_stub(name):
        module = types.ModuleType(name)
        module.__spec__ = ModuleSpec(name, loader=None)
        return module

    class DummyHFObject:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return cls()

        def eval(self):
            return self

        def requires_grad_(self, *args, **kwargs):
            return self

        @property
        def device(self):
            return torch.device("cpu")

        def __call__(self, *args, **kwargs):
            return {"last_hidden_state": torch.zeros(1, 1, 1), "pooler_output": torch.zeros(1, 1)}

    matplotlib = make_stub("matplotlib")
    pyplot = make_stub("matplotlib.pyplot")
    matplotlib.use = lambda *args, **kwargs: None
    matplotlib.pyplot = pyplot
    seaborn = make_stub("seaborn")

    scipy = make_stub("scipy")
    signal = make_stub("scipy.signal")
    signal.convolve2d = lambda *args, **kwargs: None
    ndimage = make_stub("scipy.ndimage")
    ndimage.gaussian_filter = lambda *args, **kwargs: None
    scipy.signal = signal
    scipy.ndimage = ndimage

    tqdm_mod = make_stub("tqdm")
    tqdm_mod.tqdm = lambda iterable, *args, **kwargs: iterable

    transformers = make_stub("transformers")
    transformers.CLIPTextModel = DummyHFObject
    transformers.CLIPTokenizer = DummyHFObject
    transformers.T5EncoderModel = DummyHFObject
    transformers.T5Tokenizer = DummyHFObject

    sys.modules.setdefault("matplotlib", matplotlib)
    sys.modules.setdefault("matplotlib.pyplot", pyplot)
    sys.modules.setdefault("seaborn", seaborn)
    sys.modules.setdefault("scipy", scipy)
    sys.modules.setdefault("scipy.signal", signal)
    sys.modules.setdefault("scipy.ndimage", ndimage)
    sys.modules.setdefault("tqdm", tqdm_mod)
    sys.modules["transformers"] = transformers


class FakeModel:
    def __init__(self):
        self.calls = []

    def __call__(
        self,
        *,
        img,
        img_ids,
        txt,
        txt_ids,
        y,
        timesteps,
        guidance,
        info,
        controlnet_block_samples=None,
        controlnet_single_block_samples=None,
    ):
        pred = img + timesteps.view(-1, 1, 1)
        self.calls.append(
            {
                "img": img.detach().clone(),
                "img_ids": img_ids.detach().clone(),
                "timestep": timesteps.detach().clone(),
                "pred": pred.detach().clone(),
            }
        )
        return pred, info


class InversionStepObserverTest(unittest.TestCase):
    def test_record_source_latents_in_denoising_schedule_order(self):
        install_optional_dependency_stubs()
        sampling = load_sampling_module()

        initial = torch.ones(1, 2, 2, requires_grad=True)
        inversion_input = initial.clone()
        img_ids = torch.zeros(1, 1, 3)
        txt = torch.zeros(1, 1, 4)
        txt_ids = torch.zeros(1, 1, 3)
        vec = torch.zeros(1, 4)
        timesteps = [1.0, 0.5, 0.0]
        inject_list = [False, False]

        _, info = sampling.denoise(
            FakeModel(),
            img=inversion_input,
            img_ids=img_ids,
            txt=txt,
            txt_ids=txt_ids,
            vec=vec,
            timesteps=timesteps,
            inverse=True,
            info={},
            inject_list=inject_list,
            record_source_latents=True,
        )

        self.assertEqual(sorted(info["source_latents"]), [0, 1, 2])
        self.assertEqual(sorted(info["source_midpoints"]), [0, 1])
        torch.testing.assert_close(info["source_latents"][2], initial)
        torch.testing.assert_close(info["source_latents"][1], torch.full_like(initial, 1.75))
        torch.testing.assert_close(info["source_latents"][0], torch.full_like(initial, 3.28125))
        torch.testing.assert_close(info["source_midpoints"][1], torch.full_like(initial, 1.25))
        torch.testing.assert_close(info["source_midpoints"][0], torch.full_like(initial, 2.3125))
        self.assertFalse(info["source_latents"][2].requires_grad)
        self.assertFalse(info["source_midpoints"][1].requires_grad)
        self.assertNotEqual(info["source_latents"][2].data_ptr(), inversion_input.data_ptr())
        self.assertNotEqual(info["source_midpoints"][1].data_ptr(), inversion_input.data_ptr())
        with torch.no_grad():
            inversion_input.add_(10.0)
        torch.testing.assert_close(info["source_latents"][2], initial)
        torch.testing.assert_close(info["source_midpoints"][1], torch.full_like(initial, 1.25))

    def test_source_latent_recording_is_opt_in_and_preserves_output(self):
        install_optional_dependency_stubs()
        sampling = load_sampling_module()

        initial = torch.ones(1, 2, 2)
        img_ids = torch.zeros(1, 1, 3)
        txt = torch.zeros(1, 1, 4)
        txt_ids = torch.zeros(1, 1, 3)
        vec = torch.zeros(1, 4)
        timesteps = [1.0, 0.5, 0.0]
        inject_list = [False, False]

        unrecorded_info = {}
        unrecorded, unrecorded_info = sampling.denoise(
            FakeModel(),
            img=initial.clone(),
            img_ids=img_ids,
            txt=txt,
            txt_ids=txt_ids,
            vec=vec,
            timesteps=timesteps,
            inverse=True,
            info=unrecorded_info,
            inject_list=inject_list,
        )

        recorded_info = {}
        recorded, recorded_info = sampling.denoise(
            FakeModel(),
            img=initial.clone(),
            img_ids=img_ids,
            txt=txt,
            txt_ids=txt_ids,
            vec=vec,
            timesteps=timesteps,
            inverse=True,
            info=recorded_info,
            inject_list=inject_list,
            record_source_latents=True,
        )

        torch.testing.assert_close(recorded, unrecorded)
        self.assertNotIn("source_latents", unrecorded_info)
        self.assertNotIn("source_midpoints", unrecorded_info)
        self.assertIn("source_latents", recorded_info)
        self.assertIn("source_midpoints", recorded_info)

    def test_observer_sees_pre_update_state_and_matches_plain_output(self):
        install_optional_dependency_stubs()
        sampling = load_sampling_module()
        fake_model_plain = FakeModel()
        fake_model_probe = FakeModel()

        img = torch.ones(1, 2, 2)
        img_ids = torch.zeros(1, 1, 3)
        txt = torch.zeros(1, 1, 4)
        txt_ids = torch.zeros(1, 1, 3)
        vec = torch.zeros(1, 4)
        timesteps = [1.0, 0.5, 0.0]
        inject_list = [False, False]
        info_plain = {}
        info_probe = {}
        observed = []

        def observer(**event):
            observed.append(
                {
                    key: value.clone() if torch.is_tensor(value) else value
                    for key, value in event.items()
                }
            )

        z_plain, _ = sampling.denoise(
            fake_model_plain,
            img=img.clone(),
            img_ids=img_ids.clone(),
            txt=txt.clone(),
            txt_ids=txt_ids.clone(),
            vec=vec.clone(),
            timesteps=timesteps,
            inverse=True,
            info=info_plain,
            inject_list=inject_list,
        )

        z_probe, _ = sampling.denoise(
            fake_model_probe,
            img=img.clone(),
            img_ids=img_ids.clone(),
            txt=txt.clone(),
            txt_ids=txt_ids.clone(),
            vec=vec.clone(),
            timesteps=timesteps,
            inverse=True,
            info=info_probe,
            inject_list=inject_list,
            step_observer=observer,
        )

        torch.testing.assert_close(z_plain, z_probe)
        self.assertEqual(len(observed), len(timesteps) - 1)
        self.assertEqual(observed[0]["step_index"], 0)
        torch.testing.assert_close(observed[0]["img"], fake_model_probe.calls[0]["img"])
        torch.testing.assert_close(observed[0]["timestep"], fake_model_probe.calls[0]["timestep"])
        torch.testing.assert_close(observed[0]["source_pred"], fake_model_probe.calls[0]["pred"])
        self.assertEqual(observed[1]["step_index"], 1)
        torch.testing.assert_close(observed[1]["img"], fake_model_probe.calls[2]["img"])
        torch.testing.assert_close(observed[1]["timestep"], fake_model_probe.calls[2]["timestep"])
        torch.testing.assert_close(observed[1]["source_pred"], fake_model_probe.calls[2]["pred"])

    def test_same_state_probe_integrates_with_denoise_actual_flux_path(self):
        install_optional_dependency_stubs()
        sampling = load_sampling_module()
        probe = load_probe_module()
        model = build_tiny_flux()

        img = torch.tensor([[[0.1, -0.2], [0.3, 0.4]]], dtype=torch.float32)
        img_ids = torch.zeros(1, 2, 2, dtype=torch.float32)
        txt = torch.tensor([[[0.0, 0.1, 0.2], [0.3, 0.4, 0.5]]], dtype=torch.float32)
        txt_ids = torch.zeros(1, 2, 2, dtype=torch.float32)
        vec = torch.tensor([[0.2, -0.1, 0.4, 0.0]], dtype=torch.float32)
        observer = probe.SameStateInversionProbe(
            model=model,
            target_txt=txt,
            target_txt_ids=txt_ids,
            target_vec=vec,
        )

        z, info = sampling.denoise(
            model,
            img=img,
            img_ids=img_ids,
            txt=txt,
            txt_ids=txt_ids,
            vec=vec,
            timesteps=[1.0, 0.5, 0.0],
            guidance=1.5,
            inverse=True,
            info={},
            inject_list=[False, False],
            step_observer=observer,
        )

        self.assertEqual(z.shape, img.shape)
        self.assertIn("inv_noise", info)
        self.assertEqual(observer.step_indices, [0, 1])
        self.assertEqual(len(observer.velocity_step_maps), 2)
        for velocity_map in observer.velocity_step_maps:
            self.assertEqual(velocity_map.shape, (img.shape[1],))
            torch.testing.assert_close(torch.from_numpy(velocity_map), torch.zeros(img.shape[1]))


if __name__ == "__main__":
    unittest.main()
