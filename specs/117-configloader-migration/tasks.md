# Tasks — Spec 117 ConfigLoader Migration (GE-001/GE-007)

## Story 1: Tests (RED)

- [ ] Create `tests/config/test_configloader_metric_weights.py` (3 tests: returns dict, sums to 1, matches yaml)
- [ ] Create `tests/engine/test_configloader_migration.py` (4 tests: engine init, __all__, scoring import, decay import)
- [ ] Verify RED: `pytest tests/config/test_configloader_metric_weights.py tests/engine/test_configloader_migration.py -v` → FAIL

## Story 2: ConfigLoader enhancement (GREEN T1)

- [ ] Add `get_metric_weights()` to `nikita/config/loader.py`
- [ ] Verify: metric_weights tests pass

## Story 3: Production code migration (GREEN T2)

- [ ] Migrate `nikita/engine/scoring/calculator.py`: remove METRIC_WEIGHTS + BOSS_THRESHOLDS imports, use get_config()
- [ ] Migrate `nikita/engine/decay/calculator.py`: remove DECAY_RATES + GRACE_PERIODS imports, use get_config()
- [ ] Migrate `nikita/pipeline/stages/game_state.py`: remove BOSS_THRESHOLDS + CHAPTER_NAMES imports, use get_config()
- [ ] Remove `BOSS_ENCOUNTERS` from `nikita/engine/chapters/boss.py` import

## Story 4: Dead code cleanup (GREEN T3)

- [ ] Clean `nikita/engine/__init__.py`: remove all re-exports, leave only module docstring
- [ ] Clean `nikita/engine/constants.py:__all__`: remove BOSS_ENCOUNTERS, GAME_STATUSES, CHAPTER_DAY_RANGES

## Story 5: Verification

- [ ] All new tests GREEN: `pytest tests/config/test_configloader_metric_weights.py tests/engine/test_configloader_migration.py -v`
- [ ] Engine regression: `pytest tests/engine/ -q --tb=short`
- [ ] Pipeline regression: `pytest tests/pipeline/ -q --tb=short`
- [ ] Full suite: `pytest tests/ -x -q --ignore=tests/e2e --ignore=tests/integration --ignore=tests/db`
