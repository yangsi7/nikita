---
title: "Nikita: Don't Get Dumped — Project Roadmap"
specs_total: 85
specs_complete: 80
specs_active: 3
specs_planned: 2
specs_superseded: 2
tests_total: 6822
last_deploy: 2026-05-03
version: 1.0.3
---

# Nikita: Don't Get Dumped — Project Roadmap

> See `plans/master-plan.md` for architecture. See `specs/NNN-*/` for tactical details. Superseded specs are in `specs/archive/` (or noted inline). See `specs/INDEX.md` for the per-spec status table.

---

## Project Status Dashboard

| Metric | Value | Source-of-truth |
|--------|-------|----------------|
| Total spec dirs (numeric-prefixed) | 85 | `ls -d specs/[0-9]*-*/ \| wc -l` |
| Complete | 80 | `specs/INDEX.md` (status=implemented; includes 215 heartbeat-engine flag-OFF and 210A partially-merged with GH #470 code-debt) |
| Active | 3 (214, 215A, 216) | `specs/INDEX.md` (status=active OR draft) |
| Planned | 2 (210B, 211) | `specs/INDEX.md` (status=planned) |
| Superseded | 2 (017, 037) | `specs/archive/` |
| Backend tests collected | 6,822 (184 deselected) | `uv run pytest --collect-only -q` |
| Portal routes (page.tsx files) | 30 | `find portal/src/app -name page.tsx \| wc -l` |
| Pipeline stages | 11 | `find nikita/pipeline/stages -name '*.py' -not -name '__init__.py' -not -name 'base.py' \| wc -l` |
| Feature flags (`*_enabled: bool = Field(...)`) | 11 | `rg -c "^\s+\w+_enabled: bool = Field" nikita/config/settings.py` |
| Supabase migrations | 110 | `ls supabase/migrations/*.sql \| wc -l` |
| pg_cron `cron.schedule(...)` calls in migrations | 9 (across 5 migration files) | `rg -c "cron\.schedule" supabase/migrations/*.sql \| awk -F: '{s+=$NF} END{print s}'` |
| pg_cron jobs claimed live | 12 (per Spec 215 deployment notes; live count requires `mcp__supabase__execute_sql 'SELECT count(*) FROM cron.job;'`) | Spec 215 cron registration migration |
| Cloud Run deploy | `nikita-api-00258-62c` (us-central1) | `gcloud run revisions list` |
| Portal deploy | `nikita-mygirl.com` (apex canonical; www→apex 308) | Vercel REST API |
| Last master commit | 966df9c — `feat(216,C): cinematic 15-screen wizard with archetype climax + auth-guarded resume (#464)` (2026-05-03) | `git log -1 origin/master` |
| In-flight | Spec 216 SDD authoring + 6 subspec PRs (#450, #452, #457, #461, #462, #464 merged on `feat/216-*` branches; audit-report.md FAIL 2026-04-30 — 4 CRIT + 8 HIGH + 5 MED to be re-audited). 10 W3 findings (#440-#449) all mapped to subspec ACs. | `git log --oneline --grep="(216,"` + `specs/216-*/audit-report.md` |

---

## Feature Lines

> All domains 100% complete. Superseded specs are noted but not counted in totals.

### Domain 1 — Core Engine

Scoring, chapters, decay, vices, engagement, conflicts, boss encounters.

| Spec | Name | Tests | Notes |
|------|------|-------|-------|
| 001 | nikita-text-agent | — | 8 modules, Pydantic AI agent |
| 002 | telegram-integration | — | aiogram 3.x, webhook mode |
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
| 111 | consecutive-crises-tracking | 17 | Cross-session crisis counter in JSONB (GH #91) |
| 113 | voice-post-score-evaluation | 7 | Boss + crisis hooks for voice path (DA-002/GE-005) |
| 114 | vice-pipeline-activation | — | ViceStage added to pipeline (GE-006) |
| 115 | telegram-rate-limit | 17 | Per-user webhook rate limiting (DA-005) |
| 116 | extraction-checkpoint | — | Extraction data survives memory_update failure (MP-004) |
| 117 | configloader-migration | — | Engine constants via ConfigLoader (GE-001/GE-007) |
| 203 | telegram-vice-seeder-bypass | 4 | Fix: Telegram onboarding bypasses seeder.py (quick) COMPLETE |

**Domain subtotal: 21 specs, 872 tests**

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
| 210A | kill-skip-variable-response | — | **PARTIALLY MERGED** (b0f7e7a) — variable-response half only (log-normal × chapter × momentum timing model). Supersedes 026 AC-5.x. Kill-half (skip.py + skip_rates_enabled removal) tracked in GH #470 (filed Wave 1B 2026-05-03 as code-debt). |

**Domain subtotal: 10 specs, 1,738 tests**

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
| 215 | heartbeat-engine | #330-342 | **PHASE 1 COMPLETE** (flag-OFF, awaiting 24h baseline + flag-flip decision) — 9 PRs merged on master ea67c32: foundation (#330), intensity math (#331), planner (#332), endpoints (#334), parity validator (#333), cron registration + B1 close (#339), B4 planner timeout (#340), B3 try_advisory_lock (#341), B2 cost circuit breaker + cost_usd column (#342). All 4 pre-flag-flip blockers (B1-B4 GH #335-338) closed. 12 pg_cron jobs active (3 new heartbeat + 9 pre-existing). Cron tick verification: heartbeat-hourly + touchpoints firing as scheduled; Cloud Run processing 633 job_executions/24h. New ops finding: GH #343 pg_net 5s timeout vs Cloud Run cold-start (84% timeout rate, cosmetic — work executes successfully despite timeouts). Phase 2 (Hawkes self-scheduling) + Phase 3 (Bayesian posteriors) pending separate spec cycles. Plan v6.14 at `.claude/plans/delightful-orbiting-ladybug.md`. |

**Domain subtotal: 15 specs (1 superseded), 4,369 tests (215 Phase 1 COMPLETE; flag-OFF; B1-B4 closed; awaiting flag-flip decision)**

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
| 081 | onboarding-redesign-progressive-discovery | 21 | **SUPERSEDED by 214** — Cinematic 5-section scroll-snap onboarding (archived). Replaced by step-by-step wizard with landing aesthetic. |
| 208 | portal-landing-page-hero | #209 | **COMPLETE** — "Don't Get Dumped" hero landing page, 5 sections, FallingPattern, deployed 2026-04-03 |
| 212 | phone-capture-onboarding-ux | #266-272 | **COMPLETE** — Phone field, E.164 validation, voice-callback routing, 409 conflict handling. Spec dir backfill pending. |
| 213 | onboarding-backend-foundation | 60+ | **COMPLETE** (PR 213-5, 2026-04-15) — contracts.py + tuning.py + adapters.py; migration + ORM + BackstoryCacheRepository; PortalOnboardingFacade + preview endpoint + PII fixes; GET /pipeline-ready + PATCH /profile + FR-14 session isolation; FR-6 FirstMessageGenerator backstory hook + R8 continuity regression tests. |
| 214 | portal-onboarding-wizard | 98+ | **v2 AMENDMENT 2026-04-22 — FR-11d chat-first slot-filling variant ADDED (ADR-009 / Walk V incident)**. Walks R-V (5 walks, 4 patchwork PRs #392-396) failed to converge on the chat-first wizard; root-caused as 4 coupled agentic anti-patterns (hardcoded completion gate, 7-tool fan-out, per-turn snapshot state, static prompt). Phase 0 governance shipped via PR #397 (`.claude/rules/agentic-design-patterns.md` + ADR-009). FR-11d encodes cumulative WizardSlots + Pydantic FinalForm gate + dynamic instructions + regex phone fallback per the rule. AC-11d.1 through AC-11d.6. Implementation pending. Legacy 11-step (FR-1) retained behind `NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD` flag. FR-11d **superseded by 216-B** (Spec 216 cinematic redesign). Prior PRs: 214-A/B/C/D + entry #312 + #315/#317/#319 JSONB fixes + #322 Telegram binding FR-11b. Imports Spec 213 contracts. Supersedes 081. |
| 215A | auth-flow-redesign | (no PR yet) | **DRAFT v1** (pending GATE 2 validators) — Telegram-first signup. Renamed from `215-auth-flow-redesign` Wave 1A 2026-05-03 (collision with 215-heartbeat-engine, which is COMPLETE). Partial supersession by 216-A (telegram routing). Archive once 216-A subspec audit-report.md PASS — currently 216 audit FAILED 2026-04-30 (4 CRIT + 8 HIGH + 5 MED), needs re-pass before 215A archive. |
| 216 | onboarding-redesign-cinematic | 0 (NEW) | **IN AUTHORING (2026-04-29)** — single Telegram-canonical signup path + cinematic 12-screen wizard inheriting Spec 208 design system + Pydantic AI 1.71 agent (output_type discriminated union, instructions=callable, @output_validator + ModelRetry, FinalForm gate, message_history) + M1-M4 meta-prompts + Big Five hidden inference + 12-archetype curated taxonomy + 4 firecrawl always-fetch tools. Master spec.md + 6 subspecs (216-A telegram routing, 216-B agentic core, 216-C frontend, 216-D data+inference, 216-E firecrawl, 216-F testing). 58 ACs (17 CRIT + 36 HIGH + 5 MED). Closes W3 GH #440-#449. Supersedes Spec 214 v2 FR-11d + Spec 215 portal-first auth chain. STEP-0 routing investigation complete: bare /start unbound users currently route to _handle_start deep-link (commands.py:343-348); 216-A patches telegram.py:635-666 to enter SignupHandler.handle_welcome (~30 LOC). Cost ceiling $0.50/flow hard, $0.30 median; latency p99 8s/turn. **216-B + 216-C SUPERSEDED BY SPEC 217 (2026-05-07)** — agentic-wizard core + cinematic-frontend subspecs replaced by deterministic-track redesign + bug-fix bundle in 5 sub-PRs (217-0/1/2/3A/3B). 216-A/D/E/F/G/H preserved. |
| 217 | onboarding-wizard-deterministic-redesign | 0 (NEW) | **IN AUTHORING (2026-05-07)** — supersedes 216-B/C. 5 sub-PRs (217-0 prereq cleanup, 217-1 cold-start CTA + interstitial, 217-2 backstory FE fallback, 217-3A BE emission union [ReactionOnly\|FollowUpQuestion\|TurnFailure], 217-3B FE wizard sibling-DOM refactor). Closes 5 user-reported UX failures post-Walk-A1. Authoritative inputs: `docs-to-process/20260507-spec217-onboarding-redesign-planning-brief.md` + `docs-to-process/20260507-spec217-2-backstory-diagnosis.md` (frozen spike). Each sub-PR ≤400 LOC per pr-workflow.md. |

**Domain subtotal: 18 specs (15 complete, 3 active — Specs 216 + 217 NEW)**

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
| 108 | voice-agent-optimization | 110 | V3 Conversational, audio tags, knowledge base |

**Domain subtotal: 6 specs, 649 tests**

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
| 107 | process-framework-remediation | — | Hook portability, JSON safety, ROADMAP data fixes |
| 109 | systemic-cleanup | 13 | ConflictStore removal, `@llm_retry`, DI dedup (PR #81) |

**Domain subtotal: 15 specs (1 superseded), 128 tests**

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
| 110 | pipeline-observability-event-stream | 37 | Phase A complete: pipeline_events, EventEmitter, Conversation Inspector (PR #92) |

**Domain subtotal: 8 specs, 242 tests**

---

### Domain 8 — Quality & Testing

E2E testing, integration wiring, text continuity.

| Spec | Name | Tests | Notes |
|------|------|-------|-------|
| 030 | text-continuity | 111 | Message threading |
| 048 | e2e-full-lifecycle | — | 16 phases, 4 bugs fixed |
| 103 | touchpoint-intelligence | — | Life events, dedup |
| 112 | portal-e2e-hardening | 125 | Content assertions, auth bypass, data-testid, CI (GH #101, #103) |
| 210B | test-quality-audit | — | **PLANNED** — Audit 5768 tests for empty-mock + zero-assertion anti-patterns (triggered by PR #252 / GH #248) |
| 211 | task-ledger-truth-audit | — | **PLANNED** — Audit completed-task ledger vs GH issue state + master merges (triggered by PR #253 silently-complete Task #17 discovery) |

**Domain subtotal: 5 specs, 236 tests (210, 211 PLANNED)**

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

66 spec directories exist. 9 specs were implemented pre-SDD (no directory).

### Specs with Full Artifacts (spec.md, plan.md, tasks.md, audit-report.md)

001–016, 018–027, 029–032, 034–036, 038–044, 046–048, 055–063, 070, 100–104

### Specs with Partial Artifacts

> Tracks artifact completeness for specs missing audit-report.md. Specs 049, 050, 070 listed only in Feature Lines above.

| Spec | Has spec | Has plan | Has tasks | Has audit | Note |
|------|----------|----------|-----------|-----------|------|
| 100 | Y | Y | Y | Y | Complete |
| 101 | Y | Y | Y | Y | Complete |
| 102 | Y | Y | Y | Y | Complete |
| 103 | Y | Y | Y | Y | Complete |
| 104 | Y | Y | Y | Y | Complete |
| 105 | Y | Y | Y | Y | Complete; FR-002 (game status audit trail) not implemented |

### Pre-SDD Specs (no directory or partial artifacts, implemented inline)

045, 049, 050, 051, 052, 064, 065 (production-hardening-2), 066, 067, 068, 069, 106, 107 (spec.md only), 108 (spec.md only), 109, 110

---

## Active Work

**Spec 216 — onboarding-redesign-cinematic** (ACTIVE, audit re-pass pending). Master spec.md + 6 subspecs (216-A..216-F). Subspec PRs merged on `feat/216-*` branches: #450 (SDD Phase 1 + 216-A backend routing), #452 (216-B1+B2 atomic agentic-wizard-core rewrite), #457 (216-B3 POST /answer + GET /state + flag-gated /converse 410 shim), #461 (216-D-code Big5 judge + 12 archetypes + cohort chips), #462 (216-E firecrawl tools + WebSearchTool + cost guard), #464 (216-C cinematic 15-screen wizard + auth-guarded resume). audit-report.md FAIL 2026-04-30 (4 CRIT + 8 HIGH + 5 MED) — re-audit pending after subspec merges. Supersedes Spec 214 v2 FR-11d (GH #396 to be closed by 216-B) and Spec 215A portal-first auth chain (216-A rewires bare `/start` for unbound users from `_handle_start` deep-link to `SignupHandler.handle_welcome` FSM). 10 W3 findings (#440-#449) all mapped to subspec ACs. Wireframes: ASCII (127K) + Figma file (20 frames) live. Cost ceiling $0.50/flow, latency p99 8s/turn.

**Spec 215 — heartbeat-engine** (COMPLETE Phase 1, flag-OFF, awaiting flag-flip decision). 9 PRs merged on master ea67c32. See Domain 3 row above.

**Spec 215A — auth-flow-redesign** (DRAFT v1, pending GATE 2 validators). Number-collision rename from `215-auth-flow-redesign` to `215A-auth-flow-redesign` Wave 1A 2026-05-03. Partial supersession by 216-A telegram routing.

**Spec 210A — kill-skip-variable-response** (PARTIALLY MERGED, 2026-04-12 + Wave 1B HOTFIX 2026-05-03). Variable-response half MERGED at b0f7e7a. Kill-half code-debt (delete `nikita/agents/text/skip.py` + `skip_rates_enabled` flag) tracked in **GH #470**. Renamed from `210-kill-skip-variable-response` Wave 1A 2026-05-03 (collision with 210-test-quality-audit → 210B).

**Last deployment**: 2026-05-03 (master HEAD `966df9c` — Spec 216-C cinematic-frontend). Cloud Run revision `nikita-api-00258-62c` from 2026-04-18; portal at apex `nikita-mygirl.com`.

**Note**: Spec 105 FR-002 (game status audit trail) remains unimplemented — candidate for future work.

---

## Backlog

No specs are currently planned. Candidate next work items:

| Priority | Item | Domain | Effort |
|----------|------|--------|--------|
| ~~High~~ | ~~Spec 110 Phase A: Pipeline Observability~~ | Observability | **Done** (PR #92) |
| ~~High~~ | ~~Spec 109: ConflictStore removal + LLM retry + DI dedup~~ | Infrastructure | **Done** (PR #81) |
| ~~High~~ | ~~Portal P0 bug: GH #97 conversation detail crash "Invalid time value"~~ | Portal | **Done** (fix/portal-bugs-93-100) |
| ~~High~~ | ~~Portal bugs: GH #93-#100 — 8 bugs (7 fixed, 1 was pre-fixed)~~ | Portal | **Done** (fix/portal-bugs-93-100) |
| ~~High~~ | ~~GH #105 (settings email) + #106 (notifications toggle)~~ | Portal | **Done** (PR #113) |
| ~~High~~ | ~~Portal bugs: GH #104, #107-#112 — 7 remaining from exhaustive E2E~~ | Portal | **Done** (PR #113, #114, #115) |
| ~~High~~ | ~~Spec 113: Voice post-score evaluation~~ | Voice | **Done** (PR #129) |
| ~~High~~ | ~~Spec 114: Vice pipeline activation (text path)~~ | Engine | **Done** (PR #130) |
| ~~High~~ | ~~Spec 115: Telegram webhook rate limiting~~ | Engine | **Done** (PR #128) |
| ~~High~~ | ~~Spec 116: Extraction checkpoint~~ | Pipeline | **Done** (PR #131) |
| ~~High~~ | ~~Spec 117: ConfigLoader migration + engine constants cleanup~~ | Engine | **Done** (PR #132) |
| High | Spec 105 FR-002: Game status audit trail | Observability | Small |
| High | Playwright E2E for portal (Spec 044+) | Quality | Medium |
| High | Custom domain wiring (portal) | Infrastructure | Small |
| Medium | Background task DI deduplication | Infrastructure | Small |
| Medium | Production monitoring dashboards (Grafana/Datadog) | Observability | Medium |
| Medium | Voice pipeline unification (ElevenLabs v3 API) | Voice | Large |
| Low | Multiplayer / shared Nikita state (experimental) | Core Engine | X-Large |
| Low | Native mobile app (React Native) | Portal | X-Large |

---

## Game Constants

| Constant | Value |
|--------|-------|
| Relationship metrics | 4 (warmth, trust, passion, respect) |
| Chapters | 5 (win condition: reach Chapter 5) |
| Lose condition | 3 failed boss encounters |

> Quantitative project metrics live in **Project Status Dashboard** at the top of this file (single source of truth). Old "Metrics Summary" table removed Wave 1B (was 4 months stale: 78 vs actual 85, 5,533 tests vs 6,822, 5 flags vs 11, etc.).

---

*Top dashboard regenerated 2026-05-03 (Wave 1B doc-cleanup). Maintained manually — update after each completed spec; verify via the source-of-truth commands beside each row.*
