import importlib.util
from importlib.machinery import ModuleSpec
import types
from pathlib import Path
import sys
import unittest

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLING_PATH = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src" / "flux" / "sampling.py"
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"


def load_sampling_module():
    sys.path.insert(0, str(FYS_SRC))
    spec = importlib.util.spec_from_file_location("flux.sampling", SAMPLING_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


if __name__ == "__main__":
    unittest.main()
