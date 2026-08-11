# Part-Level TDM Localization in Shape-Aware Image Editing

This project is a small diagnostic study of whether Follow-Your-Shape's trajectory divergence map (TDM) localizes part-level image edits precisely.

## Research Question

When a prompt asks for a local component edit inside an object, does the TDM used by Follow-Your-Shape identify the intended part, or does it expand to a broader object/background region?

The pilot uses PartEdit-Bench cases with ground-truth part masks and evaluates FYS TDM masks against those masks.

## Current Result

The pilot has been run on 20 PartEdit-Bench cases.

Summary:

- 20/20 cases have saved TDM artifacts.
- 19/20 cases have saved edited images.
- `synth_0014` was blocked by the FYS NSFW filter after TDM generation.
- Median binary IoU: `0.1006`.
- Median soft AP: `0.1602`.
- Median predicted/GT mask-area ratio: `6.67`.
- Small parts are hardest: median IoU `0.0500`, median predicted/GT area ratio `14.10`.

Main finding:

> Follow-Your-Shape's trajectory-guided TDM provides a useful edit-localization signal, but in this part-level setting it often over-localizes beyond the intended part mask, especially for small parts.

## Key Artifacts

Final analysis notebook:

- `core/notebooks/02_evaluate_fys_tdm_localization.ipynb`

Metrics and case table:

- `core/results/fys_case_table.csv`
- `core/results/fys_tdm_evaluation_metrics.csv`

Qualitative result sheets and charts:

- `core/results/figures/all_20_cases_review_sheet.jpg`
- `core/results/figures/tdm_area_vs_gt_area.png`
- `core/results/figures/over_localization_ratio_by_case.png`
- `core/results/figures/area_ratio_vs_iou.png`
- `core/results/figures/metrics_by_part_size.png`

TDM dynamics GIFs:

- `core/results/figures/tdm_dynamics_real_0006.gif`
- `core/results/figures/tdm_dynamics_real_0009.gif`
- `core/results/figures/tdm_dynamics_synth_0026.gif`

Raw FYS outputs:

- `core/results/follow_your_shape/<case_uid>/img_0.jpg`
- `core/results/follow_your_shape/<case_uid>/tdm/delta/delta_map_*.npy`
- `core/results/follow_your_shape/<case_uid>/tdm/aggregated_soft_tdm.npy`
- `core/results/follow_your_shape/<case_uid>/tdm/smoothed_soft_tdm.npy`
- `core/results/follow_your_shape/<case_uid>/tdm/binary_tdm_mask.npy`
- `core/results/follow_your_shape/<case_uid>/tdm/tdm_metadata.json`

Large generated artifacts are ignored by Git and are expected to be produced or copied locally.

## Project Layout

- `core/data/partedit_subset/`: pilot manifest and local exported PartEdit-Bench cases.
- `core/notebooks/01_inspect_partedit_bench.ipynb`: dataset inspection and subset selection.
- `core/notebooks/02_evaluate_fys_tdm_localization.ipynb`: final result analysis.
- `core/scripts/run_fys_pilot.py`: batch runner for FYS over the pilot manifest.
- `core/third_party/FollowYourShape/`: Follow-Your-Shape fork/submodule with TDM artifact logging.
- `core/results/`: local generated outputs, metrics, and figures.
- `notes/`: planning notes and related-work notes.

## Local Analysis Setup

Use `uv` for local notebook analysis:

```bash
uv sync
uv run python -m ipykernel install --user --name part-level-tdm-localization --display-name "part-level-tdm-localization"
uv run jupyter lab
```

Run the final analysis notebook from the project root:

```bash
uv run python -m jupyter nbconvert --execute --to notebook --inplace core/notebooks/02_evaluate_fys_tdm_localization.ipynb
```

The notebook resizes raw patch-grid TDMs to image resolution only for evaluation and visualization. The raw TDM `.npy` files are not modified.

## GPU Reproduction Guide

Recommended machine:

- One A800/A100/H800 80GB GPU.
- At least 100GB data disk; 150GB+ is safer.
- Python 3.10 with a working CUDA PyTorch environment.

