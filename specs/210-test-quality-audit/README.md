# Spec 210 — Test Quality Audit

**Status**: PLANNED
**Registered**: 2026-04-13
**Triggered by**: PR #252 (GH #248 hotfix) — discovered the "tests that don't test" anti-pattern in `tests/api/routes/test_tasks.py` (11 tests, 0 effective coverage on the content-parsing branch where the bug lived)

## Problem

Silent test-coverage gaps across the suite. Two confirmed anti-patterns:

1. **Empty-list mock bypass**: Tests mock `repo.get_*()` / `list_*()` / `find_*()` to return `[]`, which means loop bodies in the production function are never exercised. Coverage metrics pass while the risky branch is 0% covered.
2. **Zero-assertion shell tests**: Test bodies with zero `assert` / `assert_awaited_*` / `pytest.raises` — a passing green that proves nothing (`test_calls_repository_create_event_with_session` in iter 2 of PR #252 was one such).

Hypothesis: across 5768 tests, a non-trivial subset suffers from these patterns. Blast radius unknown.

## Scope

Systematic audit of `tests/` directory + remediation backlog.

**Audit tasks**:
- Grep for `return_value=[]` / `AsyncMock(return_value=[])` in mock setups; map each to its corresponding production function
- For each match: check whether ANY sibling test in the file provides a non-empty fixture + asserts on the loop body
- Grep for `async def test_*` bodies with zero `assert` / `assert_awaited_*` / `pytest.raises`
- Cross-reference hits with `nikita/` module blast radius (delivery, scoring, decay, boss fights, onboarding handoff, memory dedup, vice, pipeline) — prioritize by production impact

**Deliverables**:
- Per-module remediation backlog (GH issues per gap cluster)
- Extended `.claude/rules/testing.md` with stronger enforcement (already seeded by PR #252)
- Optional: pytest plugin / CI assertion flagging `return_value=[]` without a paired non-empty test

**Out of scope**:
- E2E tests (`tests/e2e/`) — different assertion model
- Existing integration-marked / slow-marked tests (already deferred)

## Budget

Estimate 3-5 PRs, parallel-safe across modules. Audit phase ~1 day; per-module remediation variable.

## Dependencies

None (pure quality work).

## References

- PR #252 root cause + fix log: `.claude/plans/pr-review-ledger-fix-scheduled-delivery-chat-id-248.md`
- Anti-pattern rule: `.claude/rules/testing.md` → "Tests That Don't Test" section
- Memory: `project_scheduled_events_delivery.md` (auto-memory)

## Next Step

Scope via `/feature 210-test-quality-audit` in a dedicated session (SDD Phase 3 — Socratic spec authoring). Not urgent; runs parallel to Epic 1 sprint.
