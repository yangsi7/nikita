---
title: GSD Project Roadmap
lifecycle: living
last_updated: 2026-05-19
---

# ROADMAP.md — Nikita GSD Roadmap

> **Canonical roadmap post-GSD-migration 2026-05-19.** Root `ROADMAP.md` is a redirect stub pointing here.
>
> SDD spec archive: `specs/.archive/sdd-pre-migration-2026-05-19/` (91 spec dirs).

## Active Phases

| Phase | Name | Status | Branch Template |
|---|---|---|---|
| 01 | canonical-tg-first-signup | **ACTIVE** | `gsd/phase-01-canonical-tg-first-signup` |

## Phases Backlog

| Phase | Name | Domain | Effort | Notes |
|---|---|---|---|---|
| 02 | test-quality-audit | Quality | Medium | Former Spec 210B — audit 5768 tests for empty-mock + zero-assertion anti-patterns |
| 03 | task-ledger-truth-audit | Quality | Small | Former Spec 211 — audit completed-task ledger vs GH issue state |
| 04 | heartbeat-engine-flag-flip | Core Engine | Small | Former Spec 215 Phase 2 — flip heartbeat-enabled flag after 24h baseline |
| 05 | kill-skip-code-debt | Humanization | Small | GH #470 — delete `nikita/agents/text/skip.py` + `skip_rates_enabled` flag (Spec 210A kill-half) |
| 06 | game-status-audit-trail | Observability | Small | Spec 105 FR-002 — implement game status event audit trail |

## Completed Phases (Post-GSD Migration)

_None yet — GSD migration is the starting point._

---

## SDD History (Backlog Reference)

The following domain tables preserve the SDD spec history for context. Full artifacts are at `specs/.archive/sdd-pre-migration-2026-05-19/`.

### Domain 1 — Core Engine

| Spec | Name | Status | Tests |
|---|---|---|---|
| 001 | nikita-text-agent | complete | — |
| 002 | telegram-integration | complete | — |
| 003 | scoring-engine | complete | 60 |
| 004 | chapter-boss-system | complete | 142 |
| 005 | decay-system | complete | 52 |
| 006 | vice-personalization | complete | 81 |
| 014 | engagement-model | complete | 179 |
| 049 | game-mechanics-remediation | complete | — |
| 055 | life-simulation-enhanced | complete | 33 |
| 057 | conflict-system-core | complete | 167 |
| 058 | multi-phase-boss | complete | 117 |
| 101 | game-mechanics-remediation | complete | — |
| 111 | consecutive-crises-tracking | complete | 17 |
| 113 | voice-post-score-evaluation | complete | 7 |
| 114 | vice-pipeline-activation | complete | — |
| 115 | telegram-rate-limit | complete | 17 |
| 116 | extraction-checkpoint | complete | — |
| 117 | configloader-migration | complete | — |
| 203 | telegram-vice-seeder-bypass | complete | 4 |

### Domain 2 — Humanization

| Spec | Name | Status | Tests |
|---|---|---|---|
| 021 | hierarchical-prompt-composition | complete | 345 |
| 022 | life-simulation-engine | complete | 212 |
| 023 | emotional-state-engine | complete | 233 |
| 024 | behavioral-meta-instructions | complete | 166 |
| 025 | proactive-touchpoint-system | complete | 189 |
| 026 | text-behavioral-patterns | complete | 167 |
| 027 | conflict-generation-system | complete | 263 |
| 029 | context-comprehensive | complete | — |
| 056 | psyche-agent | complete | 163 |
| 210A | kill-skip-variable-response | partial | — |

### Domain 3 — Pipeline & Memory

