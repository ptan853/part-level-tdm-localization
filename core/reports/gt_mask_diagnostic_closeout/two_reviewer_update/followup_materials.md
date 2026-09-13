# Evaluation closeout and proposed next study

Status: discussion draft, not a frozen protocol or permission to generate. Prepared 2026-09-13 against the advisor email received 2026-09-10. No submission target or deadline is committed here.

## 1. Requirement checklist

| Request | Current status | Remaining action |
| --- | --- | --- |
| Keep N=7 primary, N=15 supplementary, 59 paired cases unchanged | Preserved in the two-reviewer analysis | Maintain in all summaries |
| Preserve original scores and the single-reviewer deviation | Raw exports, correction records and old report retained | Include provenance in the shareable release |
| Second independent review with hidden identities and fixed rubric | All 354 records are complete and match the frozen package. The second reviewer scored independently without access to method identities, comparative montages, analysis reports, or the first reviewer's scores | Retain review-procedure documentation and the first reviewer's exposure limitation |
| Reviewer-level results and disagreements | Separate summaries, bootstrap tables, agreement and disagreement rows produced | Release with aggregate results, not only pooled averages |
| Preserve montage-exposure limitation | Stated in the update | Do not describe the second review as erasing earlier exposure |
| Fresh-case, multi-seed plan and compute estimate before generation | Proposed below; no fresh manifest exists yet | Select and audit inputs, resolve seed behavior, finalize rubric, send plan before generating |
| Paper outline, supported claim, remaining milestones | Working outline and milestones below | User to confirm intended submission route; this is not a submission-ready manuscript |

Latest numerical report: [two-reviewer results](README.md).

## 2. Current supported claim

On the available 59-case paired diagnostic, replacing automatic masks with source-part GT masks improves mean non-target preservation for both Endpoint and source-referenced RK2. Evidence for improving local-edit semantics is inconclusive, and the comparisons do not establish RK2 superiority over Endpoint. Longer RK2 control improves preservation but does not establish better joint editing utility. These findings are conditional on the two supplied reviewers and the documented evaluation limitations.

At N=7, preservation gains are +0.364 [0.220, 0.517] for Endpoint and +0.305 [0.186, 0.432] for RK2 on the 0-2 scale. Local-edit gains are +0.059 [-0.068, 0.186] and +0.008 [-0.127, 0.153], respectively. Endpoint joint success increases by 11.86 percentage points [2.54, 22.03]; RK2's +7.63 points [-1.69, 16.95] remains uncertain. All intervals are unadjusted paired percentile 95% CIs.

Do not claim that attention is the identified cause, that the backbone generally cannot produce hybrids, that source GT is an ideal target footprint, or that RK2 is the best controller. Selected attention and prompt-generation examples are exploratory illustrations only.

## 3. Proposed small fresh-case study

### Question and inputs

Distinguish three observable outcomes: whether the requested target feature appears at all, whether it is attached to the intended part of the intended single subject, and whether source content outside that part changes.

Propose six genuinely new source/target pairs: three head-species replacements and three simpler head appearance/attribute edits. Include no image from the existing 60-case set, six-case prefix diagnostic, attention pilots or other inspected generation runs. Select using source images and prompts only. Record original dataset IDs, provenance, image hashes and a source-part mask; audit exact duplicates and visually similar sources. These are a small diagnostic set, not a representative benchmark.

Source images and masks have not been selected. There is therefore no claim of preregistration yet. Freeze the full manifest and mask construction before any target output is generated. Source-part masks must not be adjusted after seeing results.

### Conditions

| Condition | Initialization | Control | Purpose |
| --- | --- | --- | --- |
| Random-noise N0 | Gaussian noise | None | Can the exact target prompt produce the feature and requested composition without source-image initialization? |
| Inversion N0 | Source inversion endpoint | None | Does source-conditioned initialization change the observed failure pattern? |
| GT RK2 N7 | Same inversion endpoint as paired inversion N0 | Frozen source-referenced residual control for steps 0-6 | Does spatial constraint change composition and outside preservation? |

Use the same exact target prompt across conditions. Proposed fixed seeds are 0, 1, 2; retain 15 steps, guidance 2.0 and 1024-square resolution for comparability. No new attention manipulation, KV injection, prompt search or per-case schedule tuning. This is not a new Endpoint-versus-RK2 superiority test; that question is addressed by the existing 59-case analysis.

Important preflight: changing a seed may not change a deterministic inversion trajectory. Verify the actual stochastic inputs and hash initialized latents before launching. If inversion outputs are deterministic and seed-invariant, run one unique inversion result and one unique controlled result per case, with three random-noise outputs: 30 unique outputs total. Do not count identical reruns as independent seed replications. If inversion has genuine seed-dependent inputs, pair identical cached inputs between N0 and N7 and generate 54 outputs. This branch must be resolved and written into the final protocol before generation; do not inject new noise merely to manufacture seed variation.

### Outcomes and analysis

