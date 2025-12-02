---
title: Nikita Game Master Todo
created: 2025-01-27T20:31:00Z
updated: 2025-12-02T12:00:00Z
session_id: nikita-phase0-docs-sync
current_phase: 2
blocked_by: null
notes: "System audit complete. Phase 2 at 95%. All 14 specs audited. Security issues identified."
---

# Master Todo - Nikita Game

**Source**: [../plans/master-plan.md](../plans/master-plan.md) | **Audit**: [docs-to-process/20251202-system-audit-final-report.md](../docs-to-process/20251202-system-audit-final-report.md)

---

## SDD Specification Status ✅ ALL 14 SPECS AUDITED

All specifications have complete SDD workflows (spec.md, plan.md, tasks.md, audit-report.md):

| Spec | Name | Impl | Audit | Notes |
|------|------|------|-------|-------|
| 001 | nikita-text-agent | ✅ 100% | PASS | 8 files, 156 tests |
| 002 | telegram-integration | ⚠️ 95% | PASS | 7 files, 74 tests, deploy pending |
| 003 | scoring-engine | ❌ 0% | PASS | Blocks: 013 |
| 004 | chapter-boss-system | ❌ 0% | PASS | Blocks: 003, 012 |
| 005 | decay-system | ❌ 0% | PASS | Blocks: 013 |
| 006 | vice-personalization | ❌ 0% | PASS | Blocks: 003 |
| 007 | voice-agent | ❌ 0% | PASS | Blocks: 012 |
| 008 | player-portal | ❌ 0% | PASS | Blocks: all |
| 009 | database-infrastructure | ✅ 100% | PASS | Foundation complete |
| 010 | api-infrastructure | ⚠️ 90% | PASS | Cloud Run deployed |
| 011 | background-tasks | ✅ 100% | PASS | pg_cron routes ready |
| 012 | context-engineering | ❌ 0% | PASS | **Critical** - 6-stage pipeline |
| 013 | configuration-system | ❌ 0% | PASS | **PRIORITY 1** - blocks all engine specs |
| 014 | engagement-model | ❌ 0% | PASS | **Critical** - 6 states |

### Critical Path: 013 → 014 → 012 → Game Engine → Voice → Portal

---

## SDD Implementation Phases

### Phase 0: Documentation Sync 🔄 IN PROGRESS
- [x] Update README.md (Neo4j Aura, pg_cron, Cloud Run)
- [x] Update CLAUDE.md (root) with current status
- [x] Update nikita/CLAUDE.md with phase status
- [x] Update nikita/api/CLAUDE.md, engine/CLAUDE.md, db/CLAUDE.md
- [x] Update plans/master-plan.md with SDD orchestration
- [x] Update todo/master-todo.md with SDD phases
- [ ] Git commit and push

### Phase 1A: Security Hardening (PARALLEL with Phase 2)
**Severity**: CRITICAL + HIGH issues

| Task | Issue | Severity | Status |
|------|-------|----------|--------|
| SEC-01 | Webhook signature validation | CRITICAL | ❌ TODO |
| SEC-02 | DB-backed rate limiting | HIGH | ❌ TODO |
| SEC-03 | HTML escaping in bot.py | HIGH | ❌ TODO |
| SEC-04 | Secret Manager migration | HIGH | ❌ TODO |

### Phase 2: Configuration System (013) ❌ TODO
- [ ] Create nikita/config/yaml/ directory structure
- [ ] Create YAML config files (game, chapters, engagement, scoring, decay, vices, schedule)
- [ ] Create JSON schemas for validation
- [ ] Implement ConfigLoader class
- [ ] Implement PromptLoader class
- [ ] Migrate constants.py to use ConfigLoader
- [ ] Unit tests for all loaders

### Phase 3: Engagement Model (014) ❌ TODO
- [ ] T1.1-T1.6: Data models (EngagementState, metrics)
- [ ] T2.1-T2.3: State machine (StateCalculator, TransitionEngine)
- [ ] T3.1-T3.3: Calibration system (IdealPoint, tolerance bands)
- [ ] T4.1-T4.3: Detection engine (drift detection, alerts)
- [ ] T5.1-T5.2: Recovery system (recovery rates)
- [ ] T6.1-T6.2: Integration (agent, scoring)

