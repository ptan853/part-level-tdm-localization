from __future__ import annotations

import sys

import pytest


ISOLATED_TEST_FILES = {
    "test_flux_attention_prompt_validation.py",
    "test_inversion_step_observer.py",
    "test_same_state_probe.py",
}
ISOLATED_MODULE_ROOTS = {
    "cv2",
    "diffusers",
    "fire",
    "flux",
    "fys_edit",
    "imwatermark",
    "matplotlib",
    "run_flux_attention_baseline",
    "run_fys_pilot",
    "scipy",
    "seaborn",
    "tqdm",
    "transformers",
}


@pytest.fixture(autouse=True)
def isolate_dynamic_import_tests(request):
    if request.path.name not in ISOLATED_TEST_FILES:
        yield
        return

    original_path = list(sys.path)
    original_modules = {
        name: module
        for name, module in sys.modules.items()
        if name.split(".", 1)[0] in ISOLATED_MODULE_ROOTS
    }
    yield
    sys.path[:] = original_path
    for name in list(sys.modules):
        if name.split(".", 1)[0] in ISOLATED_MODULE_ROOTS:
            sys.modules.pop(name, None)
    sys.modules.update(original_modules)
