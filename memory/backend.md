# Backend Architecture

## Current State

### Deployment: Google Cloud Run

> **Nov 2025 Update**: API deploys to Cloud Run (serverless, scales to zero).

**Configuration**:
```yaml
# cloud-run-config (inline or via cloudbuild.yaml)
service: nikita-api
region: us-central1
memory: 512Mi
cpu: 1
min-instances: 0      # Scales to zero when idle
max-instances: 10     # Handles burst traffic
timeout: 60s          # Voice tools may need longer
```

**Dockerfile** (✅ Created):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY nikita/ ./nikita/
CMD ["uvicorn", "nikita.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Cost**: $0-20/mo (scales to zero, pay only for requests)

---

### FastAPI Application Structure

```
nikita/api/
├── main.py                    ✅ COMPLETE (Sprint 3) - Full DI, lifespan, health checks
├── dependencies.py            ✅ COMPLETE - Annotated[T, Depends] patterns
├── routes/
│   ├── telegram.py            ✅ COMPLETE (Sprint 3) - Full DI webhook handler
│   │   ├── POST /telegram/webhook     # Routes to CommandHandler/MessageHandler
│   │   └── POST /telegram/set-webhook # Configure Telegram webhook URL
│   ├── tasks.py               ✅ COMPLETE (Sprint 3) - pg_cron task endpoints
│   │   ├── POST /tasks/decay      # Daily decay (3am UTC)
│   │   ├── POST /tasks/deliver    # Scheduled messages (every 30s)
│   │   ├── POST /tasks/summary    # Daily summaries (4am UTC)
│   │   └── POST /tasks/cleanup    # Expired registration cleanup
│   ├── voice.py               ❌ TODO (Phase 4) - ElevenLabs server tools
│   ├── portal.py              ✅ COMPLETE - Portal stats API (9 endpoints)
│   └── admin_debug.py         ✅ COMPLETE - Admin debug endpoints
├── schemas/
│   ├── user.py                ✅ Complete Pydantic models
│   ├── conversation.py        ✅ Complete Pydantic models
│   └── game.py                ✅ Complete Pydantic models
└── middleware/
    └── dependencies/auth.py   ✅ COMPLETE - Supabase JWT + webhook validation
```

### Text Agent Handler (✅ COMPLETE)

The text agent integrates with the backend through `MessageHandler`:

```
nikita/agents/text/
├── handler.py             ✅ MessageHandler class
│   ├── handle(user_id, message) → ResponseDecision
│   ├── Uses: ResponseTimer, SkipDecision, FactExtractor
│   └── Stores: pending responses, extracted facts
├── deps.py                ✅ NikitaDeps container
│   ├── user: User
│   ├── memory: NikitaMemory
│   └── settings: Settings
└── (other modules)        ✅ agent.py, timing.py, skip.py, facts.py, tools.py
```

**Integration Flow:**
```
User Message → MessageHandler.handle()
    │
    ├─ Load User + Memory (via get_nikita_agent_for_user)
    │
    ├─ Check SkipDecision.should_skip(chapter)
    │   └─ If skip → return ResponseDecision(should_respond=False)
    │
    ├─ Generate Response (via agent.run())
    │
    ├─ Calculate Delay (via ResponseTimer)
    │
    ├─ Extract Facts (via FactExtractor)
    │   └─ Store via memory.add_user_fact()
    │
    └─ Return ResponseDecision
        ├─ response: str
        ├─ delay_seconds: int
        ├─ scheduled_at: datetime
        ├─ facts_extracted: list[ExtractedFact]
        └─ should_respond: bool
```

**Key Models:**
- `ResponseDecision` - Handler result with timing + facts
- `ExtractedFact` - fact, confidence, source, fact_type
- `NikitaDeps` - Dependency container for agent

---

### Database Schema (Supabase PostgreSQL)

**Implemented via SQLAlchemy models** in `nikita/db/models/`:

```sql
-- Core tables (✅ COMPLETE)
users
├─ id UUID PRIMARY KEY (links to auth.users)
├─ telegram_id BIGINT UNIQUE
├─ relationship_score DECIMAL(5,2) DEFAULT 50.00
├─ chapter INT DEFAULT 1 (CHECK 1-5)
├─ boss_attempts INT DEFAULT 0 (CHECK 0-3)
├─ days_played INT DEFAULT 0
├─ last_interaction_at TIMESTAMPTZ
├─ game_status VARCHAR(20) DEFAULT 'active'
│  CHECK (game_status IN ('active', 'boss_fight', 'game_over', 'won'))
├─ graphiti_group_id TEXT (links to Neo4j Aura graphs)
├─ timezone VARCHAR(50) DEFAULT 'UTC'
└─ notifications_enabled BOOLEAN DEFAULT TRUE

user_metrics (1:1 with users)
├─ id UUID PRIMARY KEY
├─ user_id UUID REFERENCES users(id) UNIQUE
├─ intimacy DECIMAL(5,2) DEFAULT 50.00
├─ passion DECIMAL(5,2) DEFAULT 50.00
├─ trust DECIMAL(5,2) DEFAULT 50.00
└─ secureness DECIMAL(5,2) DEFAULT 50.00

user_vice_preferences (many:1 with users)
├─ id UUID PRIMARY KEY
├─ user_id UUID REFERENCES users(id)
├─ category VARCHAR(50) NOT NULL
│  (intellectual_dominance | risk_taking | substances | sexuality |
│   emotional_intensity | rule_breaking | dark_humor | vulnerability)
├─ intensity_level INT DEFAULT 1 (CHECK 1-5)
├─ engagement_score DECIMAL(5,2) DEFAULT 0.00
└─ discovered_at TIMESTAMPTZ DEFAULT NOW()

conversations
├─ id UUID PRIMARY KEY
├─ user_id UUID REFERENCES users(id)
├─ platform VARCHAR(20) NOT NULL ('telegram' | 'voice')
├─ messages JSONB DEFAULT '[]'
│  Format: [{role, content, timestamp, analysis?}]
├─ score_delta DECIMAL(5,2)
├─ started_at TIMESTAMPTZ DEFAULT NOW()
├─ ended_at TIMESTAMPTZ
├─ is_boss_fight BOOLEAN DEFAULT FALSE
├─ chapter_at_time INT
├─ elevenlabs_session_id TEXT (for voice)
├─ transcript_raw TEXT (for voice)
└─ search_vector tsvector GENERATED (for full-text search)

score_history
├─ id UUID PRIMARY KEY
├─ user_id UUID REFERENCES users(id)
├─ score DECIMAL(5,2) NOT NULL
├─ chapter INT NOT NULL
├─ event_type VARCHAR(50)
│  ('conversation' | 'decay' | 'boss_pass' | 'boss_fail')
├─ event_details JSONB (deltas, reasons)
└─ recorded_at TIMESTAMPTZ DEFAULT NOW()

daily_summaries
├─ id UUID PRIMARY KEY
├─ user_id UUID REFERENCES users(id)
├─ date DATE NOT NULL
├─ score_start DECIMAL(5,2)
├─ score_end DECIMAL(5,2)
├─ decay_applied DECIMAL(5,2)
├─ conversations_count INT DEFAULT 0
├─ nikita_summary_text TEXT (her in-character recap)
├─ key_events JSONB
└─ created_at TIMESTAMPTZ DEFAULT NOW()
   UNIQUE(user_id, date)

scheduled_events (proactive messaging - NEW)
├─ id UUID PRIMARY KEY DEFAULT gen_random_uuid()
├─ user_id UUID REFERENCES users(id)
├─ channel TEXT NOT NULL CHECK (channel IN ('telegram', 'voice'))
├─ event_type TEXT NOT NULL CHECK (event_type IN
│     ('send_message', 'outbound_call', 'daily_summary'))
├─ due_at TIMESTAMPTZ NOT NULL
├─ payload JSONB DEFAULT '{}'
│  Format: {message_text?, call_context?, mood?}
├─ status TEXT DEFAULT 'pending'
│  CHECK (status IN ('pending', 'processing', 'done', 'failed'))
├─ created_at TIMESTAMPTZ DEFAULT NOW()
├─ processed_at TIMESTAMPTZ
└─ error_message TEXT
   INDEX ON (due_at, status) WHERE status = 'pending'

message_embeddings (for semantic search)
├─ id UUID PRIMARY KEY
├─ user_id UUID REFERENCES users(id)
├─ conversation_id UUID REFERENCES conversations(id)
├─ message_text TEXT NOT NULL
├─ embedding vector(1536) (OpenAI text-embedding-3-small)
├─ role VARCHAR(20) ('user' | 'nikita')
└─ created_at TIMESTAMPTZ DEFAULT NOW()
   INDEX USING ivfflat (embedding vector_cosine_ops)
```

### Authentication Flow (Supabase Auth)

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  Telegram Bot → "Link to portal"            │
│  → portal.nikita.game/auth?telegram_id=...  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Portal: Supabase Auth OTP                  │
│  • Enter phone/email                        │
│  • Receive magic link                       │
│  • Click → authenticated                    │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Session created                            │
│  • JWT token stored                         │
│  • users.id linked to auth.users.id         │
│  • telegram_id associated                   │
└─────────────────────────────────────────────┘
```

## Target Specs

### API Endpoints ✅ MVP COMPLETE (Dec 2025)

#### Telegram Webhooks (Phase 2) - aiogram in FastAPI

> **Architecture Note**: aiogram runs in webhook mode WITHIN FastAPI (not as separate polling process). The FastAPI app includes the aiogram Dispatcher, which processes Telegram updates via HTTP webhook.

```python
# api/routes/telegram.py (aiogram webhook handler)

POST /telegram/webhook
├─ Body: TelegramUpdate (message, callback, etc.)
├─ Process:
│  1. aiogram Dispatcher receives update
│  2. Extract user_id from telegram_id
│  3. Load user via UserRepository
│  4. Pass to MessageHandler.handle()
│  5. Apply scoring (score_delta)
│  6. Store to memory (Graphiti + Supabase)
│  7. Schedule response via scheduled_events (if delay > 0)
│     OR send immediately via Telegram API
└─ Response: {"ok": true}

# aiogram integration in FastAPI
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    update = Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}
```

#### Task Endpoints (Phase 2) - pg_cron Integration

> **Scheduling Pattern**: pg_cron schedules jobs → Supabase Edge Function → POST to Cloud Run endpoints. No Celery, no Redis.

```python
# api/routes/tasks.py

