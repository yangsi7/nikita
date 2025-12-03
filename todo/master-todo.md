---
title: Nikita Game Master Todo
created: 2025-01-27T20:31:00Z
updated: 2025-12-03T17:00:00Z
session_id: nikita-meta-prompts-complete
current_phase: 1A
blocked_by: null
notes: "Meta-prompt architecture COMPLETE. Next: Phase 1A (Security) + Phase 2 (Configuration) in parallel."
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
| 012 | context-engineering | ⚠️ 50% | PASS | Meta-prompts DONE, pipeline TODO |
| 013 | configuration-system | ❌ 0% | PASS | **PRIORITY 1** - blocks all engine specs |
| 014 | engagement-model | ❌ 0% | PASS | **Critical** - 6 states |

### Critical Path: 013 → 014 → 012 → Game Engine → Voice → Portal

---

## SDD Implementation Phases

### Phase 0: Documentation Sync ✅ COMPLETE
- [x] Update README.md (Neo4j Aura, pg_cron, Cloud Run)
- [x] Update CLAUDE.md (root) with current status
- [x] Update nikita/CLAUDE.md with phase status
- [x] Update nikita/api/CLAUDE.md, engine/CLAUDE.md, db/CLAUDE.md
- [x] Update plans/master-plan.md with SDD orchestration
- [x] Update todo/master-todo.md with SDD phases
- [x] Git commit and push (e6274b7 - 131 files)

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

### Phase 5: Context Engineering (012) ⚠️ 50% COMPLETE
**Meta-Prompt Architecture ✅ COMPLETE**:
- [x] Created `nikita/meta_prompts/` module (service.py, models.py)
- [x] 4 meta-prompt templates (system_prompt, vice_detection, entity_extraction, thought_simulation)
- [x] Integration: template_generator.py delegates to MetaPromptService
- [x] Integration: post_processor.py uses MetaPromptService.extract_entities()
- [x] Integration: agent.py build_system_prompt() uses context module → MetaPromptService
- [x] Deprecated nikita_persona.py (kept as fallback)

**Pipeline Stages ❌ TODO**:
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
39 Python files, Supabase models, Graphiti memory, FastAPI skeleton, game constants, docs.

## Phase 2: Text Agent ⚠️ 95% COMPLETE
- **Text Agent**: ✅ 156 tests (agents/text/)
- **Telegram**: ✅ 74 tests (platforms/telegram/)
- **Database**: ✅ 8 migrations, RLS, 7 repos
- **Remaining**:
  - [ ] Wire text_agent in MessageHandler (currently None)
  - [ ] Deploy to Cloud Run + set webhook URL

## Phase 3: Game Engine ❌ TODO (specs/003-006)
- [ ] Scoring System (003) - ScoreCalculator, ResponseAnalysis
- [ ] Chapter System (004) - ChapterStateMachine, boss logic
- [ ] Decay System (005) - DecayCalculator, pg_cron
- [ ] Vice System (006) - ViceDiscovery, 8 categories
- [x] Background Tasks (011) - task routes ready, pg_cron config TODO

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

## Completed Sprints (Archived)

- **Security Remediation Sprint (2025-12-01)**: ✅ 6 migrations applied, RLS fixed
- **Architecture Migration**: ✅ Cloud Run + Neo4j Aura + pg_cron
- **Meta-Prompt Architecture (2025-12-03)**: ✅ nikita/meta_prompts/ module complete

---

## References

- **Specs**: [../specs/](../specs/) - Feature specifications
- **Architecture**: [../memory/architecture.md](../memory/architecture.md)
- **Game Mechanics**: [../memory/game-mechanics.md](../memory/game-mechanics.md)
- **Master Plan**: [../plan/master-plan.md](../plan/master-plan.md)
