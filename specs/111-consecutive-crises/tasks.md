# Spec 111 — Tasks

**Plan**: `specs/111-consecutive-crises/plan.md`

---

## Story 1: ConflictDetails Schema Extension (FR-001)

### Task 1.1: Write schema tests
- **File**: `tests/conflicts/test_consecutive_crises.py`
- **Tests**:
  - `test_conflict_details_new_fields_defaults` — `ConflictDetails()` has `consecutive_crises=0`, `last_crisis_at=None`
  - `test_conflict_details_from_jsonb_backward_compat` — `from_jsonb({"temperature": 80.0})` returns `consecutive_crises=0`
  - `test_conflict_details_roundtrip_with_crises` — `to_jsonb()` → `from_jsonb()` preserves `consecutive_crises=2, last_crisis_at="2026-..."`
- **AC**: AC-001, AC-002
- **Status**: [ ] Pending

### Task 1.2: Add fields to ConflictDetails
- **File**: `nikita/conflicts/models.py:397` (after `boss_phase`)
- **Change**: Add `consecutive_crises: int = Field(default=0, ge=0)` and `last_crisis_at: str | None = Field(default=None)`
- **AC**: AC-001, AC-002
- **Status**: [ ] Pending

### Task 1.3: Regression check
- **Command**: `pytest tests/ -x -q --tb=line`
- **AC**: AC-013
- **Status**: [ ] Pending

---

## Story 2: Crisis Increment Logic (FR-002)

### Task 2.1: Write increment tests
- **File**: `tests/conflicts/test_consecutive_crises.py`
- **Tests**:
  - `test_crisis_increment_critical_zone_negative_delta` — zone=CRITICAL, `result.delta < 0` → `consecutive_crises` increments
  - `test_crisis_no_increment_hot_zone` — zone=HOT (temp=74.9), negative delta → no increment
  - `test_crisis_no_increment_positive_delta` — zone=CRITICAL, `result.delta > 0` → no increment
  - `test_crisis_counter_persists_across_calls` — three consecutive calls → counter goes 1→2→3
- **AC**: AC-003, AC-004, AC-014
- **Status**: [ ] Pending

### Task 2.2: Implement increment in normal path
- **File**: `nikita/engine/scoring/service.py`
- **Location**: Normal path (after line 291, before T9 temperature delta calc)
- **Logic**: Read zone from `details.zone` (str, not enum). If `details.zone == "critical"` AND `result.delta < Decimal("0")`, increment `details.consecutive_crises` and set `details.last_crisis_at`.
- **AC**: AC-003, AC-004
- **Status**: [ ] Pending

---

## Story 3: Crisis Reset Logic (FR-003)

### Task 3.1: Write reset tests
- **File**: `tests/conflicts/test_consecutive_crises.py`
- **Tests**:
  - `test_crisis_reset_excellent_repair` — repair_quality="excellent" → counter resets to 0
  - `test_crisis_reset_good_repair` — repair_quality="good" → counter resets to 0
  - `test_crisis_no_reset_adequate_repair` — repair_quality="adequate" → counter unchanged
  - `test_crisis_no_reset_no_repair_quality` — repair_quality=None → counter unchanged
  - `test_crisis_reset_temp_below_50` — temp drops from 80→45 → counter resets
  - `test_crisis_no_reset_temp_at_50` — temp drops to exactly 50.0 → counter unchanged
- **AC**: AC-005, AC-006, AC-007, AC-008, AC-009, AC-014
- **Status**: [ ] Pending

### Task 3.2: Implement repair-path reset
- **File**: `nikita/engine/scoring/service.py`
- **Location**: Repair bypass path (before `return details.to_jsonb()` at line 286)
- **Logic**: If `analysis.repair_quality in ("excellent", "good")` and `details.consecutive_crises > 0`, reset to 0.
- **AC**: AC-005, AC-006, AC-007
- **Status**: [ ] Pending

### Task 3.3: Implement temp-threshold reset
- **File**: `nikita/engine/scoring/service.py`
- **Location**: Normal path (after `TemperatureEngine.update_conflict_details()` at lines 336-339)
- **Logic**: If `details.temperature < 50.0` and `details.consecutive_crises > 0`, reset to 0.
- **AC**: AC-008, AC-009
- **Status**: [ ] Pending

---

## Story 4: Breakup Engine Integration (FR-004)

### Task 4.1: Write breakup tests
- **File**: `tests/conflicts/test_consecutive_crises.py`
- **Tests**:
  - `test_breakup_reads_from_conflict_details` — conflict_details with `consecutive_crises=3` → breakup manager reads it
  - `test_breakup_at_threshold` — `consecutive_crises=3` → `should_breakup=True`
  - `test_breakup_below_threshold` — `consecutive_crises=2` → `should_breakup=False`
- **AC**: AC-010, AC-011
- **Status**: [ ] Pending

### Task 4.2: Replace hardcoded zero
- **File**: `nikita/conflicts/breakup.py:149`
- **Change**: Replace `consecutive_crises = 0` with `ConflictDetails.from_jsonb(conflict_details).consecutive_crises` (`ConflictDetails` import is already top-level in `breakup.py`)
- **AC**: AC-010, AC-011
- **Status**: [ ] Pending

---

## Story 5: Voice Path Temperature Fix (FR-005)

### Task 5.1: Write score_batch temperature test
- **File**: `tests/conflicts/test_consecutive_crises.py`
- **Tests**:
  - `test_score_batch_updates_temperature` — `score_batch(conflict_details=...)` calls `_update_temperature_and_gottman()`
- **AC**: AC-012
- **Status**: [ ] Pending

### Task 5.2: Add temperature update to score_batch
- **File**: `nikita/engine/scoring/service.py:140`
- **Change**: Add `conflict_details: dict[str, Any] | None = None` param. After `calculator.calculate()` (line 174), call `_update_temperature_and_gottman()` and attach result to `result.conflict_details`.
- **AC**: AC-012, AC-015
- **Status**: [ ] Pending

---

## Story 6: Final Regression

### Task 6.1: Full test suite
- **Command**: `pytest tests/ -x -q --tb=line`
- **AC**: AC-013
- **Status**: [ ] Pending

---

## Summary

| Story | Tasks | Tests | Prod Lines | Depends On |
|-------|-------|-------|-----------|------------|
| 1. Schema | 3 | 3 | 3 | — |
| 2. Increment | 2 | 4 | 5 | Story 1 |
| 3. Reset | 3 | 6 | 12 | Story 2 |
| 4. Breakup | 2 | 3 | 3 | Story 1 |
| 5. Voice | 2 | 1 | 7 | Story 1 |
| 6. Regression | 1 | — | — | All |
| **Total** | **13** | **17** | **~30** | |
