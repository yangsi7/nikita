# System Architecture

## Current State

> **Architecture Decision (Nov 2025)**: Single Python service (FastAPI + aiogram + Pydantic AI + Graphiti). Supabase handles DB + auth + scheduling. No Celery, no Redis, no microservices.

### High-Level Architecture (Option 1: Python Game Engine + Supabase Spine)

```
                      ┌───────────────────────────┐
                      │        Players            │
                      │  Telegram  |  Phone  | Web│
                      └───────┬────────┬──────────┘
                              │        │
                (text)        │        │ (voice via Twilio)
                              │        ▼
                    ┌─────────┴─────────────┐
                    │ ElevenLabs Agents     │
                    │ (telephony)           │
                    └─────────┬─────────────┘
                              │ server tools (HTTP)
                              ▼
                    ┌────────────────────────┐
Telegram Webhook →  │  Python Game Engine    │  ← Portal API (read-only)
(HTTPS)             │  (FastAPI + aiogram)   │
                    │  + Pydantic AI         │
                    │  + Graphiti client     │
                    └─────────┬──────────────┘
                              │
               ┌──────────────┼─────────────────────┐
               ▼              ▼                     ▼
        ┌─────────────┐ ┌──────────────┐    ┌─────────────────┐
        │ Supabase DB │ │ Supabase Cron│    │ Neo4j Aura      │
        │ Postgres +  │ │ + Edge Funcs │    │ (Graphiti)      │
        │ pgvector    │ └──────────────┘    └─────────────────┘
        └─────────────┘
               ▲
               │
        ┌──────┴────────┐
        │ Next.js Portal│
        │ (Vercel)      │
        │ + Supabase Auth│
        └───────────────┘
```

**Key Design Principles**:
- **One Python service** handles ALL game/agent logic (Cloud Run, scales to zero)
- **Supabase** = storage + auth + scheduler (pg_cron + Edge Functions)
- **ElevenLabs** = telephony + TTS (server tools call back to Python API)
- **Next.js** = UI only (talks to Supabase directly for reads)

### Component Hierarchy (Phase 1 Complete)

