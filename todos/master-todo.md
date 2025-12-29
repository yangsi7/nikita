---
title: Nikita Game Master Todo
created: 2025-01-27T20:31:00Z
updated: 2025-12-27T18:15:00Z
session_id: e2e-test-spec017-verification
current_phase: 6
blocked_by: null
notes: "E2E Test Complete! FR-010+FR-012 verified, BUG-001 found (scoring analyzer). Spec 017: 96% complete. Next: Fix BUG-001, Portal Polish + Voice Agent"
---

# Master Todo - Nikita Game

**Source**: [../plans/master-plan.md](../plans/master-plan.md) | **Audit**: [docs-to-process/20251202-system-audit-final-report.md](../docs-to-process/20251202-system-audit-final-report.md)

---

## SDD Specification Status ✅ ALL 14 SPECS AUDITED

All specifications have complete SDD workflows (spec.md, plan.md, tasks.md, audit-report.md):

| Spec | Name | Impl | Audit | Notes |
|------|------|------|-------|-------|
| 001 | nikita-text-agent | ✅ 100% | PASS | 8 files, 156 tests |
| 002 | telegram-integration | ✅ 100% | PASS | 7 files, 86 tests, deployed to Cloud Run |
| 003 | scoring-engine | ✅ 100% | PASS | 60 tests, 4 files, B-2 integrated |
| 004 | chapter-boss-system | ✅ 100% | PASS | 142 tests, boss scoring integrated (B-2) |
| 005 | decay-system | ✅ 100% | PASS | 52 tests, DecayProcessor wired (B-3) |
| 006 | vice-personalization | ✅ 100% | PASS | 81 tests, C-1 injection fixed |
| 007 | voice-agent | ❌ 0% | PASS | Deferred to Phase 4 |
| 008 | player-portal | ⚠️ 70% | PASS | Backend 100%, Frontend 85%, Admin 0% |
| 009 | database-infrastructure | ✅ 100% | PASS | Foundation complete |
| 010 | api-infrastructure | ✅ 100% | PASS | Cloud Run deployed |
| 011 | background-tasks | ✅ 100% | PASS | All task routes working (B-3, C-5/6) |
| 012 | context-engineering | ✅ 100% | PASS | Phase 4 Integration COMPLETE - personalization pipeline wired |
| 013 | configuration-system | ✅ 100% | PASS | 89 tests, migration complete |
| 014 | engagement-model | ✅ 100% | PASS | 179 tests, 6 states, LLM detection (C-4) |
| 015 | onboarding-fix | ✅ 100% | PASS | OTP flow fixed, magic link deprecated |
| 017 | enhanced-onboarding | ✅ 96% | PASS | E2E VERIFIED 2025-12-27! FR-010+FR-012 live test, BUG-001 found |

### Critical Path: ✅ Complete → ✅ E2E Verified → Documentation Sync

### E2E Verification Results (2025-12-18)

| Step | Component | Result | Notes |
|------|-----------|--------|-------|
| 1 | /start webhook | ✅ PASS | 200 OK, routes to CommandHandler |
| 2 | Message webhook | ✅ PASS | Conversations created, LLM responses stored |
| 3 | Post-processing | ✅ PASS | Threads + thoughts + summaries working |
| 4 | /tasks/decay | ✅ PASS | Returns correctly, respects grace period |
| 5 | /tasks/summary | ✅ PASS | Generates summaries for eligible users |
| 6 | /tasks/cleanup | ✅ PASS | Cleans expired registrations |
| 7 | /tasks/process-conversations | ✅ PASS | Detects inactive conversations |

**Limitation**: Simulated webhooks can't receive Telegram responses (fake chat_id rejected by Telegram API)

### MVP Gap Fixes (2025-12-17/18)

