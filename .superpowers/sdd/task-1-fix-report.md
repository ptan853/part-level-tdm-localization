# Task 1 Fix Report

- Finding fixed: projection masks now reject `NaN`, `+inf`, and `-inf` before conversion to the target latent dtype.
- Production commit: `0ee3b39` on submodule branch `feature/latent-state-projection`.
- Test-first evidence: the new non-finite-value test failed before the production change because `NaN` was accepted.
- Verification: `/opt/homebrew/Caskroom/miniconda/base/envs/irp/bin/python -m unittest tests.test_latent_control -v`
- Result: 10 tests passed.
