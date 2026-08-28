import importlib.util
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src" / "flux" / "attention_mask_utils.py"


def load_utils():
    spec = importlib.util.spec_from_file_location("attention_mask_utils", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ContextSplittingTokenizer:
    pad_token_id = 0

    class _Batch:
        def __init__(self, values):
            self.values = values

        def tolist(self):
            return self.values

    def __call__(self, text, **kwargs):
        if isinstance(text, list):
            return {"input_ids": [self._Batch([10, 20, 21, 23, 22, 30, 0])]}
        return {"input_ids": [101, 102]}

    def convert_ids_to_tokens(self, ids):
        return ["▁a", "▁cur", "ly", "_", "hair", "▁with", "<pad>"][: len(ids)]


class AttentionMaskUtilsTests(unittest.TestCase):
    def test_selects_all_contextual_subtokens_for_underscore_phrase(self):
        utils = load_utils()
        selected = utils.select_target_token_indices(
            ContextSplittingTokenizer(),
            "a man with curly_hair hair with a smile",
            part="hair",
            edit="curly_hair",
            max_length=7,
            token_mode="edit",
        )
        self.assertEqual(selected, [1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
