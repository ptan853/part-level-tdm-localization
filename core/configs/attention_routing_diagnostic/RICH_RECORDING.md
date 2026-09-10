# Rich attention recording

## Purpose

Investigate failed part semantics without changing generation. The compact diagnostic remains the default. Rich recording is opt-in and writes to a separate results root. This is an exploratory diagnostic, not a replacement for prior frozen comparisons.

Cases: synth_0006 (girl to robot head, failure), synth_0003 (alien to robot head, successful reference), synth_0033 (dog to cat head, failure), synth_0032 (cat to dragon head, constrained failure), synth_0036 (bear to lion head, partial-success reference). Selection is based on previous results and is not a representative test set.

Conditions remain uncontrolled N=0 and GT residual RK2 N=7. Both use source inversion, target prompt, seed 0, 15 steps, and no KV injection. No additional source reconstruction or random-noise condition is launched by this runner.

## Recording contract

- All double and single blocks, both actual start and midpoint evaluations, every step. With FLUX-dev this is 57 x 2 x 15 = 1,710 attention records per generation.
- All image queries and all heads are retained, without spatial/head averaging.
- Text columns contain every valid tokenizer position, including EOS and any valid whitespace token. Original token positions and strings are retained. Padding is stored as aggregate mass, not separate columns.
- Q/K are the actual normalized, RoPE-transformed tensors. FP32 softmax includes all joint text/image keys, including padding. Saved weights/statistics are FP32.
- For each query/head: text/inside-GT-image/outside-GT-image mass, padding mass, joint entropy in nats, maximum key weight, grouped AV norms, and total AV norm.
- AV norms are pre-output-projection per-head vector norms for all text, inside image, outside image, and subject/part/edit token groups. They do not sum and are not semantic contributions or causal effects.
- Input latent and output velocity at each actual start/midpoint evaluation, plus initial/final latent and schedule. Step endpoints are the next step's input; the last endpoint is final_latent.npy.
- Source trajectory states/midpoints are saved when present in the existing sampler (RK2 condition). They are not created by modifying uncontrolled inversion.
- Original GT grid is saved. Image positions follow row-major flattened token-grid order.

Ordinary fused attention and solver operations are unchanged. Legacy inversion/scout model calls are excluded by sampling-info identity. Recording is single-process and not thread-safe.

## Pilot before the batch

Run from the repository root using the existing model environment. Do not run the full batch until the pilot's output identity, probability audit, actual disk use, and latency have been checked. Existing run folders are never overwritten.

```bash
python core/scripts/run_attention_routing_diagnostic.py --mode rich
python core/scripts/run_attention_routing_diagnostic.py --mode rich --case-uid synth_0032 --condition rk2_gt_n07 --recording off --execute
python core/scripts/run_attention_routing_diagnostic.py --mode rich --case-uid synth_0032 --condition rk2_gt_n07 --recording on --execute
python core/scripts/analyze_attention_routing.py core/results/attention_routing_rich/recording_on/rk2_gt_n07/synth_0032/seed_000 --verify-against core/results/attention_routing_rich/recording_off/rk2_gt_n07/synth_0032/seed_000
python core/scripts/analyze_attention_routing_rich.py core/results/attention_routing_rich/recording_on/rk2_gt_n07/synth_0032/seed_000
```

The first command only prints selection. Use --prepare to inspect actual commands without launching generation. Repeat the pilot for uncontrolled before completing the other cases. After pilot runs exist, use explicit --case-uid/--condition arguments for the remaining combinations; a blanket rerun correctly refuses existing folders.

## Files and interpretation

Under each run's routing directory:

- metadata.json: schema v2, tokens, layers, shapes, full evaluation/file index, measured observation time.
- attention/step_XX_{start,midpoint}_{double,single}_L.npz: full-image valid-text attention and compact statistics. Primary axes are head, image query, selected text position/group.
- states/step_XX_{start,midpoint}.npz: actual input latent, target model velocity, actual model time.
- source_latents.npz and source_midpoints.npz: source references if available.
- initial_latent.npy, final_latent.npy, latent_record.json: reproducibility and timing evidence.
- rich_audit.json and update_diagnostics/: produced by the rich analysis command.

Update diagnostics reconstruct unconstrained proposals in FP32 and compare them with actual saved midpoint/endpoints. The difference includes floating-point solver arithmetic; it must not be described as an exact semantic signal removed by control. Source residuals are separately named. No source-reference residual is fabricated for runs lacking source states.

The complete IT data allow later selection of original GT, tracked head, or other queries. Head tracking is not automatically provided. Early noisy states may not have an identifiable head; intermediate latent decoding is not an x0 prediction. Complete II, TT/TI, full AV vectors, hidden states, and causal interventions are not recorded.

Storage scales with image tokens, valid text length, heads and block evaluations. Check the pilot's rich_audit.json bytes and latent_record.json forward_seconds before accepting batch costs. GPU on/off equality has to be measured separately from CPU unit tests.

## Server-side lightweight export

After both conditions for a case have passed audits, produce a portable export without copying the raw attention tensors. Repeat --case for each available paired case. --decode loads the existing VAE on the GPU and decodes saved endpoints; it does not regenerate the experiment.

```bash
python core/scripts/report_attention_routing_rich.py core/results/attention_routing_rich --case synth_0032 --export core/results/attention_routing_rich/export --decode
```

The export includes a report, all-layer/all-step figures, CSV tables, endpoint images, and offline HTML views selecting evaluation, step and layer. Query matrices average heads; head matrices average fixed-GT queries. Portable HTML values are rounded to seven decimals; CSV aggregates retain full precision. The raw server records retain the complete unaveraged head/position tensor.
