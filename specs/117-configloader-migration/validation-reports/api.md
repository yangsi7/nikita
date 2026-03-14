## API Validation Report

**Spec:** specs/117-configloader-migration/spec.md
**Status:** PASS
**Timestamp:** 2026-03-14T00:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 3
- LOW: 2

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Error Handling | Spec claims `get_boss_threshold()` raises `ConfigurationError` (spec.md:218), but actual implementation raises `KeyError` via `get_chapter()` (loader.py:115). The `try/except Exception` fallback in the spec catches both, so no runtime bug -- but the spec text misleads implementors about the exception type. | spec.md:218, loader.py:115 | Update spec error handling section to say `KeyError` (not `ConfigurationError`). Alternatively, update `get_chapter()` to raise `ConfigurationError` for consistency. The broad `except Exception` in FR-002/FR-005 makes this non-blocking. |
| MEDIUM | Scope Gap | `portal.py:65` and `admin_debug.py:72` also import `BOSS_THRESHOLDS`, `CHAPTER_NAMES`, `DECAY_RATES` directly from `engine.constants`. These are NOT migrated by this spec. If the goal is to eliminate all direct constant imports in favor of ConfigLoader, these two API route files are missed. | portal.py:65,105; admin_debug.py:72,372,461 | Explicitly document these as out-of-scope (deferred to a follow-up spec), or add them to the migration scope. Either way, the spec should acknowledge their existence so implementors don't think the migration is complete. |
| MEDIUM | Scope Gap | `scoring/analyzer.py:18` imports `CHAPTER_BEHAVIORS` and `CHAPTER_NAMES` from constants. `agents/text/agent.py:23` imports `CHAPTER_BEHAVIORS`. `agents/voice/server_tools.py:587` lazy-imports `CHAPTER_BEHAVIORS`. These are non-deprecated constants but represent additional direct-import sites not addressed by this spec. | analyzer.py:18, agent.py:23, server_tools.py:587 | Document these as intentionally out-of-scope (CHAPTER_BEHAVIORS is not deprecated and has no ConfigLoader equivalent). No action needed for Spec 117, but a future spec should consider migrating CHAPTER_BEHAVIORS if ConfigLoader is to become the single source of truth. |
| LOW | Documentation | `decay/calculator.py` docstring (line 33) says "Uses chapter-specific grace periods and decay rates from constants.py". After migration, this docstring becomes stale since it will use ConfigLoader. | decay/calculator.py:33 | Update docstring to reference ConfigLoader after migration. |
| LOW | Test Design | Plan T1.4 tests check "top 20 lines" of source for module-level imports (plan.md:87-88). This is fragile -- if file headers grow (new imports, docstrings), the constant import could shift past line 20 and the test would pass even without migration. | plan.md:87 | Use AST-based checking or search the full import block (everything before the first class/function def) instead of a hardcoded line count. Alternatively, use `grep -c` on the full source for `from nikita.engine.constants import.*METRIC_WEIGHTS`. |

### Core Question: Does Replacing Constants Affect API Response Shape?

**No.** The migration is purely an internal refactoring of where configuration values are read from. The analysis confirms:

1. **`ScoreCalculator.__init__`** (calculator.py:66-68): Changes from `dict(METRIC_WEIGHTS)` to `get_config().get_metric_weights()`. Both produce `dict[str, Decimal]` with identical keys and values. The `self.weights` attribute type and content are unchanged.

2. **`ScoreCalculator._detect_events`** (calculator.py:239): Changes from `BOSS_THRESHOLDS.get(chapter, Decimal("55"))` to `get_config().get_boss_threshold(chapter)` with a `try/except` fallback to `Decimal("55")`. The fallback preserves the exact same default value. The `ScoreChangeEvent` objects emitted are identical in structure.

3. **`ScoreResult` dataclass** (calculator.py:34-53): Not modified. Its fields (`score_before`, `score_after`, `metrics_before`, `metrics_after`, `deltas_applied`, `multiplier_applied`, `engagement_state`, `events`, `conflict_details`) are unchanged.