@router.post("/tasks/decay")
async def apply_daily_decay(
    secret: str = Header(..., alias="X-Cron-Secret"),
):
    """
    Called by pg_cron via Edge Function at 3am UTC.
    Applies daily decay to all users based on chapter.
    """
    verify_cron_secret(secret)
    users = await user_repo.get_all_active()
    for user in users:
        decay = get_decay_for_chapter(user.chapter)
        await user_repo.apply_decay(user.id, decay)
    return {"processed": len(users)}

@router.post("/tasks/deliver")
async def deliver_scheduled_messages(
    secret: str = Header(..., alias="X-Cron-Secret"),
):
    """
    Called by pg_cron via Edge Function every 30 seconds.
    Delivers due messages from scheduled_events table.
    """
    verify_cron_secret(secret)
    events = await event_repo.get_due_events(limit=50)
    for event in events:
        await event_repo.mark_processing(event.id)
        if event.channel == "telegram":
            await telegram_bot.send_message(
                chat_id=event.user.telegram_id,
                text=event.payload["message_text"],
            )
        await event_repo.mark_done(event.id)
    return {"delivered": len(events)}

@router.post("/tasks/summary")
async def generate_daily_summaries(
    secret: str = Header(..., alias="X-Cron-Secret"),
):
    """
    Called by pg_cron via Edge Function at 4am UTC.
    Generates Nikita's daily summaries for each user.
    """
    verify_cron_secret(secret)
    users = await user_repo.get_all_active()
    for user in users:
        summary = await generate_summary_for_user(user.id)
        await summary_repo.create(user.id, summary)
    return {"summaries": len(users)}
