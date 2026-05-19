# Spec 041: Gap Remediation

**Status**: IN_PROGRESS
**Created**: 2026-01-30
**Updated**: 2026-01-30

## Overview

Address 29 gaps identified in deep audit:
- 7 P0 (Critical): Security + Voice infrastructure
- 11 P1 (High): Pipeline + Performance + Integration
- 11 P2 (Medium): Quality + Documentation

## Gap Summary

### P0 (Critical) - 7 gaps

| ID | Gap | Status | Fix |
|----|-----|--------|-----|
| P0-1 | Voice Call Logging | VERIFIED_DONE | Uses `conversations` table with `platform='voice'` |
| P0-2 | Admin JWT Enforcement | DONE | Wired `get_current_admin_user` from auth.py |
| P0-3 | Error Logging Infrastructure | DONE | Added global exception handler in main.py |
| P0-4 | Transcript LLM Extraction | DONE | Implemented Pydantic AI agent in transcript.py |
| P0-5 | Onboarding DB Operations | VERIFIED_DONE | `_persist_profile_to_db` calls repository |
| P0-6 | Meta-prompts Tracking | VERIFIED_DONE | GeneratedPrompt model + repository implemented |
| P0-7 | Graphiti Thread Loading | VERIFIED_DONE | `get_open_threads` in thread_repository.py |

### P1 (High) - 11 gaps

| ID | Gap | Status | Notes |
|----|-----|--------|-------|
| P1-1 | Orchestrator Refactor | PENDING | 11 stage classes exist, need wiring |
| P1-2 | /admin/pipeline-health | VERIFIED_DONE | Endpoint exists in admin.py |
| P1-3 | Thread Resolution Logging | PENDING | Add error log with thread_id |
| P1-4 | Integration Tests | PENDING | Add pipeline integration tests |
| P1-5 | Spec 037 TD-1 Docs | PENDING | Update CLAUDE.md + architecture.md |
| P1-6 | Pydantic AI UsageLimits | PENDING | Add usage tracking |
| P1-7 | Neo4j Batch Operations | PENDING | Add bulk operations |
| P1-8 | Token Estimation Cache | PENDING | Cache token counts |
| P1-9 | Emotional State Integration | PENDING | Wire to touchpoints engine |
| P1-10 | Conflict System Integration | PENDING | Wire to touchpoints engine |
| P1-11 | Social Circle Backstory | VERIFIED_DONE | Backstory field in SocialCircleMember |

### P2 (Medium) - 11 gaps

| ID | Gap | Status | Notes |
|----|-----|--------|-------|
| P2-1 | Fix Test Collection Errors | PENDING | 149 test collection errors |
| P2-2 | CLAUDE.md Sync | VERIFIED_DONE | context/CLAUDE.md up to date |
| P2-3 | mypy Strict Mode | PENDING | Add type hints |
| P2-4 | E2E Automation | PENDING | CI/CD config |
| P2-5 | Deprecated Code Cleanup | PENDING | Remove nikita/prompts/ |
| P2-6 | Admin UI Polish | PENDING | Portal improvements |
| P2-7-11 | Various cleanup | PENDING | As identified |

## Implementation Phases

### Phase 1: Security + Voice (Days 1-4) - MOSTLY COMPLETE
- [x] T1.1: Wire Admin JWT (P0-2) - 10 min
- [x] T1.2: Wire Error Logging (P0-3) - 2-3h
- [x] T1.3: Verify Voice Call Logging (P0-1) - Already done
- [x] T1.4: Transcript LLM Extraction (P0-4) - 4-6h
- [x] T1.5: Verify Onboarding DB Ops (P0-5) - Already done
- [x] T1.6: Verify Meta-prompts Tracking (P0-6) - Already done
- [x] T1.7: Verify Graphiti Thread Loading (P0-7) - Already done

### Phase 2: Pipeline + Performance (Days 5-9) - PENDING
- [ ] T2.1: Orchestrator Refactor (P1-1)
- [ ] T2.2: Verify /admin/pipeline-health (P1-2)
- [ ] T2.3: Thread Resolution Logging (P1-3)
- [ ] T2.4: Integration Tests (P1-4)
- [ ] T2.5: Spec 037 TD-1 Docs (P1-5)
- [ ] T2.6: Pydantic AI UsageLimits (P1-6)
- [ ] T2.7: Neo4j Batch Operations (P1-7)
- [ ] T2.8: Token Estimation Cache (P1-8)
- [ ] T2.9: Emotional State Integration (P1-9)
- [ ] T2.10: Conflict System Integration (P1-10)
- [x] T2.11: Verify Social Circle Backstory (P1-11)

### Phase 3: Quality + Docs (Days 10-12) - PENDING
- [ ] T3.1: Fix Test Collection Errors (P2-1)
- [x] T3.2: Verify CLAUDE.md Sync (P2-2)
- [ ] T3.3: mypy Strict Mode (P2-3)
- [ ] T3.4: E2E Automation (P2-4)
- [ ] T3.5: Deprecated Code Cleanup (P2-5)
- [ ] T3.6: Admin UI Polish (P2-6)

## Acceptance Criteria

- [ ] All 29 gaps addressed or explicitly deferred with reason
- [ ] Spec 037 upgraded from CONDITIONAL PASS to PASS
- [ ] 0 test collection errors
- [ ] All documentation synchronized

## Dependencies

- Spec 037 (Pipeline Refactor) - T2.1 completes orchestrator
- Spec 039 (Unified Context Engine) - Already at 100% v2 traffic

## Test Evidence

Phase 1 Tests (implemented):
- `tests/agents/voice/test_transcript.py::TestLLMFactExtraction` - 3 tests
- `tests/api/routes/test_admin*.py` - 107 tests
- `tests/api/dependencies/test_error_logging.py` - 10 tests
- `tests/context_engine/` - 326 tests

## References

- [Deep Audit Report](../../docs-to-process/20260130-deep-audit-report.md)
- [Spec 037 Audit](../037-pipeline-refactor/audit-report.md)
- [Spec 039 Context Engine](../039-unified-context-engine/)
