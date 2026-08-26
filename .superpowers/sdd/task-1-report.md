# Task 1 Report: Default-Disabled Inversion Observer Hook

## Outcome

Implemented an optional `step_observer` hook on `flux.sampling.denoise(...)` that is only invoked during inversion steps, after the source prediction is computed and before the solver updates `img`.

## What Changed

- Added `InversionStepObserver = Callable[..., None]` in `core/third_party/FollowYourShape/src/flux/sampling.py`.
- Extended `denoise(...)` with a default-disabled `step_observer` keyword argument.
- Invoked the observer only when `inverse=True`, passing:
  - `step_index`
  - `img`
  - `img_ids`
  - `timestep`
  - `source_pred`
  - `guidance_vec`
- Added `tests/test_inversion_step_observer.py` to verify:
  - the observer sees the pre-update `img`
  - the observer receives the expected timestep and source prediction
  - the observer fires once per inversion main step
  - omitting the observer leaves the output unchanged

## TDD Evidence

### RED

Initial focused run failed because `denoise()` did not accept `step_observer`:

`TypeError: denoise() got an unexpected keyword argument 'step_observer'`

### GREEN

After the code change, the focused observer test passed, then the existing mask test passed alongside it, and finally the full suite passed.

## Verification

- Focused red-green test:
  - `uv run --with pytest python -m pytest -q /Users/pt623/Documents/career-vault-resume/applications/hkust-harry-yang/part-level-overediting/tests/test_inversion_step_observer.py`
- Focused pair:
  - `uv run --with pytest python -m pytest -q /Users/pt623/Documents/career-vault-resume/applications/hkust-harry-yang/part-level-overediting/tests/test_inversion_step_observer.py /Users/pt623/Documents/career-vault-resume/applications/hkust-harry-yang/part-level-overediting/tests/test_attention_gated_tdm_mask.py`
- Full suite:
  - `uv run --with pytest python -m pytest -q /Users/pt623/Documents/career-vault-resume/applications/hkust-harry-yang/part-level-overediting/tests`

Final result: `11 passed, 12 subtests passed`

## Commits

- Parent repo: `60fd81e27f0927de50a65fb5686d1b5239d026bb` - `feat: add inversion step observer test`
- FollowYourShape submodule: `927dea2` - `feat: add optional inversion step observer`

## Concerns

- The new test stubs unrelated optional imports from the vendored FollowYourShape module so the test stays focused on `denoise(...)` behavior instead of backend availability.
