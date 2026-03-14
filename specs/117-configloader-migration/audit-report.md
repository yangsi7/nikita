# Audit Report — Spec 117: ConfigLoader Migration

**Status**: PASS
**Date**: 2026-03-14
**Validators**: 6/6 PASS

---

## Summary

All production engine files migrated from deprecated `engine.constants` direct imports to `get_config()` calls. `engine/__init__.py` re-exports cleaned. `constants.__all__` cleaned. 18 new tests added (5 AC-001 metric weights, 13 migration + behavioral equivalence canaries). 1076 total tests passing.

---

## Validator Results

| Validator | Result | Notes |
|-----------|--------|-------|
| Frontend | PASS | No frontend changes |
| Architecture | PASS | Import migration consistent, singleton preserved |
| Data Layer | PASS | No DB changes |
| Auth | PASS | No auth changes |
| Testing | PASS | AC-004 test added; behavioral equivalence canaries added |
| API | PASS | No API changes |

---

## Acceptance Criteria

| AC | Description | Status |
|----|-------------|--------|
| AC-001 | `get_metric_weights()` method on ConfigLoader | PASS — 5 tests in `tests/config/test_configloader_metric_weights.py` |
| AC-002 | `scoring/calculator.py` uses `get_config()` | PASS |
| AC-003 | `decay/calculator.py` uses `get_config()` | PASS |
| AC-004 | `game_state.py` uses `get_config()` | PASS — test `test_game_state_no_engine_constants_import` |
| AC-005 | `boss.py` uses `get_config()` | PASS |
| AC-006 | `engine/__init__.py` no deprecated re-exports | PASS |
| AC-007 | `constants.__all__` cleaned (BOSS_ENCOUNTERS, GAME_STATUSES, CHAPTER_DAY_RANGES removed) | PASS |

---

## Findings Resolved

| Finding | Severity | Resolution |
|---------|----------|-----------|
| GE-001 | HIGH | `get_config()` now has 4 production callers |
| GE-007 | HIGH | `engine/__init__.py` re-exports removed |
| DC-005 | MEDIUM | `BOSS_ENCOUNTERS` removed from `__all__` |
| DC-006 | MEDIUM | `GAME_STATUSES` removed from `__all__` |
| DC-007 | MEDIUM | `CHAPTER_DAY_RANGES` removed from `__all__` |
| DC-008 | MEDIUM | `engine/__init__.py` re-exports deleted |
| LOW-001 | LOW | `except Exception` narrowed to `except KeyError` in `boss.py` |

---

## Notes

- YAML grace periods are authoritative (Ch1=8h natural, Ch5=72h veteran). `constants.py` had inverted values — this was a pre-existing inconsistency. Decay tests updated to reflect YAML truth.
- Behavioral equivalence canaries added in `tests/engine/test_configloader_migration.py::TestConfigLoaderBehavioralEquivalence` guard against future config drift.
- `constants.py` values remain (not deleted) for backward compatibility of any external tooling; only `__all__` cleaned and production callers migrated.
