# Six-case GT prefix diagnostic: implementation audit and execution contract

This is an exploratory diagnostic selected from observed failures, frozen before new generation. It cannot replace the 60-case frozen comparison, estimate general success rates, or establish that FLUX cannot generate these compositions. No unfinished GT-diagnostic reviewer scores were consulted.

## Frozen scope and provenance

Base repository: `3f8581894eabacf7a30ee08168923bef1a89d7ba`.
FYS submodule: `b096e8f7736b0f44d820933d5046fe252059a5eb` (unchanged).
Branch: `experiment/gt-prefix-diagnostic`.
Local worktree: sibling `part-level-prefix-diagnostic`; original branch and its two untracked evaluation files remain untouched.

`manifest.json` preserves the original six records and prompts. `selection_scores.csv` contains both old reviewers and the method means. `protocol.json` hashes the original frozen manifest and complete old reviewer CSV. `input_audit.json` records source/GT hashes, pixel/token areas, and old Endpoint/RK2 run-config hashes. `run_matrix.csv` has exactly 84 unique case-duration conditions. Fourteen plans cover N=0..13 inclusive, each with 15 steps, seed 0, target guidance 2, inversion guidance 1, flux-dev, offload enabled, GT/oracle mask, no KV injection, no attention gate and no endpoint projection. N=13 leaves two free steps; N=15 is deliberately absent.

## Mathematical audit

Use the descending denoising grid t_i, h=t_(i+1)-t_i<0, cached source endpoints s_i and s_(i+1), cached reverse-solver midpoint q_i, current target x_i, and fixed binary mask M (1=editable). Let r_i=x_i-s_i and v_T denote the target-conditioned field, including the frozen guidance.

The existing `latent_control.py` implements:

    x_mid = q_i + r_i + M * [(h/2) v_T(x_i,t_i) - (q_i-s_i)]
          = x_i + M*(h/2)*v_T(x_i,t_i) + (1-M)*(q_i-s_i)
    x_next = s_(i+1) + r_i + M * [h*v_T(x_mid,t_i+h/2) - (s_(i+1)-s_i)]
           = x_i + M*h*v_T(x_mid,t_i+h/2) + (1-M)*(s_(i+1)-s_i)

The second velocity is evaluated on the controlled midpoint. The endpoint retains the incoming r_i; it does not reuse midpoint residual or reset residual to zero. Mask-outside residual is carried forward, not removed. Thus exact source following outside a fixed binary mask requires zero initial residual and a prefix beginning at step 0. After release, source following is no longer enforced. Fractional masks blend increments and do not enjoy the same binary preservation statement. Floating-point cancellation/quantization also limits exact equality in bf16; inspect saved residual MAE/max traces rather than claiming bitwise preservation.

Boundary checks: M=1 algebraically recovers ordinary target explicit-midpoint RK2. M=0 transports the existing residual along the cached source; only r_0=0 gives source tracking. N=0 has no control stages but `edit.py` still inverts the source and sets `inp_target['img']=z`. It is target denoising from source inversion, not text-to-image from independent noise. The historical `first_order` expression simplifies to x+h*v_mid; this is explicit midpoint, despite some old tests using the name Heun.

### Cache time alignment and numerical limitation

`sampling.denoise` reverses the timestep sequence for inversion. With K=15 updates, inversion update j traverses original grid indices K-j to K-j-1. It stores its internal midpoint at `source_midpoints[K-j-1]` and completed endpoint at `source_latents[K-j-1]`, with the initial clean latent at `source_latents[K]`. Forward step i consequently reads endpoints i/i+1 and midpoint i at the matching endpoint/midpoint times. The actual negative h is passed to both residual helpers.

