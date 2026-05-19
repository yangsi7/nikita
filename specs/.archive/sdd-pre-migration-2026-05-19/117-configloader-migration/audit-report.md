# Audit Report — Spec 117: ConfigLoader Migration + Engine Constants Cleanup

**Date**: 2026-03-14
**Verdict**: PASS
**Validators run**: 6 (Frontend, Architecture, Data Layer, Auth, Testing, API)

---

## Validator Summary

| Validator | Result | Blockers |
|-----------|--------|---------|
| Frontend | PASS | 0 |
| Architecture | PASS | 0 (3 MEDIUM, 2 LOW addressed) |
| Data Layer | PASS | 0 |
| Auth/Security | PASS | 0 |
| Testing | PASS* | 0 (2 HIGH addressed: AC-004 + behavioral equivalence added) |
| API | PASS | 0 (3 MEDIUM — scope docs; 2 LOW addressed) |

*Testing validator originally FAIL. Resolved by adding AC-004 test (`test_game_state_no_engine_constants_import`) and 3 behavioral equivalence tests (`TestConfigLoaderBehavioralEquivalence`).

---

## Findings Resolved During Implementation

| ID | Severity | Finding | Resolution |
|----|----------|---------|------------|
| ARCH-MEDIUM-002 | MEDIUM | DecayCalculator inconsistent with sibling defensive patterns | Updated docstring: upstream `DecayProcessor` filtering guarantees valid chapters |
| ARCH-MEDIUM-003 | MEDIUM | `game_state.py` duplicated `from nikita.config import get_config` in try blocks | Hoisted to module-level (done in implementation) |
| ARCH-LOW-001 | LOW | `except Exception` too broad at `get_boss_threshold()` sites | Narrowed to `except KeyError` in `boss.py` and `scoring/calculator.py` |
| TEST-HIGH-001 | HIGH | No AC-004 test (game_state.py migration) | Added `test_game_state_no_engine_constants_import` |
| TEST-HIGH-002 | HIGH | No behavioral equivalence tests | Added `TestConfigLoaderBehavioralEquivalence` (3 canary tests) |
| TEST-MEDIUM-003 | MEDIUM | AC-005 coverage | Already present: `test_boss_py_no_boss_encounters_import` |
| API-LOW | LOW | DecayCalculator docstring stale | Updated to reference ConfigLoader |

---

## Findings Accepted / Deferred

| ID | Severity | Finding | Decision |
|----|----------|---------|---------|
| ARCH-MEDIUM-001 | MEDIUM | Spec error handling section says `ConfigurationError` but `get_boss_threshold()` raises `KeyError` | Accepted: `except KeyError` now used at call sites; spec text is implementation note only |
| ARCH-LOW-002 | LOW | 6 remaining `engine.constants` callers not migrated | Out of scope: `CHAPTER_BEHAVIORS` has no ConfigLoader equivalent; API files deferred |
| API-MEDIUM-002/003 | MEDIUM | `portal.py`, `admin_debug.py`, `analyzer.py`, `agent.py`, `server_tools.py` not migrated | Explicitly out of scope per spec (no ConfigLoader equivalent for `CHAPTER_BEHAVIORS`) |
| TEST-MEDIUM-005 | MEDIUM | `inspect.getsource()` fragile (top-20-lines check) | Accepted for now; constants migration is confirmed complete; fix in a follow-up cleanup |

---

## Test Results

```
tests/config/test_configloader_metric_weights.py    5/5 PASS
tests/engine/test_configloader_migration.py        13/13 PASS  (inc. 3 behavioral canaries)
tests/engine/decay/                                44/44 PASS  (updated for YAML grace periods)
tests/engine/scoring/                              60/60 PASS
tests/engine/chapters/                            142/142 PASS
tests/pipeline/                                    74/74 PASS
tests/config/                                      89/89 PASS

Total: 1076 passed, 0 failed
```

---

## Implementation Summary

Files modified:
- `nikita/config/loader.py` — Added `get_metric_weights()` (FR-001)
- `nikita/engine/scoring/calculator.py` — Migrated `METRIC_WEIGHTS`, `BOSS_THRESHOLDS` (FR-002)
- `nikita/engine/decay/calculator.py` — Migrated `DECAY_RATES`, `GRACE_PERIODS` (FR-004)
- `nikita/pipeline/stages/game_state.py` — Migrated `BOSS_THRESHOLDS`, `CHAPTER_NAMES` (FR-005)
- `nikita/engine/chapters/boss.py` — Removed unused `BOSS_ENCOUNTERS` import (FR-003)
- `nikita/engine/__init__.py` — Removed all re-exports (FR-006)
- `nikita/engine/constants.py` — Removed `BOSS_ENCOUNTERS`, `GAME_STATUSES`, `CHAPTER_DAY_RANGES` from `__all__` (FR-007)

Test files modified/added:
- `tests/config/test_configloader_metric_weights.py` — NEW (AC-001)
- `tests/engine/test_configloader_migration.py` — NEW (AC-002–008)
- `tests/engine/decay/test_calculator.py` — Updated for YAML grace period ordering (Ch1=8h, Ch5=72h)
- `tests/engine/decay/test_grace_balance.py` — Rewritten for natural grace period order (veterans > newcomers)
- `tests/engine/decay/test_processor.py` — Updated overdue fixtures to ch1 (8h grace)

Note: `engine.constants` GRACE_PERIODS had inverted values (Ch1=72h, Ch5=8h) relative to the YAML config (Ch1=8h, Ch5=72h). Tests updated to match YAML truth, which is the correct intended behavior (veterans get more grace time).

---

## AC Status

| AC | Description | Status |
|----|-------------|--------|
| AC-001 | `get_metric_weights()` returns `{str: Decimal}` matching scoring.yaml | PASS |
| AC-002 | `scoring/calculator.py` no module-level `METRIC_WEIGHTS`/`BOSS_THRESHOLDS` import | PASS |
| AC-003 | `decay/calculator.py` no module-level `DECAY_RATES`/`GRACE_PERIODS` import | PASS |
| AC-004 | `game_state.py` no module-level `engine.constants` import | PASS |
| AC-005 | `chapters/boss.py` no `BOSS_ENCOUNTERS` import | PASS |
| AC-006 | `engine/__init__.py` contains only module docstring | PASS |
| AC-007 | `BOSS_ENCOUNTERS`, `GAME_STATUSES`, `CHAPTER_DAY_RANGES` absent from `constants.__all__` | PASS |
| AC-008 | All existing tests pass | PASS (1076 passed) |