| ID | Gap | Status | Details |
|----|-----|--------|---------|
| B-1 | Neo4j in production | ✅ | Cloud Run env vars configured |
| B-2 | Boss encounters | ✅ | Scoring integration in handler.py |
| B-3 | Decay endpoint | ✅ | DecayProcessor wired in tasks.py |
| C-1 | Vice injection | ✅ | Fixed role mismatch in post_processor.py |
| C-2 | Thread resolution | ✅ | Template + service + post-processor |
| C-3 | Chapter behaviors | ✅ | Already working via prompts |
| C-4 | Engagement states | ✅ | LLM detection + scoring multipliers |
| C-5+C-6 | Daily summaries | ✅ | Full /summary endpoint implementation |

**Test Status**: 1248 passed, 18 skipped

### Discovery Gaps (2025-12-29)

| ID | Gap | Severity | Status | Details |
|----|-----|----------|--------|---------|
| D-1 | pg_cron NOT scheduled | CRITICAL | ⚠️ TODO | Background jobs never run automatically |
| D-2 | Boss response handler MISSING | CRITICAL | ✅ FIXED | Users were stuck in boss_fight - added `_handle_boss_response()` to message_handler.py |
| D-3 | BossJudgment._call_llm was STUB | CRITICAL | ✅ FIXED | Always returned FAIL - now uses Pydantic AI + Claude Sonnet |
| D-4 | Scheduled message delivery stubbed | HIGH | ⚠️ TODO | `tasks.py:146-148` returns `delivered=0`, `scheduled_events` table missing |

**Project Status**: 92% production ready (up from 85% after D-2, D-3 fixes)

---

## SDD Implementation Phases

### Phase 0: Documentation Sync ✅ COMPLETE
- [x] Update README.md (Neo4j Aura, pg_cron, Cloud Run)
- [x] Update CLAUDE.md (root) with current status
- [x] Update nikita/CLAUDE.md with phase status
- [x] Update nikita/api/CLAUDE.md, engine/CLAUDE.md, db/CLAUDE.md
- [x] Update plans/master-plan.md with SDD orchestration
- [x] Update todos/master-todo.md with SDD phases
- [x] Git commit and push (e6274b7 - 131 files)

### Phase 1A: Security Hardening ✅ COMPLETE

