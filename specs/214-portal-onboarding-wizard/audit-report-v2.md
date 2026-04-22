# Audit Report — Spec 214 FR-11d v2

**Feature:** Spec 214 FR-11d Chat-First Slot-Filling Variant
**Date:** 2026-04-23
**Branch:** `master` (post-PR-#398 merge at `6119b26`)
**Artifacts audited:** `spec.md` (FR-11d lines 654-810), `plan-v2.md`, `tasks-v2.md`, `validation-findings.md`, `.claude/rules/agentic-design-patterns.md`
**Result:** **PASS** (0 CRITICAL, 0 HIGH; 2 MEDIUM addressed via tasks-v2 amendment, 2 LOW)

## Executive Summary

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 2 (both addressable via tasks-v2 patch — see remediation) |
| LOW | 2 |

GATE 2 PASS achieved (PR #398 merged). All Walk-V-driven anti-patterns have spec-level remediation with named tests + grep gates. PR splitting fits ≤400 LOC budget per `pr-workflow.md`. Two MEDIUM findings concern test enumeration gaps in `tasks-v2.md` (driver ACs covered in plan-v2.md §3.3 but not lifted into tasks). Recommend tasks-v2 amendment before `/implement` invocation.

## Findings Table

| # | Category | Severity | Location | Issue | Remediation |
|---|---|---|---|---|---|
| 1 | Coverage gap | MEDIUM | `tasks-v2.md` T3 | AC-11d.2 (monotonic progress) lacks an explicit enumerated task. T2 implements `WizardSlots.progress_pct` but no test class is named at the task layer. Plan-v2 §3.3 calls out `TestConverseMonotonicProgress` but tasks-v2 doesn't surface it. | Extend T3 in tasks-v2.md to enumerate `TestConverseMonotonicProgress` (turn-by-turn progress never regresses) as part of T3's RED test suite. |
| 2 | Coverage gap | MEDIUM | `tasks-v2.md` T3+T4 | AC-11d.8 GET-side tests (`test_get_conversation_returns_link_after_completion`, `test_get_conversation_signals_link_expired_after_ttl`, `test_get_conversation_never_mints_code`) implicit in T4 wiring but not explicit at task layer. | Extend T3 in tasks-v2.md to enumerate the 3 GET-side tests as part of RED phase; T4 wiring (extending `ConversationProfileResponse`) already covers GREEN. |
| 3 | Risk | LOW | `plan-v2.md` §4 | PR splitting estimates PR-A ~350-400 LOC + PR-B ~350-400 LOC. Marginal headroom against 400-LOC limit. | Monitor diff size during T11 implementation; split T12 (FE wire-up) into a separate PR-C if PR-B exceeds. |
| 4 | Convention drift | LOW (DONE) | `tasks-v2.md` | Agentic-flow test class names from `.claude/rules/testing.md` "Agentic-Flow Test Requirements" (cumulative-state monotonicity, completion-gate triplet, mock-LLM-emits-wrong-tool recovery). | DONE — tasks-v2.md "Agentic-Flow Test Class Mapping" footer maps each of the 3 mandatory classes to its task (T3+T7 → cumulative monotonicity; T1+T3 → completion-gate triplet; T10 → mock-LLM-recovery). |

## Cross-Artifact Consistency Checks

### Check 1: Every AC-11d.N (1-10) maps to ≥1 task

| AC | Mapped Tasks | Status |
|---|---|---|
| AC-11d.1 (cumulative state read) | T2, T7, T8 | ✓ |
| AC-11d.2 (monotonic progress) | T2 (impl) | **GAP** — no explicit test task; see Finding #1 |
| AC-11d.3 (Pydantic completion gate) | T1, T2, T3, T4 | ✓ |
| AC-11d.4 (regex fallback) | T5, T6, T10, T11 | ✓ |
| AC-11d.5 (tool consolidation OR dynamic instructions) | T10, T11 | ✓ |
| AC-11d.6 (agent invocation contract) | T10, T11 | ✓ |
| AC-11d.7 (terminal-turn wire format) | T3, T4, T12 | ✓ |
| AC-11d.8 (GET reload + re-mint) | T4 (impl), T12 (FE) | **GAP** — GET tests implicit; see Finding #2 |
| AC-11d.9 (perf budget) | T9 | ✓ |
| AC-11d.10 (elision boundary) | T7, T8 | ✓ |

### Check 2: Every task in tasks-v2.md cites a driver AC

PASS. Every row in the tasks-v2 table has a "Driver AC" column populated with at least one AC-11d.N.

### Check 3: CRITICAL/HIGH from validation-findings disposition

| Finding | Disposition | Verified |
|---|---|---|
| API C1 (ConverseResponse extra=forbid + field name) | RESOLVED iter-1 (commit 72e06d6, now on master) | ✓ |
| API H1 (grep gate `_compute_progress`) | RESOLVED iter-1 | ✓ AC-11d.3 includes the second grep |
| API H2 (GET reload after completion) | RESOLVED iter-1 (AC-11d.8 added) | ✓ |
| Frontend C (TS type missing link_code/expires_at) | ACCEPTED as Phase 3 task; Spec Phase 3 Notes makes it PR-blocker | ✓ Mapped to T12 in tasks-v2 |
| Frontend H (no FE re-mint code path) | ACCEPTED as Phase 3 task; Spec Phase 3 Notes makes it PR-blocker | ✓ Mapped to T12 in tasks-v2 |

### Check 4: All 6 hard rules from `.claude/rules/agentic-design-patterns.md` reflected in spec ACs + tests

| Hard Rule | Spec AC | Test in tasks-v2 |
|---|---|---|
| 1. Cumulative server-side state | AC-11d.1, AC-11d.10 | T2, T7, T8 ✓ |
| 2. Pydantic completion gate (no booleans, no LLM-judge) | AC-11d.3 | T1, T2, T3, T4 ✓ |
| 3. Tool consolidation OR dynamic instructions | AC-11d.5 | T10, T11 ✓ |
| 4. Progress = `@computed_field` of cumulative state | AC-11d.2 | T2 impl; **explicit test gap** (Finding #1) |
| 5. Validation layering (pre-tool + post-tool + deterministic post-processing) | AC-11d.4 | T5, T6, T10, T11 ✓ |
| 6. `message_history=` official primitive | AC-11d.6 | T10, T11 ✓ |

### Check 5: PR splitting ≤400 LOC

PR-A: 3 NEW production files (`state.py`, `state_reconstruction.py`, `regex_fallback.py`) + 4 NEW test files (`test_wizard_state.py`, `test_state_reconstruction.py`, `test_state_reconstruction_perf.py`, `test_regex_fallback.py`) + 1 EXTENDED test file (`test_converse_endpoint.py`) + 2 refactored production files (`portal_onboarding.py`, `converse_contracts.py`). Estimated ~350-400 LOC. ✓ (margin tight; see Finding #3)
PR-B: 2 refactored production files (`conversation_agent.py`, `conversation_prompts.py`) + 1 NEW test file (`test_dynamic_instructions.py`) + 1 EXTENDED test file (`test_conversation_agent.py`) + 2 FE files (`converse.ts`, `onboarding-wizard.tsx`). Estimated ~350-400 LOC. ✓ (margin tight; see Finding #3)

## Constitution Compliance

| Article | Rule | Compliance |
|---|---|---|
| I | Intelligence-First (research before implement) | ✓ Phase 0 governance + 3-stream research synthesis prior to spec amendment |
| II | Evidence-Based (CoD^Σ) | ✓ AC-11d.3 + AC-11d.8 grep gates are falsifiable; AC-11d.9 micro-bench is empirical |
| III | Test-First (TDD) | ✓ tasks-v2 alternates RED/GREEN per task; PR workflow rule mandates 2 commits per task |
| IV | Specification-First | ✓ Spec amendment landed via PR #398 BEFORE plan/tasks; no implementation files touched yet |
| V | Template-Driven | ✓ Spec follows existing FR-N format; plan-v2 follows plan-v16 structure |
| VI | Simplicity | ✓ Reuses existing JSONB persistence, no DB migration, no new tables; pydantic-graph deferred per spec §11 |
| VII | User-Story-Centric | ✓ FR-11d ties to existing US-1 (chat-first happy path); legacy US still served by FR-1 behind flag |

## Implementation Readiness

| Gate | Status |
|---|---|
| GATE 1: spec.md exists with no `[NEEDS CLARIFICATION]` markers | ✓ PASS |
| GATE 2: 6/6 validators ran, 0 outstanding CRITICAL/HIGH at spec layer | ✓ PASS |
| GATE 3: plan + tasks generated | ✓ PASS (plan-v2.md + tasks-v2.md) |
| GATE 4 (this audit): cross-artifact consistency | ✓ PASS with 2 MEDIUM remediations recommended below |
| User approval to proceed to Phase 8 (/implement) | Pending |

## Recommended Remediation Before `/implement`

1. **Patch tasks-v2.md T3** to enumerate `TestConverseMonotonicProgress` (Finding #1 fix)
2. **Patch tasks-v2.md T3** to enumerate the 3 GET-side AC-11d.8 tests (Finding #2 fix)
3. **Optional**: add agentic-flow test classes mapping footer to tasks-v2.md (Finding #4)
4. **Monitor** PR-B diff size during T11; pre-commit `git diff --stat` after each task to flag if PR-B exceeds 400 LOC, in which case split T12 into PR-C

After remediations: PASS, ready for Phase 8 (`/implement`).

## Pass/Fail Determination

**PASS.** No CRITICAL, no HIGH. Two MEDIUM findings are coverage gaps in tasks-v2 that surface tests already named in plan-v2 — addressable via a 5-line tasks-v2 patch. Two LOW findings are advisory.

GATE 4 (this audit) closed: PASS. Proceed to Phase 8 with the tasks-v2 patches applied.