```

#### pg_cron + Edge Function Setup

```sql
-- In Supabase SQL Editor
SELECT cron.schedule(
    'apply-daily-decay',
    '0 3 * * *',  -- 3am UTC daily
    $$SELECT net.http_post(
        url := 'https://nikita-api-xxx.run.app/tasks/decay',
        headers := '{"X-Cron-Secret": "your-secret"}'::jsonb
    )$$
);

SELECT cron.schedule(
    'deliver-messages',
    '*/30 * * * * *',  -- Every 30 seconds
    $$SELECT net.http_post(
        url := 'https://nikita-api-xxx.run.app/tasks/deliver',
        headers := '{"X-Cron-Secret": "your-secret"}'::jsonb
    )$$
);

SELECT cron.schedule(
    'daily-summaries',
    '0 4 * * *',  -- 4am UTC daily
    $$SELECT net.http_post(
        url := 'https://nikita-api-xxx.run.app/tasks/summary',
        headers := '{"X-Cron-Secret": "your-secret"}'::jsonb
    )$$
);
```

#### Voice Callbacks (Phase 4)

```python
# api/routes/voice.py

POST /voice/elevenlabs/server-tool
├─ Body: ElevenLabsToolRequest
│  {tool_name, parameters, session_id}
├─ Tools:
│  • get_context → return chapter, score, vice prefs
│  • get_memory → Graphiti search
│  • score_turn → analyze conversation turn
│  • update_memory → add episodes
└─ Response: Tool-specific JSON

