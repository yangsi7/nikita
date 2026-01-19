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
                (text)        │        │ (voice via ElevenLabs)
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

### Component Hierarchy (MVP Complete - Dec 2025)

```
nikita/
├── config/                    ✅ COMPLETE (89 tests)
│   ├── settings.py            # Pydantic settings (Neo4j, Supabase, etc.)
│   ├── elevenlabs.py          # Agent ID abstraction per chapter/mood
│   ├── enums.py               # 9 enum classes (GameStatus, Chapter, etc.)
│   ├── schemas.py             # 22 Pydantic config models
│   └── loaders.py             # ConfigLoader, PromptLoader, ExperimentLoader
├── db/                        ✅ COMPLETE (8 migrations, 7 repos)
│   ├── models/                # SQLAlchemy ORM models
│   │   ├── user.py            # User, UserMetrics, UserVicePreference
│   │   ├── conversation.py    # Conversation, MessageEmbedding
│   │   ├── context.py         # ConversationThread, NikitaThought
│   │   └── game.py            # ScoreHistory, DailySummary, ScheduledEvent
│   ├── repositories/          # Data access layer (7 repos)
│   └── migrations/            # 8 Alembic migrations applied
├── engine/                    ✅ COMPLETE (516 tests)
│   ├── constants.py           ✅ Game constants defined
│   ├── scoring/               ✅ COMPLETE (60 tests) - Calculator, analyzer, service
│   ├── chapters/              ✅ COMPLETE (142 tests) - State machine, boss logic
│   ├── decay/                 ✅ COMPLETE (52 tests) - Decay calculator, processor
│   ├── vice/                  ✅ COMPLETE (81 tests) - Discovery system, injector
│   └── engagement/            ✅ COMPLETE (179 tests) - 6-state machine, detection
├── memory/                    ✅ COMPLETE
│   ├── graphiti_client.py     # NikitaMemory class (3 graphs)
│   └── graphs/                # Graph type definitions
├── meta_prompts/              ✅ COMPLETE
│   ├── service.py             # MetaPromptService (Claude Haiku)
│   ├── models.py              # ViceProfile, MetaPromptContext, GeneratedPrompt
│   └── templates/             # 6 meta-prompt templates (.meta.md)
├── context/                   ✅ COMPLETE (50 tests)
│   ├── post_processor.py      # 9-stage post-processing pipeline
│   ├── template_generator.py  # Context template generation
│   └── utils/                 # Context engineering utilities
├── agents/                    ✅ COMPLETE (156 tests)
│   └── text/                  ✅ COMPLETE (8 files, 156 tests)
│       ├── agent.py           # Pydantic AI + Claude Sonnet
│       ├── handler.py         # MessageHandler (scoring, boss check)
│       ├── deps.py            # NikitaDeps dependency container
│       ├── timing.py          # ResponseTimer (gaussian delay)
│       ├── skip.py            # SkipDecision (chapter-based rates)
│       ├── facts.py           # FactExtractor (LLM fact learning)
│       └── tools.py           # recall_memory, note_user_fact
│   └── voice/                 ✅ COMPLETE (14 modules, 186 tests, deployed Jan 2026)
├── platforms/                 ✅ COMPLETE (86 tests)
│   └── telegram/              ✅ DEPLOYED to Cloud Run
│       ├── auth.py            # TelegramAuth (OTP flow)
│       ├── bot.py             # TelegramBot (httpx async)
│       ├── commands.py        # CommandHandler (/start, /help, /status)
│       ├── otp_handler.py     # OTP verification (replaces magic link)
│       ├── delivery.py        # ResponseDelivery (message splitting)
│       ├── message_handler.py # MessageHandler (rate limit, typing)
│       ├── rate_limiter.py    # RateLimiter (20/min, 100/day)
│       └── models.py          # Pydantic models (TelegramUpdate, etc.)
├── api/                       ✅ COMPLETE (DEPLOYED to Cloud Run)
│   ├── main.py                ✅ Full DI, lifespan, health checks
│   ├── dependencies/          ✅ Annotated[T, Depends] patterns
│   ├── routes/
│   │   ├── telegram.py        ✅ POST /telegram/webhook (deployed)
│   │   ├── tasks.py           ✅ pg_cron endpoints (/decay, /summary, /cleanup, /process-conversations)
│   │   ├── portal.py          ✅ Portal stats API (score, chapter, history)
│   │   ├── admin_debug.py     ✅ Admin debug endpoints
│   │   └── voice.py           ✅ COMPLETE - 5 ElevenLabs endpoints (deployed Jan 2026)
│   └── schemas/               ✅ Pydantic models
└── services/                  ✅ COMPLETE
    └── (Service layer for complex business logic)
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

## Spec Status (MVP Complete - Dec 2025)

| Spec | Status | Implementation | Tests |
|------|--------|----------------|-------|
| 001-nikita-text-agent | ✅ COMPLETE | `nikita/agents/text/` (8 files) | 156 |
| 002-telegram-integration | ✅ COMPLETE | `nikita/platforms/telegram/` (deployed to Cloud Run) | 86 |
| 003-scoring-engine | ✅ COMPLETE | `nikita/engine/scoring/` (4 files) | 60 |
| 004-chapter-boss-system | ✅ COMPLETE | `nikita/engine/chapters/` (boss logic integrated) | 142 |
| 005-decay-system | ✅ COMPLETE | `nikita/engine/decay/` + `/tasks/decay` endpoint | 52 |
| 006-vice-personalization | ✅ COMPLETE | `nikita/engine/vice/` (discovery + injection) | 81 |
| 007-voice-agent | ✅ COMPLETE | `nikita/agents/voice/` (14 modules, deployed Jan 2026) | 186 |
| 008-player-portal | ⚠️ 85% | Next.js on Vercel (Backend 100%, Admin 100%, Settings 50%) | - |
| 009-database-infrastructure | ✅ COMPLETE | 8 RLS migrations, 7 repositories | - |
| 010-api-infrastructure | ✅ COMPLETE | `nikita/api/` (Cloud Run deployed) | - |
| 011-background-tasks | ✅ COMPLETE | `nikita/api/routes/tasks.py` (pg_cron endpoints) | 12 |
| 012-context-engineering | ✅ COMPLETE | `nikita/context/` (9-stage pipeline) | 50 |
| 013-configuration-system | ✅ COMPLETE | `nikita/config/` (YAML + loaders) | 89 |
| 014-engagement-model | ✅ COMPLETE | `nikita/engine/engagement/` (6 states) | 179 |
| 015-onboarding-fix | ✅ COMPLETE | OTP flow (replaces magic link) | - |
| 016-admin-debug-portal | ✅ COMPLETE | Debug endpoints + admin UI | 8 |
| 017-enhanced-onboarding | ⚠️ 78% | Memory integration, first message | - |
| 018-admin-prompt-viewing | ✅ COMPLETE | Prompt viewer + context snapshot | - |
| 019-admin-voice-monitoring | ✅ COMPLETE | Voice call monitoring (RETROACTIVE) | 21 |
| 020-admin-text-monitoring | ✅ COMPLETE | Text conversation monitoring (RETROACTIVE) | 29 |

**Total Tests**: 1,623+ passed
**Total Specs**: 20
**E2E Verified**: 2025-12-18

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
| ~~Twilio~~ | Not used - ElevenLabs handles voice | N/A |

**Removed** (Senior Architect Review Nov 2025):
- ~~Redis~~ - Replaced by pg_cron + Edge Functions
- ~~Celery~~ - Replaced by FastAPI BackgroundTasks
- ~~FalkorDB~~ - Replaced by Neo4j Aura (managed)
