# Spec 111 — Implementation Plan

**Spec**: `specs/111-consecutive-crises/spec.md`
**Approach**: A (ConflictDetails JSONB embed)
**Complexity**: 3 (behavioral logic change in scoring engine, 5 files, ~45 lines prod + ~250 lines tests)

---

## Implementation Order

The implementation follows TDD: write failing tests first, then implement.

### Phase 1: Schema Extension (FR-001)

**Goal**: Add `consecutive_crises` and `last_crisis_at` fields to ConflictDetails.

1. Write tests for new field defaults, backward compat, roundtrip serialization
2. Add fields to `ConflictDetails` in `nikita/conflicts/models.py:397` (after `boss_phase`)
3. Verify all existing tests still pass (new fields default to 0/None)

**Risk**: None. Additive change to Pydantic model with defaults.

### Phase 2: Crisis Increment (FR-002)

**Goal**: Increment counter when zone=CRITICAL AND `result.delta < 0` in normal path.

1. Write tests: increment on CRITICAL+negative, no increment on HOT, no increment on positive delta, accumulation 1->2->3
2. Add increment logic to `_update_temperature_and_gottman()` normal path (after line 288, before temperature update at line 336)
3. Ordering: read zone BEFORE temp update, increment if conditions met

**Key code location**: `nikita/engine/scoring/service.py:288-335` (normal path, before line 336)

**Implementation detail**:
```python
# After line 291 (is_positive check) but before T9 temperature delta calc
# details.zone is a str ("calm", "warm", "hot", "critical"), not an enum
if details.zone == "critical" and result.delta < Decimal("0"):
    details.consecutive_crises += 1
    details.last_crisis_at = datetime.now(UTC).isoformat()
    logger.info(f"Crisis #{details.consecutive_crises}")
```

### Phase 3: Crisis Reset (FR-003)

**Goal**: Reset counter on EXCELLENT/GOOD repair OR when temp drops below 50.

1. Write tests: reset on EXCELLENT, reset on GOOD, no reset on ADEQUATE, no reset on None, reset on temp<50, no reset at temp=50
2. Add repair-path reset in repair bypass section (before `return details.to_jsonb()` at line 286)
3. Add temp-threshold reset in normal path (after `TemperatureEngine.update_conflict_details()` at line 336-339)

**Repair path** (line ~285, before return):
```python
if analysis.repair_quality in ("excellent", "good") and details.consecutive_crises > 0:
    details.consecutive_crises = 0
    details.last_crisis_at = None
    logger.info(f"Crisis counter reset (repair quality: {analysis.repair_quality})")
```

**Normal path** (after line 339, after temp update):
```python
if details.temperature < 50.0 and details.consecutive_crises > 0:
    details.consecutive_crises = 0
    details.last_crisis_at = None
    logger.info(f"Crisis counter reset (temp dropped to {details.temperature:.1f})")
```

### Phase 4: Breakup Engine Integration (FR-004)

**Goal**: Replace hardcoded `consecutive_crises = 0` with real value from ConflictDetails.

1. Write tests: breakup reads from conflict_details, triggers at exactly 3, does not trigger at 2
2. Replace line 149 in `breakup.py`

**Change** (2 lines — `ConflictDetails` import is already at top of `breakup.py`):
```python
# Before (line 149):
consecutive_crises = 0

# After:
details = ConflictDetails.from_jsonb(conflict_details)
consecutive_crises = details.consecutive_crises
```

### Phase 5: Voice Path Fix (FR-005)

**Goal**: Add `_update_temperature_and_gottman()` call to `score_batch()`.

1. Write test: `score_batch` calls temperature update when `conflict_details` provided
2. Add `conflict_details: dict[str, Any] | None = None` param to `score_batch()`
3. Add temperature/Gottman update call after `calculator.calculate()` (after line 174)

**Note**: No production callers exist today. This is future-proofing for voice pipeline unification.

---

## Dependency Graph

```
Phase 1 (FR-001: Schema)
    ↓
Phase 2 (FR-002: Increment) ←── depends on Phase 1 fields
    ↓
Phase 3 (FR-003: Reset) ←── depends on Phase 2 logic being in place
    ↓
Phase 4 (FR-004: Breakup) ←── depends on Phase 1 fields
    ↓
Phase 5 (FR-005: Voice) ←── independent, but logically last
```

Phases 4 and 5 are independent of each other but both depend on Phase 1.

---

## Test File Structure

All new tests go in `tests/conflicts/test_consecutive_crises.py`:

```
TestConflictDetailsSchema       (3 tests — Phase 1)
TestCrisisIncrement             (4 tests — Phase 2)
TestCrisisReset                 (6 tests — Phase 3)
TestBreakupIntegration          (3 tests — Phase 4)
TestScoreBatchTemperature       (1 test  — Phase 5)
                                ─────────
                                17 tests total
```

---

## Regression Strategy

- Run `pytest tests/ -x -q --tb=line` after each phase
- No DB migrations → no integration test impact
- All 50+ existing mocks use `consecutive_crises=0` which matches the default → no breakage

---

## Estimated Effort

| Phase | Prod Lines | Test Lines | Risk |
|-------|-----------|------------|------|
| 1. Schema | 3 | 30 | None |
| 2. Increment | 5 | 60 | Low — ordering matters |
| 3. Reset | 12 | 80 | Low — two code paths |
| 4. Breakup | 3 | 50 | None |
| 5. Voice | 7 | 30 | Low — no callers yet |
| **Total** | **~30** | **~250** | **Low** |
