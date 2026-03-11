# Architecture Validation Report

**Spec:** `specs/111-consecutive-crises/spec.md`
**Status:** PASS
**Timestamp:** 2026-03-11T12:00:00Z
**Validator:** sdd-architecture-validator

---

## Summary

- CRITICAL: 0
- HIGH: 0
- MEDIUM: 2
- LOW: 2

---

## Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Type Safety | Plan uses `zone == TemperatureZone.CRITICAL` but `ConflictDetails.zone` is `str`, not enum | `plan.md` Phase 2 code snippet | Implementation MUST use `details.zone == "critical"` (string literal), matching existing pattern at `service.py:252` |
| MEDIUM | Type Safety | Plan uses `result.delta < Decimal("0")` — correct, but tasks.md Task 2.2 says `result.delta < 0` (int comparison) | `tasks.md` Task 2.2 | Implementation must use `result.delta < Decimal("0")` since `ScoreResult.delta` is `Decimal`. Python handles `Decimal < 0` correctly but explicit `Decimal("0")` is cleaner and matches existing patterns. |
| LOW | Separation of Concerns | Spec places new test file at `tests/conflicts/test_consecutive_crises.py` but Stories 2, 3, 5 test ScoringService behavior (engine/scoring) | `tasks.md` Stories 2, 3, 5 | Acceptable: the tests verify crisis counter behavior which is a conflict-domain concept. The test file location is consistent with existing `tests/conflicts/test_doom_spiral.py` which also tests ScoringService repair behavior. No action needed. |
| LOW | Import Pattern | Plan Phase 4 shows `from nikita.conflicts.models import ConflictDetails` as a top-level import inside `breakup.py:149` | `plan.md` Phase 4 code | Import should be at module top level. `breakup.py` already imports from `nikita.conflicts.models` at line 1-3. Just add `ConflictDetails` to the existing import statement. |

---

## Module Boundary Analysis

### Dependency Direction (Verified Clean)

```
engine/scoring/service.py ──imports──> conflicts/models.py (ConflictDetails)
engine/scoring/service.py ──imports──> conflicts/gottman.py (GottmanTracker)
engine/scoring/service.py ──imports──> conflicts/temperature.py (TemperatureEngine)
conflicts/breakup.py      ──imports──> conflicts/models.py (ConflictDetails)
conflicts/                 ──does NOT import──> engine/   (confirmed: no reverse dependency)
```

**Verdict:** The proposed changes maintain the existing one-directional dependency from `engine/scoring/` into `conflicts/`. No circular imports introduced. The `breakup.py` change adds an import within the same `conflicts/` package -- clean.

### Files Modified vs Module Boundaries

| File | Package | Change Type | Boundary Impact |
|------|---------|-------------|-----------------|
| `nikita/conflicts/models.py` | conflicts | Schema extension (2 fields) | None -- internal model |
| `nikita/engine/scoring/service.py` | engine/scoring | Logic addition (increment/reset) | None -- already imports ConflictDetails |
| `nikita/conflicts/breakup.py` | conflicts | Replace hardcoded 0 | None -- already has conflict_details param |

No new cross-module imports required. All changes stay within existing module boundaries.

---

## Separation of Concerns Analysis

| Layer | Responsibility | Spec 111 Change | Violation? |
|-------|---------------|-----------------|------------|
| `conflicts/models.py` | Data models for conflict state | Add `consecutive_crises` + `last_crisis_at` fields | No -- pure data |
| `engine/scoring/service.py` | Scoring orchestration + temperature updates | Add crisis increment/reset logic | No -- temperature/crisis logic already lives here (Spec 057) |
| `conflicts/breakup.py` | Breakup threshold evaluation | Read crisis counter from ConflictDetails | No -- replaces hardcoded stub |

**Assessment:** The crisis counter logic (increment/reset) being placed in `ScoringService._update_temperature_and_gottman()` is architecturally sound. This method already manages temperature zones and Gottman tracking -- the crisis counter is a direct derivative of zone state + score delta. Placing it in `conflicts/` would require passing `ScoreResult` into the conflicts package, creating a reverse dependency.

---

## Type Safety Analysis

### ConflictDetails Extension (FR-001)

```python
consecutive_crises: int = Field(default=0, ge=0)  # Pydantic enforces >= 0
last_crisis_at: str | None = Field(default=None)   # ISO timestamp or None
```

- **Backward compatibility**: `from_jsonb()` at line 400-404 filters to `cls.model_fields` -- old JSONB rows without new fields get defaults automatically. Verified.
- **Forward compatibility**: `to_jsonb()` uses `model_dump(mode="json")` -- new fields serialize correctly.
- **Constraint**: `ge=0` prevents negative values at the Pydantic level. No DB CHECK constraint needed since this is a JSONB field.