| Spec | Name | Status | Tests |
|---|---|---|---|
| 012 | context-engineering | complete | — |
| 031 | post-processing-unification | complete | — |
| 037 | pipeline-refactor | superseded | — |
| 039 | unified-context-engine | complete | 231 |
| 040 | context-engine-enhancements | complete | 326 |
| 042 | unified-pipeline | complete | — |
| 043 | integration-wiring | complete | — |
| 060 | prompt-caching | complete | 15 |
| 067 | persistence-stage | complete | — |
| 068 | context-enrichment | complete | — |
| 100 | cron-infrastructure-hardening | complete | — |
| 102 | memory-data-integrity | complete | — |
| 104 | context-engineering-enrichment | complete | — |
| 215 | heartbeat-engine | complete-phase1-flag-off | — |

### Domain 4 — Portal + Auth

| Spec | Name | Status | Tests |
|---|---|---|---|
| 008 | player-portal | complete | — |
| 044 | portal-respec | complete | — |
| 046 | portal-emotional-intelligence | complete | — |
| 047 | portal-deep-insights | complete | — |
| 050 | portal-fixes | complete | — |
| 059 | portal-nikita-day | complete | 5 |
| 061 | portal-resilience | complete | — |
| 062 | portal-visual-polish | complete | — |
| 063 | portal-data-viz-notifications | complete | — |
| 070 | push-notifications | complete | — |
| 106 | player-facing-experience | complete | — |
| 208 | portal-landing-page-hero | complete | — |
| 212 | phone-capture-onboarding-ux | complete | — |
| 213 | onboarding-backend-foundation | complete | 60+ |
| 214 | portal-onboarding-wizard | superseded-by-216 | 98+ |
| 215A | auth-flow-redesign | superseded-by-220 | — |
| 216 | onboarding-redesign-cinematic | superseded-by-218 | — |
| 217 | onboarding-wizard-deterministic-redesign | superseded-by-218 | — |
| 218 | onboarding-wizard-v2-agent-driven | complete | — |
| 219 | telegram-binding-hardening | complete | — |
| 220 | canonical-tg-first-signup | **ACTIVE (Phase 01)** | — |

### Domain 5 — Voice

| Spec | Name | Status | Tests |
|---|---|---|---|
| 007 | voice-agent | complete | 186 |
| 028 | voice-onboarding | archived | 230 |
| 032 | voice-agent-optimization | complete | 94 |
| 033 | unified-phone-number | complete | 29 |
| 108 | voice-agent-optimization-v3 | complete | 110 |

### Domain 6 — Infrastructure

| Spec | Name | Status | Tests |
|---|---|---|---|
| 009 | database-infrastructure | complete | — |
| 010 | api-infrastructure | complete | — |
| 011 | background-tasks | complete | — |
| 013 | configuration-system | complete | 89 |
| 015 | onboarding-fix | complete | — |
| 036 | humanization-fixes | complete | 26 |
| 038 | conversation-continuity | complete | — |
| 041 | gap-remediation | complete | — |
| 064 | production-hardening | complete | — |
| 066 | feature-flag-activation | complete | — |
| 069 | flag-activation-safeguards | complete | — |
| 107 | process-framework-remediation | complete | — |
| 109 | systemic-cleanup | complete | 13 |

### Domain 7 — Admin & Observability

| Spec | Name | Status | Tests |
|---|---|---|---|
| 016 | admin-debug-portal | complete | 8 |
| 018 | admin-prompt-viewing | complete | — |
| 019 | admin-voice-monitoring | complete | 21 |
| 020 | admin-text-monitoring | complete | 29 |
| 034 | admin-user-monitoring | complete | 64 |
| 035 | context-surfacing-fixes | complete | 120 |
| 105 | schema-cleanup-observability | complete | — |
| 110 | pipeline-observability-event-stream | complete | 37 |

### Domain 8 — Quality & Testing

| Spec | Name | Status | Tests |
|---|---|---|---|
| 030 | text-continuity | complete | 111 |
| 048 | e2e-full-lifecycle | complete | — |
| 103 | touchpoint-intelligence | complete | — |
| 112 | portal-e2e-hardening | complete | 125 |

---

*Roadmap migrated from SDD to GSD on 2026-05-19. SDD artifacts archived at `specs/.archive/sdd-pre-migration-2026-05-19/`.*
