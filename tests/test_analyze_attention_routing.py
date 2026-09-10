import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core/scripts"))


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("analyze_attention_routing"))
        import analyze_attention_routing
        self.module = analyze_attention_routing

    def test_verification_detects_changed_initial_or_final_latent(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            for p in (a, b):
                (p / "routing").mkdir(parents=True)
                for name in ("initial", "final"):
                    np.save(p / f"routing/{name}_latent.npy", np.zeros((1, 4, 2)))
            self.assertTrue(self.module.verify_latents(a, b)["passed"])
            np.save(b / "routing/final_latent.npy", np.ones((1, 4, 2)))
            self.assertFalse(self.module.verify_latents(a, b)["passed"])

    def test_read_rejects_invalid_probability_mass(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "routing"
            p.mkdir()
            (p / "metadata.json").write_text(json.dumps({"records": 1, "text_length": 2,
                "num_steps": 1, "layers": {"double": [0]}, "tokens": {"token_ids": [1, 2]}}))
            np.savez(p / "attention_statistics.npz", text_attention=np.zeros((1, 1, 2)),
                     region_mass=np.zeros((1, 1, 3)), steps=[0], layers=["double_0"], times=[.5])
            with self.assertRaises(ValueError):
                self.module.read_run(Path(tmp))


if __name__ == "__main__":
    unittest.main()