POST /voice/elevenlabs/callback
├─ Body: ConversationEvent (user_transcript, agent_response)
├─ Process: Log to conversations table
└─ Response: {"ok": true}
```

#### Portal Stats API (Phase 5)

```python
# api/routes/portal.py

GET /portal/stats/{user_id}
├─ Auth: Supabase JWT required (RLS enforced)
├─ Response:
│  {
│    "current_score": 67.5,
│    "chapter": 2,
│    "chapter_name": "Intrigue",
│    "days_played": 18,
│    "boss_attempts": 1,
│    "score_history": [{date, score}, ...],
│    "game_status": "active"
│  }
└─ Uses: UserRepository.get_stats()

GET /portal/conversations/{user_id}
├─ Auth: Supabase JWT
├─ Query: ?limit=20&offset=0&platform=telegram
├─ Response:
│  {
│    "conversations": [
│      {id, platform, started_at, messages, score_delta},
│      ...
│    ],
│    "total": 45
│  }
└─ Uses: ConversationRepository.list()

GET /portal/daily-summary/{user_id}/{date}
├─ Auth: Supabase JWT
├─ Response:
│  {
│    "date": "2025-01-15",
│    "score_start": 65.0,
│    "score_end": 67.5,
│    "decay_applied": -2.0,
│    "conversations_count": 3,
│    "nikita_summary_text": "We talked about...",
│    "key_events": [...]
│  }
└─ Uses: DailySummaryRepository.get()
```

### Repository Pattern ✅ COMPLETE (7 repos)

```python
# db/repositories/user_repository.py

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: UUID) -> User:
        """Get user by ID with metrics loaded"""

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID"""

    async def create(self, telegram_id: int, phone: str) -> User:
        """Create new user with default metrics"""

    async def update_score(
        self,
        user_id: UUID,
        new_score: Decimal,
        event_type: str,
    ) -> None:
        """Update score and log to score_history"""

    async def apply_decay(self, user_id: UUID, decay: Decimal) -> None:
        """Apply daily decay and log event"""

    async def advance_chapter(self, user_id: UUID) -> None:
        """Advance to next chapter after boss pass"""

    async def increment_boss_attempts(self, user_id: UUID) -> int:
        """Increment boss attempts, return new count"""

    async def get_score_history(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> list[ScoreHistory]:
        """Get recent score history for graphs"""

# Similar repositories for:
# - ConversationRepository
# - UserMetricsRepository
# - VicePreferenceRepository
# - DailySummaryRepository
```

### Middleware ✅ COMPLETE

```python
# api/middleware/auth.py

async def supabase_auth_middleware(request: Request, call_next):
    """
    Verify Supabase JWT token for portal endpoints.
    Attach user_id to request.state.
    """
    if request.url.path.startswith("/portal/"):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        # Verify with Supabase
        # Attach user_id to request.state

# api/middleware/rate_limit.py

async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limit by user_id or IP.
    • Telegram: 10 req/min per user
    • Voice: 5 req/min per user
    • Portal: 100 req/min per user
    """
