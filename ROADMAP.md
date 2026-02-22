---
title: "Nikita: Don't Get Dumped — Project Roadmap"
specs_total: 75
specs_complete: 73
specs_superseded: 2
tests_total: 5005
last_deploy: 2026-02-23
version: 1.0.0
---

# Nikita: Don't Get Dumped — Project Roadmap

> See `plans/master-plan.md` for architecture. See `specs/NNN-*/` for tactical details. Superseded specs are in `specs/archive/` (or noted inline).

---

## Project Status Dashboard

| Metric | Value |
|--------|-------|
| Total specs | 75 |
| Complete | 73 |
| Superseded | 2 (037, 017) |
| Backend tests | 5,005+ passing |
| Portal routes | 25 (19 + admin) |
| Pipeline stages | 10 |
| Feature flags | 5/5 ON |
| pg_cron jobs | 7 active |
| Cloud Run deploy | `nikita-api-00209-zf6` (us-central1) |
| Portal deploy | `portal-phi-orcin.vercel.app` |
| Last deploy | 2026-02-23 |
| Active specs | 0 |

---

## Feature Lines

> All domains 100% complete. Superseded specs are noted but not counted in totals.

### Domain 1 — Core Engine

Scoring, chapters, decay, vices, engagement, conflicts, boss encounters.

| Spec | Name | Tests | Notes |
|------|------|-------|-------|
| 003 | scoring-engine | 60 | 4 files, 4 relationship metrics |
| 004 | chapter-boss-system | 142 | Boss scoring, 5 chapters |
| 005 | decay-system | 52 | 0.8–0.2/hr decay rates |
| 006 | vice-personalization | 81 | Per-player vice tracking |
| 014 | engagement-model | 179 | 6 states |
| 049 | game-mechanics-remediation | — | Pre-SDD; boss/grace fixes |
| 055 | life-simulation-enhanced | 33 | 22 tasks |
| 057 | conflict-system-core | 167 | 20 tasks |
| 058 | multi-phase-boss | 117 | OPENING→RESOLUTION, PARTIAL outcome |
| 101 | game-mechanics-remediation | — | Boss cooldown, grace period |

**Domain subtotal: 10 specs, 831 tests**

---

### Domain 2 — Humanization

Prompt composition, life simulation, emotional state, behavioral patterns, psyche.

| Spec | Name | Tests | Notes |
|------|------|-------|-------|
| 021 | hierarchical-prompt-composition | 345 | 6-layer composition |
| 022 | life-simulation-engine | 212 | Daily life events |
| 023 | emotional-state-engine | 233 | 4D mood model |
| 024 | behavioral-meta-instructions | 166 | Tone/style injection |
| 025 | proactive-touchpoint-system | 189 | Event-driven outreach |
| 026 | text-behavioral-patterns | 167 | Typing cadence, habits |
| 027 | conflict-generation-system | 263 | Conflict triggers |
| 029 | context-comprehensive | — | 31 tasks; context assembly |
| 056 | psyche-agent | 163 | 25 tasks, batch job, circuit breaker |

**Domain subtotal: 9 specs, 1,738 tests**

---

### Domain 3 — Pipeline & Memory

Context engineering, pipeline stages, memory system, processing.

| Spec | Name | Tests | Notes |
|------|------|-------|-------|
| 012 | context-engineering | — | Phase 4 integration |
| 031 | post-processing-unification | — | 16/17 tasks |
| 037 | pipeline-refactor | — | SUPERSEDED by 042 |
| 039 | unified-context-engine | 231 | — |
| 040 | context-engine-enhancements | 326 | — |
| 042 | unified-pipeline | — | 45/45 tasks, 3,797 tests; supersedes 037 |
| 043 | integration-wiring | — | 11 tasks |
| 045 | prompt-unification | — | Pre-SDD |
| 060 | prompt-caching | 15 | 11 tasks, Claude prefix caching |
| 067 | persistence-stage | — | Pipeline stage 10 |
| 068 | context-enrichment | — | Historical thoughts injection |
| 100 | cron-infrastructure-hardening | — | Idempotency, concurrency guards |
| 102 | memory-data-integrity | — | Batch search, embedding dedup |
| 104 | context-engineering-enrichment | — | Arcs, thought resolution |

**Domain subtotal: 14 specs (1 superseded), 4,369 tests**

---

### Domain 4 — Portal

Player portal, admin dashboards, data viz, push notifications.

| Spec | Name | Tests | Notes |
|------|------|-------|-------|
| 008 | player-portal | — | 50/50 tasks; initial portal |
| 044 | portal-respec | — | 94 files, 19 routes, Next.js 16 |
| 046 | portal-emotional-intelligence | — | MoodOrb, life event feed |
| 047 | portal-deep-insights | — | Score chart, trajectory |
| 050 | portal-fixes | — | Pre-SDD patches |
| 059 | portal-nikita-day | 5 | 12 tasks, psyche-tips endpoint |
| 061 | portal-resilience | — | Error boundaries, a11y |
| 062 | portal-visual-polish | — | Framer Motion, mobile nav |
| 063 | portal-data-viz-notifications | — | Charts, CSV/JSON export |
| 070 | push-notifications | — | Push service, Service Worker |
| 106 | player-facing-experience | — | Vice visibility, decay warnings |

**Domain subtotal: 11 specs**

---

### Domain 5 — Voice

Voice agent, onboarding, optimization, phone number unification.

| Spec | Name | Tests | Notes |
|------|------|-------|-------|
| 007 | voice-agent | 186 | 14 modules, ElevenLabs Conv AI 2.0 |
| 028 | voice-onboarding | 230 | Supersedes 017; server tools pattern |
| 032 | voice-agent-optimization | 94 | Latency, context window |
| 033 | unified-phone-number | 29 | Single phone per user |
| 051 | voice-pipeline-polish | — | Pre-SDD |

