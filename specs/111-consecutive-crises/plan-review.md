# Challenger Plan Review: Spec 111

**Reviewer**: challenger
**Date**: 2026-03-11
**Verdict**: PASS — no blocking issues

---

## Spec Fix Verification

All 3 critical findings from spec review were addressed:
- C1: `result.total_delta` changed to `result.delta` (verified in spec.md line 90)
- C2: Phantom `POOR`/`HARMFUL` values removed (verified: zero matches in spec.md)
- I1 code path placement: Plan explicitly splits logic — repair path reset (Phase 3, line 51-57) and normal path increment/reset (Phase 2 line 34-41, Phase 3 line 59-64)

---

## Plan Quality Assessment

### Strengths

1. **TDD ordering correct**: Tests before implementation in every phase. Story structure enforces this naturally.
2. **Dependency graph accurate**: Phase 1 (schema) must precede all others. Phases 4-5 are correctly noted as independent of each other.
3. **Code locations precise**: Line numbers match current codebase (verified: `breakup.py:149`, `service.py:291`, `service.py:336`).
4. **Effort estimates conservative**: ~30 prod lines + ~250 test lines is realistic for 5 files across 5 phases.
5. **Regression strategy sound**: Run full suite after each phase. No DB migrations = no integration test risk.

### Issues Found

**IMPORTANT: Task 2.2 zone check uses string comparison, not enum**

Plan Phase 2 (line 37): `zone == TemperatureZone.CRITICAL`
Task 2.2: "Read zone from `details.zone`. If `zone == "critical"`"

The `details.zone` field is a `str` (see `models.py:385`: `zone: str = Field(default="calm")`), NOT a `TemperatureZone` enum. But the plan code snippet at line 37 uses `TemperatureZone.CRITICAL` enum comparison while task 2.2 correctly uses the string `"critical"`.

The plan code snippet should match the task: use `details.zone == "critical"` (string), not `TemperatureZone.CRITICAL`. Or alternatively, compute zone via `TemperatureEngine._compute_zone(details.temperature)` which returns a `TemperatureZone` enum. The existing code at `service.py:252` uses `details.zone in ("hot", "critical")` — string comparison is the established pattern.

**Recommendation**: Use `details.zone == "critical"` for consistency with line 252.

---

**MINOR: AC-014 and AC-015 referenced in tasks but not in spec**

Task 2.1 references AC-014, Task 5.2 references AC-015. The spec's acceptance criteria table ends at AC-013. These appear to be new ACs added during plan writing. They should be back-ported to the spec's AC table for traceability.

---

**MINOR: Phase 4/5 independence not exploited**

The dependency graph shows Phases 4 and 5 are independent (both only depend on Phase 1). The plan sequences them 4→5 but they could be implemented in parallel or in either order. This is a minor optimization opportunity, not a blocker.

---

## Alternative Approaches Considered

The plan doesn't discuss alternatives because the spec already chose Approach A (JSONB embed). The plan correctly implements A without deviation. No alternative plan approaches are warranted — this is a straightforward behavioral fix, not an architectural decision.

---

## TDD Correctness

| Story | Tests First? | Tests Match ACs? | Implementation After? |
|-------|-------------|-------------------|----------------------|
| 1 (Schema) | Yes (T1.1) | AC-001, AC-002 | Yes (T1.2) |
| 2 (Increment) | Yes (T2.1) | AC-003, AC-004 | Yes (T2.2) |
| 3 (Reset) | Yes (T3.1) | AC-005-009 | Yes (T3.2, T3.3) |
| 4 (Breakup) | Yes (T4.1) | AC-010, AC-011 | Yes (T4.2) |
| 5 (Voice) | Yes (T5.1) | AC-012 | Yes (T5.2) |
| 6 (Regression) | N/A | AC-013 | N/A |

All stories follow TDD correctly.

---

## Summary

| Priority | Count | Items |
|----------|-------|-------|
| CRITICAL | 0 | — |
| IMPORTANT | 1 | Zone string vs enum mismatch in plan code snippet |
| MINOR | 2 | AC-014/015 not in spec, phase parallelism |
