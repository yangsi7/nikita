# Validation Findings — Spec 217 Onboarding Wizard Deterministic-Track Redesign

**Spec ID**: 217-onboarding-wizard-deterministic-redesign
**GATE**: 2 (Spec Review)
**Date**: 2026-05-07
**Status**: PARTIAL — structural cross-check ONLY. Full GATE 2 validator dispatch deferred to orchestrator main thread.

---

## Important Note

GATE 2 mandates 6 parallel `Task(subagent_type=sdd-*-validator)` invocations per CLAUDE.md SDD Enforcement #3. This spec was authored by a worktree-isolated subagent under a 50 tool-call dispatch-cap budget. Spawning 6 nested validator subagents from within this run would exceed the cap and break the worktree-safety boundary.

**This file therefore records a STRUCTURAL CROSS-CHECK only** (FR ↔ AC ↔ tasks ↔ verification ↔ subspec coherence). The orchestrator MUST dispatch the 6 validators from main thread before any `/implement` invocation.

The 6 mandatory validators (per `~/.claude/skills/sdd/phases/04.5-spec-review.md`) are listed below for the orchestrator's reference.

---

## Validators to Dispatch (orchestrator action)

| Validator | Dispatch | Status |
|---|---|---|
| sdd-spec-completeness-validator | `Task(subagent_type="sdd-spec-completeness-validator", prompt="Validate specs/217-onboarding-wizard-deterministic-redesign/spec.md...")` | DEFERRED |
| sdd-spec-clarity-validator | same | DEFERRED |
| sdd-spec-testability-validator | same | DEFERRED |
| sdd-spec-feasibility-validator | same | DEFERRED |
| sdd-spec-consistency-validator | same | DEFERRED |
| sdd-spec-traceability-validator | same | DEFERRED |

(Exact validator names may differ — orchestrator should consult `~/.claude/agents/` directory for the canonical list.)

---

## Pre-validator Structural Cross-Check (this run)

### Section 1: Functional-requirement coverage

| Requirement type | Count | Met? |
|---|---|---|
| FRs declared | 15 (FR-1 through FR-15 incl. 4a/4b/4c, 10a/10b) | ≥3 PASS |
| User stories | 7 | ≥1 per FR cluster PASS |
| ACs per US | min 4, max 6 | ≥2 PASS |
| NFRs | 7 | reasonable |
| Open questions | 0 blocking | clean |

### Section 2: Traceability

Each FR is traced to (a) a sub-PR slug, (b) a user story, (c) at least one AC, (d) a verification R-tier, (e) a Reuse-Map row in plan.md. Spot-checked all 15 FRs — PASS.

### Section 3: Testability

Every AC names a falsifiable check:
- Playwright text/locator assertions (AC-1.x, AC-2.x, AC-3.x)
- DOM tree shape assertions via `parentNode === parentNode` (AC-3.3)
- vitest behavior assertions (AC-5.5, AC-6.4)
- pytest isinstance checks (AC-5.1)
- Structured log greps (AC-4.4)

No vague language ("works correctly", "is robust") — PASS.

### Section 4: Consistency with project rules

- `agentic-design-patterns.md` 6 hard rules — addressed in NFR-3 + FR-5/6/7/8/9 PASS
- `live-testing-protocol.md` walk protocol + anti-fabrication — addressed in NFR-7 PASS
- `pr-workflow.md` ≤400 LOC + pre-push HARD GATE — addressed in NFR-2 + Constraints PASS
- `parallel-agents.md` dispatch caps — addressed in Constraints PASS
- `feedback_no_real_users_no_migration_ceremony.md` — addressed in Constraints PASS

### Section 5: Cross-spec consistency

- Spec 216 master + 216-A/D/E/F/G/H preserved (Out of Scope) PASS
- 216-B + 216-C explicitly superseded with banner application required (subspecs/216-{B,C}/spec.md edits) PASS
- Spec 215 FR-6 preserved — interstitial route stays PASS

### Section 6: Subspec coherence

5 subspecs created at `subspecs/217-{0,1,2,3A,3B}-<slug>/{spec,plan,tasks,audit-report}.md` (24 files). Each:
- Contains a Scope clause naming the sub-PR slug + estimated LOC.
- Lists ACs that subset the master ACs.
- Lists files-touched within the Reuse Map.
- Carries a per-sub-PR audit-report.md verdict.

PASS.

### Section 7: ROADMAP-217 registration

PASS — entry added during this authoring run (row 147 of ROADMAP.md).

---

## Open Findings (raised by structural cross-check)

