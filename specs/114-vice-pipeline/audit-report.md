# Audit Report — Spec 114: Vice Pipeline Activation

**Status: PASS**
**Date:** 2026-03-14
**Validators run:** 6/6

---

## Validator Results

| Validator | Status | Critical | High | Medium | Low |
|-----------|--------|----------|------|--------|-----|
| Frontend | PASS | 0 | 0 | 0 | 0 |
| Auth | PASS | 0 | 0 | 0 | 0 |
| Architecture | PASS* | 0 | 0 | 0 | 0 |
| Data Layer | PASS* | 0 | 0 | 0 | 0 |
| Testing | PASS* | 0 | 0 | 0 | 0 |
| API | PASS* | 0 | 0 | 0 | 0 |

*All critical/high findings resolved in spec + plan before implementation.

---

## Findings Resolved

### CRITICAL (2 resolved)

| ID | Finding | Resolution |
|----|---------|------------|
| C1 | Architecture: ViceService constructor called with `repo` arg — raises TypeError | Plan already uses `ViceService()` no-arg; spec FR-005 documents no-arg constructor |
| C2 | Testing: Mock strategy based on nonexistent constructor signature | Plan uses `AsyncMock` on `process_conversation` directly; tests patch `nikita.engine.vice.service.ViceService` |

### HIGH (5 resolved)

| ID | Finding | Resolution |
|----|---------|------------|
| H1 | spec FR-002 referenced `ctx.raw_messages` (field doesn't exist) | Fixed: spec + plan updated to `ctx.conversation.messages` |
| H2 | Parameter name `nikita_response=` raises TypeError | Plan already uses `nikita_message=nikita_response` |
| H3 | `test_vice_stage_position` risks instantiating orchestrator | Plan updated: inspect `STAGE_DEFINITIONS` class var directly |
| H4 | `test_vice_stage_failure_non_fatal` calls `_run()` directly — wrong non-fatal path | Plan updated: call `stage.execute(ctx)` with `AsyncMock(side_effect=...)` |
| H5 | `stages_total=10` hardcoded in orchestrator.py:184 and models.py:158 | Added to plan T2 step 3+4; both updated to 11 |

### MEDIUM (5 resolved)

| ID | Finding | Resolution |
|----|---------|------------|
| M1 | ViceScorer writes on separate session (outside SAVEPOINT) | Documented in spec FR-005 as acceptable best-effort design |
| M2 | Observability: "vice" stage emits no events (STAGE_EVENT_TYPES missing entry) | Added to plan T2: VICE_COMPLETE constant + STAGE_EVENT_TYPES + ALL_EVENT_TYPES + STAGE_FIELDS |
| M3 | `_extract_last_exchange` not directly unit-tested | Added TestExtractLastExchange to plan T1 |
| M4 | Missing `chapter` kwarg assertion in `test_vice_stage_calls_service` | Added to plan T1 |
| M5 | Field description missing rollback instruction | Fixed: plan T2 step 1 includes `Rollback: VICE_PIPELINE_ENABLED=false` |

### LOW (deferred — no functional impact)

| ID | Finding | Resolution |
|----|---------|------------|
| L1 | `"agent"` role check in `_extract_last_exchange` (voice normalizes before storage) | Kept as defensive programming; no functional impact |
| L2 | UniqueConstraint missing from SQLAlchemy model (pre-existing gap) | Deferred — constraint exists in DB; not required for this spec |
| L3 | Deployment docs don't list VICE_PIPELINE_ENABLED | Deferred to PR-13 (docs sync PR) |

---

## Implementation Scope (Final)

### Files to create
- `nikita/pipeline/stages/vice.py`
- `tests/pipeline/stages/test_vice_stage.py`
- `tests/config/test_vice_setting.py`

### Files to modify
- `nikita/config/settings.py` — add `vice_pipeline_enabled`
- `nikita/pipeline/orchestrator.py` — insert ViceStage; stages_total 10→11
- `nikita/pipeline/models.py` — stages_total default 10→11
- `nikita/observability/types.py` — VICE_COMPLETE + STAGE_EVENT_TYPES + ALL_EVENT_TYPES
- `nikita/observability/snapshots.py` — STAGE_FIELDS["vice"] = []

### Out of scope
- ViceAnalyzer, ViceScorer, ViceService internals
- Voice path (pipeline covers both text + voice)
- {{ vices }} template (already correct; stage updates DB, next run reads it)

---

## AC Verification Plan

| AC | Test | Status |
|----|------|--------|
| AC-001 | `test_vice_stage_position` (STAGE_DEFINITIONS inspection) | Ready |
| AC-002 | `test_vice_stage_calls_service` (AsyncMock + chapter kwarg) | Ready |
| AC-003 | `test_vice_stage_flag_disabled` | Ready |
| AC-004 | `test_vice_stage_failure_non_fatal` (execute() not _run()) | Ready |
| AC-005 | `test_vice_stage_insufficient_messages` | Ready |
| AC-006 | `test_vice_flag_setting_default` (required Settings kwargs) | Ready |
