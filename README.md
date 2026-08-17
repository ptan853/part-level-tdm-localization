# Part-Level TDM Localization in Follow-Your-Shape

This repository is a small diagnostic study of part-level controllable image editing. The main question is:

> When an edit targets a local object part, does Follow-Your-Shape's trajectory divergence map (TDM) localize the intended part, or does it expand to a broader object/background region?

The experiment uses a fixed PartEdit-Bench subset with ground-truth part masks, runs Follow-Your-Shape (FYS), and compares the original FYS-TDM mask with attention-gated TDM variants.

Start with the compact research note: [`core/reports/final_note.md`](core/reports/final_note.md).

## Key Result

FYS-TDM is useful as an edit-localization signal, but it often over-localizes for part-level edits. Attention-gated TDM substantially improves mask localization, but the final edited image is still limited by the FYS control mechanism: target-prompt trajectory changes can accumulate before the late masked KV-injection stage.

Mask localization against GT part masks:

| Method | Command runs | Unique outputs | Binary IoU ↑ | Soft AP ↑ | Predicted / GT area ↓ |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original FYS-TDM | 36 | 12 | 0.174 | 0.247 | 8.04 |
| Attention-gated FYS, part+edit tokens | 36 | 12 | 0.327 | 0.591 | 2.81 |
| Attention-gated FYS, part-only tokens | 36 | 12 | 0.323 | 0.619 | 2.51 |

Edited-image preservation outside the GT part mask:

| Method | Outside L1 ↓ | Outside PSNR ↑ | Outside SSIM ↑ | Outside LPIPS ↓ |
| --- | ---: | ---: | ---: | ---: |
| Original FYS-TDM | 0.056 | 20.36 | 0.919 | 0.191 |
| Attention-gated FYS, part+edit tokens | 0.047 | 21.79 | 0.938 | 0.146 |
| Attention-gated FYS, part-only tokens | 0.046 | 22.10 | 0.941 | 0.142 |

The three requested seeds are deterministic for this inversion-based pipeline: the 36 command runs correspond to 12 unique case outputs for each method, so repeated seed rows are not treated as independent samples.

## Visual Examples

The main diagnostic example is `real_0010` (`head -> dragon`): the original TDM expands over the cow body and road, while attention-gated masks focus closer to the head. The edited image still changes more than the head, showing that better masks help but do not strictly constrain FYS's late KV-injection edit.

<div align="center">
  <a href="core/results/attention_gated_fys_eval/figures/cow_road_case_analysis.jpg">
    <img src="core/results/attention_gated_fys_eval/figures/cow_road_case_analysis.jpg" width="1000" alt="Representative cow road attention-gated FYS case analysis">
  </a>
  <br>
  <sub>Click to open full resolution.</sub>
</div>

Supporting diagnostic sheets are in:

- `core/results/attention_gated_fys_eval/figures/attention_gated_fys_case_sheet_seed0.jpg`
- `core/results/attention_gated_fys_eval/figures/mask_metric_boxplots.png`
- `core/results/controlled_revision/figures/tdm_diagnostic_sheet_part1.jpg`
- `core/results/controlled_revision/figures/tdm_diagnostic_sheet_part2.jpg`
- `core/results/controlled_revision/figures/tdm_diagnostic_sheet_part3.jpg`

## What Is Included

- `core/data/partedit_subset/pilot_12_manifest.json`: fixed 12-case subset.
- `core/artifacts/partedit_pilot_12_cases_strict.tar.gz`: portable copy of selected images, masks, references, and metadata.
- `core/configs/fys_controlled_revision.json`: fixed experiment configuration and pinned FYS submodule revision.
- `core/scripts/run_fys_pilot.py`: FYS batch runner.
- `core/scripts/run_flux_attention_baseline.py`: FLUX attention baseline runner.
- `core/notebooks/03_evaluate_controlled_revision.ipynb`: final evaluation notebook.
- `core/notebooks/05_evaluate_attention_gated_fys.ipynb`: attention-gated FYS evaluation notebook.
- `core/results/follow_your_shape/`: FYS edited images, logs, configs, and TDM artifacts.
- `core/results/flux_attention_baseline/`: attention maps, logs, and configs.
- `core/results/controlled_revision/`: final metric tables and qualitative figures.
- `core/results/attention_gated_fys_eval/`: attention-gated FYS metric tables and figures.
- `core/reports/final_note.md`: compact project note.

Main result tables:

- `core/results/controlled_revision/localization_comparison.csv`
- `core/results/controlled_revision/fys_run_metrics.csv`
- `core/results/controlled_revision/flux_attention_metrics.csv`
- `core/results/controlled_revision/compact_fys_summary.csv`
- `core/results/attention_gated_fys_eval/attention_gated_fys_summary.csv`
- `core/results/attention_gated_fys_eval/mask_localization_metrics.csv`
- `core/results/attention_gated_fys_eval/image_preservation_metrics.csv`

## Methods

### Follow-Your-Shape TDM

