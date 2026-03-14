## API Validation Report

**Spec:** specs/116-extraction-checkpoint/spec.md
**Plan:** specs/116-extraction-checkpoint/plan.md
**Status:** FAIL
**Timestamp:** 2026-03-14T12:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 1
- MEDIUM: 1
- LOW: 1

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| HIGH | Spec Accuracy | Spec claims "11 stages (10 original + ViceStage from Spec 114)" and plan asserts `len(STAGE_DEFINITIONS) == 11`. Code has 10 stages. Spec 114 is in PR #130, not yet merged. `stages_total` in `models.py:158` is `10`. Test `test_all_11_stages_present` will fail RED and never turn GREEN with the changes in this spec alone. | spec.md:74,77 / plan.md:46 | Change all references from 11 to 10: AC-004 to "All 10 pipeline stages remain present", FR-004 text to "Stage count remains 10", and plan test to `assert len(...) == 10`. If Spec 114 merges first, rebase and adjust to 11. |
| MEDIUM | Session Commit Semantics | Spec line 14-16 states "the API handler calls `conv_session.commit()` even on failure (to persist the `mark_failed` status). This means any SAVEPOINT-released (committed) stages that ran before the failure WILL be durably saved." This is correct but the reasoning deserves scrutiny. The SAVEPOINT pattern at `orchestrator.py:230` (`async with self._session.begin_nested()`) releases each savepoint on success. However, those writes are only durable after the outer `conv_session.commit()` at `tasks.py:770`. If the `except` at `tasks.py:771` fires (an unhandled exception escaping `orchestrator.process()` itself), the handler opens a fresh `err_session` (line 775) that only calls `mark_failed` -- the persistence stage writes from the original session are lost because `conv_session` is never committed. The spec should document this edge case: persistence writes survive a **critical stage failure** (where `process()` returns `PipelineResult.failed()`), but do NOT survive an **unhandled exception** that escapes `process()` entirely. | spec.md:14-16 / tasks.py:770-780 | Add a note to the Security/Reliability section: "If an unhandled exception escapes `orchestrator.process()` (not a stage failure but a framework-level crash), the error handler at tasks.py:771 opens a fresh session and only marks the conversation as failed. Persistence writes from the original session are discarded. This is an acceptable residual risk since framework-level crashes are rare and the data can be re-extracted on the next pipeline run." |
| LOW | Docstring Accuracy (pipeline CLAUDE.md) | `nikita/pipeline/CLAUDE.md` line 9 says PersistenceStage is at "pos 3". After this spec it will be at position 2 (index 1). The module-level CLAUDE.md should be updated alongside the docstring fix in FR-002. | pipeline/CLAUDE.md:9 | Update line 9 from "non-critical, pos 3" to "non-critical, pos 2" after implementation. |

### API Inventory

This spec introduces NO new API endpoints, server actions, or route changes. The only API-relevant surface is the existing `POST /api/v1/tasks/process-conversations` endpoint in `tasks.py`.

| Method | Endpoint | Purpose | Auth | Change in Spec 116 |
|--------|----------|---------|------|---------------------|
| POST | /api/v1/tasks/process-conversations | Batch pipeline execution | Bearer (task secret) | No change -- commit pattern already correct for the reorder |

### Commit Pattern Verification (User's Key Concern)

The user asked whether `tasks.py` correctly commits the session on pipeline failure, ensuring persistence writes survive. Here is the verified flow:

**Code path (tasks.py lines 740-780):**

1. `session_maker()` opens `conv_session` (line 740)
2. `PipelineOrchestrator(conv_session)` is created (line 749)
3. `orchestrator.process()` runs stages sequentially (line 750)
4. Each stage runs inside `async with self._session.begin_nested()` (orchestrator.py:230) -- SAVEPOINT isolation
5. On critical stage failure, `process()` returns `PipelineResult.failed()` (orchestrator.py:294) -- it does NOT raise an exception
6. Back in tasks.py, `result.success is False` triggers `conv_repo.mark_failed(conv_id)` (line 768)
7. `await conv_session.commit()` executes unconditionally at line 770

**Verdict: CORRECT.** The commit at line 770 runs for both success and failure paths because `PipelineResult.failed()` is a normal return, not an exception. All released SAVEPOINTs (including a successfully-completed PersistenceStage) are durably committed.

After the Spec 116 reorder:
- ExtractionStage runs at index 0 (SAVEPOINT released on success)
- PersistenceStage runs at index 1 (SAVEPOINT released on success -- thoughts/threads written)
- MemoryUpdateStage runs at index 2 (CRITICAL -- if it fails, `process()` returns failed)
- `conv_session.commit()` at tasks.py:770 persists the extraction + persistence writes + mark_failed status

The reorder achieves the stated goal: extracted thoughts and threads survive a memory_update failure.

### Request/Response Schemas

No schema changes. The `process-conversations` endpoint response format is unchanged:
```python
{"status": "ok", "detected": int, "processed": int, "failed": list[str], "errors": dict}
```

### Error Code Inventory

No new error codes. Existing error handling is unaffected by the stage reorder.

### Recommendations

1. **HIGH (Spec accuracy -- stage count):** Change all "11" references to "10" in spec.md (FR-004, AC-004) and plan.md (test assertion). The ViceStage from Spec 114 is not yet merged (PR #130 in progress). If Spec 114 merges before Spec 116 implementation begins, rebase the count to 11. The plan's test `test_all_11_stages_present` will fail at the assertion level and never go GREEN with only Spec 116 changes applied.

2. **MEDIUM (Edge case documentation):** Add a note to spec.md Security/Reliability acknowledging that an unhandled exception escaping `orchestrator.process()` (distinct from a stage failure) would bypass the commit at tasks.py:770, losing persistence writes. This is acceptable residual risk but should be documented for completeness.

3. **LOW (CLAUDE.md staleness):** Update `nikita/pipeline/CLAUDE.md` line 9 to reflect the new PersistenceStage position after implementation.

### Positive Patterns

- The SAVEPOINT-per-stage isolation at `orchestrator.py:227-230` is an excellent pattern. It prevents a failed stage from poisoning the session for subsequent stages.
- The unconditional `conv_session.commit()` at `tasks.py:770` (covering both success and failure returns) is the correct design for ensuring stage writes persist.
- The spec's analysis of the root cause (PersistenceStage positioned after the critical MemoryUpdateStage) is accurate and the reorder is the minimal viable fix.
- The plan's TDD approach with explicit RED/GREEN phases and targeted assertions for stage ordering is well-structured.
