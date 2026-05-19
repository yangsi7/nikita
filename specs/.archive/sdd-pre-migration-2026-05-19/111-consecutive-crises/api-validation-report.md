# API & Backend Validation Report — Spec 111

**Spec:** `specs/111-consecutive-crises/spec.md`
**Status:** PASS (conditional)
**Timestamp:** 2026-03-11T00:00:00Z
**Validator:** sdd-api-validator

---

## Summary

- CRITICAL: 0
- HIGH: 2
- MEDIUM: 3
- LOW: 2

**Verdict:** PASS — 0 CRITICAL findings. The 2 HIGH findings are design-time issues that can be resolved during implementation without re-specifying. The spec is well-structured, accurate to codebase line numbers, and covers error handling for JSONB backward compatibility. Proceed to implementation with the mitigations below.

---

## Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| 1 | HIGH | Method Naming | Spec references `BreakupEngine.check_thresholds()` (plural, spec.md:127,140) but actual code is `BreakupManager.check_threshold()` (singular, breakup.py:126). Both class name AND method name are wrong in spec. | spec.md:127 | Fix references to `BreakupManager.check_threshold()`. Plan.md:69 also says "BreakupEngine" — update to `BreakupManager`. |
| 2 | HIGH | Data Flow | `_update_temperature_and_gottman()` has NO `user_id` parameter (service.py:224-228: `self, analysis, result, conflict_details`). FR-002 and FR-003 both specify `logger.info(f"Crisis #{...} for user {user_id}")` but `user_id` is not in scope. | spec.md:96,123 | Either (a) add `user_id` param to `_update_temperature_and_gottman()` and update both callers (`score_interaction` line 130, `score_batch` new call), or (b) drop `user_id` from log messages and log only counter value + zone. Option (b) is lower blast radius. |
| 3 | MEDIUM | Zone Comparison | Plan.md:37 uses `zone == TemperatureZone.CRITICAL` (enum comparison) but codebase pattern at service.py:252 is `details.zone in ("hot", "critical")` (string comparison). `ConflictDetails.zone` is `str` type (models.py:385), not `TemperatureZone` enum. `TemperatureEngine.get_zone()` returns enum but `details.zone` stores the string value. | plan.md:37 | Use string comparison: `if details.zone == "critical" and result.delta < Decimal("0")`. The plan code snippet should match existing codebase convention. Alternatively, call `TemperatureEngine.get_zone(details.temperature)` to get the enum, but this duplicates the zone lookup that `update_conflict_details` already performs. |
| 4 | MEDIUM | Reset Threshold | FR-003 specifies reset when `details.temperature < 50.0` AFTER `TemperatureEngine.update_conflict_details()` is called (spec.md:114-115). However, this check uses `details.temperature` which is the float on the Pydantic model. `TemperatureEngine.update_conflict_details()` (temperature.py:242) returns a NEW `ConflictDetails` instance. The `details` variable is reassigned at service.py:336-338. Verify that the spec's ordering instruction ("after lines 336-339") correctly refers to the reassigned `details`. | spec.md:114, plan.md:60-64 | The code at service.py:336-338 does `details = TemperatureEngine.update_conflict_details(details=details, temp_delta=...)` which reassigns `details`. The reset check `if details.temperature < 50.0` AFTER this line is correct — it reads the UPDATED temperature. No code change needed, but add a comment in implementation: `# Crisis reset check uses post-update temperature`. |
| 5 | MEDIUM | score_batch Analysis | FR-005 calls `_update_temperature_and_gottman(analysis=analysis, ...)` but `score_batch` gets its analysis from `analyzer.analyze_batch()` (service.py:163) which may return a different `ResponseAnalysis` shape than `analyzer.analyze()`. Specifically, `analyze_batch` may not populate `repair_attempt_detected` or `repair_quality` fields for batch voice transcripts. If these default to `None`/`False`, the repair path in `_update_temperature_and_gottman` is safely skipped — but this implicit behavior should be documented. | spec.md:148-158 | Add a note to FR-005: "Voice batch analysis via `analyze_batch()` does not detect repairs (fields default to False/None). This means voice calls can increment crises but cannot trigger repair-based resets. This is acceptable for v1 — voice repair detection is out of scope." |
| 6 | LOW | Spec Naming | Spec title uses "check_thresholds" in multiple places but the method is `check_threshold` (singular). The internal method `_check_temperature_threshold` is also singular. Consistent naming prevents confusion during implementation. | spec.md:127,140 | Global find-replace `check_thresholds` to `check_threshold` in spec.md and plan.md. |
| 7 | LOW | Test Count | Spec section 5 lists 18 tests, plan says 17, tasks.md summary table says 17. The spec test table has 18 rows. | spec.md:196-214, plan.md:127, tasks.md:137 | Reconcile — the spec test table includes `test_crisis_no_increment_with_repair` which maps to Story 3 (reset), not Story 2 (increment). The plan's 17-count appears correct if that test is counted under Story 3. Clarify in tasks.md. |

---

## API Inventory

No REST API routes are added or modified by this spec. All changes are internal engine methods.