### Zone Comparison (FR-002) -- MEDIUM FINDING

The `ConflictDetails.zone` field is `str` (line 385), NOT `TemperatureZone` enum.

- **Existing pattern** (service.py:252): `details.zone in ("hot", "critical")` -- string comparison
- **Plan snippet**: `zone == TemperatureZone.CRITICAL` -- would work due to `TemperatureZone(str, Enum)` but is inconsistent with existing code
- **Recommendation**: Use `details.zone == "critical"` for consistency

### Decimal Comparison (FR-002)

`ScoreResult.delta` is `Decimal` (from `calculator.py:51`). The comparison `result.delta < Decimal("0")` is correct. Python also handles `Decimal < 0` (int) correctly, but the explicit Decimal form is preferred for clarity.

---

## Error Handling Analysis

### Existing Error Boundary

`_update_temperature_and_gottman()` is called within `score_interaction()` (line 130-136):

```python
updated_details = self._update_temperature_and_gottman(...)
if updated_details is not None:
    result.conflict_details = updated_details
```

The method returns `None` on error (line 240-241 docstring). However, examining the actual code -- it does NOT have a try/except wrapper. If the crisis logic raises (e.g., unexpected `details.zone` value), it will propagate up to `score_interaction()`.

**Assessment:** This is acceptable because:
1. The new fields have safe defaults (0, None)
2. `ConflictDetails.from_jsonb()` handles malformed data gracefully
3. The crisis logic is simple arithmetic (increment/compare) -- no I/O that could fail
4. Existing pattern: temperature/Gottman updates also lack try/except in this method

### score_batch() Error Path

Adding `conflict_details=None` as optional kwarg is backward compatible. When `None`, `_update_temperature_and_gottman()` creates an empty `ConflictDetails()` with `consecutive_crises=0` -- safe default behavior.

---

## Import Pattern Checklist

- [x] No new cross-package dependencies introduced
- [x] No circular imports (conflicts/ does not import from engine/)
- [x] Lazy imports in `_update_temperature_and_gottman()` maintained (existing pattern)
- [x] `breakup.py` already imports from `conflicts/models` -- just extend existing import
- [x] Test file location (`tests/conflicts/`) follows existing convention

---

## Security Architecture

- [x] No new API endpoints exposed
- [x] No new user input surfaces -- crisis counter is computed server-side only
- [x] Pydantic `ge=0` constraint prevents negative counter injection via JSONB
- [x] No RLS changes needed -- `conflict_details` JSONB is on existing `nikita_emotional_states` table which already has RLS
- [x] No secrets or credentials involved

---

## Scalability Considerations

- [x] No new DB tables or migrations
- [x] No new queries -- counter lives in existing JSONB column
- [x] No per-request overhead increase -- crisis check is O(1) integer comparison
- [x] `score_batch()` optional param is backward compatible

---

## Recommendations (by priority)

1. **[MEDIUM] Fix zone comparison in implementation.** Use `details.zone == "critical"` (string), NOT `TemperatureZone.CRITICAL` (enum). The plan's code snippet is misleading -- the implementer must follow the existing string comparison pattern at `service.py:252`.

2. **[MEDIUM] Use explicit Decimal comparison.** Ensure `result.delta < Decimal("0")` in implementation, not `result.delta < 0`, for consistency with existing scoring code patterns.

3. **[LOW] Consolidate breakup.py import.** Instead of adding a new import statement inline at line 149, add `ConflictDetails` to the existing import at the top of `breakup.py` (which already imports from `nikita.conflicts.models`).

4. **[LOW] Consider adding `last_crisis_at` as `datetime | None` instead of `str | None`.** The spec uses `str` with `.isoformat()` -- this works but loses type safety. However, since `ConflictDetails` stores to JSONB (which doesn't natively support datetime), `str` is actually the pragmatic choice. The existing `last_temp_update` field (line 392) uses the same `str | None` pattern. **No action needed -- consistent with existing convention.**

---

## Verdict

**PASS** -- 0 CRITICAL, 0 HIGH findings. The two MEDIUM findings are implementation guidance (string vs enum comparison, Decimal literal) that do not block planning. The spec demonstrates clean architecture:

- Minimal blast radius (45 lines of production code across 3 files)
- Maintains existing module boundaries and dependency direction
- Leverages established patterns (JSONB extension, from_jsonb/to_jsonb, lazy imports)
- No new cross-cutting concerns or infrastructure
- Backward compatible with zero migration