```
nikita/
├── config/                    ✅ COMPLETE
│   ├── settings.py            # Pydantic settings (Neo4j, Supabase, etc.)
│   └── elevenlabs.py          # Agent ID abstraction per chapter/mood
├── db/                        ✅ COMPLETE
│   ├── models/                # SQLAlchemy ORM models
│   │   ├── user.py            # User, UserMetrics, UserVicePreference
│   │   ├── conversation.py    # Conversation, MessageEmbedding
│   │   └── game.py            # ScoreHistory, DailySummary, ScheduledEvent
│   ├── repositories/          # Data access layer (stub)
│   └── migrations/            # Alembic (stub)
├── engine/                    ⚠️ PARTIAL
│   ├── constants.py           ✅ Game constants defined
│   ├── scoring/               ❌ TODO: Calculator, analyzer
│   ├── chapters/              ❌ TODO: State machine, boss logic
│   ├── decay/                 ❌ TODO: Decay calculator
│   ├── vice/                  ❌ TODO: Discovery system
│   └── conflicts/             ❌ TODO: Conflict handling
├── memory/                    ✅ COMPLETE
│   ├── graphiti_client.py     # NikitaMemory class (3 graphs)
│   └── graphs/                # Graph type definitions (stub)
├── meta_prompts/              ✅ COMPLETE
│   ├── service.py             # MetaPromptService (Claude Haiku)
│   ├── models.py              # ViceProfile, MetaPromptContext, GeneratedPrompt
│   └── templates/             # 4 meta-prompt templates (.meta.md)
├── agents/                    ⚠️ PARTIAL
│   └── text/                  ✅ COMPLETE (8 files, 1072 lines, 156 tests)
│       ├── agent.py           # Pydantic AI + Claude Sonnet
│       ├── handler.py         # MessageHandler (timing, skip, facts)
│       ├── deps.py            # NikitaDeps dependency container
│       ├── timing.py          # ResponseTimer (gaussian delay)
│       ├── skip.py            # SkipDecision (chapter-based rates)
│       ├── facts.py           # FactExtractor (LLM fact learning)
│       └── tools.py           # recall_memory, note_user_fact
│   └── voice/                 ❌ TODO: Phase 4
├── platforms/                 ✅ COMPLETE (Phase 2)
│   └── telegram/              ✅ 74 tests passing
│       ├── auth.py            # TelegramAuth (DB-backed pending_registrations)
│       ├── bot.py             # TelegramBot (httpx async)
│       ├── commands.py        # CommandHandler (/start, /help, /status)
│       ├── delivery.py        # ResponseDelivery (message splitting)
│       ├── message_handler.py # MessageHandler (rate limit, typing)
│       ├── rate_limiter.py    # RateLimiter (20/min, 100/day)
│       └── models.py          # Pydantic models (TelegramUpdate, etc.)
├── api/                       ⚠️ 90% COMPLETE (Sprint 3)
│   ├── main.py                ✅ Full DI, lifespan, health checks
│   ├── dependencies.py        ✅ Annotated[T, Depends] patterns
│   ├── routes/
│   │   ├── telegram.py        ✅ POST /telegram/webhook (CommandHandler/MessageHandler DI)
│   │   ├── tasks.py           ✅ pg_cron endpoints (/decay, /deliver, /summary, /cleanup)
│   │   ├── voice.py           ❌ TODO: Phase 4 - ElevenLabs server tools
│   │   └── portal.py          ❌ TODO: Phase 5 - Read-only stats API
│   └── schemas/               ✅ Pydantic models (basic)
└── tasks/                     ✅ Moved to api/routes/tasks.py
    └── (No longer separate - pg_cron via HTTP endpoints)
```

### Database Split Architecture

```
SUPABASE (Structured Data)          NEO4J AURA (Temporal Graphs)
════════════════════════            ════════════════════════════

users                               nikita_graph_{user_id}
├─ id (UUID, PK)                   ├─ WorkProject nodes
├─ telegram_id                     ├─ LifeEvent nodes
├─ relationship_score              ├─ Opinion nodes
├─ chapter                         └─ Memory nodes
├─ game_status
├─ graphiti_group_id               user_graph_{user_id}
                                   ├─ UserFact nodes
user_metrics                       ├─ UserPreference nodes
├─ intimacy                        └─ UserPattern nodes
├─ passion
├─ trust                           relationship_graph_{user_id}
├─ secureness                      ├─ Episode nodes
                                   ├─ Milestone nodes
conversations                      ├─ InsideJoke nodes
├─ messages (JSONB)                └─ Conflict nodes
├─ platform (telegram|voice)
├─ score_delta

score_history
├─ score, chapter, event_type
└─ recorded_at

scheduled_events (NEW - Proactive Messaging)
├─ id (UUID, PK)
├─ user_id → users(id)
├─ channel (telegram|voice)
├─ event_type (send_message|outbound_call|daily_summary)
├─ due_at (TIMESTAMPTZ)
├─ payload (JSONB)
├─ status (pending|processing|done|failed)
└─ created_at

WHY THIS SPLIT:                    WHY THIS SPLIT:
• ACID transactions                • Temporal awareness
• Row-level security               • "When did I learn X?"
• Real-time subscriptions          • Entity relationships
• pgVector similarity search       • Memory evolution tracking
• pg_cron scheduling
```

## Spec Status

