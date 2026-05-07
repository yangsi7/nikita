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
