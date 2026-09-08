# Local Preparation Validation

Date: 2026-09-08. Status: CPU preparation verified; not cleared for GPU launch.

- Preparation repeated successfully with byte-identical frozen artifacts.
- 240 generation rows: 60 each for endpoint_gt, rk2_gt, rk2_n15_auto and rk2_n15_gt.
- All 240 output directories are distinct and absent before generation.
- All control masks and resolved-plan paths exist. All commands resolve to the existing edit.py.
- Primary intervals are 0..6; supplemental intervals are 0..14. No image-KV injection is enabled.
- 360 evaluation records and 720 unique reviewer IDs are registered.
- Every cached N=7 configuration was checked against the proposed controller plan and source/prompt/seed/guidance settings.
- FollowYourShape remains at b096e8f7736b0f44d820933d5046fe252059a5eb, without model-code changes.

Focused tests: diagnostic 5 passed; control runner 5 passed; held-out runner 15 passed; review randomization 3 passed.

Full unittest discovery reported 133 entries, with 7 import errors because the local Python environment lacks torch. These affected test_attention_control, test_control_plan_sampling, test_controlled_attention_integration, test_flux_attention_prompt_validation, test_inversion_step_observer, test_latent_control and test_same_state_probe. The full suite must be rerun in the server environment before generation; no full-suite pass is claimed here.

## Before Launch

1. Record the committed code SHA, submodule SHA and protocol hashes in a separate pre-launch record.
2. Verify server dependencies, model files and frozen data/cache hashes against the original experiment; save runtime_environment.json.
3. Run the full tests, including the PyTorch-dependent numerical and sampling tests.
4. Use run_control_plan.execute_command with overwrite=False for the registered commands so run_config.json, case_record.json, resolved_control_plan.json and run.log are retained. The shell strings in run_matrix.csv describe model invocations only; executing them directly bypasses these wrapper-generated evidence files.
5. Complete the pre-launch communication before starting generation. Do not launch the superseded v1 matrix.

The launch orchestration, server verification, final review-page materialization and diagnostic analysis have not been executed by this preparation step.