```

## Key Patterns

### 1. Dependency Injection Pattern

```python
# api/main.py (planned)

from nikita.db.database import get_async_session
from nikita.db.repositories.user_repository import UserRepository

async def get_user_repo(
    session: AsyncSession = Depends(get_async_session)
) -> UserRepository:
    return UserRepository(session)

@router.get("/stats/{user_id}")
async def get_stats(
    user_id: UUID,
    repo: UserRepository = Depends(get_user_repo),
):
    user = await repo.get(user_id)
    return {"score": user.relationship_score}
```

### 2. Pydantic Schema Pattern

```python
# api/schemas/user.py (current basic, expand in Phase 2)

class UserResponse(BaseModel):
    id: UUID
    telegram_id: int | None
    relationship_score: Decimal
    chapter: int
    game_status: str

class StatsResponse(BaseModel):
    current_score: Decimal
    chapter: int
    chapter_name: str
    days_played: int
    score_history: list[ScorePoint]

class ScorePoint(BaseModel):
    date: datetime
    score: Decimal
```

### 3. Error Handling Pattern

```python
# api/main.py (planned)

from fastapi import HTTPException

class GameOverError(Exception):
    pass

class BossFailureError(Exception):
    pass

@app.exception_handler(GameOverError)
async def game_over_handler(request, exc):
    return JSONResponse(
        status_code=200,
        content={
            "status": "game_over",
            "message": "Nikita dumped you. Game over.",
        },
    )
```

## Critical Files

| File | Purpose | Status |
|------|---------|--------|
| `nikita/db/models/user.py:19-110` | User model with game state | ✅ Complete |
| `nikita/db/models/user.py:112-167` | UserMetrics with composite score | ✅ Complete |
| `nikita/db/models/user.py:169-207` | UserVicePreference tracking | ✅ Complete |
| `nikita/api/schemas/user.py` | Pydantic request/response models | ⚠️ Basic |
| `nikita/config/settings.py:10-79` | All environment settings | ✅ Complete |

## Database Migrations ✅ COMPLETE (8 migrations)

```bash
# Using Alembic

# Generate migration from models
alembic revision --autogenerate -m "Initial schema"

# Apply to Supabase
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Row-Level Security (Supabase)

**CRITICAL**: Use `(select auth.uid())` pattern for performance (evaluates once per query, not per row).

```sql
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_embeddings ENABLE ROW LEVEL SECURITY;

-- OPTIMIZED RLS Pattern: (select auth.uid()) instead of auth.uid()
-- This creates an initplan that evaluates once, not per row (50-100x faster)

CREATE POLICY "users_own_data" ON users
    FOR ALL USING (id = (select auth.uid()))
    WITH CHECK (id = (select auth.uid()));

CREATE POLICY "user_metrics_own_data" ON user_metrics
    FOR ALL USING (user_id = (select auth.uid()))
    WITH CHECK (user_id = (select auth.uid()));

CREATE POLICY "conversations_own_data" ON conversations
    FOR ALL USING (user_id = (select auth.uid()))
    WITH CHECK (user_id = (select auth.uid()));

CREATE POLICY "message_embeddings_own_data" ON message_embeddings
    FOR ALL USING (user_id = (select auth.uid()))
    WITH CHECK (user_id = (select auth.uid()));

-- Admin service role bypasses RLS automatically
-- API uses service_role key for internal operations
```

### RLS Best Practices

1. **Performance**: Always use `(select auth.uid())` not `auth.uid()`
2. **Single Policy**: Use `FOR ALL` with `WITH CHECK` (avoid multiple permissive policies)
3. **Denormalization**: Add `user_id` to child tables for direct RLS checks (e.g., message_embeddings)
4. **Extensions**: Keep vector/pg_trgm in `extensions` schema, not public