4. **`ScoringService`** (service.py): Instantiates `ScoreCalculator()` and returns `ScoreResult`. Since neither the constructor signature nor return types change, `ScoringService.score_interaction()` and `score_batch()` return the same shape.

5. **API routes** (`portal.py`, `admin_debug.py`): These import constants directly and are NOT touched by this spec. Their response shapes are unaffected.

6. **`DecayCalculator`** (decay/calculator.py): Migrates `GRACE_PERIODS[chapter]` and `DECAY_RATES[chapter]` to `get_config().get_grace_period(chapter)` and `get_config().get_decay_rate(chapter)`. The return types match: `get_grace_period()` returns `timedelta` (same as `GRACE_PERIODS` values), `get_decay_rate()` returns `Decimal` (same as `DECAY_RATES` values). `DecayResult` shape is unchanged.

**Conclusion:** Zero impact on API response shapes, HTTP status codes, or error handling behavior. All changes are internal to the engine/pipeline layer and produce identical values from a different source (YAML via ConfigLoader instead of hardcoded constants).

### API Inventory

No new API endpoints are introduced by this spec. Existing endpoints are unaffected:

| Method | Endpoint | Impact | Notes |
|--------|----------|--------|-------|
| GET | /api/v1/portal/dashboard | None | Uses `BOSS_THRESHOLDS` directly (not migrated) |
| GET | /api/v1/admin/debug/* | None | Uses `BOSS_THRESHOLDS`, `CHAPTER_NAMES`, `DECAY_RATES` directly (not migrated) |
| POST | /api/v1/tasks/decay | None | Calls `DecayCalculator` internally; output shape unchanged |
| POST | /api/v1/tasks/process-conversations | None | Calls pipeline (GameStateStage); output shape unchanged |

### Server Actions

N/A -- This is a Python/FastAPI backend project, not Next.js server actions.

### Request/Response Schemas

No schema changes. All existing request and response schemas remain identical.

### Error Code Inventory

No new error codes. The spec introduces `try/except Exception` fallbacks at two call sites (scoring calculator and game_state stage) that silently fall back to default values, matching the existing `.get(key, default)` behavior. No new error responses are surfaced to API consumers.

### Positive Patterns

1. **Fallback defaults match originals**: FR-002 uses `Decimal("55")` (matching `BOSS_THRESHOLDS.get(chapter, Decimal("55"))`), FR-005 uses `Decimal("75")` (matching the existing default). This ensures behavioral equivalence.

2. **Singleton ConfigLoader**: `get_config()` is `@lru_cache(maxsize=1)`, so repeated calls in hot paths (scoring, decay) incur no YAML re-parsing overhead.

3. **YAML schema validation**: `MetricWeights` model validator (schemas.py:137) enforces weights sum to 1.0, providing a safety net that the hardcoded constants lack.

4. **Backward compatibility**: Constants remain defined in `constants.py` and are only removed from `__all__` / re-exports, not deleted. External callers (if any) continue to work.

### Recommendations

1. **MEDIUM (spec accuracy):** Correct the error handling section (spec.md:218) to say `KeyError` instead of `ConfigurationError`. While the broad `except Exception` catches both, accurate documentation prevents implementor confusion.

2. **MEDIUM (scope documentation):** Add a "Not In Scope" section to the spec explicitly listing `portal.py`, `admin_debug.py`, `scoring/analyzer.py`, `agents/text/agent.py`, and `agents/voice/server_tools.py` as files that still import from `engine.constants` and are intentionally deferred.

3. **MEDIUM (follow-up tracking):** Consider creating a follow-up spec (or GitHub issue) to migrate the remaining 5 files that import from `engine.constants`, so the migration can be tracked to completion.

4. **LOW (docstring):** Update `DecayCalculator` class docstring after migration to reference ConfigLoader instead of constants.py.

5. **LOW (test robustness):** Replace the "top 20 lines" source inspection test with AST-based import checking or full-source grep to avoid false passes from file growth.
