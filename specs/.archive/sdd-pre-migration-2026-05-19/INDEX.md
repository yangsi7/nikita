# Spec Directory Index

**Generated**: 2026-05-03 (Wave 1A doc-cleanup)
**Source of truth**: filesystem (`specs/[0-9]*-*/`) cross-referenced with `ROADMAP.md` rows + recent git log.
**Spec dir count**: 85 (numeric-prefixed dirs in `specs/`).
**Archived dirs**: `specs/archive/` holds superseded specs with full artifact preservation (e.g., 037, 081).

> Status legend
> - **implemented** — code shipped, audit-report PASS, on master
> - **active** — in-flight authoring or implementation; partial PR shipped
> - **planned** — registered in ROADMAP but no spec.md/code yet
> - **superseded** — replaced by a successor spec; spec.md retained for traceability
> - **partial** — pre-SDD or partial artifacts; no full audit-report.md
> - **draft** — spec.md in DRAFT; pending GATE 2 validators
> - **abandoned** — explicitly dropped (none currently)
> - **unknown** — not classified by Wave 1A; Wave 1B / SPEC_INVENTORY rebuild fills

## Number-collision history (Wave 1A 2026-05-03)

| Old ID | Old slug | New ID | Reason |
|---|---|---|---|
| 210 | kill-skip-variable-response | 210A | Number-prefix collision with 210-test-quality-audit. Suffix added. Driver: GH #210 (MERGED b0f7e7a, variable-response half only — kill-half deferred to Wave 1B HOTFIX GH issue). |
| 210 | test-quality-audit | 210B | Number-prefix collision (sibling to 210A). PLANNED, no PR yet. |
| 215 | auth-flow-redesign | 215A | Number-prefix collision with 215-heartbeat-engine. Auth-flow renamed (DRAFT v1); heartbeat retained as `215` per merged-PR commit-message preservation policy. |

Hook regex `.claude/hooks/session-start.sh:31` extended to `^\| [0-9]{3}[A-Z]?` in the same Wave 1A PR — required to prevent silent under-count of suffixed specs by `sort -u`.

## Index

