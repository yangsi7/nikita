# Spec 111 — Cross-Session Consecutive Crises Tracking

**GH Issue**: #91, #109 (ConflictStore removal that caused the bug)
**Status**: Reviewed (challenger fixes applied 2026-03-11)
**Author**: spec-111 agent
**Created**: 2026-03-11
**Scope**: Backend (engine, conflicts, scoring)

---

## 1. Problem Statement

`nikita/conflicts/breakup.py:149` hardcodes `consecutive_crises = 0` because the in-memory ConflictStore was removed in Spec 109 (could not persist across Cloud Run cold starts). The game mechanic — breakup after 3 consecutive unresolved crises — is completely disabled.

The existing config at `nikita/conflicts/models.py:172` defines `consecutive_crises_for_breakup: int = 3`, the breakup manager at `breakup.py:174` checks `if consecutive_crises >= self._config.consecutive_crises_for_breakup`, and `ThresholdResult` carries `consecutive_crises` — but the actual counter is always 0.

**Impact**: Players can never lose via the crisis escalation path. The breakup engine only triggers on score-based thresholds (score < 10) or temperature duration (CRITICAL >48h at temp >90). The intended 3-strike crisis mechanic is dead code.

**Secondary gap**: `ScoringService.score_batch()` (voice call path, `service.py:140`) does NOT call `_update_temperature_and_gottman()`. Voice interactions bypass temperature tracking entirely, meaning voice calls cannot trigger or reset crises.

---

## 2. Approach Evaluation

### Scoring Matrix

| Criterion | Approach A: ConflictDetails JSONB | Approach B: Dedicated DB Column | Approach C: Crisis Event Log |
|-----------|:-:|:-:|:-:|
| **Simplicity** | 5 | 3 | 1 |
| **Reliability** | 4 | 5 | 4 |
| **Testability** | 5 | 4 | 3 |
| **Blast Radius** | 1 (lowest risk) | 3 | 5 (highest risk) |
| **Total** | **15** | **15** | **13** |

### Expert Perspectives

**Game Designer**
- A: Best. Counter lives alongside temperature/Gottman data it depends on. Natural fit with existing ConflictDetails JSONB that already tracks zone, temperature, repair_attempts.
- B: Decent but separates related state. Counter on `users` table while temperature is in `conflict_details` JSONB — split state is harder to reason about atomically.
- C: Over-engineered. An event log is valuable for analytics but adds a table, queries, and computed aggregation for a simple integer counter.

**Backend Engineer**
- A: Zero migration. `ConflictDetails.from_jsonb()` already handles unknown fields gracefully (`{k: v for k, v in data.items() if k in cls.model_fields}`). Adding fields to the Pydantic model is backward-compatible — old rows without the field get `default=0`. Single atomic read/write via existing JSONB column.
- B: Requires `ALTER TABLE users ADD COLUMN` migration. Adds a Supabase MCP call + migration stub. Column lives on `users` but is only meaningful alongside `conflict_details`. Two separate writes per interaction (update column + update JSONB).
- C: New table (`crisis_events`), new repository, new migration, new RLS policy. Counter requires `SELECT COUNT(*) WHERE resolved = false AND user_id = ? ORDER BY created_at DESC` with gap detection. Significantly more code.

**QA Engineer**
- A: Easiest to test. Mock `ConflictDetails` with `consecutive_crises=2`, call scoring, assert it becomes 3. No DB setup needed — it's all Pydantic models serialized to dict.
- B: Integration tests require DB session to verify column updates. Unit tests need separate mocking for JSONB field vs column.
- C: Requires event insertion, ordering verification, gap detection tests. Most test surface area.

