---
title: Nikita Game Master Plan
created: 2025-01-27T20:23:00Z
updated: 2025-11-29
session_id: nikita-streamlined-arch
status: active
phases_complete: [1]
phases_in_progress: [2]
phases_pending: [3, 4, 5]
notes: "Text agent complete. Streamlined to Cloud Run + Neo4j Aura + pg_cron (no Celery/Redis)"
---

# Nikita Game - Technical Architecture & Implementation Plan

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
│  │                     Graphiti (Temporal KG)                            │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐  │   │
│  │  │  Nikita Graph  │  │   User Graph   │  │  Relationship Graph    │  │   │
│  │  │  Her life,     │  │  What she      │  │  Shared history,       │  │   │
│  │  │  work, story   │  │  knows of you  │  │  episodes, jokes       │  │   │
│  │  └────────────────┘  └────────────────┘  └────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PERSISTENCE LAYER                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Supabase (PostgreSQL)                             │   │
│  │  • User profiles + auth        • Conversation logs                   │   │
│  │  • Relationship state          • pgVector embeddings                 │   │
│  │  • Score history               • Vice preferences                    │   │
│  │  • Chapter/Boss progress       • Daily summaries                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Neo4j (Graph Database)                            │   │
│  │  • Graphiti temporal knowledge graphs                                │   │
│  │  • Entity nodes, relationship edges                                  │   │
│  │  • Temporal versioning                                               │   │
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
| **Memory/KG** | Graphiti | Temporal knowledge graphs | [Docs](https://github.com/getzep/graphiti) |
| **Database** | Supabase (PostgreSQL + pgVector) | Persistence + embeddings | [Docs](https://supabase.com/docs) |
| **Graph DB** | Neo4j Aura (Free Tier) | Graphiti backend (managed, zero-install) | [Docs](https://neo4j.com/docs/) |
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
├── memory/                    # Memory Pipeline
│   ├── graphiti_client.py     # Graphiti wrapper
│   ├── graphs/
│   │   ├── nikita_graph.py    # Her life/work/story
│   │   ├── user_graph.py      # What she knows of user
│   │   └── relationship_graph.py # Shared history
│   ├── embeddings.py          # pgVector operations
│   └── context_builder.py     # Assemble context for prompts
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
│   └── migrations/            # Alembic migrations
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
         │  (Chapter, Score, │               │  (Graphiti query) │  │ (Vice prefs,   │
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
         │  • Analyze text   │            │  • Graphiti add   │    │  • Threshold met? │
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
│                              Days 1-14 | Decay: -5%/day                      │
│  ┌─────────────────┐                                    ┌─────────────────┐ │
│  │  ACTIVE_PLAY    │──────────────────────────────────▶│  BOSS_AVAILABLE │ │
│  │  Score < 60%    │        Score >= 60%                │  "Worth my time"│ │
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
│                              Days 15-35 | Decay: -4%/day                     │
│  [Same pattern: ACTIVE → BOSS_AVAILABLE (65%) → PASS/FAIL]                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CHAPTER 3: INVESTMENT                           │
│                              Days 36-70 | Decay: -3%/day                     │
│  [Same pattern: ACTIVE → BOSS_AVAILABLE (70%) → PASS/FAIL]                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CHAPTER 4: INTIMACY                             │
│                              Days 71-120 | Decay: -2%/day                    │
│  [Same pattern: ACTIVE → BOSS_AVAILABLE (75%) → PASS/FAIL]                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CHAPTER 5: ESTABLISHED                          │
│                              Days 121+ | Decay: -1%/day                      │
│  ┌─────────────────┐                                    ┌─────────────────┐ │
│  │  ACTIVE_PLAY    │──────────────────────────────────▶│  FINAL_BOSS     │ │
│  │  Score < 80%    │        Score >= 80%                │  "Ultimate test"│ │
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

## 7. Memory Pipeline (Graphiti Integration)

**Implementation**: `nikita/memory/graphiti_client.py` (271 lines)

### Three Knowledge Graphs
| Graph | Purpose | Entity Types |
|-------|---------|--------------|
| Nikita Graph | Her simulated life | WorkProject, LifeEvent, Opinion, Memory |
| User Graph | What she knows of player | UserFact, UserPreference, UserPattern |
| Relationship Graph | Shared history | Episode, Milestone, InsideJoke, Conflict |

### Key Methods
- `add_episode(content, source, graph_type)` - Add to any graph
- `search_memory(query, graph_types, limit)` - Hybrid search
- `get_context_for_prompt(user_message)` - Build LLM context
- `add_user_fact(fact, confidence)` - Store learned facts
- `get_user_facts(limit)` - Retrieve for deduplication

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

**Voice Agent** ❌ TODO (Phase 4) - See `specs/007-voice-agent/spec.md`

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
| message_embeddings | pgVector embeddings for semantic search |

---

## 10. API Endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/telegram/webhook` | POST | Handle Telegram bot messages |
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
│  ┌──────────────────┐  ┌────────────────────┐  ┌───────────────────────┐   │
│  │  SUPABASE        │  │  NEO4J AURA CLOUD  │  │  LLM SERVICES         │   │
│  │  ────────────    │  │  (FREE TIER)       │  │  ───────────          │   │
│  │  • Auth (OTP)    │  │  ─────────────     │  │  • Claude Sonnet 4    │   │
│  │  • PostgreSQL    │  │  Graphiti KGs:     │  │  • OpenAI Embeddings  │   │
│  │  • pgVector      │  │  • nikita_graph    │  │                       │   │
│  │  • pg_cron ──────┼──┼─► (triggers tasks) │  │                       │   │
│  │  • Edge Functions│  │  • user_graph      │  │                       │   │
│  │                  │  │  • relationship_   │  │                       │   │
│  └──────────────────┘  └────────────────────┘  └───────────────────────┘   │
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

## 13. Implementation Phases

### Phase 1: Core Infrastructure ✅ COMPLETE
- [x] Project structure (39 Python files)
- [x] Supabase database models defined
- [x] Graphiti integration (NikitaMemory) - migrating to Neo4j Aura
- [x] FastAPI skeleton
- [x] Pydantic models
- [x] Game constants (CHAPTERS, DECAY_RATES, CHAPTER_BEHAVIORS)

### Phase 2: Text Agent ⚠️ PARTIAL
**Text Agent Core** ✅ COMPLETE (specs/001-nikita-text-agent)
- [x] Pydantic AI agent with Nikita persona (nikita/agents/text/)
- [x] Memory tools (recall_memory, note_user_fact)
- [x] MessageHandler with timing + skip logic
- [x] FactExtractor for user fact learning
- [x] 156 tests passing

**Remaining Phase 2**:
- [ ] Telegram integration (specs/002-telegram-integration)
- [ ] API routes (webhook endpoints)
- [ ] Database repositories

### Phase 3: Game Engine ❌ TODO
- [ ] Scoring calculator (specs/003-scoring-engine)
- [ ] Chapter state machine (specs/004-chapter-boss-system)
- [ ] Decay scheduler (specs/005-decay-system)
- [ ] Vice discovery (specs/006-vice-personalization)

### Phase 4: Voice Agent ❌ TODO
- [ ] ElevenLabs integration (specs/007-voice-agent)
- [ ] Server tools
- [ ] Voice session management

### Phase 5: Portal & Polish ❌ TODO
- [ ] Next.js dashboard (specs/008-player-portal)
- [ ] Daily summaries
- [ ] Logging/monitoring

---

## 14. Key Documentation References

| Resource | URL |
|----------|-----|
| ElevenLabs Agents SDK | https://elevenlabs.io/docs/agents-platform/libraries/python |
| ElevenLabs Server Tools | https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools |
| Pydantic AI Docs | https://ai.pydantic.dev/ |
| Pydantic AI Agents | https://ai.pydantic.dev/agents/ |
| Pydantic AI Tools | https://ai.pydantic.dev/tools/ |
| Graphiti GitHub | https://github.com/getzep/graphiti |
| Graphiti Temporal KG | https://arxiv.org/abs/2501.13956 |
| Supabase Python | https://supabase.com/docs/reference/python |
| Supabase pgVector | https://supabase.com/docs/guides/ai |
| aiogram 3.x | https://docs.aiogram.dev/ |
| FastAPI WebSockets | https://fastapi.tiangolo.com/advanced/websockets/ |

---

## 15. Architecture Decisions (Finalized)

### 15.1 Hosting
- **Primary**: Supabase hosted (PostgreSQL + Auth + Storage)
- **API**: Self-hosted or Supabase Edge Functions
- **Graph DB**: FalkorDB Free tier → upgrade path to paid when scaling

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

### 15.3 Database Architecture (REVISED)

**Supabase handles ALL persistent data:**
- User profiles, auth (OTP)
- Conversation logs, transcriptions
- Score history, daily summaries
- User memory (raw facts)
- Vice preferences
- Game state

**FalkorDB (via Graphiti) handles ONLY temporal knowledge graphs:**
- Nikita Graph (her life/work/story)
- User Graph (what she knows about player)
- Relationship Graph (shared history/episodes)

### 15.4 Graph Database Decision

**Evaluated Options:**

| Option | Cost | Graphiti Support | Status |
|--------|------|------------------|--------|
| Kuzu | $0 | Yes | ❌ **ARCHIVED Oct 2025** |
| FalkorDB Free | $0 | Yes | ❌ Requires self-hosting (ops burden) |
| Neo4j Aura Free | $0 | Yes (native) | ✅ **SELECTED** - Managed, zero install |
| Neo4j Aura Professional | $65/mo | Yes | Upgrade path for production |

**Decision**: **Neo4j Aura Free tier** (2025-11 Update)
- Install: `pip install graphiti-core` (Neo4j is default backend)
- **Why change from FalkorDB?** Senior architect review: eliminate ops burden
- Neo4j Aura Free tier: 200k nodes, 400k relationships (sufficient for MVP)
- Zero installation, managed service, automatic backups
- Graphiti natively supports Neo4j - minimal code changes

**Connection Config:**
```python
# settings.py
NEO4J_URI = "neo4j+s://xxxx.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "..."  # from Aura console
```

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
| **Graph DB** | Neo4j Aura Free | $0 | Temporal knowledge graphs via Graphiti |
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

*Documentation: see memory/*.md files for detailed architecture*
