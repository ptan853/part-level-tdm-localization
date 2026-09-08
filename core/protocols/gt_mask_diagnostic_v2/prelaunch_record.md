# GT-Mask Diagnostic: Pre-Launch Record

Date: 2026-09-08

Status: protocol and preparation artifacts frozen; server verification pending. Generation has not started. This record does not indicate approval of the supplemental experiment.

## Code Reference

- Branch: `experiment/heldout-control-comparison`; no merge to main.
- Frozen code and protocol commit: `5ab29c1d0785a94a10bcc119326c8294092f89c7`.
- FollowYourShape submodule: `b096e8f7736b0f44d820933d5046fe252059a5eb`.
- This record is added in a subsequent documentation-only commit. Run the recorded code revision, not an unrecorded moving branch tip. Any additional execution-code change requires an updated reference before launch.

## Registered Comparisons

Primary: Endpoint N=7 and Residual RK2 N=7, each with automatic and GT masks. Reuse the original automatic-mask images without changing them.

Supplement: Residual RK2 N=15 with automatic and GT masks. N=15 controls steps 0..14, without image-KV injection. It does not replace the primary N=7 analysis.

60 cases; 240 new generation commands; 118 available cached images; 360 registered condition records; 720 planned assignments across two reviewers. The primary common-case set contains at most 59 cases because synth_0014 is absent from both cached conditions. Actual coverage will be reported under the protocol rules.

Estimated generation budget: approximately 8-12 A800 80GB GPU-hours, plus metric evaluation. This is a planning estimate, not a measured guarantee. No new mask-scout pass is planned.

## SHA-256 References

Paths are relative to the repository root.

| Artifact | SHA-256 |
| --- | --- |
| `core/reports/gt_mask_diagnostic_protocol.md` | `1ae7397528cb7a77e1f77b56bf472907715a7744c6cb4687bb197e058f5ba0d7` |
| `core/data/partedit_subset/synth_60_frozen_manifest.json` | `8e69fd42969286ce028c00c285a5a12600a5a4127e18a2c1f03d5ccbc3283147` |
| `core/protocols/gt_mask_diagnostic_v2/run_matrix.csv` | `16b932aacbc8493b526a11d82dc99e567666672a2c11d180f3dad1213aadfe15` |
| `core/protocols/gt_mask_diagnostic_v2/mask_and_cache_audit.json` | `76fe8f8e5831a53f086c62760d84b667ab2dc80d59ff663671c8c690bc3a5bc2` |
| `core/protocols/gt_mask_diagnostic_v2/reviewer_randomization.csv` | `3e7d8f284181bbc8ffafc61210634b856c0ae84ceb84888a87151b239bee14fc` |
| `core/protocols/gt_mask_diagnostic_v2/evaluation_rows.csv` | `e76439bf3c5dc3d7cdb8eb71bfb6025c1bdd571e87d65cce6ca8f45b3d0e0f84` |
| `core/protocols/gt_mask_diagnostic_v2/review_config_template.json` | `1fbfeb68f14b9e4677cbadd9d7ca8b5f550747ab204e280bd9c251cdb45b9246` |

Per-case source-image, native-GT, token-grid, cached-image and cached-configuration checksums are in mask_and_cache_audit.json. Resolved controller plans are fixed by the code commit.

## Required Before Generation

1. Share the protocol, this record and immutable code link, explicitly identifying N=15 as an additional proposed diagnostic.
2. Verify the server checkout and submodule revisions, source data, mask and cached-output hashes.
3. Capture runtime_environment.json and compare the model/dependency configuration with the completed experiment. Resolve material differences before generation.
4. Run the full test suite in the server environment. Seven test modules could not load locally because torch was unavailable; see local_validation.md.
5. Preserve per-run configuration, resolved plan, case record, logs and attempt status through the existing execution wrapper. Do not invoke bare model commands without these records. Do not overwrite existing outputs.

After these checks, append the server verification evidence and actual launch timestamp. Frozen scientific settings must not be changed while completing operational checks.