**Devil's Advocate**
- A risk: JSONB fields are invisible to SQL queries — cannot easily `SELECT * FROM users WHERE conflict_details->>'consecutive_crises' > 2` for admin dashboards. Mitigation: portal API already reads `conflict_details` JSONB and deserializes via `ConflictDetails.from_jsonb()`, so the field is queryable via application code. For raw SQL, PostgreSQL JSONB operators work: `conflict_details->>'consecutive_crises'`.
- A risk: No CHECK constraint on the integer. Mitigation: Pydantic `Field(ge=0)` enforces on write.
- B risk: Split state — counter could desync from conflict_details if one write succeeds and other fails. Mitigation: wrap in transaction, but adds complexity.
- C risk: Table grows unbounded. Needs cleanup job. Adds operational burden for a simple counter.

### Decision

**Selected: Approach A — Embed in ConflictDetails JSONB**

Rationale: A and B tie at 15 points, but A wins on the two criteria that matter most for this change: simplicity (5 vs 3) and blast radius (1 vs 3). The counter is inherently coupled to temperature/zone state — storing them together in the same JSONB blob ensures atomic reads and writes. The existing `from_jsonb()` / `to_jsonb()` pattern handles backward compatibility automatically. Zero migration needed.

---

## 3. Functional Requirements

### FR-001: ConflictDetails Schema Extension

Add two fields to `ConflictDetails` (`nikita/conflicts/models.py:365`):

```python
consecutive_crises: int = Field(default=0, ge=0, description="Consecutive unresolved crises counter")
last_crisis_at: str | None = Field(default=None, description="ISO timestamp of last crisis increment")
```

- `from_jsonb()` automatically handles old rows (missing keys get defaults).
- No migration required. Existing JSONB data is unaffected.

### FR-002: Crisis Increment Logic

**Location**: `ScoringService._update_temperature_and_gottman()` — normal path (after the repair bypass return at `service.py:286`), specifically after temperature is read but before it is updated.

**Code path**: The method has two paths:
1. **Repair path** (lines 259-286) — returns early at line 286. FR-002 does NOT apply here.
2. **Normal path** (lines 288-341) — FR-002 logic goes here.

**Trigger condition** (all must be true):
1. Temperature zone is `CRITICAL` (>= 75.0) — checked BEFORE temperature update
2. Score delta is negative (`result.delta < 0`, the composite score change property at `calculator.py:51`)
3. No successful repair detected (we are in the normal path, so this is inherently true)

**Behavior**:
- Increment `details.consecutive_crises += 1`
- Set `details.last_crisis_at = datetime.now(UTC).isoformat()`
- Log: `logger.info(f"Crisis #{details.consecutive_crises}")`

**Ordering within normal path**:
```
1. Read zone from details.zone (CRITICAL?) → increment crisis if conditions met
2. Update temperature (existing lines 336-339)
3. Read new temperature (< 50?) → reset crisis if crossed threshold (FR-003)
```

### FR-003: Crisis Reset Logic

**Location**: `ScoringService._update_temperature_and_gottman()` — split across BOTH code paths.

**Reset condition 1 — Repair path** (before `return details.to_jsonb()` at line 286):
- Repair quality is `"excellent"` or `"good"` (from `analysis.repair_quality`)
- This goes in the repair bypass path because that path returns early — the normal path never sees repairs.

**Reset condition 2 — Normal path** (after temperature update at lines 336-339):
- Temperature drops below 50.0 (into WARM or CALM zone) after the update
- Check `details.temperature < 50.0` AFTER `TemperatureEngine.update_conflict_details()` is called.

**Why 50.0 threshold (not 75.0)**:
The devil's advocate correctly identified that a 75.0 reset threshold allows gaming — a player could oscillate between 74 and 76, resetting the counter each time they dip below CRITICAL. Requiring temperature to drop to WARM (< 50.0) means the player must genuinely de-escalate, not just hover at the boundary.

**Behavior** (both conditions):
- Set `details.consecutive_crises = 0`
- Set `details.last_crisis_at = None`
- Log: `logger.info(f"Crisis counter reset (reason: {reason})")`