| Method | Location | Change Type | Signature Change |
|--------|----------|------------|-----------------|
| `ScoringService._update_temperature_and_gottman()` | service.py:224 | Modified (logic added) | None (or +user_id per finding #2) |
| `ScoringService.score_batch()` | service.py:140 | Modified | +`conflict_details: dict[str, Any] \| None = None` param |
| `BreakupManager.check_threshold()` | breakup.py:126 | Modified (line 149) | None |
| `ConflictDetails` | models.py:365 | Extended | +`consecutive_crises`, +`last_crisis_at` fields |

---

## Data Flow Analysis

### score_interaction path (text messages)
```
score_interaction(conflict_details=dict)
  -> calculator.calculate() -> ScoreResult (has .delta)
  -> _update_temperature_and_gottman(analysis, result, conflict_details)
     -> ConflictDetails.from_jsonb(conflict_details)
     -> [REPAIR PATH] if repair detected:
        -> Reset crisis if quality in (excellent, good)  [FR-003]
        -> return details.to_jsonb()
     -> [NORMAL PATH]:
        -> Check zone == "critical" AND result.delta < 0 -> increment crisis  [FR-002]
        -> TemperatureEngine.update_conflict_details() -> new details
        -> Check details.temperature < 50.0 -> reset crisis  [FR-003]
        -> return details.to_jsonb()
  -> result.conflict_details = updated_details
```

### score_batch path (voice — NEW)
```
score_batch(conflict_details=dict|None)  [FR-005 adds param]
  -> analyzer.analyze_batch() -> ResponseAnalysis
  -> calculator.calculate() -> ScoreResult
  -> _update_temperature_and_gottman(analysis, result, conflict_details)  [FR-005 adds call]
  -> result.conflict_details = updated_details
```

### check_threshold path (breakup check)
```
BreakupManager.check_threshold(conflict_details=dict|None)
  -> ConflictDetails.from_jsonb(conflict_details)  [FR-004 replaces hardcoded 0]
  -> consecutive_crises = details.consecutive_crises
  -> _check_temperature_threshold(..., consecutive_crises)
  -> if consecutive_crises >= config.consecutive_crises_for_breakup -> breakup
```

---

## JSONB Backward Compatibility Assessment

**PASS.** The `ConflictDetails.from_jsonb()` method at models.py:400-404 filters input keys via `{k: v for k, v in data.items() if k in cls.model_fields}`. Adding `consecutive_crises` and `last_crisis_at` to the Pydantic model means:

1. Old JSONB rows without these keys: `from_jsonb()` returns model with defaults (`consecutive_crises=0`, `last_crisis_at=None`). Verified by existing pattern — `boss_phase` field (models.py:397) uses same default mechanism.
2. New JSONB rows with these keys: `from_jsonb()` includes them via the key filter.
3. `to_jsonb()` calls `model_dump(mode="json")` which always includes all fields. First write after read will persist the new fields. No migration needed.

**Risk: None.** This is the safest schema extension pattern in the codebase.

---

## Error Handling Assessment

| Scenario | Handling | Status |
|----------|----------|--------|
| `conflict_details=None` passed to breakup | `from_jsonb(None)` returns `ConflictDetails()` with `consecutive_crises=0` | SAFE |
| `conflict_details=None` in `_update_temperature_and_gottman` | Already handled at service.py:251 — returns defaults | SAFE |
| `conflict_details=None` in `score_batch` (new) | FR-005 adds `conflict_details=None` default. `_update_temperature_and_gottman` handles `None` at line 251 | SAFE |
| Old JSONB missing `consecutive_crises` | `from_jsonb` filter + Pydantic default = 0 | SAFE |
| `result.delta` type mismatch (Decimal vs float) | FR-002 compares `result.delta < Decimal("0")` — `result.delta` is `Decimal` (calculator.py:51-53, returns `score_after - score_before` both Decimal) | SAFE |
| `details.zone` type (str vs enum) | See finding #3 — must use string comparison | NEEDS FIX |

---

## Positive Patterns (Replicate These)

1. **Approach evaluation matrix** with expert perspectives and devil's advocate — excellent decision documentation.
2. **Precise line number references** for all code locations — verified accurate against current codebase.
3. **Backward compatibility analysis** for JSONB schema extension — correctly identifies `from_jsonb` safety.
4. **Caller audit** for `score_batch()` — correctly notes zero production callers and documents future risk.
5. **Boundary condition tests** (temp=50.0 exact, consecutive_crises=2 vs 3) — thorough edge case coverage.
6. **Reset threshold rationale** (50.0 not 75.0 to prevent gaming) — game design reasoning documented.

---

## Recommendations

1. **HIGH (Finding #1):** Fix all spec/plan references from `BreakupEngine.check_thresholds()` to `BreakupManager.check_threshold()`. This is a documentation-only fix but prevents implementor confusion.

2. **HIGH (Finding #2):** The `user_id` logging gap has two solutions. **Recommended:** Drop `user_id` from crisis log messages. The method is a `@staticmethod`-candidate (only uses `self` for nothing) and adding `user_id` just for logging increases blast radius (two callers must change). Use `logger.info(f"Crisis #{details.consecutive_crises} (zone={zone})")` instead. If user tracing is needed, the caller (`score_interaction`/`score_batch`) already has `user_id` in scope and can log separately.

3. **MEDIUM (Finding #3):** Use `details.zone == "critical"` string comparison, not enum comparison, in the implementation. The plan's code snippet should be updated.