| ID | Severity | Finding | Owner | GH issue |
|---|---|---|---|---|
| 217-VAL-001 | MEDIUM | GATE 2 validators not yet dispatched | orchestrator | (file post-dispatch if any new findings) |
| 217-VAL-002 | LOW | 217-3A LOC budget at risk if all 7 FRs land in one PR | 217-3A implementor | (track via mid-flight `git diff --stat`) |
| 217-VAL-003 | LOW | 217-0c hygiene action ambiguous — PR #538 keeps `/onboarding/auth/` as 410 GONE stub with `delete-after 2026-06-06` | 217-0 implementor | (verify with user before deletion) |

No CRITICAL or HIGH findings.

---

## User Approval

- [ ] User has reviewed this file and approves proceeding to Phase 5 (`/plan`) → already executed; conditional approval to `/implement` after GATE 2 validators dispatch returns 0 CRITICAL/HIGH.

---

## References

- `~/.claude/skills/sdd/phases/04.5-spec-review.md` — GATE 2 protocol
- `~/.claude/skills/sdd/phases/07-audit.md` — Phase 7 audit protocol
- CLAUDE.md SDD Enforcement #3, #7, #8
- Auto-memory: `feedback_planning_quality.md`

---

## GATE 2 Validator Dispatch Results (2026-05-07, orchestrator main thread)

**6 parallel `Task(subagent_type=sdd-*-validator)` calls executed against worktree-isolated spec set.**

**Aggregate verdict: PASS-CONDITIONAL — 0 CRITICAL, 0 HIGH, 15 MEDIUM, 5 LOW.**

### Per-validator summary

| Validator | Verdict | CRIT | HIGH | MED | LOW |
|---|---|---|---|---|---|
| sdd-api-validator | PASS-CONDITIONAL | 0 | 0 | 3 | 0 |
| sdd-architecture-validator | PASS | 0 | 0 | 2 | 0 |
| sdd-auth-validator | PASS-CONDITIONAL | 0 | 0 | 3 | 0 |
| sdd-data-layer-validator | PASS-CONDITIONAL | 0 | 0 | 3 | 2 |
| sdd-frontend-validator | PASS-CONDITIONAL | 0 | 0 | 2 | 3 |
| sdd-testing-validator | PASS-CONDITIONAL | 0 | 0 | 2 | 0 |
| **TOTAL** | | **0** | **0** | **15** | **5** |

### MEDIUM findings (require user decision per CLAUDE.md SDD #7c)