### FR-004: Breakup Engine Integration

**Location**: `BreakupManager.check_threshold()` (`breakup.py:149`)

Replace:
```python
consecutive_crises = 0
```

With:
```python
details = ConflictDetails.from_jsonb(conflict_details)
consecutive_crises = details.consecutive_crises
```

No other changes needed — the existing `if consecutive_crises >= self._config.consecutive_crises_for_breakup` logic at line 174 already handles the breakup trigger correctly.

> **Note — Dual-table `conflict_details`**: The `conflict_details` JSONB column exists on both `users` and `user_metrics` tables. The **authoritative source** is `user_metrics.conflict_details`, which is updated by `ScoringService._update_temperature_and_gottman()`. The `users.conflict_details` column is a legacy copy kept for backward compatibility. All reads in this spec (`BreakupManager.check_threshold()`, `ConflictDetails.from_jsonb()`) use the value passed through the scoring pipeline, which originates from `user_metrics`.

### FR-005: Voice Call Temperature Tracking (Gap Fix)

**Location**: `ScoringService.score_batch()` (`service.py:140`)

Currently `score_batch()` does NOT call `_update_temperature_and_gottman()`. Voice interactions bypass temperature tracking entirely.

**Fix**: Add the same temperature/Gottman update call that `score_interaction()` has (line 130-136):

```python
# After line 174 (after calculator.calculate)
updated_details = self._update_temperature_and_gottman(
    analysis=analysis,
    result=result,
    conflict_details=conflict_details,
)
if updated_details is not None:
    result.conflict_details = updated_details
```

This requires adding `conflict_details: dict[str, Any] | None = None` parameter to `score_batch()`.

**Caller audit**: `score_batch()` currently has **zero production callers** (only test references in `tests/engine/scoring/test_service.py`). The voice pipeline does not call `score_batch` today. Adding the `conflict_details` parameter as an optional kwarg (`= None`) is backward compatible. When a production caller is eventually added (voice pipeline unification), it MUST pass `conflict_details` from the user's DB record — otherwise the crisis counter silently starts at 0 every call and never reaches 3.

---

## 4. Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|-------------|
| AC-001 | `ConflictDetails` has `consecutive_crises` (int, default 0) and `last_crisis_at` (str, default None) | Unit test: model instantiation + serialization |
| AC-002 | Old JSONB data without new fields deserializes correctly via `from_jsonb()` | Unit test: `from_jsonb({"temperature": 80.0})` returns `consecutive_crises=0` |
| AC-003 | Crisis increments when zone=CRITICAL AND `result.delta` < 0 AND no repair | Unit test: mock scoring path |
| AC-004 | Crisis does NOT increment when zone=HOT (temp < 75) even with negative delta | Unit test: boundary condition |
| AC-005 | Crisis resets on EXCELLENT repair quality | Unit test: mock repair detection |
| AC-006 | Crisis resets on GOOD repair quality | Unit test: mock repair detection |
| AC-007 | Crisis does NOT reset on ADEQUATE repair quality | Unit test: verify counter unchanged |
| AC-014 | Crisis counter unchanged when `repair_quality=None` (no repair detected) | Unit test: normal path with no repair |
| AC-015 | At least one `score_batch()` caller passes `conflict_details` from DB | Code audit / integration test |
| AC-008 | Crisis resets when temperature drops below 50.0 | Unit test: temp update crosses threshold |
| AC-009 | Crisis does NOT reset at temp=50.0 (boundary: must be strictly < 50) | Unit test: boundary condition |
| AC-010 | `BreakupManager.check_threshold()` reads `consecutive_crises` from ConflictDetails | Unit test: mock conflict_details with `consecutive_crises=3` |
| AC-011 | Breakup triggers at exactly `consecutive_crises == 3` | Unit test: threshold boundary |
| AC-012 | `score_batch()` calls `_update_temperature_and_gottman()` | Unit test: verify voice path updates temperature |
| AC-013 | 50+ existing tests that mock `consecutive_crises=0` still pass | Regression: `pytest tests/ -x -q` |