This indexing does **not** make a reverse RK2 internal midpoint equal to a forward RK2 internal midpoint or an exact ODE solution. For dx/dt=x, inversion from x(0)=1 with step +0.5 gives reverse midpoint 1.25 and endpoint 1.625. Forward explicit midpoint starting at 1.625 with step -0.5 gives 1.21875, not 1.25. Reverse explicit midpoint is not a time-reversible integrator. The cached source path is a numerical reference; a general second-order accuracy claim for this coupled masked construction would require additional consistency/smoothness/error analysis, not merely invoking RK2. Neither this audit nor the image experiment supplies that proof.

### Call path, masks and released control

`edit.py` embeds source and target prompts separately, performs inversion with source embeddings, then passes target embeddings (txt, txt_ids, vec) into `denoise_with_TDM`. Both updating model calls consume those target embeddings. Stage `prompt='target'` is consistent with this path; it is the call arguments that establish target conditioning.

GT conversion is `>0`, nearest resize to VAE H/8,W/8, followed by 2x2 max pooling and row-major flattening to H/16,W/16. All six source/GT pairs are 1024x1024 and produce nonempty, non-full 64x64 masks. `gt_to_token_grid` independently reproduces nearest floor indexing and pooling for audit; runtime uses the original oracle conversion, not a separately selected auto mask.

`configure_step_control` clears old attention fields and KV operation every step. Empty layer tuples and image_kv=none make injection false during the prefix; missing stages return false after it. Projection is also none. Inversion's legacy inject flags can save source K/V tensors, but the inverse branch returns its unmodified K/V, and these caches are not injected into the target run. ControlNet is disabled.

The existing sampler still performs two extra uncontrolled target TDM diagnostic forwards per step in addition to two updating forwards (60 target forwards plus 30 inversion forwards per condition). These are not extra attention-control operations. TDM maps/edit_map are computed/saved but no target injection consumes them in this plan. This costs time/memory. A zero-range TDM normalization can produce NaN diagnostics for degenerate constant toy fields; it is not evidence of a residual-formula bug. The six real runs still require server verification of finite traces and successful completion. No sampler formulas or legacy evidence were changed.

## Reproduction and GPU gate

From the new worktree, using the original local Python only for preparation:

```sh
../part-level-overediting/.venv/bin/python core/scripts/run_gt_prefix_diagnostic.py prepare --data-root ../part-level-overediting
```

Preparation reads the old repository, freezes protocol artifacts idempotently and creates no generated images. It refuses changed hashes/selection evidence. All new outputs resolve beneath the new code checkout. Data are not bulk-copied and no old result directory is reused. The driver reuses `build_prefix_plan`, `build_sweep_commands`, `gt_to_token_grid`, the frozen metric implementation, randomization and HTML review renderer. `prepare_gt_mask_diagnostic.prepare()` itself is not suitable: it hardcodes the full 60-case 2x2/N15 experiment. The old sweep evaluator CLI likewise assumes old pilot baselines, so the driver calls its residual-row API directly.

The server is powered off. Do not launch it or buy resources automatically. After the user starts it, use SSH port 47410 at root@connect.nma1.seetacloud.com. Keep `/autodl-fs/data/heldout-control-run` as the read-only data root. Transfer the exact reviewed experiment commit and submodule into a separate checkout, for example `/autodl-fs/data/gt-prefix-diagnostic`; do not switch the old server checkout. Confirm its commit with `git rev-parse HEAD` before running:

```sh
/root/miniconda3/bin/python core/scripts/run_gt_prefix_diagnostic.py prepare --data-root /autodl-fs/data/heldout-control-run
/root/miniconda3/bin/python core/scripts/run_gt_prefix_diagnostic.py run --data-root /autodl-fs/data/heldout-control-run
/root/miniconda3/bin/python core/scripts/run_gt_prefix_diagnostic.py evaluate --data-root /autodl-fs/data/heldout-control-run --lpips require
```

`run` requires a clean committed checkout, the audited FYS commit, base ancestry, CUDA and four suites of torch tests before generation. It saves the exact experiment commit, FYS commit, Python/torch/CUDA/GPU metadata, protocol hash and roots in `execution_provenance.json`. Model weight identity/availability, environment dependencies, peak memory, actual bf16 behavior and first-condition trace must still be checked on the server. Existing outputs are refused, never silently overwritten. A failed partial run needs explicit recovery planning before retry; this entry point does not auto-delete or auto-resume output folders.

