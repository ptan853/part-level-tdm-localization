from pathlib import Path


def test_notebook_declares_reverse_step_mapping():
    notebook = Path("core/notebooks/06_inspect_same_state_inversion_probe.ipynb").read_text()
    assert "reverse_step_indices" in notebook
    assert "def otsu_threshold" in notebook
    assert "from skimage.filters import threshold_otsu" not in notebook
    assert "Defensive recomputation" in notebook


def test_fys_interval_maps_to_reversed_inversion_steps():
    denoise_steps = list(range(2, 9))
    assert [14 - step for step in denoise_steps] == [12, 11, 10, 9, 8, 7, 6]
