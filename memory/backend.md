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

**Dockerfile** (TODO):
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
├── main.py                    ⚠️ Skeleton app
├── routes/
│   ├── telegram.py            ❌ TODO (Phase 2)
│   ├── tasks.py               ❌ TODO (Phase 2) - pg_cron endpoints
│   ├── voice.py               ❌ TODO (Phase 4)
│   ├── portal.py              ❌ TODO (Phase 5)
│   └── admin.py               ❌ TODO (Phase 5)
├── schemas/
│   ├── user.py                ✅ Basic Pydantic models
│   ├── conversation.py        ✅ Basic Pydantic models
│   └── game.py                ✅ Basic Pydantic models
└── middleware/
    ├── auth.py                ❌ TODO (Phase 2)
    └── rate_limit.py          ❌ TODO (Phase 2)
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
├─ graphiti_group_id TEXT (links to FalkorDB)
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

### API Endpoints (TODO Phase 2-5)

#### Telegram Webhooks (Phase 2)

```python
# api/routes/telegram.py

POST /telegram/webhook
├─ Body: TelegramUpdate (message, callback, etc.)
├─ Process:
│  1. Extract user_id from telegram_id
│  2. Pass to ConversationOrchestrator
│  3. Route to text agent
│  4. Score response
│  5. Update memory
│  6. Send reply via Telegram API
└─ Response: {"ok": true}

POST /telegram/set-webhook
├─ Admin endpoint to configure Telegram webhook
└─ Response: {"ok": true, "url": "..."}
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

### Repository Pattern (TODO Phase 2)

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

### Middleware (TODO Phase 2)

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

## Database Migrations (TODO Phase 2)

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

```sql
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users see own data" ON users
    FOR ALL USING (auth.uid() = id);

CREATE POLICY "Users see own metrics" ON user_metrics
    FOR ALL USING (auth.uid() IN (SELECT id FROM users WHERE users.id = user_id));

-- Admin service role bypasses RLS
-- API uses service key for internal operations
```