## Evaluation contract and local verification

Evaluation requires all 84 outputs, matching run parameters/resolved plans and traces: 15 steps, exactly N residual steps, correct i/i+1 indices, descending control times, and no extra control. It reuses the frozen heldout 512x512 (bicubic RGB, nearest GT) selected-pixel L1/MSE/PSNR/global-SSIM proxy and outside-masked AlexNet LPIPS, both for strict GT and GT dilated by a two-token-radius disk (16 pixels at 512x512). The global-SSIM proxy is not windowed SSIM. These metrics measure source preservation/change, not semantic editing success. LPIPS must be present for a complete same-contract report.

Two reviewers each receive 84 randomized, opaque-ID Source/Candidate items with the unchanged four 0..2 rubric fields. Candidate filenames are opaque too. Do not share randomization keys or duration comparison pages before scoring. The exploratory comparison page has each case's Source + GT mask + N0..N13, horizontal scrolling, and original image links; GT here means the part mask, not a ground-truth target image. Keep individual scores and report local success separately from preservation, overall adherence and quality. Treat cases as paired and selected; do not count 84 dependent conditions as independent cases or choose a best N without disclosing that it was selected on these data.

Local Python 3.12 has no torch. The initial 8 existing runner tests passed. The targeted combined check ran 52 tests: 50 passed, 2 torch integration tests explicitly skipped. New NumPy tests verify algebraic increment equivalence, negative steps, zero/one/mixed masks and the reverse-midpoint counterexample; these are mathematical checks, not execution of torch kernels. A synthetic 16x16 input fixture, resized through the frozen 512x512 evaluation contract, exercised all 84 strict/buffered metric rows (LPIPS off), 168 blinded review rows and 96 comparison cells. This validates the output pipeline, not real image generation, LPIPS, real-model prompt conditioning, or visual layout on actual results. The real torch tests check nonlinear midpoint coupling, prefix release, prompt inputs, N0 inversion initialization and all-one behavior; their results remain pending until server execution. Existing latent/control/inversion tensor suites are required there as well.

Independent code review found no critical generation-path issue and requested explicit source/GT provenance validation. That check and a wrong-GT rejection test were added. Residual numeric fields now reject missing/non-finite values. A second inspection aligned evaluation with heldout strict/buffered 512x512 metrics; the old pilot full-resolution metric CLI is not used.

## Server preflight follow-up (2026-09-09)

The user started and authorized deployment to the A800 80GB server. Runtime is Python 3.10, torch 2.1.2+cu118. The old server checkout remains unchanged. An isolated data overlay at `/autodl-fs/data/gt-prefix-inputs` symlinks existing data and old method result directories; only the missing frozen old reviewer CSV was uploaded into that overlay. Preparation passed all frozen hashes.

The first startup gate correctly rejected regenerated tracked Python 3.10 `.pyc` files in the upstream submodule. Only those seven generated files were restored in the new checkout. Set `PYTHONPYCACHEPREFIX=/tmp/gt-prefix-pycache` for all future server Python calls, including the driver, to avoid writing tracked bytecode. The second gate found an existing test fixture overwriting real transformers with an incomplete stub, causing torch Dynamo to fail. The test now preserves an installed transformers package; the previously failing four-test inversion suite then passed. Sampling source and frozen experiment plans remain unchanged.

Independent server checks passed: 20 latent-control tests, 17 control-plan sampling tests, 4 inversion-observer tests after the fixture correction, and 2 new prefix tests. The driver repeats all four suites before actual generation. Cached model snapshot/blob paths and sizes (not independently recomputed full weight hashes), environment, exact generation commit and launch logs are recorded with new results. The deployed generation commit includes this test-only correction and is recorded by the driver rather than assumed to remain the initial preparation commit.