**Domain subtotal: 5 specs, 539 tests**

---

### Domain 6 — Infrastructure

DB, API, background tasks, config, onboarding, CI/CD, deployment.

| Spec | Name | Tests | Notes |
|------|------|-------|-------|
| 009 | database-infrastructure | — | Supabase, pgVector, RLS |
| 010 | api-infrastructure | — | FastAPI, Cloud Run |
| 011 | background-tasks | — | pg_cron, 5 initial jobs |
| 013 | configuration-system | 89 | Pydantic settings |
| 015 | onboarding-fix | — | OTP flow |
| 017 | enhanced-onboarding | — | SUPERSEDED by 028 |
| 036 | humanization-fixes | 26 | Response post-processing |
| 038 | conversation-continuity | — | 6/11 tasks |
| 041 | gap-remediation | — | 22/24 tasks |
| 052 | infrastructure-cleanup | — | Pre-SDD |
| 064 | production-hardening | — | CI/CD pipelines |
| 066 | feature-flag-activation | — | All 5 flags ON |
| 069 | flag-activation-safeguards | — | Psyche safeguards |

**Domain subtotal: 13 specs (1 superseded), 115 tests**

---

### Domain 7 — Admin & Observability

Admin monitoring, schema cleanup, pipeline observability.

| Spec | Name | Tests | Notes |
|------|------|-------|-------|
| 016 | admin-debug-portal | 8 | Debug endpoints |
| 018 | admin-prompt-viewing | — | Prompt inspection |
| 019 | admin-voice-monitoring | 21 | 5 endpoints |
| 020 | admin-text-monitoring | 29 | 6 endpoints |
| 034 | admin-user-monitoring | 64 | User state overview |
| 035 | context-surfacing-fixes | 120 | Context visibility |
| 105 | schema-cleanup-observability | — | Scoring fallback, timings |

**Domain subtotal: 7 specs, 242 tests**

---

### Domain 8 — Quality & Testing

E2E testing, integration wiring, text continuity.

| Spec | Name | Tests | Notes |
|------|------|-------|-------|
| 030 | text-continuity | 111 | Message threading |
| 048 | e2e-full-lifecycle | — | 16 phases, 4 bugs fixed |
| 103 | touchpoint-intelligence | — | Life events, dedup |

**Domain subtotal: 3 specs, 111 tests**

---

## Dependency Graph (Historical)

All blocking dependencies are resolved. Shown for architectural reference.

```
[009 DB] ──────────────────────────────────────┐
[010 API] ─────────────────────────────────────┤
[013 Config] ──────────────────────────────────┤
        │                                       ▼
[001 Text Agent] ◄── [021 Prompt Composition]  [Core Engine]
[007 Voice Agent] ◄── [028 Voice Onboarding]       │
        │                                       │
[042 Pipeline] ◄── [039 Context Engine] ────────┘
        │
[044 Portal] ◄── [046..063 Portal Features]
        │
[056 Psyche] ──► [058 Boss] ──► [057 Conflicts]
        │
[100..106 Remediation] (all resolved)
```

---

## Artifact Index

65 spec directories exist. 10 specs were implemented pre-SDD (no directory).

### Specs with Full Artifacts (spec.md, plan.md, tasks.md, audit-report.md)

001–016, 018–027, 029–032, 034–036, 038–044, 046–048, 055–063, 070, 100–104

### Specs with Partial Artifacts

| Spec | Has spec | Has plan | Has tasks | Has audit | Note |
|------|----------|----------|-----------|-----------|------|
| 049 | Y | Y | N | N | Pre-SDD |
| 050 | Y | N | N | N | Pre-SDD |
| 070 | Y | Y | Y | N | Audit pending |
| 100 | Y | Y | Y | N | Audit pending |
| 101 | Y | Y | Y | N | Audit pending |
| 102 | Y | Y | Y | N | Audit pending |
| 103 | Y | Y | Y | N | Audit pending |
| 104 | Y | Y | Y | N | Audit pending |
| 105 | Y | Y | Y | N | Audit pending |

### Pre-SDD Specs (no directory, implemented inline)

045, 051, 052, 064, 065, 066, 067, 068, 069, 106

---

## Active Work

**No active specs.** All 73 complete specs are deployed to production.

Last deployment: 2026-02-23 — Phase 7 (Specs 070, 100–106)

---

## Backlog

No specs are currently planned. Candidate next work items:

| Priority | Item | Domain | Effort |
|----------|------|--------|--------|
| High | Playwright E2E for portal (Spec 044+) | Quality | Medium |
| High | Custom domain wiring (portal) | Infrastructure | Small |
| Medium | Production monitoring dashboards (Grafana/Datadog) | Observability | Medium |
| Medium | Voice pipeline unification (ElevenLabs v3 API) | Voice | Large |
| Low | Multiplayer / shared Nikita state (experimental) | Core Engine | X-Large |
| Low | Native mobile app (React Native) | Portal | X-Large |

---

## Metrics Summary

| Metric | Count |
|--------|-------|
| Total specs | 75 |
| Spec directories | 65 |
| Backend tests | 5,005+ |
| Portal routes | 25 |
| Pipeline stages | 10 |
| Feature flags | 5 |
| pg_cron jobs | 7 |
| Supabase migrations | 30+ |
| Cloud Run revisions | 209+ |
| Vercel deployments | multiple |
| Relationship metrics | 4 (warmth, trust, passion, respect) |
| Chapters | 5 (win condition: reach Chapter 5) |
| Lose condition | 3 failed boss encounters |

---

*Generated 2026-02-23. Maintained manually — update after each completed spec.*
