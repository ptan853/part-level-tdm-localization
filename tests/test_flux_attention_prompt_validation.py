import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

import numpy as np
import torch
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "core" / "scripts" / "run_flux_attention_baseline.py"
FYS_RUNNER_PATH = REPO_ROOT / "core" / "scripts" / "run_fys_pilot.py"
EDIT_PATH = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src" / "edit.py"
FYS_SRC = REPO_ROOT / "core" / "third_party" / "FollowYourShape" / "src"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_flux_attention_baseline", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_fys_runner_module():
    spec = importlib.util.spec_from_file_location("run_fys_pilot", FYS_RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_edit_module():
    sys.path.insert(0, str(FYS_SRC))
    flux_util_module = types.ModuleType("flux.util")
    flux_util_module.configs = {"flux-dev": object()}
    flux_util_module.embed_watermark = lambda value: value
    flux_util_module.load_ae = lambda *args, **kwargs: None
    flux_util_module.load_clip = lambda *args, **kwargs: None
    flux_util_module.load_flow_model = lambda *args, **kwargs: None
    flux_util_module.load_t5 = lambda *args, **kwargs: None
    sys.modules["flux.util"] = flux_util_module
    if "fire" not in sys.modules:
        fire_module = types.ModuleType("fire")
        fire_module.Fire = object()
        sys.modules["fire"] = fire_module
    transformers_module = sys.modules.get("transformers")
    if transformers_module is None:
        transformers_module = types.ModuleType("transformers")
        sys.modules["transformers"] = transformers_module
    for name in [
        "CLIPTextModel",
        "CLIPTokenizer",
        "T5EncoderModel",
        "T5Tokenizer",
        "DPTForDepthEstimation",
        "DPTImageProcessor",
    ]:
        if not hasattr(transformers_module, name):
            setattr(transformers_module, name, type(name, (), {}))
    if not hasattr(transformers_module, "pipeline"):
        transformers_module.pipeline = lambda *args, **kwargs: None
    if "diffusers" not in sys.modules:
        diffusers_module = types.ModuleType("diffusers")
        diffusers_module.FluxControlNetModel = type("FluxControlNetModel", (), {})
        diffusers_module.FluxMultiControlNetModel = type("FluxMultiControlNetModel", (), {})
        sys.modules["diffusers"] = diffusers_module
    if "seaborn" not in sys.modules:
        sys.modules["seaborn"] = types.ModuleType("seaborn")
    if "cv2" not in sys.modules:
        sys.modules["cv2"] = types.ModuleType("cv2")
    if "imwatermark" not in sys.modules:
        imwatermark_module = types.ModuleType("imwatermark")
        imwatermark_module.WatermarkEncoder = type("WatermarkEncoder", (), {})
        sys.modules["imwatermark"] = imwatermark_module
    spec = importlib.util.spec_from_file_location("fys_edit", EDIT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class DummyT5:
    def __init__(self):
        self.max_length = 512
        self.tokenizer = object()

    def to(self, device):
        return self


class DummyClip:
    def to(self, device):
        return self


class DummyModel:
    def to(self, device):
        return self

    def cpu(self):
        return self


class DummyEncoderDecoder:
    def to(self, device):
        return self


class DummyAE:
    def __init__(self):
        self.encoder = DummyEncoderDecoder()
        self.decoder = DummyEncoderDecoder()

    def to(self, device):
        return self

    def cpu(self):
        return self

    def decode(self, x):
        return x


class RecordingAttentionProbe:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.closed = False
        self.step_records = {"part": [], "edit": []}
        self.token_groups = kwargs["token_groups"]
        self.layer_ids = set(kwargs["layer_ids"])

    def close(self):
        self.closed = True


class RecordingSameStateProbe:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.finalize_calls = []

    def __call__(self, **event):
        return None

    def finalize(self, output_dir, metadata):
        self.finalize_calls.append((Path(output_dir), metadata))
        return {"probe_dir": str(output_dir)}


class PromptValidationTest(unittest.TestCase):
    def test_part_mode_accepts_prompt_containing_part(self):
        runner = load_runner_module()
        records = [
            {
                "case_uid": "case_ok",
                "part": "curly_hair",
                "edit": "curly",
                "target_prompt": "a man with curly hair smiling",
            }
        ]

        runner.validate_prompt_terms(records, token_mode="part")

    def test_part_mode_rejects_prompt_missing_part(self):
        runner = load_runner_module()
        records = [
            {
                "case_uid": "case_bad",
                "part": "head",
                "edit": "alien",
                "target_prompt": "an alien standing in a park",
            }
        ]

        with self.assertRaisesRegex(ValueError, "case_bad"):
            runner.validate_prompt_terms(records, token_mode="part")

    def test_attention_gated_fys_command_uses_separate_output_and_part_edit_args(self):
        runner = load_fys_runner_module()
        record = {
            "case_uid": "case_0001",
            "source_image": "core/data/case/source.png",
            "source_prompt": "a man standing",
            "target_prompt": "a man with alien head standing",
            "follow_your_shape_output_dir": "core/results/follow_your_shape/case_0001",
            "part": "head",
            "edit": "alien",
        }

        command = runner.build_fys_command(
            record,
            repo_root=REPO_ROOT,
            python_executable="python",
            seed=0,
            seed_subdirs=True,
            use_oracle_mask=False,
            name="flux-dev",
            guidance=2.0,
            num_steps=15,
            front=2,
            inject=4,
            offload=True,
            controlnet_type="none",
            tdm_mask_mode="attention_gated",
            attention_token_mode="part_edit",
            attention_layers="28,29",
            output_root=REPO_ROOT / "core" / "results" / "fys_mask_ablation" / "attention_gated_tdm",
        )

        self.assertIn("--tdm_mask_mode", command.args)
        self.assertIn("attention_gated", command.args)
        self.assertIn("--attention_part", command.args)
        self.assertIn("head", command.args)
        self.assertIn("--attention_edit", command.args)
        self.assertIn("alien", command.args)
        self.assertIn("fys_mask_ablation/attention_gated_tdm/case_0001/seed_000", command.run_config["output_dir"])

    def test_oracle_fys_command_uses_gt_mask_and_oracle_mode(self):
        runner = load_fys_runner_module()
        record = {
            "case_uid": "case_0001",
            "source_image": "core/data/case/source.png",
            "gt_mask": "core/data/case/gt_mask.png",
            "source_prompt": "a man standing",
            "target_prompt": "a man with alien head standing",
            "follow_your_shape_output_dir": "core/results/follow_your_shape/case_0001",
            "part": "head",
            "edit": "alien",
        }

        command = runner.build_fys_command(
            record,
            repo_root=REPO_ROOT,
            python_executable="python",
            seed=0,
            seed_subdirs=True,
            use_oracle_mask=True,
            name="flux-dev",
            guidance=2.0,
            num_steps=15,
            front=2,
            inject=4,
            offload=True,
            controlnet_type="none",
            tdm_mask_mode="oracle",
            attention_token_mode="part_edit",
            attention_layers="28,29",
            output_root=REPO_ROOT / "core" / "results" / "fys_mask_ablation" / "oracle_gt_mask",
        )

        self.assertIn("--mask_path", command.args)
        self.assertIn("core/data/case/gt_mask.png", "/".join(command.args))
        self.assertIn("--tdm_mask_mode", command.args)
        self.assertIn("oracle", command.args)
        self.assertEqual(command.run_config["tdm_mask_mode"], "oracle")
        self.assertIn("fys_mask_ablation/oracle_gt_mask/case_0001/seed_000", command.run_config["output_dir"])

    def test_same_state_probe_requires_part_and_edit_terms(self):
        edit = load_edit_module()
        parser = edit.build_arg_parser()

        with self.assertRaises(SystemExit):
            args = parser.parse_args(["--same_state_probe_dir", "probe"])
            edit.validate_args(parser, args)

        args = parser.parse_args(
            [
                "--same_state_probe_dir",
                "probe",
                "--probe_part",
                "head",
                "--probe_edit",
                "alien",
            ]
        )
        edit.validate_args(parser, args)

        controlnet_args = parser.parse_args(
            [
                "--same_state_probe_dir",
                "probe",
                "--probe_part",
                "head",
                "--probe_edit",
                "alien",
                "--controlnet_type",
                "single",
            ]
        )
        with self.assertRaises(SystemExit):
            edit.validate_args(parser, controlnet_args)

    def test_main_wires_same_state_probe_only_for_inversion_and_finalizes(self):
        edit = load_edit_module()
        denoise_calls = []
        probe_instances = []
        attention_instances = []
        select_calls = []

        def fake_prepare(t5, clip, img, prompt):
            return {
                "img": torch.zeros(1, 4, 4),
                "img_ids": torch.zeros(1, 4, 3),
                "txt": torch.zeros(1, 8, 4),
                "txt_ids": torch.zeros(1, 8, 3),
                "vec": torch.zeros(1, 4),
            }

        def fake_select(tokenizer, target_prompt, part, edit, max_length, token_mode):
            select_calls.append(
                {
                    "target_prompt": target_prompt,
                    "part": part,
                    "edit": edit,
                    "max_length": max_length,
                    "token_mode": token_mode,
                }
            )
            if token_mode == "part":
                return [4, 5]
            if token_mode == "edit":
                return [2]
            raise AssertionError(f"unexpected token mode: {token_mode}")

        def fake_attention_probe(*args, **kwargs):
            instance = RecordingAttentionProbe(*args, **kwargs)
            attention_instances.append(instance)
            return instance

        def fake_same_state_probe(*args, **kwargs):
            instance = RecordingSameStateProbe(*args, **kwargs)
            probe_instances.append(instance)
            return instance

        def fake_denoise(*args, **kwargs):
            denoise_calls.append(kwargs)
            return torch.zeros(1, 4, 4), kwargs["info"]

        def fake_denoise_with_tdm(*args, **kwargs):
            self.assertNotIn("step_observer", kwargs)
            return torch.zeros(1, 3, 4, 4), kwargs["info"]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            image_path = tmp_path / "source.png"
            Image.new("RGB", (16, 16), color="white").save(image_path)
            output_dir = tmp_path / "outputs"
            feature_dir = tmp_path / "features"
            vis_dir = tmp_path / "vis"
            probe_dir = tmp_path / "probe"

            args = edit.build_arg_parser().parse_args(
                [
                    "--source_img_dir",
                    str(image_path),
                    "--source_prompt",
                    "a man standing in a park wearing a green shirt",
                    "--target_prompt",
                    "a man with alien head standing in a park wearing a green shirt",
                    "--feature_path",
                    str(feature_dir),
                    "--vis_path",
                    str(vis_dir),
                    "--output_dir",
                    str(output_dir),
                    "--same_state_probe_dir",
                    str(probe_dir),
                    "--probe_part",
                    "head",
                    "--probe_edit",
                    "alien",
                    "--probe_layers",
                    "28,29",
                ]
            )
            edit.validate_args(edit.build_arg_parser(), args)

            with mock.patch.object(edit, "pipeline", return_value=lambda img: [{"label": "nsfw", "score": 0.0}]), \
                mock.patch.object(edit, "load_t5", return_value=DummyT5()), \
                mock.patch.object(edit, "load_clip", return_value=DummyClip()), \
                mock.patch.object(edit, "load_flow_model", return_value=DummyModel()), \
                mock.patch.object(edit, "load_ae", return_value=DummyAE()), \
                mock.patch.object(edit, "encode", return_value=torch.zeros(1, 16, 4, 4)), \
                mock.patch.object(edit, "prepare", side_effect=fake_prepare), \
                mock.patch.object(edit, "get_schedule", return_value=[1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]), \
                mock.patch.object(edit, "denoise", side_effect=fake_denoise), \
                mock.patch.object(edit, "denoise_with_TDM", side_effect=fake_denoise_with_tdm), \
                mock.patch.object(edit, "build_inject_list", return_value=[False] * 10), \
                mock.patch.object(edit, "unpack", return_value=torch.zeros(1, 3, 4, 4)), \
                mock.patch.object(edit, "embed_watermark", side_effect=lambda x: x), \
                mock.patch.object(edit, "select_target_token_indices", side_effect=fake_select), \
                mock.patch.object(edit, "NamedSingleBlockAttentionProbe", side_effect=fake_attention_probe), \
                mock.patch.object(edit, "SameStateInversionProbe", side_effect=fake_same_state_probe):
                edit.main(args, device="cpu")

        self.assertEqual(len(select_calls), 2)
        self.assertEqual([call["token_mode"] for call in select_calls], ["part", "edit"])
        self.assertEqual(len(attention_instances), 1)
        self.assertEqual(attention_instances[0].token_groups, {"part": [4, 5], "edit": [2]})
        self.assertEqual(attention_instances[0].layer_ids, {28, 29})
        self.assertEqual(len(probe_instances), 1)
        self.assertEqual(len(denoise_calls), 1)
        self.assertIs(denoise_calls[0]["step_observer"], probe_instances[0])
        self.assertTrue(attention_instances[0].closed)
        self.assertEqual(len(probe_instances[0].finalize_calls), 1)
        finalize_dir, finalize_metadata = probe_instances[0].finalize_calls[0]
        self.assertEqual(finalize_dir.name, "probe")
        self.assertEqual(finalize_metadata["probe_part"], "head")
        self.assertEqual(finalize_metadata["probe_edit"], "alien")
        self.assertEqual(finalize_metadata["part_token_indices"], [4, 5])
        self.assertEqual(finalize_metadata["edit_token_indices"], [2])
        self.assertEqual(finalize_metadata["probe_layer_ids"], [28, 29])

    def test_main_without_same_state_probe_leaves_probe_path_unused(self):
        edit = load_edit_module()
        denoise_calls = []

        def fake_prepare(t5, clip, img, prompt):
            return {
                "img": torch.zeros(1, 4, 4),
                "img_ids": torch.zeros(1, 4, 3),
                "txt": torch.zeros(1, 8, 4),
                "txt_ids": torch.zeros(1, 8, 3),
                "vec": torch.zeros(1, 4),
            }

        def fake_denoise(*args, **kwargs):
            denoise_calls.append(kwargs)
            return torch.zeros(1, 4, 4), kwargs["info"]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            image_path = tmp_path / "source.png"
            Image.new("RGB", (16, 16), color="white").save(image_path)
            output_dir = tmp_path / "outputs"
            feature_dir = tmp_path / "features"
            vis_dir = tmp_path / "vis"
            probe_dir = tmp_path / "probe"

            args = edit.build_arg_parser().parse_args(
                [
                    "--source_img_dir",
                    str(image_path),
                    "--source_prompt",
                    "a man standing in a park wearing a green shirt",
                    "--target_prompt",
                    "a man with alien head standing in a park wearing a green shirt",
                    "--feature_path",
                    str(feature_dir),
                    "--vis_path",
                    str(vis_dir),
                    "--output_dir",
                    str(output_dir),
                ]
            )
            edit.validate_args(edit.build_arg_parser(), args)

            with mock.patch.object(edit, "pipeline", return_value=lambda img: [{"label": "nsfw", "score": 0.0}]), \
                mock.patch.object(edit, "load_t5", return_value=DummyT5()), \
                mock.patch.object(edit, "load_clip", return_value=DummyClip()), \
                mock.patch.object(edit, "load_flow_model", return_value=DummyModel()), \
                mock.patch.object(edit, "load_ae", return_value=DummyAE()), \
                mock.patch.object(edit, "encode", return_value=torch.zeros(1, 16, 4, 4)), \
                mock.patch.object(edit, "prepare", side_effect=fake_prepare), \
                mock.patch.object(edit, "get_schedule", return_value=[1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]), \
                mock.patch.object(edit, "denoise", side_effect=fake_denoise), \
                mock.patch.object(edit, "denoise_with_TDM", return_value=(torch.zeros(1, 3, 4, 4), {"feature": {}, "inject_step": 4})), \
                mock.patch.object(edit, "build_inject_list", return_value=[False] * 10), \
                mock.patch.object(edit, "unpack", return_value=torch.zeros(1, 3, 4, 4)), \
                mock.patch.object(edit, "embed_watermark", side_effect=lambda x: x), \
                mock.patch.object(edit, "NamedSingleBlockAttentionProbe", side_effect=AssertionError("probe should stay disabled")), \
                mock.patch.object(edit, "SameStateInversionProbe", side_effect=AssertionError("probe should stay disabled")):
                edit.main(args, device="cpu")

        self.assertEqual(len(denoise_calls), 1)
        self.assertIsNone(denoise_calls[0].get("step_observer"))
        self.assertFalse(denoise_calls[0].get("record_source_latents", False))
        self.assertFalse(probe_dir.exists())

    def test_main_records_source_latents_only_for_projection_plan(self):
        edit = load_edit_module()

        def fake_prepare(t5, clip, img, prompt):
            return {
                "img": torch.zeros(1, 4, 4),
                "img_ids": torch.zeros(1, 4, 3),
                "txt": torch.zeros(1, 8, 4),
                "txt_ids": torch.zeros(1, 8, 3),
                "vec": torch.zeros(1, 4),
            }

        def run_with_plan(tmp_path, plan):
            plan_path = tmp_path / f"{plan['name']}.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            image_path = tmp_path / "source.png"
            mask_path = tmp_path / "mask.png"
            Image.new("RGB", (16, 16), color="white").save(image_path)
            Image.new("L", (16, 16), color=255).save(mask_path)
            args = edit.build_arg_parser().parse_args(
                [
                    "--source_img_dir", str(image_path),
                    "--source_prompt", "a man standing",
                    "--target_prompt", "a man with alien head standing",
                    "--feature_path", str(tmp_path / f"{plan['name']}_features"),
                    "--vis_path", str(tmp_path / f"{plan['name']}_vis"),
                    "--output_dir", str(tmp_path / f"{plan['name']}_outputs"),
                    "--mask_path", str(mask_path),
                    "--tdm_mask_mode", "oracle",
                    "--num_steps", "10",
                    "--control-plan-resolved", str(plan_path),
                ]
            )
            edit.validate_args(edit.build_arg_parser(), args)
            denoise_calls = []
            target_infos = []
            target_masks = []

            def fake_denoise(*args, **kwargs):
                denoise_calls.append(kwargs)
                if kwargs.get("record_source_latents"):
                    kwargs["info"]["source_latents"] = {index: torch.zeros(1, 4, 4) for index in range(11)}
                return torch.zeros(1, 4, 4), kwargs["info"]

            def fake_denoise_with_tdm(*args, **kwargs):
                target_infos.append(kwargs["info"])
                target_masks.append(kwargs["control_spatial_mask"])
                return torch.zeros(1, 3, 4, 4), kwargs["info"]

            with mock.patch.object(edit, "pipeline", return_value=lambda img: [{"label": "nsfw", "score": 0.0}]), \
                mock.patch.object(edit, "load_t5", return_value=DummyT5()), \
                mock.patch.object(edit, "load_clip", return_value=DummyClip()), \
                mock.patch.object(edit, "load_flow_model", return_value=DummyModel()), \
                mock.patch.object(edit, "load_ae", return_value=DummyAE()), \
                mock.patch.object(edit, "encode", return_value=torch.zeros(1, 16, 4, 4)), \
                mock.patch.object(edit, "prepare", side_effect=fake_prepare), \
                mock.patch.object(edit, "get_schedule", return_value=[1.0 - index / 10 for index in range(11)]), \
                mock.patch.object(edit, "denoise", side_effect=fake_denoise), \
                mock.patch.object(edit, "denoise_with_TDM", side_effect=fake_denoise_with_tdm), \
                mock.patch.object(edit, "build_inject_list", return_value=[False] * 10), \
                mock.patch.object(edit, "unpack", return_value=torch.zeros(1, 3, 4, 4)), \
                mock.patch.object(edit, "embed_watermark", side_effect=lambda x: x):
                edit.main(args, device="cpu")

            return denoise_calls, target_infos, target_masks

        projection_plan = {
            "name": "projection",
            "num_steps": 10,
            "mask_source": "oracle",
            "stages": [{
                "name": "project",
                "start": 2,
                "end": 8,
                "latent_projection": "source_outside_mask",
            }],
        }
        legacy_plan = {
            "name": "legacy",
            "num_steps": 10,
            "mask_source": "oracle",
            "stages": [{"name": "target", "start": 2, "end": 8}],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            projection_calls, projection_infos, projection_masks = run_with_plan(tmp_path, projection_plan)
            legacy_calls, legacy_infos, legacy_masks = run_with_plan(tmp_path, legacy_plan)

        self.assertTrue(projection_calls[0]["record_source_latents"])
        self.assertIn("source_latents", projection_infos[0])
        self.assertEqual(np.asarray(projection_masks[0]).shape, (2, 2))
        self.assertFalse(legacy_calls[0].get("record_source_latents", False))
        self.assertNotIn("source_latents", legacy_infos[0])
        self.assertEqual(np.asarray(legacy_masks[0]).shape, (2, 2))

    def test_main_aligns_mixed_nonsquare_oracle_mask_to_image_token_grid(self):
        edit = load_edit_module()
        captured_masks = []

        def fake_prepare(t5, clip, img, prompt):
            return {
                "img": torch.zeros(1, 4, 4),
                "img_ids": torch.zeros(1, 4, 3),
                "txt": torch.zeros(1, 8, 4),
                "txt_ids": torch.zeros(1, 8, 3),
                "vec": torch.zeros(1, 4),
            }

        def fake_denoise(*args, **kwargs):
            return torch.zeros(1, 4, 4), kwargs["info"]

        def fake_denoise_with_tdm(*args, **kwargs):
            captured_masks.append(kwargs["control_spatial_mask"])
            return torch.zeros(1, 3, 4, 4), kwargs["info"]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            image_path = tmp_path / "source.png"
            mask_path = tmp_path / "mixed_nonsquare_mask.png"
            Image.new("RGB", (7, 5), color="white").save(image_path)

            # Deliberately asymmetric foreground cells exercise orientation,
            # nearest-neighbor resize, max pooling, and row-major flattening.
            mask_pixels = np.zeros((5, 7), dtype=np.uint8)
            mask_pixels[1, 1] = 255
            mask_pixels[3, 5] = 255
            mask_pixels[4, 0] = 255
            Image.fromarray(mask_pixels, mode="L").save(mask_path)

            args = edit.build_arg_parser().parse_args(
                [
                    "--source_img_dir", str(image_path),
                    "--source_prompt", "a man standing",
                    "--target_prompt", "a man with alien head standing",
                    "--feature_path", str(tmp_path / "features"),
                    "--vis_path", str(tmp_path / "vis"),
                    "--output_dir", str(tmp_path / "outputs"),
                    "--mask_path", str(mask_path),
                    "--tdm_mask_mode", "oracle",
                    "--num_steps", "10",
                ]
            )
            edit.validate_args(edit.build_arg_parser(), args)

            with mock.patch.object(edit, "pipeline", return_value=lambda img: [{"label": "nsfw", "score": 0.0}]), \
                mock.patch.object(edit, "load_t5", return_value=DummyT5()), \
                mock.patch.object(edit, "load_clip", return_value=DummyClip()), \
                mock.patch.object(edit, "load_flow_model", return_value=DummyModel()), \
                mock.patch.object(edit, "load_ae", return_value=DummyAE()), \
                mock.patch.object(edit, "encode", return_value=torch.zeros(1, 16, 8, 6)), \
                mock.patch.object(edit, "prepare", side_effect=fake_prepare), \
                mock.patch.object(edit, "get_schedule", return_value=[1.0 - index / 10 for index in range(11)]), \
                mock.patch.object(edit, "denoise", side_effect=fake_denoise), \
                mock.patch.object(edit, "denoise_with_TDM", side_effect=fake_denoise_with_tdm), \
                mock.patch.object(edit, "build_inject_list", return_value=[False] * 10), \
                mock.patch.object(edit, "unpack", return_value=torch.zeros(1, 3, 4, 4)), \
                mock.patch.object(edit, "embed_watermark", side_effect=lambda x: x):
                edit.main(args, device="cpu")

        self.assertEqual(len(captured_masks), 1)
        expected_grid = np.array(
            [[0, 0, 0], [1, 0, 0], [0, 0, 1], [1, 0, 1]],
            dtype=np.uint8,
        )
        np.testing.assert_array_equal(captured_masks[0], expected_grid)
        np.testing.assert_array_equal(
            np.asarray(captured_masks[0]).flatten(),
            np.array([0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1], dtype=np.uint8),
        )

    def test_main_aligns_top_left_pixel_quarter_to_top_left_token_quarter(self):
        edit = load_edit_module()
        captured_masks = []
        prepared_image_token_counts = []

        def fake_prepare(t5, clip, img, prompt):
            prepared = {
                "img": torch.zeros(1, 16, 4),
                "img_ids": torch.zeros(1, 16, 3),
                "txt": torch.zeros(1, 8, 4),
                "txt_ids": torch.zeros(1, 8, 3),
                "vec": torch.zeros(1, 4),
            }
            prepared_image_token_counts.append(prepared["img"].shape[1])
            return prepared

        def fake_denoise(*args, **kwargs):
            return torch.zeros(1, 16, 4), kwargs["info"]

        def fake_denoise_with_tdm(*args, **kwargs):
            captured_masks.append(kwargs["control_spatial_mask"])
            return torch.zeros(1, 3, 4, 4), kwargs["info"]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            image_path = tmp_path / "source.png"
            mask_path = tmp_path / "top_left_quarter.png"
            Image.new("RGB", (8, 8), color="white").save(image_path)

            mask_pixels = np.zeros((8, 8), dtype=np.uint8)
            mask_pixels[:4, :4] = 255
            Image.fromarray(mask_pixels, mode="L").save(mask_path)

            args = edit.build_arg_parser().parse_args(
                [
                    "--source_img_dir", str(image_path),
                    "--source_prompt", "a man standing",
                    "--target_prompt", "a man with alien head standing",
                    "--feature_path", str(tmp_path / "features"),
                    "--vis_path", str(tmp_path / "vis"),
                    "--output_dir", str(tmp_path / "outputs"),
                    "--mask_path", str(mask_path),
                    "--tdm_mask_mode", "oracle",
                    "--num_steps", "10",
                ]
            )
            edit.validate_args(edit.build_arg_parser(), args)

            with mock.patch.object(edit, "pipeline", return_value=lambda img: [{"label": "nsfw", "score": 0.0}]), \
                mock.patch.object(edit, "load_t5", return_value=DummyT5()), \
                mock.patch.object(edit, "load_clip", return_value=DummyClip()), \
                mock.patch.object(edit, "load_flow_model", return_value=DummyModel()), \
                mock.patch.object(edit, "load_ae", return_value=DummyAE()), \
                mock.patch.object(edit, "encode", return_value=torch.zeros(1, 16, 8, 8)), \
                mock.patch.object(edit, "prepare", side_effect=fake_prepare), \
                mock.patch.object(edit, "get_schedule", return_value=[1.0 - index / 10 for index in range(11)]), \
                mock.patch.object(edit, "denoise", side_effect=fake_denoise), \
                mock.patch.object(edit, "denoise_with_TDM", side_effect=fake_denoise_with_tdm), \
                mock.patch.object(edit, "build_inject_list", return_value=[False] * 10), \
                mock.patch.object(edit, "unpack", return_value=torch.zeros(1, 3, 4, 4)), \
                mock.patch.object(edit, "embed_watermark", side_effect=lambda x: x):
                edit.main(args, device="cpu")

        self.assertEqual(len(captured_masks), 1)
        expected_grid = np.zeros((4, 4), dtype=np.uint8)
        expected_grid[:2, :2] = 1
        actual = np.asarray(captured_masks[0])
        np.testing.assert_array_equal(actual, expected_grid)
        self.assertEqual(actual.size, prepared_image_token_counts[0])
        self.assertEqual(set(np.unique(actual)), {0, 1})


if __name__ == "__main__":
    unittest.main()
