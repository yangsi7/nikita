## Testing Validation Report

**Spec:** `specs/111-consecutive-crises/spec.md`
**Status:** PASS
**Timestamp:** 2026-03-11T12:00:00Z
**Validator:** sdd-testing-validator (Claude Opus 4.6)

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 3
- LOW: 3

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Edge Cases | No test for `consecutive_crises` overflow / max value behavior | spec.md:192-214 (test table) | Add test: `test_crisis_counter_capped_at_reasonable_max` -- verify behavior if counter reaches e.g. 100 (Pydantic `ge=0` but no `le` constraint). Low risk but defensive. |
| MEDIUM | Integration Tests | No integration test verifying JSONB roundtrip through actual Supabase | spec.md:217-219 (Regression section) | Add one integration test in `tests/db/integration/` that writes `ConflictDetails` with `consecutive_crises=2` to DB and reads it back via `from_jsonb()`. Verifies PostgreSQL JSONB doesn't silently drop the new field. Mark with `@pytest.mark.integration`. |
| MEDIUM | E2E Coverage | No E2E test for the full crisis-to-breakup flow | spec.md:189-219 (Section 5) | Consider a future E2E scenario: 3 consecutive CRITICAL+negative interactions trigger breakup. Not blocking for this spec (pure backend, no user-facing flow yet), but should be tracked. |
| LOW | Test Pyramid | 17 unit tests, 0 integration, 0 E2E -- pyramid is 100/0/0 | spec.md:191-214 | Acceptable for this spec since the change is pure Pydantic model + in-memory logic with no DB migration. The 70-20-10 ratio applies at project level, not per-feature for small backend changes. |
| LOW | Mock Strategy | `test_crisis_no_increment_with_repair` listed in spec Section 5 but not in tasks.md | spec.md:203 vs tasks.md:35-39 | Spec lists 18 tests, plan/tasks list 17. The "no increment with repair" test is in the spec table but not in Task 2.1. It is partially covered by Task 3.1's `test_crisis_no_reset_no_repair_quality` but tests a different thing (increment vs reset). Add to Task 2.1 or clarify coverage. |
| LOW | CI/CD | No explicit mention of CI pipeline impact | plan.md | Confirm `backend-ci.yml` pytest markers will pick up the new test file automatically. Since it's in `tests/conflicts/` with no special markers, it will run in default suite -- this is correct. |

### Testing Pyramid Analysis

```
Target:     Actual in Spec:     Assessment:
  /\            /\
 /E \  10%     /  \   0%        Acceptable - pure backend
 /--\          /    \            logic change, no UI flow
/I   \ 20%   /      \  0%       1 integration test recommended
/----\        /        \         (JSONB roundtrip, MEDIUM finding)
/ U  \ 70%  /  U 100%  \
/------\    /------------\       17 unit tests: comprehensive
```

**Assessment:** The 100% unit ratio is appropriate for this feature. The change is entirely in Pydantic models and in-memory scoring logic. No DB migration, no API endpoint changes, no UI. One integration test for JSONB roundtrip would improve confidence but is not blocking.

### AC Testability Analysis

| AC ID | AC Description | Testable | Test Type | Issue |
|-------|----------------|----------|-----------|-------|
| AC-001 | ConflictDetails has new fields with defaults | Yes | Unit | Clear, specific |
| AC-002 | Old JSONB backward compat | Yes | Unit | Clear, specific |
| AC-003 | Crisis increment on CRITICAL + negative delta | Yes | Unit | Clear, specific |
| AC-004 | No increment on HOT zone | Yes | Unit | Clear, boundary test |
| AC-005 | Reset on EXCELLENT repair | Yes | Unit | Clear, specific |
| AC-006 | Reset on GOOD repair | Yes | Unit | Clear, specific |
| AC-007 | No reset on ADEQUATE repair | Yes | Unit | Clear, specific |
| AC-008 | Reset when temp < 50 | Yes | Unit | Clear, threshold test |
| AC-009 | No reset at temp = 50 (boundary) | Yes | Unit | Excellent boundary test |
| AC-010 | BreakupEngine reads from ConflictDetails | Yes | Unit | Clear, specific |
| AC-011 | Breakup at exactly 3 | Yes | Unit | Clear, boundary test |
| AC-012 | score_batch calls temperature update | Yes | Unit | Clear, mock verification |
| AC-013 | 50+ existing tests still pass | Yes | Regression | Run full suite |
| AC-014 | Counter unchanged with repair_quality=None | Yes | Unit | Clear, specific |
| AC-015 | score_batch caller passes conflict_details | Partial | Code audit | Not fully automatable -- "at least one caller" is a code review criterion, not a test assertion. But test can verify the parameter exists and is used. |

