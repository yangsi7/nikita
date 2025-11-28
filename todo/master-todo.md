---
title: Nikita Game Master Todo
created: 2025-01-27T20:31:00Z
updated: 2025-11-28
session_id: nikita-docs-sync
current_phase: 2
blocked_by: null
---

# Master Todo - Nikita Game

**Source**: [../plan/master-plan.md](../plan/master-plan.md) Section 13

---

## Phase 1: Core Infrastructure ✅ COMPLETE

- [x] Project structure (39 Python files)
- [x] Supabase database models
- [x] FalkorDB + Graphiti (NikitaMemory class)
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

### Telegram Integration ❌ TODO (specs/002-telegram-integration)
- [ ] Build Telegram bot with aiogram → `nikita/platforms/telegram/`
- [ ] Telegram webhook endpoint → `nikita/api/routes/telegram.py`
- [ ] Auth + rate limiting middleware

### Database Layer ❌ TODO
- [ ] Implement repositories (user, conversation, metrics)
- [ ] Set up Alembic migrations
- [ ] Deploy to Supabase + RLS policies

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
  - Celery task: apply_daily_decay()

- [ ] **Vice System** (specs/006-vice-personalization)
  - ViceDiscovery + intensity tracking
  - 8 vice categories

- [ ] **Background Tasks** (Celery)
  - Daily decay task
  - Daily summary generation

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

## Current Sprint: Documentation Sync

- [ ] Sync memory/architecture.md with actual state
- [ ] Update memory/backend.md with text agent section
- [ ] Verify memory/game-mechanics.md constants
- [ ] Complete SDD workflow for specs 002-008

---

## References

- **Specs**: [../specs/](../specs/) - Feature specifications
- **Architecture**: [../memory/architecture.md](../memory/architecture.md)
- **Game Mechanics**: [../memory/game-mechanics.md](../memory/game-mechanics.md)
- **Master Plan**: [../plan/master-plan.md](../plan/master-plan.md)
