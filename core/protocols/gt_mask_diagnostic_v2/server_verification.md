# Server Verification

Date: 2026-09-08. Formal generation has not started.

## Verified State

- Server checkout: `/autodl-fs/data/heldout-control-run`.
- Execution commit: `5ab29c1d0785a94a10bcc119326c8294092f89c7`.
- FollowYourShape: `b096e8f7736b0f44d820933d5046fe252059a5eb`.
- Hardware: NVIDIA A800 80GB PCIe, driver 595.71.05.
- Python 3.10.8 and PyTorch 2.1.2+cu118. Python version, GPU/driver description and the complete pip-freeze package set match the previous runtime record.
- 480 source, native-GT, token-mask, cached-configuration and cached-output checks passed. Expected absent cached outputs remain absent.
- Full unittest discovery: 202 tests passed, exit code 0.
- FLUX, VAE, T5, CLIP and safety-classifier weight files exist and have nonzero sizes. This is a file-availability check, not a full model-load or weight-checksum validation.

GitHub access was unreliable. The already-published commits were transferred as a Git bundle and fetched into the existing repository. Bundle SHA-256 matched locally and remotely: `5f8110de5152c6c3ae0f7dbaa64a56bbd4697c47148620dc9c3dff46f77df7ab`.

## Test Data and Preserved Records

Initial full-suite failures were caused by missing artifacts for the historical 12-case Oracle review page. The existing 12 output images and 12 injection-mask images were copied from local results without regeneration or replacement of differing files. The full suite then passed. Initial and final logs are retained.

The previous experiment's locally generated command matrix, preflight summary and runtime record remain in place. They were not reset. No inference code or frozen scientific setting was changed during server preparation.

## Evidence and Remaining Launch Steps

Environment, input audit and test logs were downloaded to `core/results/gt_mask_diagnostic_v2/prelaunch/`. The final test log is `unittest_complete_fixtures.log`; the input audit is `input_cache_verification.json`.

Before generation, complete the pre-launch communication, explicitly distinguishing the proposed N=15 supplement from the requested primary comparison. Configure the launch process to use the verified local model cache and existing execution wrapper, retaining per-run configuration and logs with overwrite disabled. The noninteractive SSH environment does not currently set FLUX_DEV, AE or Hugging Face cache variables; these must be supplied explicitly at launch.

This verification does not constitute a generation launch or a diagnostic result. The frozen execution commit remains unchanged by this documentation-only record.
