# Attention Routing Diagnostic

Exploratory, read-only analysis of information routing during local editing.
This study does not replace the completed frozen GT-mask comparison.

## Cases and Conditions

| Case | Target change | Selection rationale |
| --- | --- | --- |
| synth_0032 | cat with dragon head | Core failure; requested footprint expansion |
| synth_0028 | cow with dragon head | Same edit, different source species |
| synth_0033 | dog with cat head | Common-species part binding |
| synth_0036 | bear with lion head | Partial success: prior RK2 GT edit/preservation = 1/2 |
| synth_0023 | man with blond hair | Positive reference: prior RK2 GT edit/preservation = 2/1 |

Selection uses the existing single-reviewer diagnostic and is exploratory, not
a representative sample or a new success-rate estimate. A positive reference
under N=7 does not imply success in the uncontrolled condition.

Each case has uncontrolled N=0 and source-referenced residual RK2 N=7 conditions.
Both use source-prompt inversion, target-prompt generation, FLUX.1-dev, seed 0,
15 midpoint-RK2 updates, target guidance 2 and source guidance 1. Source images
retain the existing 1024-pixel setup. KV injection, IT control and ControlNet are
disabled during generation. The original sampler and its diagnostic forwards
are preserved; this is not an optimized sampler rewrite.

The precomputed GT grids from `gt_mask_diagnostic_v2/gt_masks` define observation
queries in both conditions. Only N=7 uses that grid for generation control,
at steps 0 through 6. The observer does not change Q, K, V, logits or latents.

## Recorded Signals

Record all 15 actual forward midpoints, including after control ends. Exclude
inversion, RK2 starting evaluations and legacy TDM diagnostic/scout forwards.
Select double-stream layers 0, 9, 18 and single-stream layers 0, 18, 37.

For every selected layer retain per-head statistics averaged over GT queries:

- Attention to each text position, including special and padded positions.
- Joint attention mass to all text, inside-GT image keys and outside-GT image keys.
- Actual model timestep, layer, step, query count and probability-sum error.

Weights are reconstructed in FP32 from the exact normalized and RoPE-transformed
Q/K presented to ordinary attention. This is a diagnostic reconstruction, not
access to the fused SDPA kernel's internal probabilities. All text and image keys
share a denominator; do not normalize IT and II independently. Padding is retained
because the original joint attention does not remove those keys.

Save 90 small records per condition, not 90 full attention matrices. With 24 heads
and 512 text positions the primary float32 statistics occupy about 4.4 MB before
compression. Query chunks of 16 bound the additional logits allocation. There is
still compute/synchronization overhead. No full A, AV or spatial maps are saved.

The fixed source GT may no longer coincide with the generated head after spatial
drift. Outside-GT is not a body segmentation. Attention is descriptive, not causal
attribution; text-position values can contain contextual image information.

## Local Checks and Server Launch

Run commands from the repository root using an environment with the existing FYS
dependencies. The runner defaults to a dry run and refuses to overwrite runs.
The observer is installed only by the new worker and is restored on exit; existing
entry points and the FYS submodule have no source-code changes.

```bash
python -m unittest tests.test_attention_routing tests.test_attention_routing_worker tests.test_run_attention_routing tests.test_analyze_attention_routing
python core/scripts/run_attention_routing_diagnostic.py --prepare
```

First run the core case with observation off and on, for both conditions:

```bash
python core/scripts/run_attention_routing_diagnostic.py --case-uid synth_0032 --recording off --execute
python core/scripts/run_attention_routing_diagnostic.py --case-uid synth_0032 --recording on --execute
```

Check each condition before extending the batch:

```bash
python core/scripts/analyze_attention_routing.py core/results/attention_routing_diagnostic/recording_on/uncontrolled/synth_0032/seed_000 --verify-against core/results/attention_routing_diagnostic/recording_off/uncontrolled/synth_0032/seed_000
python core/scripts/analyze_attention_routing.py core/results/attention_routing_diagnostic/recording_on/rk2_gt_n07/synth_0032/seed_000 --verify-against core/results/attention_routing_diagnostic/recording_off/rk2_gt_n07/synth_0032/seed_000
```

Initial latents must match exactly; final latents must pass atol=rtol=1e-6.
Both equality and maximum difference are reported. A failure stops this validation
stage; do not interpret attention or expand the batch until investigated.
Small-model CPU tests are not a substitute for this full-model GPU check.

After both checks pass, retain the recorded pilot and run the other four cases:

```bash
python core/scripts/run_attention_routing_diagnostic.py --case-uid synth_0028 --case-uid synth_0033 --case-uid synth_0036 --case-uid synth_0023 --execute
```

This gives ten scientific runs plus two observer-off verification runs. No new
training, N sweep, automatic-mask comparison or attention intervention is included.
The source images, model weights and dependencies must already be on the server.

## Outputs and Analysis

Results are isolated under
`core/results/attention_routing_diagnostic/recording_{on,off}/{condition}/{case}/seed_000`.
Each run retains the ordinary image, log, configuration and control trace. New
files include `routing_runtime.json` (commit, dirty state, code/mask hashes and
runtime versions), `generation_status.json`, and `routing/` containing initial
and final latents, fingerprints, schedule and timing. Recorded runs additionally
contain `metadata.json` and `attention_statistics.npz`.

Source-model safety filtering is unchanged. A missing image is reported, not
silently retried. A complete routing dump does not imply an image passed that check.

After downloading, generate paired figures on the Mac without torch or a GPU:

```bash
python core/scripts/analyze_attention_routing.py core/results/attention_routing_diagnostic/recording_on/uncontrolled/synth_0032/seed_000 --compare-run core/results/attention_routing_diagnostic/recording_on/rk2_gt_n07/synth_0032/seed_000 --output core/results/attention_routing_diagnostic/analysis/synth_0032
```

The three figures show joint text weights, valid-text-conditional weights and
region-mass curves. Conditional weights are a ratio of query/head means, exclude
padding but retain valid special tokens, and are not total joint attention mass.
Paired heatmaps share a color scale. The compressed arrays retain heads separately
for later inspection; displayed figures average heads. No scientific conclusion
is generated before actual observations exist.