| Spec | Status | Implementation |
|------|--------|----------------|
| 001-nikita-text-agent | ✅ COMPLETE | `nikita/agents/text/` (8 files, 156 tests) |
| 002-telegram-integration | ⚠️ 95% | `nikita/platforms/telegram/` (74 tests) + `nikita/api/routes/` (23 tests) |
| 003-scoring-engine | ❌ TODO | `nikita/engine/scoring/` |
| 004-chapter-boss-system | ❌ TODO | `nikita/engine/chapters/` |
| 005-decay-system | ❌ TODO | `nikita/engine/decay/` + `nikita/api/routes/tasks.py` |
| 006-vice-personalization | ❌ TODO | `nikita/engine/vice/` |
| 007-voice-agent | ❌ TODO | `nikita/agents/voice/` |
| 008-player-portal | ❌ TODO | Separate Next.js repo |
| 009-database-infrastructure | ✅ COMPLETE | 6 RLS migrations applied |
| 010-api-infrastructure | ⚠️ 90% | `nikita/api/` (DI, lifespan, routes) |
| 011-background-tasks | ✅ COMPLETE | `nikita/api/routes/tasks.py` (pg_cron endpoints) |

**Full specs**: See `specs/` directory

## Key Patterns

### 1. Settings Pattern

All configuration via Pydantic Settings:

```python
# nikita/config/settings.py:82-84
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### 2. Memory Pattern

Three-graph temporal knowledge system:

```python
# nikita/memory/graphiti_client.py:54-79
async def add_episode(
    self,
    content: str,
    source: str,
    graph_type: str = "relationship",  # nikita | user | relationship
    metadata: dict[str, Any] | None = None,
) -> None:
```

### 3. Composite Score Pattern

Hidden metrics → visible composite:

```python
# nikita/db/models/user.py:155-166
def calculate_composite_score(self) -> Decimal:
    return (
        self.intimacy * Decimal("0.30")
        + self.passion * Decimal("0.25")
        + self.trust * Decimal("0.25")
        + self.secureness * Decimal("0.20")
    )
```

## Critical Files

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `nikita/config/settings.py` | All environment settings | 85 | ✅ Complete |
| `nikita/config/elevenlabs.py` | Agent ID abstraction | - | ✅ Complete |
| `nikita/engine/constants.py` | Game constants | 148 | ✅ Complete |
| `nikita/memory/graphiti_client.py` | Memory system | 271 | ✅ Complete |
| `nikita/db/models/user.py` | User data models | 220 | ✅ Complete |
| `nikita/agents/text/agent.py` | Text agent core | 195 | ✅ Complete |
| `nikita/agents/text/handler.py` | MessageHandler | 229 | ✅ Complete |
| `nikita/agents/text/facts.py` | FactExtractor | 178 | ✅ Complete |
| `nikita/api/main.py` | FastAPI app | - | ✅ Complete (DI, lifespan) |
| `nikita/api/dependencies.py` | DI patterns | - | ✅ Complete |
| `nikita/api/routes/telegram.py` | Webhook handler | - | ✅ Complete |
| `nikita/api/routes/tasks.py` | pg_cron endpoints | - | ✅ Complete |
| `nikita/platforms/telegram/*.py` | Bot platform | - | ✅ Complete (74 tests) |

## External Dependencies

| Service | Purpose | Status |
|---------|---------|--------|
| Supabase | PostgreSQL + Auth + pgVector + pg_cron | ✅ Configured |
| Neo4j Aura | Graphiti graph backend (free tier) | ✅ Configured |
| Google Cloud Run | Serverless API hosting | ✅ To configure |
| Anthropic | Claude Sonnet (text agent + scoring) | ✅ Configured |
| OpenAI | Embeddings for Graphiti | ✅ Configured |
| ElevenLabs | Voice agent (Server Tools pattern) | ✅ Configured |
| Telegram | Bot platform | ✅ Configured |
| Twilio | Voice call initiation | ❌ TODO |

**Removed** (Senior Architect Review Nov 2025):
- ~~Redis~~ - Replaced by pg_cron + Edge Functions
- ~~Celery~~ - Replaced by FastAPI BackgroundTasks
- ~~FalkorDB~~ - Replaced by Neo4j Aura (managed)