Proposed new diagnostic labels, separate from the unchanged old rubric:

- Target-feature presence: absent, ambiguous/partial, clear. A separate cat can count as feature presence but not correct binding.
- Correct part-to-body binding: absent/wrong, ambiguous/partial, clear attachment to the intended single subject. A cat sitting on a dog's head is a binding failure.
- Non-target preservation: use the existing 0-2 rubric and frozen strict/buffered outside metrics for the two source-initialized conditions only. Random-noise images are not source-preserving edits and must not receive comparable outside-preservation scores.

Record the original four human criteria as well for source-initialized outputs, without altering the completed evaluation. Finalize diagnostic label examples before review. Hide condition identities where feasible, randomize output order, score independently, and document unavoidable visual clues to initialization. Keep every output and every seed; no best-of-seed selection. Present case-by-seed outcomes and separate reviewer assessments, not a claim based on treating all outputs as independent cases. With six cases, subgroup and inferential claims will remain limited.

Random noise succeeding while inversion fails would support an initialization/path sensitivity hypothesis. Failure in both settings would indicate a difficulty under the tested prompt/settings, not universal model incapability. N0 succeeding while controlled N7 fails would support a control-related tradeoff, without identifying its specific attention-level mechanism.

### Compute and launch gate

The recent three-seed A800 run took about 46-56 seconds per random-noise image after shared loading (15-step sampling itself about 17 seconds). This is a timing reference, not a benchmark of inversion or RK2-control cost. At that reference, 30-54 forward outputs alone correspond to roughly 23-50 minutes; inversion, cache I/O, model loading and evaluation add time. Budget a provisional 1-3 A800 GPU-hours without full attention recording. Confirm a configuration-based estimate after checking the exact runner and unique-input count. Do not promise this as a measured end-to-end runtime or estimate a monetary cost without the current server rate.

Before launch: select all six inputs, resolve deterministic seed behavior, freeze masks and prompt strings, finish scorer guidance, record code/model/input hashes and environment, send the plan and compute estimate to the advisor, and resolve any requested changes. Do not generate while these items remain open. The previous selected three-seed dog/cat exploration must remain excluded.

## 4. Working paper outline

Working framing: **Spatial Preservation and Semantic Binding in Training-Free Local Image Editing**. This is an evidence-organizing outline, not a novelty or publication-readiness claim.

1. Introduction: separate non-target preservation from successful target semantics; state the narrow empirical question and avoid controller-superiority claims.
2. Background and related work: distinguish latent/velocity constraints, feature or attention interventions, and trained part localization. Verify all literature claims before manuscript drafting; this outline supplies no unverified citations.
3. Controllers and evaluation design: define Endpoint and source-referenced residual RK2 precisely, initialization, masks, schedules, the fixed paired set, metrics and review deviations.
4. Main evidence: frozen automatic-mask comparison, mask-quality diagnostic, two-reviewer estimates, disagreement and uncertainty. Keep the distinct studies and their sample sets separate.
5. Duration and category analysis: N15 supplementary; head versus other parts descriptive. Do not turn selected categories into population claims.
6. Exploratory diagnostics: inversion versus random noise, feature presence versus correct binding, and attention observations. Clearly separate completed selected-case exploration from any future fresh-case preregistered study.
7. Limitations: source GT versus target footprint, fixed prompts/settings, limited reviewers and ceiling effects, montage exposure, missing-case handling, small diagnostic samples, lack of attention-causal identification.
8. Conclusion: preservation can improve without reliable semantic editing; current evidence does not establish RK2 superiority. State what remains unresolved.

## 5. Remaining milestones

| Milestone | Completion criterion |
| --- | --- |
| Evaluation closeout | Independence/exposure attestation and score validation complete; retain historical report and release reproducible two-reviewer materials |
| Advisor update | Share updated report, bounded claim, working outline and this explicitly non-frozen plan; answer submission-target question without inventing a commitment |
| Fresh-study preparation | Complete manifest, masks, unique stochastic-input design, rubric and compute estimate; send the final preregistered plan before generation |
| Fresh-study execution | Generate every frozen condition, retain all outputs/failures and run records; no selective reruns or prompt changes |
| Analysis and writing | Independent scoring, separate presence/binding/preservation results, revise claim strength to match evidence, write methods/results/limitations before broader framing |
| Submission decision | Advisor/user review of evidence and manuscript; venue and dates remain undecided |

## 6. Additional exploration disclosure

After the September 10 email, three random-noise outputs for the already-inspected synth_0033 prompt were generated at user request without first sending a fresh-study plan. They show separate cat/dog compositions, not clear replacement cat heads. They are post-hoc exploration, do not satisfy the requested fresh-case preregistration, and do not alter any frozen score or output. No further generation is proposed before completing the launch gate above.

Links within these materials are repository-relative. The accompanying email identifies the immutable Git revision for this report and plan. This release documents completed evaluation and a proposed study; it does not freeze or authorize a new generation run.
