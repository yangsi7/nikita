# System Architecture

## Current State

> **Architecture Decision (Nov 2025, updated Feb 2026)**: Single Python service (FastAPI + aiogram + Pydantic AI + SupabaseMemory). Supabase handles DB + auth + scheduling + memory (pgVector). No Celery, no Redis, no microservices.

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
                    │  + SupabaseMemory      │
                    └─────────┬──────────────┘
                              │
               ┌──────────────┼──────────────┐
               ▼              ▼              ▼
        ┌─────────────┐ ┌──────────────┐ ┌──────────────┐
        │ Supabase DB │ │ Supabase Cron│ │ pgVector     │
        │ Postgres    │ │ + Edge Funcs │ │ (embeddings) │
        │             │ └──────────────┘ └──────────────┘
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
│   ├── settings.py            # Pydantic settings (Supabase, Claude, ElevenLabs, etc.)
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
├── memory/                    ✅ Spec 042
│   ├── supabase_memory.py     # SupabaseMemory class (pgVector + dedup)
│   └── __init__.py              # Memory module exports
├── pipeline/                  ✅ Spec 042 (74 tests)
│   ├── orchestrator.py        # 9-stage async pipeline orchestrator
│   ├── stages/                # 9 PipelineStage classes
│   ├── models.py              # PipelineContext, PipelineResult
│   └── utils.py               # Circuit breakers, retry logic
├── context/                   ⚠️ PARTIAL (validation, session detection remain)
│   ├── validation.py          # Guardrails validation
│   ├── session_detector.py    # Session end detection
│   └── (DEPRECATED: package.py, template_generator.py, post_processor.py)
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

### Unified Pipeline Architecture (Spec 042)

The 9-stage async pipeline handles all prompt generation and post-processing:

```
┌─────────────────────────────────────────────────────────────────┐
│                     UNIFIED PIPELINE (Spec 042)                  │
├─────────────────────────────────────────────────────────────────┤
│ PROMPT GENERATION PATH (text/voice)                             │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│ │1.CtxLoading  │→ │2.Metrics     │→ │3.Emotional   │→          │
│ └──────────────┘  └──────────────┘  └──────────────┘          │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│ │4.Memory      │→ │5.Template    │→ │6.Prompt      │           │
│ └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│ POST-PROCESSING PATH (after conversation ends)                  │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│ │7.Extraction  │→ │8.Summary     │→ │9.MemoryUpd   │           │
│ └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Single pipeline** replaces 3 prompt paths (text/voice/meta-prompt) + 2 post-processing paths
- **Memory**: Supabase pgVector (NOT Neo4j) - embeddings + deduplication
- **Feature flag**: `unified_pipeline_enabled` controls rollout (per user)
- **74 tests**: Stage unit tests + orchestrator + integration

**Trigger**:
- Prompt generation: On-demand via `/api/v1/{platform}/message`
- Post-processing: pg_cron calls `/tasks/process-conversations` every minute

**See**: `nikita/pipeline/` for implementation.

### Database Architecture (Spec 042: Unified Supabase)

```
SUPABASE (All Data)
════════════════════════════

users
├─ id (UUID, PK)
├─ telegram_id
├─ relationship_score
├─ chapter
├─ game_status

user_metrics
├─ intimacy
├─ passion
├─ trust
├─ secureness

conversations
├─ messages (JSONB)
├─ platform (telegram|voice)
├─ score_delta

score_history
├─ score, chapter, event_type
└─ recorded_at

scheduled_events (Proactive Messaging)
├─ id (UUID, PK)
├─ user_id → users(id)
├─ channel (telegram|voice)
├─ event_type (send_message|outbound_call|daily_summary)
├─ due_at (TIMESTAMPTZ)
├─ payload (JSONB)
├─ status (pending|processing|done|failed)
└─ created_at

memory_facts (NEW - Spec 042)
├─ id (UUID, PK)
├─ user_id → users(id)
├─ fact (TEXT)
├─ fact_type (user|nikita|relationship)
├─ embedding (vector(1536))  -- pgVector
├─ hash (TEXT, UNIQUE)       -- Deduplication
├─ created_at
└─ INDEX USING ivfflat (embedding vector_cosine_ops)

ready_prompts (NEW - Spec 042)
├─ id (UUID, PK)
├─ user_id → users(id)
├─ platform (telegram|voice)
├─ prompt_text (TEXT)
├─ dynamic_variables (JSONB)
├─ valid_until (TIMESTAMPTZ)
└─ created_at

WHY SUPABASE ONLY:
• ACID transactions
• Row-level security
• Real-time subscriptions
• pgVector similarity search
• pg_cron scheduling
• No separate Neo4j management
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
| 012-context-engineering | ✅ COMPLETE | `nikita/context/` (11-stage pipeline, Spec 037) | 315 |
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

pgVector-based semantic memory with deduplication:

```python
# nikita/memory/supabase_memory.py
async def add_memory(
    self,
    content: str,
    source: str,
    memory_type: str = "relationship",
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
| `nikita/memory/supabase_memory.py` | Memory system (pgVector) | — | ✅ Complete |
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
| Google Cloud Run | Serverless API hosting | ✅ Configured |
| Anthropic | Claude Sonnet 4.6 (text agent + scoring) | ✅ Configured |
| ElevenLabs | Voice agent (Server Tools pattern) | ✅ Configured |
| Telegram | Bot platform | ✅ Configured |
| ~~Twilio~~ | Not used - ElevenLabs handles voice | N/A |

**Removed** (Senior Architect Review Nov 2025):
- ~~Redis~~ - Replaced by pg_cron + Edge Functions
- ~~Celery~~ - Replaced by FastAPI BackgroundTasks
- ~~FalkorDB~~ - Replaced by pgVector (via Supabase)
- ~~Neo4j Aura~~ - Replaced by pgVector (Spec 042, Feb 2026)
- ~~OpenAI Embeddings~~ - Replaced by Supabase built-in embeddings