FYS is run with `flux-dev`, guidance `2.0`, `15` denoising steps, `front=2`, `inject=4`, no ControlNet, no oracle mask, and offload enabled. Each case is executed with seeds `0, 1, 2`; in this inversion-based path, the outputs are deterministic, so metrics are reported as 12 unique case outputs per method.

### FLUX Target-Token Attention

The baseline runs plain target-prompt FLUX denoising from the same inverted latent, without FYS KV injection or oracle masks. It records softmax attention mass from image-token queries to selected target part/edit T5 tokens in late single-stream blocks `28-37`, over step indices `2-8` of the 15-step schedule. The maps are averaged over tokens, heads, layers, and steps, reshaped to the `32 x 32` image-token grid, smoothed, and binarized with Otsu thresholding. This is a localization-only diagnostic baseline, not an editing method.

### Attention-Gated FYS

Attention-gated FYS keeps the same inversion, target denoising, and late KV-injection schedule as FYS, but replaces the final binary TDM mask with a TDM-attention hybrid mask. The hybrid is formed by normalizing the smoothed TDM and the target-token attention map, multiplying them as a soft gate, smoothing the product, and binarizing with Otsu thresholding. I evaluate both `part+edit` token attention and `part`-only token attention. The current repo excludes the attempted oracle-mask run because the original code path gives priority to the internally computed `edit_map`; it is not a clean GT-mask oracle.

## Reproduce

Recommended GPU: one A800/A100/H800 80GB GPU, Python 3.10, and 100GB+ available disk space for FLUX downloads.

Clone and unpack the selected cases:

```bash
export WORKDIR=/path/to/data-disk
mkdir -p "$WORKDIR"
cd "$WORKDIR"
git clone --recurse-submodules https://github.com/ptan853/part-level-tdm-localization.git part-level-overediting
cd part-level-overediting
tar -xzf core/artifacts/partedit_pilot_12_cases_strict.tar.gz
```

If `core/third_party/FollowYourShape/` is empty after cloning, initialize the submodule from the repository root:

```bash
git submodule update --init --recursive
```

Check that the submodule is present:

```bash
test -f core/third_party/FollowYourShape/src/edit.py && echo "FollowYourShape ready"
git submodule status --recursive
```

Do not use GitHub's "Download ZIP" for full reproduction, because ZIP downloads do not include submodule contents.

Set caches:

```bash
export HF_HOME="$WORKDIR/hf_cache"
export HUGGINGFACE_HUB_CACHE="$HF_HOME/hub"
export TRANSFORMERS_CACHE="$HF_HOME/transformers"
export TORCH_HOME="$WORKDIR/torch_cache"
export PIP_CACHE_DIR="$WORKDIR/pip_cache"
export OMP_NUM_THREADS=8
mkdir -p "$HF_HOME" "$HUGGINGFACE_HUB_CACHE" "$TRANSFORMERS_CACHE" "$TORCH_HOME" "$PIP_CACHE_DIR"
```

If HuggingFace or PyPI access is slow, optionally set mirrors:

```bash
export HF_ENDPOINT=https://hf-mirror.com
export PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
```

Install dependencies. If your image already has a working CUDA PyTorch, avoid reinstalling Torch.

```bash
pip install -e .

cd core/third_party/FollowYourShape
pip install -e ".[all]"
cd ../../..

python -m pip install --force-reinstall \
  "numpy==1.26.4" \
  "opencv-python==4.10.0.84" \
  "transformers==4.44.2" \
  "tokenizers==0.19.1" \
  "diffusers==0.32.2" \
  "huggingface-hub==0.25.2" \
  "seaborn==0.13.2" \
  "scikit-image==0.24.0"
```

Accept the FLUX.1-dev license and log in:

```bash
hf auth login
```

Run the full experiment:

```bash
python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --execute

python core/scripts/run_flux_attention_baseline.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --execute

python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --tdm-mask-mode attention_gated \
  --attention-token-mode part_edit \
  --execute

python core/scripts/run_fys_pilot.py \
  --manifest core/data/partedit_subset/pilot_12_manifest.json \
  --seeds 0,1,2 \
  --tdm-mask-mode attention_gated \
  --attention-token-mode part \
  --output-root core/results/fys_mask_ablation/attention_gated_tdm_part \
  --run-matrix core/results/run_matrices/attention_gated_part_pilot_12_manifest_multi_seed.csv \
  --execute
```

Run evaluation:

```bash
python -m jupyter nbconvert --execute --to notebook --inplace core/notebooks/03_evaluate_controlled_revision.ipynb
python -m jupyter nbconvert --execute --to notebook --inplace core/notebooks/05_evaluate_attention_gated_fys.ipynb
```

## Metrics

- `binary_iou`: IoU between predicted binary localization mask and GT part mask.
- `soft_ap`: average precision using the soft localization map as a pixel-level score.
- `pred_to_gt_area_ratio`: predicted binary area divided by GT part area.
- `soft_inside_gt_mass`: fraction of soft localization mass inside the GT part.
- `outside_mask_psnr`, `outside_mask_global_ssim`, `outside_mask_lpips`: preservation outside the GT part mask for FYS edited images.

The FLUX attention baseline is localization-only, so image-preservation metrics are reported only for FYS edited images.
