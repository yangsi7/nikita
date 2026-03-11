# Challenger Review: Spec 111 — Consecutive Crises Tracking

**Reviewer**: challenger
**Date**: 2026-03-11
**Verdict**: PASS with 2 CRITICAL fixes, 3 IMPORTANT notes

---

## CRITICAL Findings

### C1: `result.total_delta` Does Not Exist on ScoreResult

**Spec reference**: FR-002, line 94
**Spec says**: "Use `result.total_delta` from `ScoreResult`"
**Actual code**: `ScoreResult` has `result.delta` (property, `calculator.py:51`), NOT `total_delta`. The `total_delta` property exists on `MetricDeltas` (`models.py:82`), not `ScoreResult`.

**Fix**: Change FR-002 to use `result.delta` (which is `score_after - score_before`). Alternatively, use `result.deltas_applied.total_delta` if per-metric sum is preferred, but `result.delta` is the composite score change and is more semantically correct for "did the relationship get worse."

### C2: Phantom Repair Quality Values in AC-007

**Spec reference**: AC-007
**Spec says**: "Crisis does NOT reset on ADEQUATE/POOR/HARMFUL repair"
**Actual code**: `repair_quality` validator (`models.py:134-141`) only allows `{"excellent", "good", "adequate", None}`. There are no `poor` or `harmful` values. `REPAIR_QUALITY_DELTAS` (`models.py:21-25`) only maps `excellent`, `good`, `adequate`.

**Fix**: Change AC-007 to "Crisis does NOT reset on ADEQUATE repair quality" (remove POOR/HARMFUL references). Add AC for `repair_quality=None` (no repair detected) to explicitly state counter is unchanged.

---

## IMPORTANT Findings

### I1: Crisis Increment Placement — Early Return on Repair Path

**Spec reference**: FR-002 location `_update_temperature_and_gottman()`
**Observation**: The method has two paths:
1. Repair path (lines 259-286) — returns early at line 286 with `return details.to_jsonb()`
2. Normal path (lines 288-341)

FR-002 says increment when "no successful repair detected." The crisis increment/reset logic MUST go in the normal path (after line 288), since the repair path already returns early. FR-003 reset logic for EXCELLENT/GOOD repairs MUST go in the repair path (before the return at line 286).

**Risk**: If implementer places all crisis logic in one location, either the repair reset or the normal increment will be missed. The spec should explicitly state which code path each FR belongs to.

**Recommendation**: Add to FR-002: "This logic belongs in the normal path (after the repair bypass return)." Add to FR-003: "Reset condition 1 (repair quality) belongs in the repair bypass path (before `return details.to_jsonb()` at line 286). Reset condition 2 (temp < 50) belongs in the normal path after temperature update."

### I2: FR-003 Reset Threshold — Temperature Check Timing

**Spec reference**: FR-003, reset condition 2
**Spec says**: "Temperature drops below 50.0 after the update"
**Question**: In the normal path, temperature is updated at line 336-339. The crisis increment check (FR-002) needs the zone BEFORE the temperature update (to check if zone is CRITICAL). But FR-003 reset needs the temperature AFTER the update (to check if it dropped below 50). This ordering matters:

```
1. Read zone (CRITICAL?) → increment crisis if conditions met
2. Update temperature
3. Read new temperature (< 50?) → reset crisis if crossed threshold
```

The spec should make this ordering explicit to avoid implementer confusion.

### I3: `score_batch` Caller Audit Incomplete

**Spec reference**: FR-005, last note
**Spec says**: "Note: `score_batch` callers must be updated to pass `conflict_details`. The voice pipeline caller needs verification."
**Observation**: This is flagged as a risk (Risk table row 1) but not as a concrete FR or AC. If callers don't pass `conflict_details`, the fix is silently a no-op (`conflict_details=None` → `_update_temperature_and_gottman` initializes empty `ConflictDetails` → crisis counter starts at 0 every call → never reaches 3).

**Recommendation**: Add AC-014: "At least one `score_batch()` caller passes `conflict_details` from the user's DB record." Or explicitly list the caller file paths that need updating.

---

## MINOR Findings

### M1: GH Issue Reference

**Spec says**: GH Issue #91
**Actual**: GH #91 is an enhancement issue. The spec doesn't reference GH #109 which is the ConflictStore removal that caused this bug. Consider referencing both.

### M2: Complexity Assessment

The spec is well-scoped for full SDD (not SDD Quick). ~45 lines prod code + 250 lines tests across 5 files with behavioral logic changes in the scoring engine is complexity 3-4. Appropriate.

### M3: Approach Scoring Tie

Approaches A and B tie at 15 points. The decision rationale justifies A convincingly, but the tie should be acknowledged in the spec or the blast radius scores adjusted (A=1 vs B=3 is a 2-point gap that is the only differentiator after summing).

---

## Edge Cases Not Covered

1. **Concurrent scoring**: Two parallel scoring calls (text + voice) could both read `consecutive_crises=2`, both increment to 3, and both trigger breakup. Since JSONB is read-modify-write, the last writer wins. Unlikely but possible with `score_batch` fix enabling voice.
2. **Crisis counter overflow**: No upper bound constraint. If breakup check is somehow skipped (e.g., `conflict_details` is `None` on `check_thresholds` call), counter grows unbounded. Low risk — Pydantic `ge=0` only sets floor.
3. **Cold start with stale JSONB**: If `conflict_details` JSONB hasn't been updated in weeks (user inactive), `last_crisis_at` could be very old. The spec doesn't define a staleness window for crises. Should 3 crises spread over 30 days still trigger breakup? Game-design question.

---

## Cross-Spec Conflicts with Spec 112

**None identified.** Spec 111 touches `nikita/` backend only. Spec 112 touches `portal/` frontend only. No file overlap. Implementation order is independent.

---

## Summary

| Priority | Count | Items |
|----------|-------|-------|
| CRITICAL | 2 | C1 (wrong property name), C2 (phantom repair values) |
| IMPORTANT | 3 | I1 (code path placement), I2 (ordering), I3 (caller audit) |
| MINOR | 3 | M1 (GH ref), M2 (complexity OK), M3 (tie score) |
| Edge Cases | 3 | Concurrency, overflow, staleness |