| ID | Validator | Sub-PR | Finding |
|---|---|---|---|
| 217-VAL-API-M1 | api | 217-3A | Spec describes /answer dispatch response shapes in PROSE only; no named Pydantic response_model classes (`AnswerResponse = ReactionResponse \| FollowUpResponse \| FieldErrorResponse \| TurnFailureResponse`). FastAPI/OpenAPI surface drift risk. Recommend AC-9.1bis: declare discriminated-union Pydantic response envelope with `kind: Literal[...]` discriminator. |
| 217-VAL-API-M2 | api | 217-2 | `asyncio.wait_for(..., timeout=20.0)` falls through to `except Exception` returning default cards — but no HTTP status code spec (200 with `degraded: true` flag? 503 with Retry-After?). Add observability marker so FE can warn-log without UX breakage. |
| 217-VAL-API-M3 | api | 217-3A | Spec relies on existing `(user_id, turn_id)` idempotency at portal_onboarding.py:1846-1851 but does not re-assert idempotency for new IdentityPair compound slot. Add explicit AC for replay-with-same-body returns identical payload. |
| 217-VAL-ARCH-M1 | architecture | 217-3A | `pending_followup` JSONB key namespace not audited against existing `onboarding_profile` shape. Add one-line note confirming key namespace clean. |
| 217-VAL-ARCH-M2 | architecture | 217-3A | `hydrate_message_history` reuse from `nikita/agents/onboarding/message_history.py:44` cited in agentic-design-patterns.md but NOT in 217-3A's Files Touched / Pydantic AI Primitives table. Add explicit "REUSE" row. |
| 217-VAL-AUTH-M1 | auth | 217-1 | AC-2.6 JWT-cookie-persists assertion lacks failure-mode falsifier. Add: (a) cookie present in browser jar BEFORE router.push, (b) negative iOS-UA test asserting NO auto-advance fires. |
| 217-VAL-AUTH-M2 | auth | 217-1 | AC-2.4 says "userAgent() from next/server OR next/headers" — these are different APIs (middleware vs RSC). Pick one + cite it. Ambiguity invites client-only window.navigator regression. |
| 217-VAL-AUTH-M3 | auth | 217-1 | AC-1.4 stops at "Nikita first reply within 5s" — should add assertion that bot-side branch invoked is the `welcome` payload handler (216-A AC A1.1+A1.2), not generic /start fallback. |
| 217-VAL-DATA-M1 | data-layer | 217-3A | AC-8.2 "cleared by setting null on followup resolution" — semantics ambiguous between SQL NULL JSONB key vs JSON null literal. Specify: `jsonb_set(..., 'null'::jsonb)` OR `#-` operator removal. |
| 217-VAL-DATA-M2 | data-layer | 217-3A | Cross-device resume / page-reload behavior with `pending_followup` undefined. Either explicitly defer (like FR-4c) OR enumerate /state shape addition. |
| 217-VAL-DATA-M3 | data-layer | 217-3A | AC-8.3 monotonicity test addresses progress_pct only; does not assert AgentEmissionState.pending_followup transitions (set→cleared) leave WizardSlots untouched on same turn. Add explicit invariant assertion. |
| 217-VAL-FE-M1 | frontend | 217-1 | AC-2.1/2.2 tap-anywhere overlay does not explicitly require `role="button"` + keyboard activation (Enter/Space). Add: tap surface MUST render as native `<button>` OR carry `role="button"` + `tabindex=0` + Enter/Space onKeyDown. |
| 217-VAL-FE-M2 | frontend | 217-1, 217-3B | No explicit responsive-breakpoint requirements (sm/md/lg) for new components. Sibling DOM layout on mobile vs desktop unspecified. Add breakpoint specifications + touch-target ≥44px. |
| 217-VAL-TEST-M1 | testing | 217-3A | Spec lists NEW test files but does NOT explicitly direct extending existing 216-B baseline tests at `tests/agents/onboarding/test_{cumulative_state,completion_gate,tool_recovery}.py` for ReactionOnly\|FollowUpQuestion union. Risk: stale duplicate coverage. Add "EXTEND existing 216-B tests" clause OR mark 216-B tests deprecated-and-replaced. |
| 217-VAL-TEST-M2 | testing | 217-2 | FR-4a 3-5s fallback timer + AC-T.1 vitest spec silent on fake-timers strategy. Real wall-clock would slow tests by 3-5s each. Require `vi.useFakeTimers()` (vitest); if Playwright e2e added, require `page.clock.install()` + `fastForward(3000)`. |

### LOW findings (logged, non-blocking per `.claude/rules/issue-triage.md`)

| ID | Validator | Sub-PR | Finding |
|---|---|---|---|
| 217-VAL-DATA-L1 | data-layer | 217-3A | `db/models/user.py` JSONB-no-migration confirmed via project_users_table_schema.md. Acknowledged. |
| 217-VAL-DATA-L2 | data-layer | 217-2 | FR-4c DEFERRED OPTIONAL handling appropriate; backwards-compatible. |
| 217-VAL-FE-L1 | frontend | 217-3B | EASE_OUT_QUART easing not explicitly named in 217-3B AnimatePresence requirement (Spec 208 mandates it). |
| 217-VAL-FE-L2 | frontend | 217-2 | Alert retry copy not specified verbatim → em-dash absence + i18n consideration unauditable at PR time. |
| 217-VAL-FE-L3 | frontend | 217-3B | AC-12.4 "input" definition could disambiguate text-inputs vs CTA buttons. |

### Aggregate verdict

**0 CRITICAL, 0 HIGH** — gate is NOT blocked per CLAUDE.md SDD #7b.

**15 MEDIUM** — per CLAUDE.md SDD #7c: "create GH issue or document as accepted". User decides per-finding.

**5 LOW** — logged here, non-blocking per `issue-triage.md`.

### Path forward (user decides)

Per CLAUDE.md SDD Enforcement #7e: "user approves proceeding to Phase 5". Three options:

1. **Accept all 15 MEDIUMs as documented + proceed to Step 5.1** (`/implement 217-0`). Document accepted MEDIUMs in spec amendments OR file as GH issues for Spec 217 backlog. 217-0 is FE-only test cleanup — none of the MEDIUMs touch its scope, so proceeding is safe.

2. **Fix some/all MEDIUMs in spec NOW + re-validate** (max 3 GATE 2 iterations per CLAUDE.md SDD #7f). Highest-leverage MEDIUMs: API-M1 (response_model), DATA-M1 (null cleanup), AUTH-M2 (userAgent API). Estimated +30 min spec amendments + 1 validator round.

3. **File MEDIUMs as GH issues + proceed**. Each MEDIUM gets a `gh issue create --label "bug,spec-217"` for tracking; implementor consults issues during their sub-PR.