### Phase 4: Scoring Engine (003) ❌ TODO
- [ ] ScoreCalculator class
- [ ] ResponseAnalyzer (LLM-based)
- [ ] Engagement multiplier integration
- [ ] Score history logging

### Phase 5: Context Engineering (012) ❌ TODO
- [ ] Stage 1: StateCollector
- [ ] Stage 2: TemporalBuilder
- [ ] Stage 3: MemorySummarizer
- [ ] Stage 4: MoodComputer
- [ ] Stage 5: PromptAssembler
- [ ] Stage 6: Validator
- [ ] Verification: <200ms, <4000 tokens

### Phases 6-11: See spec-specific tasks.md files

---

## Phase 1: Core Infrastructure ✅ COMPLETE

- [x] Project structure (39 Python files)
- [x] Supabase database models
- [x] Graphiti memory (NikitaMemory class) - migrating to Neo4j Aura
- [x] FastAPI skeleton + Pydantic models
- [x] Game constants (CHAPTERS, DECAY_RATES, CHAPTER_BEHAVIORS)
- [x] Documentation system (memory/, plan/, todo/)

---

## Phase 2: Text Agent ⚠️ IN PROGRESS

### Text Agent Core ✅ COMPLETE (specs/001-nikita-text-agent)
- [x] Pydantic AI agent with Nikita persona → `nikita/agents/text/agent.py`
- [x] NikitaDeps dependency container → `nikita/agents/text/deps.py`
- [x] MessageHandler with timing + skip → `nikita/agents/text/handler.py`
- [x] ResponseTimer (gaussian delay) → `nikita/agents/text/timing.py`
- [x] SkipDecision (chapter-based rates) → `nikita/agents/text/skip.py`
- [x] FactExtractor (LLM fact learning) → `nikita/agents/text/facts.py`
- [x] Memory tools (recall_memory, note_user_fact) → `nikita/agents/text/tools.py`
- [x] 156 tests passing

### Telegram Integration ⚠️ 95% COMPLETE (specs/002-telegram-integration)
- [x] Telegram bot client (TelegramBot, models) → `nikita/platforms/telegram/bot.py`
- [x] Auth system with magic links (TelegramAuth) → `nikita/platforms/telegram/auth.py`
- [x] Command handler (/start, /help, /status) → `nikita/platforms/telegram/commands.py`
- [x] Message handler + delivery → `nikita/platforms/telegram/message_handler.py`
- [x] Rate limiter (20/min, 100/day) → `nikita/platforms/telegram/rate_limiter.py`
- [x] **T046: pending_registrations DB migration** → COMPLETE (74 tests passing)
- [x] Telegram webhook endpoint → `nikita/api/routes/telegram.py` (Sprint 3)
- [x] Wire real dependencies in `main.py` (Sprint 3 - full DI)
- [x] Task routes for pg_cron → `nikita/api/routes/tasks.py` (Sprint 3)
- [ ] Wire text_agent in MessageHandler (currently None)
- [ ] Deploy to Cloud Run + set webhook URL

### Database Layer ✅ COMPLETE
- [x] Implement repositories (user, conversation, metrics, pending_registrations)
- [x] Database migrations applied to Supabase (8 migrations)
- [x] RLS policies with performance optimization

---

## Phase 3: Game Engine ❌ TODO (specs/003-006)

- [ ] **Scoring System** (specs/003-scoring-engine)
  - ScoreCalculator: analyze_response(), apply_deltas()
  - ResponseAnalysis model (LLM-based)
  - Metrics updater + score_history logging

- [ ] **Chapter System** (specs/004-chapter-boss-system)
  - ChapterStateMachine
  - Boss encounter logic (pass/fail, attempts)

- [ ] **Decay System** (specs/005-decay-system)
  - DecayCalculator + grace periods
  - pg_cron + Edge Function: apply_daily_decay()

