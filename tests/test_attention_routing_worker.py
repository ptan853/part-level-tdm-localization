import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core/scripts"))
sys.path.insert(0, str(ROOT / "core/third_party/FollowYourShape/src"))


class WorkerTests(unittest.TestCase):
    def test_target_token_metadata_uses_actual_tokenizer_and_padding(self):
        from attention_routing_worker import observe_edit

        class Tokenizer:
            pad_token_id = 0
            vocabulary = {"a": 1, "cat": 2, "with": 3, "dragon": 4, "head": 5}

            def __call__(self, text, **kwargs):
                if isinstance(text, str):
                    return {"input_ids": [self.vocabulary[x] for x in text.split()]}
                ids = [self.vocabulary[x] for x in text[0].split()] + [6]
                n = kwargs["max_length"]
                return {"input_ids": torch.tensor([ids + [0] * (n - len(ids))]),
                        "attention_mask": torch.tensor([[1] * len(ids) + [0] * (n - len(ids))])}

            def convert_ids_to_tokens(self, ids):
                values = {v: k for k, v in self.vocabulary.items()} | {0: "<pad>", 6: "</s>"}
                return [values[x] for x in ids]

        edit = SimpleNamespace(
            prepare=lambda *a, **k: {"txt": torch.zeros(1, 8, 2)},
            denoise_with_TDM=lambda model, **k: (k["img"], k["info"]),
        )
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(output_dir=tmp, target_prompt="a cat with dragon head",
                                   attention_part="head", attention_edit="dragon")
            with mock.patch("attention_routing_worker.RoutingRecorder") as recorder:
                with observe_edit(edit, args, np.array([[1, 0], [0, 0]]), recording=True, subject="cat"):
                    edit.prepare(SimpleNamespace(tokenizer=Tokenizer(), max_length=8), None, None,
                                 prompt=args.target_prompt)
                    edit.denoise_with_TDM(None, img=torch.zeros(1, 4, 2), info={},
                                         txt=torch.zeros(1, 8, 2), width=32, height=32, timesteps=[1, 0])
                tokens = recorder.return_value.save.call_args.kwargs["tokens"]
                self.assertEqual(tokens["groups"], {"subject": [1], "part": [4], "edit": [3]})
                self.assertEqual(tokens["valid_positions"], [1, 1, 1, 1, 1, 1, 0, 0])

    def test_disabled_worker_passes_through_and_restores(self):
        self.assertIsNotNone(importlib.util.find_spec("attention_routing_worker"))
        from attention_routing_worker import observe_edit
        original_prepare = lambda *a, **k: None
        def original_denoise(model, **kwargs):
            return kwargs["img"] + 1, kwargs["info"]
        edit = SimpleNamespace(prepare=original_prepare, denoise_with_TDM=original_denoise)
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(output_dir=tmp, target_prompt="a cat", attention_part="head",
                                   attention_edit="dragon")
            image = torch.zeros(1, 4, 2)
            with observe_edit(edit, args, np.array([[1, 0], [0, 0]]), recording=False, subject="cat"):
                result, _ = edit.denoise_with_TDM(None, img=image, info={}, timesteps=[1., 0.],
                                                 txt=torch.zeros(1, 3, 2), width=32, height=32)
            self.assertTrue(torch.equal(result, image + 1))
            np.testing.assert_array_equal(np.load(Path(tmp) / "routing/final_latent.npy"), result.numpy())
        self.assertIs(edit.prepare, original_prepare)
        self.assertIs(edit.denoise_with_TDM, original_denoise)


if __name__ == "__main__":
    unittest.main()