On AutoDL, use the data disk:

```bash
cd /root/autodl-tmp
git clone --recurse-submodules https://github.com/ptan853/part-level-tdm-localization.git part-level-overediting
cd part-level-overediting
```

Set HuggingFace cache and mirror:

```bash
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=/root/autodl-tmp/hf_cache
export HUGGINGFACE_HUB_CACHE=/root/autodl-tmp/hf_cache/hub
export TRANSFORMERS_CACHE=/root/autodl-tmp/hf_cache/transformers
export TORCH_HOME=/root/autodl-tmp/torch_cache
export PIP_CACHE_DIR=/root/autodl-tmp/pip_cache
mkdir -p "$HF_HOME" "$HUGGINGFACE_HUB_CACHE" "$TRANSFORMERS_CACHE" "$TORCH_HOME" "$PIP_CACHE_DIR"
```

Login to HuggingFace after accepting the FLUX.1-dev license:

```bash
hf auth login
```

Install project and FYS dependencies. If the base image already has working PyTorch, do not reinstall Torch.

```bash
pip install -e . -i https://mirrors.aliyun.com/pypi/simple/

cd core/third_party/FollowYourShape
pip install -e ".[all]" -i https://mirrors.aliyun.com/pypi/simple/
cd ../../..
```

Pin the versions that were validated with AutoDL's PyTorch `2.1.2+cu118` image:

```bash
python -m pip install --force-reinstall \
  "numpy==1.26.4" \
  "opencv-python==4.10.0.84" \
  "transformers==4.44.2" \
  "tokenizers==0.19.1" \
  "diffusers==0.32.2" \
  "huggingface-hub==0.25.2" \
  "seaborn==0.13.2" \
  "scikit-image==0.24.0" \
  -i https://mirrors.aliyun.com/pypi/simple/
```

Check imports:

```bash
python -c "import torch; import numpy; import cv2; import transformers; import diffusers; print('ok'); print(torch.__version__, torch.cuda.is_available())"
cd core/third_party/FollowYourShape/src
python -c "import flux; from flux.sampling import denoise_with_TDM; print('fys import ok')"
cd ../../..
```

Preview the first command without running the model:

```bash
python core/scripts/run_fys_pilot.py --limit 1
```

Run one case:

```bash
python core/scripts/run_fys_pilot.py --limit 1 --execute
```

Run the full pilot:

```bash
python core/scripts/run_fys_pilot.py --execute
```

Monitor GPU and disk in a separate terminal:

```bash
watch -n 2 nvidia-smi
watch -n 10 'df -h /root/autodl-tmp && du -sh /root/autodl-tmp/hf_cache'
```

## Evaluation Metrics

The final notebook computes:

- `gt_area`: PartEdit GT part mask area ratio.
- `pred_tdm_area`: upsampled binary TDM mask area ratio.
- `pred_to_gt_area_ratio`: predicted TDM area divided by GT area.
- `binary_iou`: IoU between upsampled binary TDM and GT mask.
- `soft_ap`: average precision using smoothed soft TDM as a pixel-level score.
- `soft_inside_gt_mass`: fraction of soft TDM mass inside the GT mask.
- `image_change_inside_gt`: fraction of source-to-edit pixel difference inside the GT mask.

The most important diagnostic metrics are binary IoU, soft AP, and predicted/GT area ratio.

## Prompt Choice

The main run uses PartEdit's `p2p_prompt` as the target prompt. This prompt explicitly describes the part-level modification while preserving the source object context, for example:

```text
a dog with bear head standing in a field with grass and water
```

This is preferred over `prompt_changed` for the main experiment because many `prompt_changed` prompts imply full object replacement rather than part-level editing.

## Limitations

- Local semantic edit success is not yet manually annotated.
- LPIPS/SSIM/DINO outside-mask preservation metrics are not included.
- A FLUX attention localization baseline is not included.
- The pilot has 20 cases, so the result is diagnostic rather than a full benchmark.