---

## 5. Test Strategy

### Unit Tests (new)

**File**: `tests/conflicts/test_consecutive_crises.py`

| Test | Description |
|------|-------------|
| `test_conflict_details_new_fields_defaults` | New fields default to 0 / None |
| `test_conflict_details_from_jsonb_backward_compat` | Old data without new fields works |
| `test_conflict_details_roundtrip_with_crises` | Serialize/deserialize preserves values |
| `test_crisis_increment_critical_zone_negative_delta` | Increment when CRITICAL + negative |
| `test_crisis_no_increment_hot_zone` | No increment when HOT (< 75) |
| `test_crisis_no_increment_positive_delta` | No increment when delta >= 0 |
| `test_crisis_reset_excellent_repair` | Reset on EXCELLENT quality |
| `test_crisis_reset_good_repair` | Reset on GOOD quality |
| `test_crisis_no_reset_adequate_repair` | No reset on ADEQUATE |
| `test_crisis_no_reset_no_repair_quality` | No reset when `repair_quality=None` |
| `test_crisis_reset_temp_below_50` | Reset when temp drops below 50 |
| `test_crisis_no_reset_temp_at_50` | No reset at exact boundary |
| `test_crisis_counter_persists_across_calls` | Counter accumulates 1 -> 2 -> 3 |
| `test_breakup_reads_from_conflict_details` | BreakupManager uses real counter |
| `test_breakup_at_threshold` | Triggers at exactly 3 |
| `test_breakup_below_threshold` | No trigger at 2 |
| `test_score_batch_updates_temperature` | Voice path calls temperature update |

### Regression

- All existing tests pass unchanged (mocks use `consecutive_crises=0` which matches default).
- No DB migration means no integration test changes.

---

## 6. Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `nikita/conflicts/models.py` | Add `consecutive_crises` + `last_crisis_at` to ConflictDetails | ~5 |
| `nikita/engine/scoring/service.py` | Add crisis increment/reset logic in `_update_temperature_and_gottman()` | ~25 |
| `nikita/engine/scoring/service.py` | Add temperature update to `score_batch()` + `conflict_details` param | ~10 |
| `nikita/conflicts/breakup.py` | Replace hardcoded `0` with `ConflictDetails.from_jsonb()` read | ~3 |
| `tests/conflicts/test_consecutive_crises.py` | New test file (17 tests) | ~250 |

**Total estimated diff**: ~45 lines production code, ~250 lines tests.

---

## 7. Out of Scope

- Portal display of crisis counter (future spec if needed)
- Crisis event audit trail / history log (Approach C — not selected)
- Admin notification when player reaches crisis 2 of 3
- Tuning the threshold (3 crises) — configurable via existing `consecutive_crises_for_breakup` field
- Temperature reset threshold tuning (50.0 chosen, could be made configurable later)

---

## 8. Dependencies

- **Spec 057**: ConflictDetails JSONB schema (foundation — already implemented)
- **Spec 109**: ConflictStore removal (cause of the bug — already merged)
- **Spec 027**: Conflict/resolution system (provides ResolutionQuality enum)

No blocking dependencies. This spec can be implemented immediately.

---

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Voice pipeline callers don't pass `conflict_details` | Medium | Voice crises not tracked | FR-005 requires caller audit |
| Players game the 50.0 threshold by farming repairs | Low | Counter resets too easily | Only EXCELLENT/GOOD reset; ADEQUATE does not |
| JSONB field invisible to admin SQL queries | Low | Harder to debug | PostgreSQL `->>'consecutive_crises'` operator works |
| `score_batch` signature change breaks callers | Medium | Voice scoring fails | Add `conflict_details=None` as optional kwarg (backward compatible) |