| # | Name | Status | Driver PR(s) | Notes |
|---|---|---|---|---|
| 001 | nikita-text-agent | implemented | (pre-SDD batch) | Pydantic AI text agent foundation |
| 002 | telegram-integration | implemented | (pre-SDD) | aiogram 3.x webhook |
| 003 | scoring-engine | implemented | (pre-SDD) | 4 metrics, 60 tests |
| 004 | chapter-boss-system | implemented | (pre-SDD) | Boss scoring, 5 chapters, 142 tests |
| 005 | decay-system | implemented | (pre-SDD) | 0.8-0.2/hr rates, 52 tests |
| 006 | vice-personalization | implemented | (pre-SDD) | 81 tests |
| 007 | voice-agent | implemented | (pre-SDD) | ElevenLabs Conv AI 2.0, 186 tests |
| 008 | player-portal | implemented | (pre-SDD) | Initial portal, 50/50 tasks |
| 009 | database-infrastructure | implemented | (pre-SDD) | Supabase + pgVector + RLS |
| 010 | api-infrastructure | implemented | (pre-SDD) | FastAPI + Cloud Run |
| 011 | background-tasks | implemented | (pre-SDD) | pg_cron + 5 initial jobs |
| 012 | context-engineering | implemented | (pre-SDD) | Phase 4 integration |
| 013 | configuration-system | implemented | (pre-SDD) | Pydantic settings, 89 tests |
| 014 | engagement-model | implemented | (pre-SDD) | 6 states, 179 tests |
| 015 | onboarding-fix | implemented | (pre-SDD) | OTP flow |
| 016 | admin-debug-portal | implemented | (pre-SDD) | 8 tests |
| 017 | enhanced-onboarding | superseded | — | Superseded by 028 voice-onboarding |
| 018 | admin-prompt-viewing | implemented | (pre-SDD) | Prompt inspection |
| 019 | admin-voice-monitoring | implemented | (pre-SDD) | 5 endpoints, 21 tests |
| 020 | admin-text-monitoring | implemented | (pre-SDD) | 6 endpoints, 29 tests |
| 021 | hierarchical-prompt-composition | implemented | (pre-SDD) | 6-layer composition, 345 tests |
| 022 | life-simulation-engine | implemented | (pre-SDD) | Daily life events, 212 tests |
| 023 | emotional-state-engine | implemented | (pre-SDD) | 4D mood model, 233 tests |
| 024 | behavioral-meta-instructions | implemented | (pre-SDD) | 166 tests |
| 025 | proactive-touchpoint-system | implemented | (pre-SDD) | 189 tests |
| 026 | text-behavioral-patterns | implemented | (pre-SDD) | 167 tests; AC-5.x superseded by 210A |
| 027 | conflict-generation-system | implemented | (pre-SDD) | 263 tests |
| 028 | voice-onboarding | implemented | (pre-SDD) | Supersedes 017; 230 tests |
| 029 | context-comprehensive | implemented | (pre-SDD) | 31 tasks |
| 030 | text-continuity | implemented | (pre-SDD) | 111 tests |
| 031 | post-processing-unification | implemented | (pre-SDD) | 16/17 tasks |
| 032 | voice-agent-optimization | implemented | (pre-SDD) | 94 tests |
| 033 | unified-phone-number | implemented | (pre-SDD) | 29 tests |
| 034 | admin-user-monitoring | implemented | (pre-SDD) | 64 tests |
| 035 | context-surfacing-fixes | implemented | (pre-SDD) | 120 tests |
| 036 | humanization-fixes | implemented | (pre-SDD) | 26 tests |
| 038 | conversation-continuity | implemented | (pre-SDD) | 6/11 tasks |
| 039 | unified-context-engine | implemented | (pre-SDD) | 231 tests |
| 040 | context-engine-enhancements | implemented | (pre-SDD) | 326 tests |
| 041 | gap-remediation | implemented | (pre-SDD) | 22/24 tasks |
| 042 | unified-pipeline | implemented | (pre-SDD) | 45/45 tasks, 3,797 tests; supersedes 037 (archived) |
| 043 | integration-wiring | implemented | (pre-SDD) | 11 tasks |
| 044 | portal-respec | implemented | (pre-SDD) | 94 files, 19 routes, Next.js 16 |
| 046 | portal-emotional-intelligence | implemented | (pre-SDD) | MoodOrb, life event feed |
| 047 | portal-deep-insights | implemented | (pre-SDD) | Score chart, trajectory |
| 048 | e2e-full-lifecycle | implemented | (pre-SDD) | 16 phases, 4 bugs fixed |
| 049 | game-mechanics-remediation | partial | (pre-SDD) | Boss/grace fixes; no full audit-report |
| 050 | portal-fixes | partial | (pre-SDD) | Pre-SDD patches |
| 055 | life-simulation-enhanced | implemented | (pre-SDD) | 22 tasks, 33 tests |
| 056 | psyche-agent | implemented | (pre-SDD) | 25 tasks, batch job, 163 tests |
| 057 | conflict-system-core | implemented | (pre-SDD) | 20 tasks, 167 tests |
| 058 | multi-phase-boss | implemented | (pre-SDD) | OPENING→RESOLUTION, PARTIAL outcome, 117 tests |
| 059 | portal-nikita-day | implemented | (pre-SDD) | 12 tasks, psyche-tips endpoint, 5 tests |
| 060 | prompt-caching | implemented | (pre-SDD) | 11 tasks, Claude prefix caching, 15 tests |
| 061 | portal-resilience | implemented | (pre-SDD) | Error boundaries, a11y |
| 062 | portal-visual-polish | implemented | (pre-SDD) | Framer Motion, mobile nav |
| 063 | portal-data-viz-notifications | implemented | (pre-SDD) | Charts, CSV/JSON export |
| 070 | push-notifications | partial | (pre-SDD) | Push service, Service Worker; partial artifacts |
| 100 | cron-infrastructure-hardening | implemented | (pre-SDD) | Idempotency, concurrency guards |
| 101 | game-mechanics-remediation | implemented | (pre-SDD) | Boss cooldown, grace period |
| 102 | memory-data-integrity | implemented | (pre-SDD) | Batch search, embedding dedup |
| 103 | touchpoint-intelligence | implemented | (pre-SDD) | Life events, dedup |
| 104 | context-engineering-enrichment | implemented | (pre-SDD) | Arcs, thought resolution |
| 105 | schema-cleanup-observability | implemented | (pre-SDD) | Scoring fallback, timings; FR-002 audit-trail unimplemented |
| 107 | process-framework-remediation | partial | (pre-SDD) | Hook portability; spec.md only |
| 108 | voice-agent-optimization | implemented | (pre-SDD) | V3 Conversational, 110 tests; spec.md only |
| 109 | systemic-cleanup | implemented | PR #81 | ConflictStore removal, `@llm_retry`, DI dedup; 13 tests |
| 110 | pipeline-observability | implemented | PR #92 | Phase A: pipeline_events, EventEmitter, Conversation Inspector; 37 tests |
| 111 | consecutive-crises | implemented | (pre-SDD) | Cross-session crisis counter (GH #91); 17 tests |
| 112 | portal-e2e-hardening | implemented | (pre-SDD) | Content assertions, auth bypass, data-testid; 125 tests |
| 113 | voice-post-score | implemented | PR #129 | Boss + crisis hooks for voice path; 7 tests |
| 114 | vice-pipeline | implemented | PR #130 | ViceStage added to pipeline |
| 115 | telegram-rate-limit | implemented | PR #128 | Per-user webhook rate limiting; 17 tests |
| 116 | extraction-checkpoint | implemented | PR #131 | Extraction data survives memory_update failure |
| 117 | configloader-migration | implemented | PR #132 | Engine constants via ConfigLoader |
| 203 | telegram-vice-seeder-bypass | implemented | (pre-SDD) | 4 tests |
| 208 | portal-landing-page-hero | implemented | PR #209 | "Don't Get Dumped" hero landing, deployed 2026-04-03 |
| 210A | kill-skip-variable-response | active | PR #210 | MERGED (b0f7e7a) variable-response half only. Kill-half (skip.py + skip_rates_enabled removal) deferred to Wave 1B HOTFIX GH issue. Renamed from `210` Wave 1A 2026-05-03. |
| 210B | test-quality-audit | planned | — | Audit 5768 tests for empty-mock + zero-assertion (triggered by PR #252 / GH #248). Renamed from `210` Wave 1A. |
| 211 | task-ledger-truth-audit | planned | — | Audit completed-task ledger vs GH issue state + master merges (triggered by PR #253 silently-complete Task #17 discovery) |
| 213 | onboarding-backend-foundation | implemented | PRs 213-1..213-5 | COMPLETE 2026-04-15. contracts.py + tuning.py + adapters.py; migration + ORM; PortalOnboardingFacade + preview endpoint + PII fixes; GET /pipeline-ready + PATCH /profile + FR-14 session isolation; 60+ tests. |
| 214 | portal-onboarding-wizard | active | PRs 214-A/B/C/D + #312/315/317/319/322 + #392-396 | v2 AMENDMENT 2026-04-22 — FR-11d chat-first wizard ADDED (ADR-009). FR-11d superseded by 216-B. Imports Spec 213 contracts. Supersedes 081 (archived). |
| 215 | heartbeat-engine | implemented | PRs #330-342 | PHASE 1 COMPLETE 2026-04-18 (flag-OFF, awaiting flag-flip decision). 9 PRs merged on master ea67c32. 12 pg_cron jobs active. Phase 2 (Hawkes) + Phase 3 (Bayesian) pending separate spec cycles. |
| 215A | auth-flow-redesign | draft | (no PR yet) | DRAFT v1 — Telegram-first signup. Pending GATE 2 validators. Renamed from `215-auth-flow-redesign` Wave 1A 2026-05-03 (collision with 215-heartbeat-engine). Partial supersession by 216-A telegram routing. |
| 216 | onboarding-redesign-cinematic | active | PRs #450/452/457/461/462/464 | IN AUTHORING 2026-04-29; audit FAILED 2026-04-30 (4 CRIT, 8 HIGH, 5 MED) needs re-pass. Master spec.md + 6 subspecs (216-A..216-F). 58 ACs. Supersedes Spec 214 v2 FR-11d + Spec 215A portal-first auth chain. Branch `feat/216-*`. |

## Archive

`specs/archive/` (NOT in count above):

- `037-pipeline-refactor` — superseded by 042 unified-pipeline
- `081-onboarding-redesign-progressive-discovery` — superseded by 214 portal-onboarding-wizard

## Pre-SDD specs (no dir or partial artifacts only)

Per ROADMAP.md "Pre-SDD Specs" list: 045, 051, 052, 064, 065, 066, 067, 068, 069, 106. These are tracked in ROADMAP rows for traceability but lack the four-artifact SDD set (spec.md/plan.md/tasks.md/audit-report.md).

## Wave 1B status (2026-05-03)

- Stale orphans deleted: `specs/SPEC_INVENTORY.md`, `specs/CROSS_VALIDATION_REPORT.md`, `specs/humanization-cross-spec-audit.md`, `plans/spec-210-session-resume.md`, `plans/e2e-fix-plan-2025-12-17.md`.
- ROADMAP `| 215A |` row added for `auth-flow-redesign` (DRAFT v1).
- Spec 210A row HOTFIX: status updated to PARTIALLY MERGED with GH #470 tracking the kill-half code-debt.
- ROADMAP totals rebuilt against filesystem + code (85 spec dirs / 11 flags / 30 portal pages / 6,822 tests collected).

## Open follow-ups

- Backfill `212` (phone-capture-onboarding-ux) spec dir — currently in ROADMAP only.
- Reconcile each `(pre-SDD)` row against actual git log + closed PRs to upgrade `partial` rows to `implemented` where audit-report.md exists.
- 215A archive once 216-A subspec audit-report.md PASS (currently 216 master audit FAILED 2026-04-30; needs re-pass).
