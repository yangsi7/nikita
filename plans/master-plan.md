---
title: Nikita Game Master Plan
created: 2025-01-27T20:23:00Z
updated: 2026-02-23T12:00:00Z
session_id: audit-remediation-phase7
status: architecture-reference
notes: "2026-02-23: Phase 7 audit remediation complete. Specs 070, 100-106 implemented."
---

> **Spec tracking has moved to [ROADMAP.md](../ROADMAP.md).** This document covers architecture and technical reference only.

# Nikita Game - Technical Architecture & Implementation Plan

## Key Configuration

- Boss thresholds: 55/60/65/70/75%
- Grace periods: 8/16/24/48/72 hours
- Decay rates: 0.8/0.6/0.4/0.3/0.2 per hour
- Claude model: claude-sonnet-4-6-20250514 (via `Models.sonnet()` registry)
- Test status: **5,347+ passed, 85 deselected, 0 failures** (2026-02-24)

### Security Status

| Issue | Severity | Status |
|-------|----------|--------|
| Webhook signature validation | CRITICAL | ✅ DONE (telegram.py) |
| DB-backed rate limiting | HIGH | ✅ DONE (rate_limiter.py) |
| HTML escaping | HIGH | ✅ DONE (escape_html()) |
| Secret Manager migration | HIGH | ✅ DONE (Issue #8 - all secrets in GCP Secret Manager) |

---

## Executive Summary

This document defines the complete technical architecture for **Nikita: Don't Get Dumped** - an AI girlfriend simulation game featuring dual-agent architecture (voice + text), temporal knowledge graphs for memory, and a sophisticated game engine with scoring, chapters, and boss encounters.

---

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACES                                 │
├─────────────────────┬─────────────────────┬─────────────────────────────────┤
│   Telegram Bot      │   Voice Calls       │      Player Portal              │
│   (aiogram 3.x)     │ (ElevenLabs Agent)  │      (Next.js/React)            │
│   • Text messages   │ • Real-time voice   │      • Stats dashboard          │
│   • Media support   │ • Emotion controls  │      • Score history            │
│   • Webhooks        │ • <100ms latency    │      • Chapter progress         │
└─────────┬───────────┴─────────┬───────────┴───────────────┬─────────────────┘
          │                     │                           │
          ▼                     ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY (FastAPI)                              │
│  ┌─────────────────┬─────────────────┬─────────────────┬──────────────────┐ │
│  │  /telegram/*    │  /voice/*       │  /portal/*      │  /webhooks/*     │ │
│  │  Bot webhooks   │  ElevenLabs CB  │  Stats API      │  External hooks  │ │
│  └─────────────────┴─────────────────┴─────────────────┴──────────────────┘ │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Conversation Orchestrator                          │   │
│  │  • Route to appropriate agent (voice/text)                           │   │
│  │  • Inject context (chapter, score, history, vice preferences)        │   │
│  │  • Process response through scoring engine                           │   │
│  │  • Update memory graphs                                              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────────┐
│   VOICE AGENT       │   │    TEXT AGENT       │   │     GAME ENGINE         │
│   (ElevenLabs)      │   │    (Pydantic AI)    │   │                         │
├─────────────────────┤   ├─────────────────────┤   ├─────────────────────────┤
│ • Conv AI 2.0 SDK   │   │ • Claude Sonnet LLM │   │ • Scoring System        │
│ • Server Tools:     │   │ • Structured Output │   │ • Chapter Manager       │
│   - get_context     │   │ • Tools:            │   │ • Boss Encounters       │
│   - score_response  │   │   - get_memory      │   │ • Decay Calculator      │
│   - update_memory   │   │   - score_response  │   │ • Vice Discovery        │
│ • Emotion controls  │   │   - update_state    │   │ • Conflict Handler      │
│ • Voice synthesis   │   │ • Dependency inject │   │ • Daily Summaries       │
└─────────┬───────────┘   └─────────┬───────────┘   └───────────┬─────────────┘
          │                         │                           │
          └─────────────────────────┼───────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY & KNOWLEDGE LAYER                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                  SupabaseMemory (pgVector)                            │   │
│  │  • Semantic search via pgVector embeddings                          │   │
│  │  • Fact deduplication + conflict resolution                         │   │
│  │  • User facts, relationship context, conversation memory            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PERSISTENCE LAYER                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Supabase (PostgreSQL + pgVector)                  │   │
│  │  • User profiles + auth        • Conversation logs                   │   │
│  │  • Relationship state          • pgVector embeddings (memory)        │   │
│  │  • Score history               • Vice preferences                    │   │
│  │  • Chapter/Boss progress       • Daily summaries                     │   │
│  │  • Life events + social circle • Psyche state                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack Specification

| Layer | Technology | Purpose | Documentation |
|-------|------------|---------|---------------|
| **Voice Agent** | ElevenLabs Conversational AI 2.0 | Real-time voice conversations | [Docs](https://elevenlabs.io/docs/agents-platform) |
| **Text Agent** | Pydantic AI + Claude Sonnet | Structured text responses | [Docs](https://ai.pydantic.dev/) |
| **API Backend** | FastAPI (Python 3.11+) | REST/WebSocket API | [Docs](https://fastapi.tiangolo.com/) |
| **Telegram Bot** | aiogram 3.x | Async Telegram integration | [Docs](https://docs.aiogram.dev/) |
| **Memory** | SupabaseMemory (pgVector) | Semantic search, fact storage, dedup | [Spec 042](../specs/042-unified-pipeline/) |
| **Database** | Supabase (PostgreSQL + pgVector) | Persistence + embeddings + memory | [Docs](https://supabase.com/docs) |
| **Scheduling** | pg_cron + Supabase Edge Functions | Background jobs (decay, summaries) | [Docs](https://supabase.com/docs/guides/database/extensions/pg_cron) |
| **Player Portal** | Next.js + React | Stats dashboard | [Docs](https://nextjs.org/docs) |
| **Compute** | Google Cloud Run | Serverless API hosting (scales to zero) | [Docs](https://cloud.google.com/run/docs) |

---

## 3. Module Breakdown

### 3.1 Core Modules

```
nikita/
├── agents/                    # AI Agent Implementations
│   ├── base_agent.py          # Shared agent interface
│   ├── voice_agent.py         # ElevenLabs integration
│   ├── text_agent.py          # Pydantic AI text agent
│   └── tools/                 # Shared tools for both agents
│       ├── memory_tools.py    # get_memory, update_memory
│       ├── scoring_tools.py   # evaluate_response, get_score
│       └── context_tools.py   # get_chapter, get_vice_prefs
│
├── engine/                    # Game Engine
│   ├── scoring/
│   │   ├── calculator.py      # Composite score calculation
│   │   ├── metrics.py         # Intimacy, Passion, Trust, Secureness
│   │   └── analyzer.py        # Response analysis for scoring
│   ├── chapters/
│   │   ├── state_machine.py   # Chapter progression FSM
│   │   ├── boss_encounters.py # Boss fight logic
│   │   └── conditions.py      # Unlock conditions
│   ├── decay/
│   │   ├── calculator.py      # Daily decay by chapter
│   │   └── scheduler.py       # Decay job scheduling
│   ├── vice/
│   │   ├── discovery.py       # Vice preference detection
│   │   ├── categories.py      # 8 vice categories
│   │   └── intensity.py       # Intensity level tracking
│   └── conflicts/
│       ├── detector.py        # Conflict type detection
│       ├── resolution.py      # Resolution scoring
│       └── silence.py         # Strategic silence logic
│
├── memory/                    # Memory System (pgVector)
│   ├── supabase_memory.py     # SupabaseMemory (search, add_fact, dedup)
│   └── models.py              # MemoryFact, SearchResult
│
├── platforms/                 # Platform Integrations
│   ├── telegram/
│   │   ├── bot.py             # aiogram bot setup
│   │   ├── handlers.py        # Message handlers
│   │   └── middleware.py      # Auth, rate limiting
│   ├── voice/
│   │   ├── elevenlabs.py      # ElevenLabs SDK wrapper
│   │   ├── callbacks.py       # Server tool callbacks
│   │   └── session.py         # Voice session management
│   └── portal/
│       └── api.py             # Portal REST endpoints
│
├── db/                        # Database Layer
│   ├── models/                # SQLAlchemy/Pydantic models
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── score_history.py
│   │   └── daily_summary.py
│   ├── repositories/          # Data access patterns
│   └── migrations/            # Supabase migration stubs (90 comment-only files)
│
├── prompts/                   # Prompt Templates
│   ├── nikita_persona.py      # Core personality
│   ├── chapter_contexts.py    # Per-chapter variations
│   ├── boss_scripts.py        # Boss encounter prompts
│   └── summary_templates.py   # Daily/conversation summaries
│
├── api/                       # FastAPI Application
│   ├── main.py                # App entrypoint
│   ├── routes/
│   │   ├── telegram.py        # Webhook handlers
│   │   ├── voice.py           # ElevenLabs callbacks
│   │   ├── portal.py          # Stats API
│   │   └── admin.py           # Admin endpoints
│   └── middleware/
│       ├── auth.py
│       └── rate_limit.py
│
└── tasks/                     # Background Jobs
    ├── decay_task.py          # Daily decay calculation
    ├── summary_task.py        # Generate daily summaries
    └── cleanup_task.py        # Old data cleanup
```

---

## 4. Data Flow Diagrams

### 4.1 Message Processing Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────────┐
│   Telegram   │────▶│  API Gateway │────▶│      Conversation Orchestrator   │
│   Message    │     │  /telegram/* │     │                                  │
└──────────────┘     └──────────────┘     └──────────────┬───────────────────┘
                                                         │
                     ┌───────────────────────────────────┼───────────────────┐
                     │                                   │                   │
                     ▼                                   ▼                   ▼
         ┌───────────────────┐               ┌───────────────────┐  ┌────────────────┐
         │  1. Load Context  │               │  2. Get Memory    │  │ 3. Get State   │
         │  (Chapter, Score, │               │  (pgVector search)│  │ (Vice prefs,   │
         │   Vice prefs)     │               │                   │  │  last convo)   │
         └─────────┬─────────┘               └─────────┬─────────┘  └───────┬────────┘
                   │                                   │                    │
                   └───────────────────────────────────┼────────────────────┘
                                                       │
                                                       ▼
                                          ┌────────────────────────┐
                                          │   4. Build Prompt      │
                                          │   • Nikita persona     │
                                          │   • Chapter context    │
                                          │   • Memory injection   │
                                          │   • User message       │
                                          └───────────┬────────────┘
                                                      │
                                                      ▼
                                          ┌────────────────────────┐
                                          │   5. Text Agent        │
                                          │   (Pydantic AI +       │
                                          │    Claude Sonnet)      │
                                          └───────────┬────────────┘
                                                      │
                     ┌────────────────────────────────┼────────────────────────┐
                     │                                │                        │
                     ▼                                ▼                        ▼
         ┌───────────────────┐            ┌───────────────────┐    ┌───────────────────┐
         │  6. Score Response│            │  7. Update Memory │    │  8. Check Boss    │
         │  • Analyze text   │            │  • pgVector store │    │  • Threshold met? │
         │  • Update metrics │            │  • User graph     │    │  • Trigger boss?  │
         │  • Apply deltas   │            │  • Relationship   │    │                   │
         └─────────┬─────────┘            └─────────┬─────────┘    └─────────┬─────────┘
                   │                                │                        │
                   └────────────────────────────────┼────────────────────────┘
                                                    │
                                                    ▼
                                          ┌────────────────────────┐
                                          │   9. Send Response     │
                                          │   via Telegram         │
                                          └────────────────────────┘
```

### 4.2 Voice Call Flow

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────────────┐
│  User initiates  │─────▶│  ElevenLabs      │─────▶│   Agent receives call    │
│  voice call      │      │  Conversation    │      │   (WebSocket connection) │
└──────────────────┘      └──────────────────┘      └────────────┬─────────────┘
                                                                 │
                                                                 ▼
                                                    ┌────────────────────────┐
                                                    │   Server Tool Calls    │
                                                    │   (via ElevenLabs SDK) │
                                                    └────────────┬───────────┘
                          ┌──────────────────────────────────────┼─────────────────┐
                          │                                      │                 │
                          ▼                                      ▼                 ▼
              ┌───────────────────┐                  ┌───────────────────┐  ┌─────────────┐
              │  get_context()    │                  │  get_memory()     │  │ score_turn()│
              │  Returns:         │                  │  Returns:         │  │ Updates:    │
              │  • Chapter        │                  │  • Recent history │  │ • Metrics   │
              │  • Score          │                  │  • User facts     │  │ • Score     │
              │  • Vice prefs     │                  │  • Relationship   │  │             │
              └───────────────────┘                  └───────────────────┘  └─────────────┘
                          │                                      │                 │
                          └──────────────────────────────────────┼─────────────────┘
                                                                 │
                                                                 ▼
                                                    ┌────────────────────────┐
                                                    │   Voice response       │
                                                    │   (with emotion ctrl)  │
                                                    └────────────────────────┘
```

---

## 5. Scoring System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SCORING PIPELINE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Response Analyzer (LLM-based)                      │   │
│  │                                                                       │   │
│  │  Input: User message + Nikita response + Context                     │   │
│  │  Output: Structured analysis (Pydantic model)                        │   │
│  │                                                                       │   │
│  │  class ResponseAnalysis(BaseModel):                                  │   │
│  │      intimacy_delta: float      # -10 to +10                         │   │
│  │      passion_delta: float       # -10 to +10                         │   │
│  │      trust_delta: float         # -10 to +10                         │   │
│  │      secureness_delta: float    # -10 to +10                         │   │
│  │      conflict_detected: bool                                         │   │
│  │      conflict_type: Optional[ConflictType]                           │   │
│  │      vice_signals: List[ViceSignal]                                  │   │
│  │      engagement_quality: float  # 0 to 1                             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Score Calculator                                   │   │
│  │                                                                       │   │
│  │  COMPOSITE_SCORE = (                                                 │   │
│  │      intimacy * 0.30 +                                               │   │
│  │      passion * 0.25 +                                                │   │
│  │      trust * 0.25 +                                                  │   │
│  │      secureness * 0.20                                               │   │
│  │  )                                                                   │   │
│  │                                                                       │   │
│  │  Each metric: 0-100, clamped after delta application                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    State Updater                                      │   │
│  │                                                                       │   │
│  │  • Update user_metrics table                                         │   │
│  │  • Update users.relationship_score                                   │   │
│  │  • Check chapter advancement conditions                              │   │
│  │  • Trigger boss if threshold met                                     │   │
│  │  • Log score_history                                                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Game State Machine

```
                                    ┌────────────────┐
                                    │   NEW_USER     │
                                    │   score: 50%   │
                                    └───────┬────────┘
                                            │ First message
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CHAPTER 1: CURIOSITY                            │
│                              Days 1-3 | Decay: 0.8/hr (cap 12%/day)          │
│  ┌─────────────────┐                                    ┌─────────────────┐ │
│  │  ACTIVE_PLAY    │──────────────────────────────────▶│  BOSS_AVAILABLE │ │
│  │  Score < 55%    │        Score >= 55%                │  "Worth my time"│ │
│  └─────────────────┘                                    └────────┬────────┘ │
│          │                                                       │          │
│          │ Score = 0%                            ┌───────────────┴──────┐   │
│          │                                       │                      │   │
│          ▼                                       ▼                      ▼   │
│  ┌─────────────────┐                    ┌─────────────┐        ┌─────────┐ │
│  │   GAME_OVER     │◀───────────────────│  BOSS_FAIL  │        │BOSS_PASS│ │
│  │   (Dumped)      │   3 failures       │  attempts++ │        │         │ │
│  └─────────────────┘                    └─────────────┘        └────┬────┘ │
└─────────────────────────────────────────────────────────────────────┼──────┘
                                                                      │
                                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CHAPTER 2: INTRIGUE                             │
│                              Days 4-7 | Decay: 0.6/hr (cap 10%/day)          │
│  [Same pattern: ACTIVE → BOSS_AVAILABLE (60%) → PASS/FAIL]                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CHAPTER 3: INVESTMENT                           │
│                              Days 8-11 | Decay: 0.4/hr (cap 8%/day)          │
│  [Same pattern: ACTIVE → BOSS_AVAILABLE (65%) → PASS/FAIL]                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CHAPTER 4: INTIMACY                             │
│                              Days 12-16 | Decay: 0.3/hr (cap 6%/day)         │
│  [Same pattern: ACTIVE → BOSS_AVAILABLE (70%) → PASS/FAIL]                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CHAPTER 5: ESTABLISHED                          │
│                              Days 17-21 | Decay: 0.2/hr (cap 4%/day)         │
│  ┌─────────────────┐                                    ┌─────────────────┐ │
│  │  ACTIVE_PLAY    │──────────────────────────────────▶│  FINAL_BOSS     │ │
│  │  Score < 75%    │        Score >= 75%                │  "Ultimate test"│ │
│  └─────────────────┘                                    └────────┬────────┘ │
│                                                                  │          │
│                                                                  ▼          │
│                                                         ┌─────────────────┐ │
│                                                         │    GAME_WON     │ │
│                                                         │   Victory msg   │ │
│                                                         └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Memory System (SupabaseMemory — pgVector)

**Implementation**: `nikita/memory/supabase_memory.py` (Spec 042 — replaced Graphiti/Neo4j)

### Memory Architecture
| Component | Purpose |
|-----------|---------|
| pgVector embeddings | Semantic search over user facts and conversation context |
| Fact deduplication | Prevents duplicate facts from accumulating |
| Pipeline integration | 10-stage async pipeline extracts + stores facts automatically |

### Key Methods
- `search(query, user_id, limit)` — Semantic search via pgVector
- `add_fact(fact, user_id)` — Store learned fact with embedding
- `get_context_for_prompt(user_message, user_id)` — Build LLM context

---

## 8. Agent Implementation

**Text Agent** ✅ COMPLETE - `nikita/agents/text/` (8 files, 1072 lines)
- `agent.py` - Pydantic AI agent with dynamic system prompt
- `handler.py` - MessageHandler with timing + skip logic
- `deps.py` - NikitaDeps dependency container
- `timing.py` - ResponseTimer (gaussian delay distribution)
- `skip.py` - SkipDecision (chapter-based skip rates)
- `facts.py` - FactExtractor (LLM-based fact extraction)
- `tools.py` - recall_memory, note_user_fact tools

**Voice Agent** ✅ COMPLETE - `nikita/agents/voice/` (14 files, 186 tests)

---

## 8.5 Meta-Prompt Architecture ✅ COMPLETE

**Problem Solved**: All prompt generation used static f-string templates ("dumb templates"). Now uses LLM-generated prompts via meta-prompts.

**Module**: `nikita/meta_prompts/` (3 Python files, 4 templates, 1 CLAUDE.md)

```
nikita/meta_prompts/
├── __init__.py              # Module exports
├── service.py               # MetaPromptService (Claude Haiku)
├── models.py                # ViceProfile, MetaPromptContext, GeneratedPrompt
├── CLAUDE.md                # Module documentation
└── templates/
    ├── system_prompt.meta.md      # 6-layer system prompt generation
    ├── vice_detection.meta.md     # 8 vice categories detection
    ├── entity_extraction.meta.md  # Post-processing extraction
    └── thought_simulation.meta.md # Nikita's inner life
```

**Key Classes**:
- `MetaPromptService`: Central service for all meta-prompt operations
- `MetaPromptContext`: Aggregates user, game state, vice profile, temporal, memory context
- `ViceProfile`: 8 vice category intensities (0-5 each)
- `GeneratedPrompt`: Result with content, token count, timing

**Integration Points**:
- `template_generator.py` → delegates to MetaPromptService.generate_system_prompt()
- `post_processor.py` → uses MetaPromptService.extract_entities()
- `agent.py` → build_system_prompt() uses context module → MetaPromptService

**Key Decisions**:
- **Model**: Claude 3.5 Haiku (fast ~150ms, cheap ~$0.005/call)
- **Caching**: None initially (low cache hit rate due to temporal context)
- **Content**: Full adult - NO limits except underage (legal requirement)
- **Vice Integration**: User vice_profile actively shapes prompts

---

## 9. Database Schema

*Full schema: `memory/backend.md` and `nikita/db/models/`*

| Table | Purpose |
|-------|---------|
| users | Core user state, chapter, score |
| user_metrics | Hidden sub-metrics (intimacy, passion, trust, secureness) |
| user_vice_preferences | Vice category tracking (8 categories) |
| conversations | Session logs with JSONB messages |
| score_history | Score changes over time |
| daily_summaries | Nikita's in-character recaps |
| scheduled_events | Proactive messaging queue (delayed texts, outbound calls) |
| message_embeddings | pgVector embeddings for semantic search |

---

## 10. API Endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/telegram/webhook` | POST | Handle Telegram bot messages (aiogram in webhook mode) |
| `/tasks/decay` | POST | Apply daily decay (pg_cron triggered) |
| `/tasks/deliver` | POST | Deliver scheduled messages (pg_cron triggered) |
| `/tasks/summary` | POST | Generate daily summaries (pg_cron triggered) |
| `/voice/elevenlabs/server-tool` | POST | ElevenLabs server tool callbacks |
| `/portal/stats/{user_id}` | GET | Player stats for dashboard |

*Full endpoint specs: `specs/002-telegram-integration`, `specs/007-voice-agent`, `specs/008-player-portal`*

---

## 11. Background Tasks (pg_cron + Edge Functions)

**Architecture**: pg_cron triggers Supabase Edge Functions → calls Cloud Run API endpoints

| Task | Schedule | Trigger | Purpose |
|------|----------|---------|---------|
| `apply_daily_decay` | Daily 3am UTC | pg_cron → Edge Function → POST /tasks/decay | Apply chapter-specific score decay |
| `deliver_pending_msgs` | Every 30s | pg_cron → Edge Function → POST /tasks/deliver | Send delayed Nikita responses |
| `generate_daily_summaries` | Daily 4am UTC | pg_cron → Edge Function → POST /tasks/summary | Generate Nikita's in-character recap |

**Why not Celery/Redis?** Eliminates operational overhead. pg_cron is built into Supabase, Edge Functions are serverless.

*Full task specs: `specs/011-background-tasks`*

---

## 12. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT (Serverless)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER INTERFACES                                                             │
│  ┌────────────────────┬────────────────────┬────────────────────────────┐   │
│  │   Telegram Bot     │   Voice Calls      │   Player Portal             │   │
│  │   (aiogram 3.x)    │   (Twilio)         │   (Next.js on Vercel)       │   │
│  └─────────┬──────────┴─────────┬──────────┴──────────────┬─────────────┘   │
│            │ webhook            │ audio stream            │ REST API        │
│            │                    ▼                         │                 │
│            │           ┌────────────────────┐             │                 │
│            │           │  ELEVENLABS        │             │                 │
│            │           │  Conv AI 2.0       │             │                 │
│            │           │  (handles audio)   │             │                 │
│            │           └─────────┬──────────┘             │                 │
│            │                     │ Server Tools (REST)    │                 │
│            ▼                     ▼                        ▼                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        GOOGLE CLOUD RUN                               │  │
│  │                    FastAPI + Pydantic AI + Claude                     │  │
│  │                         (Python 3.11+)                                │  │
│  │  ─────────────────────────────────────────────────────────────────    │  │
│  │  Endpoints:                                                           │  │
│  │  • POST /telegram/webhook     (Telegram messages)                     │  │
│  │  • POST /voice/get-context    (ElevenLabs Server Tool)                │  │
│  │  • POST /voice/score-turn     (ElevenLabs Server Tool)                │  │
│  │  • POST /tasks/decay          (pg_cron webhook)                       │  │
│  │  • POST /tasks/deliver        (pg_cron webhook)                       │  │
│  │  • GET  /portal/stats/{id}    (Portal API)                            │  │
│  │                                                                       │  │
│  │  Scaling: min=0, max=10 (scales to zero when idle)                    │  │
│  └─────────┬───────────────────┬───────────────────────┬─────────────────┘  │
│            │                   │                       │                    │
│            ▼                   ▼                       ▼                    │
│  ┌──────────────────────────────┐  ┌───────────────────────┐             │
│  │  SUPABASE                    │  │  LLM SERVICES         │             │
│  │  ────────────                │  │  ───────────          │             │
│  │  • Auth (OTP)                │  │  • Claude Sonnet 4    │             │
│  │  • PostgreSQL + pgVector     │  │  • OpenAI Embeddings  │             │
│  │  • SupabaseMemory (facts)    │  │                       │             │
│  │  • pg_cron (triggers tasks)  │  │                       │             │
│  │  • Edge Functions            │  │                       │             │
│  └──────────────────────────────┘  └───────────────────────┘             │
│                                                                              │
│  Voice Cold Start Mitigation:                                               │
│    Default: min-instances=0 (scales to zero)                                │
│    If latency issues: set min-instances=1 (~$6/mo extra)                    │
│                                                                              │
│  Cost Estimate: $35-65/mo (usage-based, can scale to near-free)             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Key Documentation References

| Resource | URL |
|----------|-----|
| ElevenLabs Agents SDK | https://elevenlabs.io/docs/agents-platform/libraries/python |
| ElevenLabs Server Tools | https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools |
| Pydantic AI Docs | https://ai.pydantic.dev/ |
| Pydantic AI Agents | https://ai.pydantic.dev/agents/ |
| Pydantic AI Tools | https://ai.pydantic.dev/tools/ |
| SupabaseMemory (Spec 042) | ../specs/042-unified-pipeline/spec.md |
| Supabase Python | https://supabase.com/docs/reference/python |
| Supabase pgVector | https://supabase.com/docs/guides/ai |
| aiogram 3.x | https://docs.aiogram.dev/ |
| FastAPI WebSockets | https://fastapi.tiangolo.com/advanced/websockets/ |

---

## 15. Architecture Decisions (Finalized)

### 15.1 Hosting
- **Primary**: Supabase hosted (PostgreSQL + Auth + Storage)
- **API**: Self-hosted or Supabase Edge Functions
- **Memory**: SupabaseMemory (pgVector — replaced Neo4j Aura in Spec 042)

### 15.2 ElevenLabs Configuration
- **Agent ID**: `PB6BdkFkZLbI39GHdnbQ` (abstracted for easy switching)
- **Design**: Agent ID configurable per chapter/mood - stored in config, not hardcoded

```python
# config/agents.py
ELEVENLABS_AGENTS = {
    "default": "PB6BdkFkZLbI39GHdnbQ",
    "chapter_1": "PB6BdkFkZLbI39GHdnbQ",  # Can customize per chapter
    "boss_fight": "PB6BdkFkZLbI39GHdnbQ",  # Different voice for intensity
}
```

### 15.3 Database Architecture (REVISED — Spec 042)

**Supabase handles ALL persistent data AND memory:**
- User profiles, auth (OTP)
- Conversation logs, transcriptions
- Score history, daily summaries
- **SupabaseMemory (pgVector)** — semantic search, fact storage, deduplication
- Vice preferences, life events, social circle, psyche state
- Game state (chapters, boss, engagement)

**Note**: Neo4j/Graphiti was used in early specs but replaced by pgVector-based SupabaseMemory in Spec 042 (Feb 2026). All memory operations now use Supabase PostgreSQL with pgVector extension.

### 15.5 Authentication
- **Method**: Supabase Auth with OTP (phone/email magic link)
- **Flow**: Telegram bot → links to portal → OTP login → session
- **No passwords** - simple magic link flow

### 15.6 Content Moderation
- **Level**: None (0%)
- **18+ game**: Full adult content allowed
- **Vice system**: Unrestricted discussion of sex, drugs, etc.
- **No content filtering** on LLM outputs

---

## 16. Revised Tech Stack (Streamlined Nov 2025)

| Layer | Technology | Cost | Purpose |
|-------|------------|------|---------|
| **Compute** | Google Cloud Run | $0-20/mo | Serverless API hosting (scales to zero) |
| **Database** | Supabase Pro | ~$25/mo | All persistent data, embeddings, auth, pg_cron |
| **Memory** | SupabaseMemory (pgVector) | $0 (included in Supabase) | Semantic search, fact storage |
| **Voice Agent** | ElevenLabs Conv AI 2.0 | ~$4/user/mo | Real-time voice (Server Tools pattern) |
| **Text Agent** | Pydantic AI + Claude Sonnet | ~$15/user/mo | Structured text responses |
| **Scheduling** | pg_cron + Edge Functions | $0 (included) | Background jobs (decay, msg delivery) |
| **Telegram Bot** | aiogram 3.x | $0 | Async Telegram integration |
| **Portal** | Next.js | Vercel free | Stats dashboard |
| **Voice Dial** | Twilio | $10-20/mo | Voice call initiation |

**What we removed (Senior Architect Review):**
- ❌ Celery + Redis (over-engineered for MVP)
- ❌ Self-hosted FalkorDB (maintenance burden)
- ❌ Always-on VPS/VM (wasteful for idle periods)

**Estimated monthly cost (MVP)**: $35-65/mo (usage-based, can scale to near-free)

---

## 17. ElevenLabs Agent Abstraction

*Implementation: `nikita/config/elevenlabs.py`*

- Agent IDs configurable per chapter/mood/boss_fight
- `get_agent_id(chapter, mood, is_boss)` → returns appropriate agent ID
- Environment prefix: `ELEVENLABS_`

---

## 18. Security Remediation (Dec 2025)

**Source**: Backend/DB Security Audit (`docs-to-process/20251201-analysis-backend-db-audit.md`)
**Verified**: Against actual Supabase database via MCP tools (2025-12-01)

### 18.1 Identified Issues

| Issue | Severity | Status | Migration |
|-------|----------|--------|-----------|
| message_embeddings missing user_id | CRITICAL | ✅ Fixed | 0003 |
| RLS policies use `auth.uid()` (slow) | HIGH | ✅ Fixed | 0004 |
| Duplicate permissive policies | HIGH | ✅ Fixed | 0005 |
| Extensions in public schema | MEDIUM | ✅ Fixed | 0006 |
| In-memory pending_registrations | HIGH | ✅ Table created | 0006 |

### 18.2 RLS Best Practices (CRITICAL)

```sql
-- ALWAYS use (select auth.uid()) NOT auth.uid()
-- This evaluates once per query instead of per row (50-100x faster)

CREATE POLICY "users_own_data" ON users
    FOR ALL USING (id = (select auth.uid()))
    WITH CHECK (id = (select auth.uid()));

-- Use single FOR ALL policy, NOT separate SELECT/INSERT/UPDATE policies
```

### 18.3 Migrations Created

| Migration | Purpose | Location |
|-----------|---------|----------|
| 0003 | Fix message_embeddings user_id | `nikita/db/migrations/versions/20251128_0003_fix_message_embeddings.py` |
| 0004 | RLS performance optimization | `nikita/db/migrations/versions/20251128_0004_rls_performance.py` |
| 0005 | Consolidate duplicate policies | `nikita/db/migrations/versions/20251128_0005_consolidate_policies.py` |
| 0006 | Extensions schema + pending_registrations | `nikita/db/migrations/versions/20251128_0006_extensions_pending_reg.py` |

**Apply**: Use Supabase MCP `apply_migration` tool (Alembic is no longer used — all migrations are comment-only stubs applied via Supabase MCP)

---

*Documentation: see memory/*.md files for detailed architecture*
