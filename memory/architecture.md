# System Architecture

## Current State

### Component Hierarchy (Phase 1 Complete)

```
nikita/
├── config/                    ✅ COMPLETE
│   ├── settings.py            # Pydantic settings for all services
│   └── elevenlabs.py          # Agent ID abstraction per chapter/mood
├── db/                        ✅ COMPLETE
│   ├── models/                # SQLAlchemy ORM models
│   │   ├── user.py            # User, UserMetrics, UserVicePreference
│   │   ├── conversation.py    # Conversation, MessageEmbedding
│   │   └── game.py            # ScoreHistory, DailySummary
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
├── platforms/                 ❌ TODO: Phase 2-4
│   ├── telegram/              # aiogram bot
│   ├── voice/                 # ElevenLabs callbacks
│   └── portal/                # Stats dashboard
├── api/                       ⚠️ PARTIAL
│   ├── main.py                ✅ FastAPI skeleton
│   ├── routes/                ❌ TODO: Telegram, voice, portal
│   └── schemas/               ✅ Pydantic models (basic)
└── tasks/                     ❌ TODO: Phase 3
    ├── decay_task.py          # Daily decay
    └── summary_task.py        # Daily summaries
```

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       DUAL INPUT CHANNELS                        │
├────────────────────────┬────────────────────────────────────────┤
│  Telegram Messages     │       Voice Calls (ElevenLabs)         │
│  (aiogram 3.x)        │       (Conv AI 2.0 SDK)                │
└───────────┬────────────┴────────────────┬───────────────────────┘
            │                             │
            ▼                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              API GATEWAY (FastAPI) - nikita/api/main.py          │
│  /telegram/*   /voice/*   /portal/*   /webhooks/*               │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│        ORCHESTRATION LAYER (TODO Phase 2)                        │
│  • Route to agent (voice/text)                                  │
│  • Inject context (chapter, score, memory)                      │
│  • Process response through scoring                             │
│  • Update memory graphs                                         │
└──────────┬────────────────────────────────┬─────────────────────┘
           │                                │
           ▼                                ▼
┌──────────────────────┐       ┌──────────────────────┐
│   TEXT AGENT         │       │   VOICE AGENT        │
│   (Pydantic AI)      │       │   (ElevenLabs)       │
│   ✅ COMPLETE        │       │   TODO Phase 4       │
└──────────┬───────────┘       └──────────┬───────────┘
           │                              │
           └──────────────┬───────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│             MEMORY & KNOWLEDGE LAYER (Phase 1 ✅)                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  NikitaMemory (graphiti_client.py)                       │   │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐   │   │
│  │  │ Nikita     │  │ User       │  │ Relationship     │   │   │
│  │  │ Graph      │  │ Graph      │  │ Graph            │   │   │
│  │  └────────────┘  └────────────┘  └──────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│               PERSISTENCE LAYER (Phase 1 ✅)                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Supabase (PostgreSQL + pgVector)                        │   │
│  │  • users, user_metrics, user_vice_preferences            │   │
│  │  • conversations, message_embeddings                     │   │
│  │  • score_history, daily_summaries                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FalkorDB (Graph Database via Graphiti)                  │   │
│  │  • Temporal knowledge graphs                             │   │
│  │  • Entity relationships with timestamps                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Database Split Architecture

```
SUPABASE (Structured Data)          FALKORDB (Temporal Graphs)
════════════════════════            ══════════════════════════

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

WHY THIS SPLIT:                    WHY THIS SPLIT:
• ACID transactions                • Temporal awareness
• Row-level security               • "When did I learn X?"
• Real-time subscriptions          • Entity relationships
• pgVector similarity search       • Memory evolution tracking
```

## Spec Status

| Spec | Status | Implementation |
|------|--------|----------------|
| 001-nikita-text-agent | ✅ COMPLETE | `nikita/agents/text/` (8 files, 156 tests) |
| 002-telegram-integration | ❌ TODO | `nikita/platforms/telegram/` |
| 003-scoring-engine | ❌ TODO | `nikita/engine/scoring/` |
| 004-chapter-boss-system | ❌ TODO | `nikita/engine/chapters/` |
| 005-decay-system | ❌ TODO | `nikita/engine/decay/` + `nikita/tasks/` |
| 006-vice-personalization | ❌ TODO | `nikita/engine/vice/` |
| 007-voice-agent | ❌ TODO | `nikita/agents/voice/` |
| 008-player-portal | ❌ TODO | Separate Next.js repo |

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
| `nikita/api/main.py` | FastAPI app | - | ⚠️ Skeleton |

## External Dependencies

| Service | Purpose | Status |
|---------|---------|--------|
| Supabase | PostgreSQL + Auth + pgVector | ✅ Configured |
| FalkorDB | Graphiti graph backend | ✅ Configured |
| Anthropic | Claude Sonnet (text agent + scoring) | ✅ Configured |
| OpenAI | Embeddings for Graphiti | ✅ Configured |
| ElevenLabs | Voice agent | ✅ Configured |
| Telegram | Bot platform | ✅ Configured |
| Redis | Celery broker | ✅ Configured |