- [ ] **Vice System** (specs/006-vice-personalization)
  - ViceDiscovery + intensity tracking
  - 8 vice categories

- [x] **Background Tasks** ✅ COMPLETE (specs/011-background-tasks)
  - [x] Task routes created (Sprint 3) → `nikita/api/routes/tasks.py`
  - [x] POST /tasks/decay (daily decay)
  - [x] POST /tasks/deliver (delayed messages)
  - [x] POST /tasks/summary (daily summaries)
  - [x] POST /tasks/cleanup (expired registrations)
  - [ ] Configure pg_cron → Supabase Edge Functions → Cloud Run (after deploy)

---

## Phase 4: Voice Agent ❌ TODO (specs/007-voice-agent)

- [ ] ElevenLabs Conversational AI 2.0 integration
- [ ] Server tools: get_context, get_memory, score_turn, update_memory
- [ ] Voice session management
- [ ] API routes: /voice/elevenlabs/server-tool

---

## Phase 5: Portal ❌ TODO (specs/008-player-portal)

- [ ] Next.js dashboard (stats, score history, conversations)
- [ ] Daily summaries view
- [ ] Admin endpoints
- [ ] Logging/monitoring (Sentry)

---

## Security Remediation Sprint ✅ COMPLETE (2025-12-01)

**Source**: Backend/DB Audit Report (`docs-to-process/20251201-analysis-backend-db-audit.md`)

### ALL Issues Resolved

| Task | Description | Status |
|------|-------------|--------|
| T15 | Fix message_embeddings schema (add user_id column) | ✅ Applied |
| T16 | Fix RLS performance (`(select auth.uid())` pattern) | ✅ Applied |
| T17 | Consolidate duplicate RLS policies | ✅ Applied |
| T18.1 | Create pending_registrations table | ✅ Applied |
| T18.2 | Move extensions to dedicated schema | ✅ Applied |
| T046 | Update auth.py to use DB table | 🔄 Code pending (Sprint 2) |

### Migrations Applied to Supabase (via MCP)

| Migration ID | Name | Applied |
|--------------|------|---------|
| 20251201154007 | fix_message_embeddings_user_id | ✅ |
| 20251201154048 | add_auth_users_fk | ✅ |
| 20251201154125 | rls_performance_optimization | ✅ |
| 20251201154147 | consolidate_duplicate_policies | ✅ |
| 20251201154152 | extensions_and_pending_registrations | ✅ |
| 20251201154224 | cleanup_remaining_issues | ✅ |

**Supabase Advisor**: Only INFO-level warning (pending_registrations has no RLS - expected for backend-only table)

---

## Current Sprint: Streamlined Architecture Migration

### Documentation Updates ✅ COMPLETE
- [x] Update plan/master-plan.md with Cloud Run + Neo4j Aura + scheduled_events
- [x] Update todo/master-todo.md with pg_cron (no Celery)
- [x] Update memory/architecture.md with Option 1 diagram + scheduled_events
- [x] Update memory/backend.md with task endpoints + aiogram webhook mode
- [x] Update memory/integrations.md (Neo4j Aura, pg_cron, scheduled_events)
- [x] Update memory/game-mechanics.md (replace Celery with pg_cron)
- [x] Update memory/user-journeys.md (fix Celery reference)
- [x] Update memory/constitution.md (fix FalkorDB/Celery references)

### Code Migration (Neo4j) ❌ TODO
- [ ] Update nikita/config/settings.py (NEO4J_* env vars)
- [ ] Update nikita/memory/graphiti_client.py (Neo4j driver)
- [ ] Remove nikita/tasks/ Celery files (if any)

### Git Workflow
- [ ] Commit all documentation changes
- [ ] Push to origin/master

---

## References

- **Specs**: [../specs/](../specs/) - Feature specifications
- **Architecture**: [../memory/architecture.md](../memory/architecture.md)
- **Game Mechanics**: [../memory/game-mechanics.md](../memory/game-mechanics.md)
- **Master Plan**: [../plan/master-plan.md](../plan/master-plan.md)