| Task | Issue | Severity | Status |
|------|-------|----------|--------|
| SEC-01 | Webhook signature validation | CRITICAL | ✅ DONE (telegram.py:213-220) |
| SEC-02 | DB-backed rate limiting | HIGH | ✅ DONE (rate_limiter.py, migration 0007) |
| SEC-03 | HTML escaping in bot.py | HIGH | ✅ DONE (escape_html() function) |
| SEC-04 | Secret Manager migration | HIGH | ✅ DONE (Issue #8 - Neo4j credentials rotated, all secrets in GCP) |

### Phase 2: Configuration System (013) ✅ COMPLETE
- [x] Create nikita/config_data/ directory structure
- [x] Create YAML config files (game, chapters, engagement, scoring, decay, vices, schedule) - 7 files
- [x] Implement enums.py (9 enum classes, 19 tests)
- [x] Implement schemas.py (22 Pydantic models, 12 tests)
- [x] Implement ConfigLoader class (singleton, 21 tests)
- [x] Implement PromptLoader class (37 tests)
- [x] Implement ExperimentLoader class
- [x] Integration tests (89 tests total)

### Phase 3: Engagement Model (014) ✅ COMPLETE
- [x] T1.1-T1.6: Data models (EngagementState, metrics) - 20 tests
- [x] T2.1-T2.3: State machine (StateCalculator, TransitionEngine) - 27 tests
- [x] T3.1-T3.3: Calibration system (IdealPoint, tolerance bands) - 43 tests
- [x] T4.1-T4.3: Detection engine (drift detection, alerts) - 45 tests
- [x] T5.1-T5.2: Recovery system (recovery rates) - 25 tests
- [x] T6.1-T6.2: Integration (agent, scoring) - 18 tests
**Total: 179 tests passing**

### Phase 4: Scoring Engine (003) ✅ COMPLETE
- [x] ScoreCalculator class (calculator.py - 20 tests)
- [x] ResponseAnalyzer (analyzer.py - 14 tests)
- [x] Engagement multiplier integration
- [x] ScoringService with history logging (service.py - 6 tests)
**Total: 60 tests passing**

### Phase 5: Context Engineering (012) ✅ 100% COMPLETE
**Meta-Prompt Architecture ✅ COMPLETE**:
- [x] Created `nikita/meta_prompts/` module (service.py, models.py)
- [x] 4 meta-prompt templates (system_prompt, vice_detection, entity_extraction, thought_simulation)
- [x] Integration: template_generator.py delegates to MetaPromptService
- [x] Integration: post_processor.py uses MetaPromptService.extract_entities()
- [x] Integration: agent.py build_system_prompt() uses context module → MetaPromptService
- [x] Deprecated nikita_persona.py (kept as fallback)

**Phase 4 Integration ✅ COMPLETE (2025-12-21)**:
- [x] Wired build_system_prompt() into generate_response()
- [x] Added @agent.instructions add_personalized_context() decorator
- [x] Added profile/backstory loading to _load_context()
- [x] Added session.commit() to persist generated_prompts
- [x] Added 3 tests for generated_prompts logging

**Pipeline Architecture**:
- MetaPromptService implements all stages internally:
  - StateCollector → _load_context() loads user, metrics, vices, engagement
  - TemporalBuilder → _compute_nikita_* methods for time/mood/energy
  - MemorySummarizer → Context includes user_facts, threads, thoughts
  - MoodComputer → _compute_nikita_mood() based on chapter + time since contact
  - PromptAssembler → _format_template() generates personalized prompt
  - Validator → Token counting via _count_tokens()

### Phase 6: Enhanced Onboarding (017) ✅ 96% COMPLETE - E2E VERIFIED
**Memory Integration + First Nikita Message (2025-12-22)**:
- [x] FR-011: Mandatory onboarding completion (skip continues flow)
- [x] FR-012: Profile gate check in MessageHandler - ✅ **E2E VERIFIED 2025-12-27**
- [x] FR-013: Graphiti memory loading in MetaPromptService
- [x] FR-014: Conversation summaries (today/week) integration
- [x] FR-015: Per-conversation prompt generation verified
- [x] 4 first Nikita message tests + 3 memory context tests (34 total)
- [x] **Bug Fixes (2025-12-22)**:
  - ✅ [Issue #2](https://github.com/yangsi7/nikita/issues/2): Fixed via PR #5 (factory + field names)
  - ✅ [Issue #3](https://github.com/yangsi7/nikita/issues/3): Fixed via PR #6 (first message + 3 new tests)
- [x] **E2E Verification (2025-12-27)**:
  - ✅ FR-010: Existing user bypass verified via Telegram MCP
  - ✅ FR-012: Game-over detection verified (pre-canned response)
  - ✅ Historical flow: Complete onboarding reconstructed from 2025-12-22 messages
  - ⚠️ **PERF**: Neo4j cold start 83.8s (exceeds expected 60-73s)
  - 🐛 **BUG-001**: Scoring analyzer AttributeError on game-over responses (MEDIUM severity)
  - ⚠️ **Limitation**: Memory integration untested (user in game-over state)
**Report**: [docs-to-process/20251227-e2e-test-spec017-final-report.md](../docs-to-process/20251227-e2e-test-spec017-final-report.md)
**See**: [specs/017-enhanced-onboarding/tasks.md](../specs/017-enhanced-onboarding/tasks.md)

### Phases 7-11: See spec-specific tasks.md files

---

## Phase 1: Core Infrastructure ✅ COMPLETE
39 Python files, Supabase models, Graphiti memory, FastAPI skeleton, game constants, docs.

## Phase 2: Text Agent & Telegram ✅ COMPLETE
- **Text Agent**: ✅ 156 tests (agents/text/)
- **Telegram**: ✅ 86 tests (platforms/telegram/) - RegistrationHandler + MessageHandler
- **Database**: ✅ 8 migrations, RLS, 7 repos
- **Security**: ✅ SEC-01/02/03 hardening complete
- **Deployment**: ✅ Cloud Run revision 00030-mdh (100% traffic)

## Phase 3: Game Engine ✅ 100% COMPLETE (specs/003-006)
- [x] Scoring System (003) - ✅ 60 tests, 4 files
- [x] Chapter System (004) - ✅ 142 tests, ChapterStateMachine, boss logic, judgment
- [x] Decay System (005) - ✅ 52 tests, DecayCalculator, 99% coverage
- [x] Vice System (006) - ✅ 81 tests (70 unit + 11 integration), 100% complete
- [x] Background Tasks (011) - task routes ready, pg_cron config TODO

---

## Phase 4: Voice Agent ❌ TODO (specs/007-voice-agent)

- [ ] ElevenLabs Conversational AI 2.0 integration
- [ ] Server tools: get_context, get_memory, score_turn, update_memory
- [ ] Voice session management
- [ ] API routes: /voice/elevenlabs/server-tool

---

## Phase 5: Portal ⚠️ 70% COMPLETE (specs/008-player-portal)

- [x] Backend API (100%): 9 portal endpoints + admin endpoints
- [x] Next.js dashboard: ScoreCard, ChapterCard, MetricsGrid, EngagementCard, VicesCard, DecayWarning
- [x] History page: ScoreHistoryGraph, DailySummaryCard, ConversationList
- [x] Auth flow: Supabase SSR, magic links, proxy routes
- [x] Dashboard hooks: useUserStats, useEngagement, useVices, useDecayStatus, useScoreHistory
- [ ] Admin UI: User list, user detail, game controls (optional)
- [ ] Settings & Polish: 5 remaining tasks

---

## Current Sprint: Post-MVP Polish (2025-12-24)

### Status: Security ✅ Complete → Portal Polish + Voice Agent

**Completed This Sprint:**
- ✅ SEC-04: Neo4j credential rotation (Issue #8)
- ✅ All 4 security tasks now complete
- ✅ All credentials in Google Cloud Secret Manager

**Next Priorities:**
1. **Portal Polish** (Spec 008 - 30% remaining)
   - Admin UI: User list, user detail, game controls
   - Settings & Polish: 5 remaining tasks
2. **Voice Agent** (Spec 007 - 0% complete)
   - ElevenLabs Conversational AI 2.0 integration
   - Server tools: get_context, get_memory, score_turn, update_memory
   - Voice session management
3. **Production Hardening**
   - Monitoring/alerting setup
   - Error handling improvements
   - Performance optimization (Neo4j cold start = 60-73s)

**Project Status:**
- MVP: 99% complete (up from 98%)
- All 14 specs audited and PASS
- Test suite: 1248 passed, 18 skipped
- Deployment: Cloud Run (nikita-api)

---

## Completed Sprints (Archived)

- **Security Remediation Sprint (2025-12-01)**: ✅ 6 migrations applied, RLS fixed
- **Architecture Migration**: ✅ Cloud Run + Neo4j Aura + pg_cron
- **Meta-Prompt Architecture (2025-12-03)**: ✅ nikita/meta_prompts/ module complete
- **Configuration System (2025-12-04)**: ✅ 013 - 89 tests, migration complete
- **Engagement Model (2025-12-04)**: ✅ 014 - 179 tests, 6 states
- **Scoring Engine (2025-12-04)**: ✅ 003 - 60 tests, calibration integration

---

## References

- **Specs**: [../specs/](../specs/) - Feature specifications
- **Architecture**: [../memory/architecture.md](../memory/architecture.md)
- **Game Mechanics**: [../memory/game-mechanics.md](../memory/game-mechanics.md)
- **Master Plan**: [../plan/master-plan.md](../plan/master-plan.md)