### Test Scenario Inventory

**E2E Scenarios:**
| Scenario | Priority | User Flow | Status |
|----------|----------|-----------|--------|
| 3-strike breakup flow | P2 | Player sends 3 negative messages in CRITICAL zone, gets breakup | Not specified (future) |
| Crisis reset via repair | P3 | Player triggers crisis, then sends excellent repair | Not specified (future) |

**Integration Test Points:**
| Component | Integration Point | Mock Required |
|-----------|-------------------|---------------|
| ConflictDetails JSONB | Supabase PostgreSQL read/write | No (real DB) |
| ScoringService + BreakupEngine | Cross-module crisis flow | Yes (LLM analyzer) |

**Unit Test Coverage:**
| Module | Functions | Coverage Target |
|--------|-----------|-----------------|
| `conflicts/models.py` | ConflictDetails fields, from_jsonb, to_jsonb | 100% of new fields |
| `engine/scoring/service.py` | _update_temperature_and_gottman (crisis increment/reset), score_batch | 100% of new branches |
| `conflicts/breakup.py` | check_thresholds (line 149 replacement) | 100% of changed line |

### TDD Readiness Checklist
- [x] ACs are specific -- all 15 ACs have clear pass/fail criteria
- [x] ACs are measurable -- integer counters, boolean triggers, exact thresholds
- [x] Test types clear per AC -- all mapped to unit tests with specific test names
- [x] Red-green-refactor path clear -- plan.md explicitly states "write failing tests first, then implement" per phase

### Coverage Requirements
- [x] Overall target specified -- 17 new tests covering all 5 FRs
- [x] Critical path coverage -- breakup trigger path (FR-004) has 3 dedicated tests
- [x] Branch coverage -- boundary conditions at temp=50.0, crisis=2 vs 3, all repair qualities
- [ ] Exclusions documented -- no explicit mention of what is NOT tested (e.g., concurrent writes, race conditions in Cloud Run multi-instance)

### Recommendations

1. **(MEDIUM) Add JSONB integration test.** Create one test in `tests/db/integration/` that writes `ConflictDetails(consecutive_crises=2, last_crisis_at="2026-03-11T00:00:00Z")` to the actual Supabase `conflict_details` column and reads it back. This verifies PostgreSQL doesn't silently drop the new JSONB key. Use the project's existing integration test pattern with `@pytest.mark.integration` and `skipif(not _SUPABASE_REACHABLE)`.

2. **(MEDIUM) Add counter overflow test.** The field has `ge=0` but no upper bound. Add `test_crisis_counter_high_value` verifying `ConflictDetails(consecutive_crises=999)` serializes and deserializes correctly. This is defensive but ensures no unexpected Pydantic validation at high values.

3. **(MEDIUM) Track E2E scenario for future.** The 3-strike breakup is a critical game mechanic. Once the portal displays crisis state, create an E2E test. For now, the unit tests adequately cover the backend logic.

4. **(LOW) Reconcile test count.** Spec Section 5 lists 18 tests, plan.md says 17, tasks.md enumerates 17. The discrepancy is `test_crisis_no_increment_with_repair` (spec line 203) which is not in tasks.md Task 2.1. Either add it to Task 2.1 or confirm it's covered by Task 3.1's repair tests.

5. **(LOW) Document AC-015 verification method.** AC-015 ("at least one score_batch caller passes conflict_details from DB") is a code audit criterion, not a testable assertion. Either (a) convert to a test that greps production code for `score_batch(.*conflict_details`, or (b) mark as "manual verification" in the AC table.

6. **(LOW) Add concurrent write note.** Cloud Run can have multiple instances. If two requests for the same user process simultaneously, both read `consecutive_crises=1`, both increment to 2, and one write overwrites the other. This is a known limitation of JSONB-based counters. Document as an accepted risk or add a note about future optimistic locking if needed.
