# External Integrations

## Current State

All integrations configured in `nikita/config/settings.py` and `nikita/config/elevenlabs.py`. **MVP COMPLETE (Dec 2025)** - Text agent, Telegram, scoring, and background tasks all deployed to Cloud Run.

## Supabase Integration

### Configuration (Phase 1 ✅)

**Settings** (`nikita/config/settings.py:24-30`):

```python
supabase_url: str = Field(..., description="Supabase project URL")
supabase_anon_key: str = Field(..., description="Supabase anonymous/public key")
supabase_service_key: str = Field(..., description="Supabase service role key")
database_url: str = Field(..., description="PostgreSQL connection string")
```

**Environment Variables**:

```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres
```

### Usage Patterns ✅ COMPLETE

**1. Dual-Mode Access**:

```python
# API/Backend: SQLAlchemy via direct PostgreSQL connection
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine(settings.database_url)

# Portal: Supabase Client SDK (for RLS, Auth)
from supabase import create_client
supabase = create_client(settings.supabase_url, settings.supabase_anon_key)
```

**2. Row-Level Security (RLS)**:

```sql
-- OPTIMIZED: Use (select auth.uid()) for performance (evaluates once per query)
-- Portal users can only access their own data
CREATE POLICY "users_own_data" ON users
    FOR ALL USING (id = (select auth.uid()))
    WITH CHECK (id = (select auth.uid()));

-- API uses service_role key to bypass RLS for internal operations
-- Backend uses direct PostgreSQL connection with service_role (bypasses RLS)
```

**RLS Performance Note**: The `(select auth.uid())` pattern creates an initplan that evaluates the auth function once per query instead of once per row. This provides 50-100x performance improvement on large tables.

**3. Authentication Flows**:

```python
# Telegram OTP Flow (PRIMARY - Dec 2025)
# Step 1: Send 6-digit OTP code to email (NO redirect URL = code-only email)
await supabase.auth.sign_in_with_otp({
    "email": email,
    "options": {"should_create_user": True}
    # NOTE: No "email_redirect_to" = Supabase sends 6-digit code only
})

# Step 2: Verify OTP code entered in Telegram chat
response = await supabase.auth.verify_otp({
    "email": email,
    "token": "847291",  # 6-digit code from user
    "type": "email"     # CRITICAL: "email" for OTP, not "magiclink"
})
user_id = response.user.id  # Create user record with this ID

# Portal: Magic link sign-in (still uses redirect)
response = supabase.auth.sign_in_with_otp({
    "email": email,
    "options": {"email_redirect_to": "https://portal.nikita.game/auth/callback"}
})

# Backend: Verify JWT from portal requests
jwt_token = request.headers["Authorization"].split("Bearer ")[1]
user = supabase.auth.get_user(jwt_token)
```

**4. Real-time Subscriptions** (Portal):

```typescript
// Portal dashboard listens for score updates
const channel = supabase
  .channel('score_updates')
  .on('postgres_changes', {
    event: 'UPDATE',
    schema: 'public',
    table: 'users',
    filter: `id=eq.${userId}`
  }, (payload) => {
    updateScoreDisplay(payload.new.relationship_score)
  })
  .subscribe()
```

### Schema Deployment

```bash
# Using Alembic for migrations
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head

# Or: Direct SQL via Supabase Dashboard
# Copy from plan section 9 (database schema)
```

## Memory Backend (Spec 042: Supabase pgVector)

> **Feb 2026 Update**: Migrated from Neo4j/Graphiti to **Supabase pgVector**.
> Consolidates all data in PostgreSQL with vector embeddings for semantic search.

### Configuration (Updated)

**Settings** (`nikita/config/settings.py`):

```python
# Neo4j settings REMOVED
# Memory now uses pgVector extension in Supabase

database_url: str = Field(
    ...,
    description="PostgreSQL connection string (pgVector enabled)",
)
openai_api_key: str = Field(
    ...,
    description="OpenAI API key for embeddings",
)
embedding_model: str = Field(
    default="text-embedding-3-small",
    description="OpenAI embedding model",
)
```

**Migration**:

```bash
# Apply Spec 042 migration (adds memory_facts table)
alembic upgrade head

# Optional: Migrate existing Neo4j data
python scripts/migrate_neo4j_to_supabase.py
```

### SupabaseMemory Client (Updated)

**Implemented** in `nikita/memory/supabase_memory.py`:

```python
class SupabaseMemory:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.embedder = OpenAIEmbedder(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
        )

    async def add_fact(
        self,
        fact: str,
        user_id: UUID,
        fact_type: str = "user",  # user | nikita | relationship
    ) -> None:
        """Add fact with deduplication (hash-based)"""

    async def search(
        self,
        query: str,
        user_id: UUID,
        fact_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[MemoryFact]:
        """Semantic search via pgVector cosine similarity"""

    async def get_recent(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[MemoryFact]:
        """Get recent facts (time-ordered)"""
```

### Memory Schema (pgVector)

```
memory_facts
├─ id (UUID, PK)
├─ user_id (UUID, FK to users)
├─ fact (TEXT)
├─ fact_type (user|nikita|relationship)
├─ embedding (vector(1536))  -- pgVector
├─ hash (TEXT, UNIQUE)       -- Deduplication
├─ created_at (TIMESTAMPTZ)
└─ INDEX USING ivfflat (embedding vector_cosine_ops)

# Deduplication: Hash prevents duplicate facts
# Semantic search: pgVector cosine similarity
# No separate graph database needed
```

### Usage Patterns ✅ Spec 042

```python
from nikita.memory.supabase_memory import SupabaseMemory

# Initialize with session
memory = SupabaseMemory(session)

# Search relevant memories
facts = await memory.search(
    query="recent conversations about work",
    user_id=user_id,
    fact_types=["user", "relationship"],
    limit=5,
)

# Add new fact (auto-deduplication)
await memory.add_fact(
    fact="User is learning Python",
    user_id=user_id,
    fact_type="user",
)

# Get recent memories
recent = await memory.get_recent(user_id, limit=10)
```

## Anthropic (Claude) Integration

### Configuration (Phase 1 ✅)

**Settings** (`nikita/config/settings.py:38-43`):

```python
anthropic_api_key: str = Field(..., description="Anthropic API key")
anthropic_model: str = Field(
    default="claude-sonnet-4-5-20250929",
    description="Claude model for text agent",
)
```

**Environment Variables**:

```bash
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
```

### Usage: Pydantic AI Text Agent ✅ COMPLETE (156 tests)

```python
from pydantic_ai import Agent, RunContext

nikita_agent = Agent(
    'anthropic:claude-sonnet-4-5-20250929',
    deps_type=NikitaDependencies,
    output_type=NikitaResponse,
    instructions="""You are Nikita, a 25-year-old hacker who:
    - Survives on black coffee and spite
    - Microdoses LSD while coding
    - Will pick fights to test what someone is made of
    - Is direct, intellectually rigorous, emotionally complicated
    """,
)

@nikita_agent.instructions
async def add_dynamic_context(ctx: RunContext[NikitaDependencies]) -> str:
    """Inject chapter, score, memories"""
    user = await ctx.deps.user_repo.get(ctx.deps.user_id)
    memory_context = await ctx.deps.memory.get_context_for_prompt(ctx.prompt)

    return f"""
    CURRENT STATE:
    - Chapter: {user.chapter} ({CHAPTER_NAMES[user.chapter]})
    - Score: {user.relationship_score}%
    - Behavior: {CHAPTER_BEHAVIORS[user.chapter]}

    RELEVANT MEMORIES:
    {memory_context}
    """

# Run agent
result = await nikita_agent.run(
    user_message,
    deps=NikitaDependencies(user_id, memory, repo, calculator),
)
response: NikitaResponse = result.data
```

### Usage: Response Scoring ✅ COMPLETE (60 tests)

```python
# LLM-based scoring analyzer
scoring_agent = Agent(
    'anthropic:claude-sonnet-4-5-20250929',
    output_type=ResponseAnalysis,
    instructions="""Analyze this conversation turn and return metric deltas.
    Consider: intellectual depth, emotional vulnerability, trust signals, etc.
    """,
)

result = await scoring_agent.run(
    f"User: {user_message}\nNikita: {nikita_response}",
    deps=ScoringDependencies(chapter, score, context),
)

analysis: ResponseAnalysis = result.data
# Returns: intimacy_delta, passion_delta, trust_delta, secureness_delta
```

## OpenAI Integration

### Configuration (Phase 1 ✅)

**Settings** (`nikita/config/settings.py:45-50`):

```python
openai_api_key: str = Field(..., description="OpenAI API key for embeddings")
embedding_model: str = Field(
    default="text-embedding-3-small",
    description="OpenAI embedding model",
)
```

**Purpose**: Embeddings only (for Graphiti and pgVector semantic search)

### Usage: Graphiti Embeddings (Phase 1 ✅)

```python
from graphiti_core.embedder import OpenAIEmbedder

embedder = OpenAIEmbedder(
    api_key=settings.openai_api_key,
    model=settings.embedding_model,  # text-embedding-3-small
)

# Used internally by Graphiti for semantic search
# No direct API calls needed in application code
```

### Usage: Message Embeddings ✅ COMPLETE

```python
# Store embeddings in Supabase for semantic search
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.openai_api_key)

async def embed_message(message_text: str) -> list[float]:
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=message_text,
    )
    return response.data[0].embedding

# Store in message_embeddings table
embedding = await embed_message(user_message)
await db.execute(
    insert(MessageEmbedding).values(
        user_id=user_id,
        message_text=user_message,
        embedding=embedding,
        role="user",
    )
)

# Later: Semantic search
similar = await db.execute(
    select(MessageEmbedding)
    .order_by(MessageEmbedding.embedding.cosine_distance(query_embedding))
    .limit(5)
)
```

## ElevenLabs Integration

### Configuration (Phase 1 ✅)

**Settings** (`nikita/config/settings.py:52-54`):

```python
elevenlabs_api_key: str = Field(..., description="ElevenLabs API key")
```

**Agent ID Abstraction** (`nikita/config/elevenlabs.py`):

```python
ELEVENLABS_AGENTS = {
    "default": "PB6BdkFkZLbI39GHdnbQ",
    "chapter_1_curious": "PB6BdkFkZLbI39GHdnbQ",
    "chapter_2_playful": "PB6BdkFkZLbI39GHdnbQ",  # Can swap per chapter/mood
    "chapter_3_vulnerable": "PB6BdkFkZLbI39GHdnbQ",
    "chapter_4_intimate": "PB6BdkFkZLbI39GHdnbQ",
    "chapter_5_secure": "PB6BdkFkZLbI39GHdnbQ",
    "boss_fight": "PB6BdkFkZLbI39GHdnbQ",
}

def get_agent_id(chapter: int, is_boss: bool = False) -> str:
    """Get appropriate agent ID based on game state"""
    if is_boss:
        return ELEVENLABS_AGENTS["boss_fight"]
    return ELEVENLABS_AGENTS.get(f"chapter_{chapter}_...", ELEVENLABS_AGENTS["default"])
```

### Usage: Voice Agent ✅ DEPLOYED (Jan 2026)

**Architecture**: ElevenLabs Conversational AI 2.0 with Server Tools (REST callbacks, not WebSocket)

**Implementation**: `nikita/agents/voice/` (14 modules, 193 tests)

**API Endpoints**:
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/voice/availability/{user_id}` | GET | Check call availability |
| `/api/v1/voice/initiate` | POST | Start voice call |
| `/api/v1/voice/pre-call` | POST | Inbound webhook (Twilio → ElevenLabs) |
| `/api/v1/voice/server-tool` | POST | Server tool dispatch |
| `/api/v1/voice/webhook` | POST | Call events (connected, ended) |

**Server Tools**: `get_context`, `get_memory`, `score_turn`, `update_memory`

### Server Tools ✅ DEPLOYED (Jan 2026)

```python
# api/routes/voice.py

@router.post("/api/v1/voice/server-tool")
async def elevenlabs_server_tool(request: ElevenLabsToolRequest):
    tool_name = request.tool_name
    parameters = request.parameters
    session_id = request.session_id  # Map to user_id

    if tool_name == "get_context":
        user = await get_user(session_id)
        return {
            "chapter": user.chapter,
            "score": float(user.relationship_score),
            "behavior_hints": CHAPTER_BEHAVIORS[user.chapter],
        }

    elif tool_name == "get_memory":
        memory = NikitaMemory(session_id)
        results = await memory.search_memory(parameters["query"])
        return {"memories": [r["fact"] for r in results]}

    elif tool_name == "score_turn":
        calculator = ScoreCalculator(llm_client)
        analysis = await calculator.analyze_response(
            user_message=parameters["user_said"],
            nikita_response=parameters["nikita_said"],
            context=...,
        )
        return {
            "score_delta": float(analysis.total_delta),
            "new_score": float(analysis.new_score),
        }
```

## ElevenLabs Webhook Handling (Jan 2026)

### Signature Verification

**CRITICAL**: ElevenLabs uses `v0` signature (NOT `v1`):

```python
# nikita/api/routes/voice.py

def verify_elevenlabs_signature(
    payload: bytes, signature_header: str, signing_secret: str
) -> bool:
    """Verify ElevenLabs webhook signature.

    Format: 't=1704067200,v0=abc123...' (NOT v1!)
    """
    parts = dict(part.split("=", 1) for part in signature_header.split(","))
    timestamp = parts["t"]
    signature = parts["v0"]  # CRITICAL: Use v0

    signed_payload = f"{timestamp}.{payload.decode()}"
    expected = hmac.new(
        signing_secret.encode(), signed_payload.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)
```

### Webhook Payload Structure

**CRITICAL**: Field names differ from documentation:

```python
# ElevenLabs sends THIS format:
{
    "type": "conversation_initiation_client_data",  # NOT 'event_type'
    "conversation_id": "conv_xxx",
    "data": {  # Nested under 'data', not flat
        "conversation_id": "conv_xxx",
        "agent_id": "...",
        # ... more fields
    }
}

# Handler:
@router.post("/api/v1/voice/webhook")
async def elevenlabs_webhook(request: Request):
    payload = await request.json()
    event_type = payload.get("type")  # NOT 'event_type'
    data = payload.get("data", {})    # Nested data

    if event_type == "post_conversation_summary":
        transcript = data.get("transcript_raw")
        # ...
```

### DynamicVariables Pattern

**CRITICAL**: Return ALL defined variables in EVERY path:

```python
# nikita/agents/voice/models.py

class DynamicVariables(BaseModel):
    """Dynamic variables for ElevenLabs prompt injection."""

    # User context
    user_name: str = "friend"
    chapter: int = 1
    relationship_score: float = 50.0
    engagement_state: str = "IN_ZONE"

    # Nikita state
    nikita_mood: str = "neutral"
    nikita_energy: str = "medium"
    time_of_day: str = "evening"

    # Conversation context
    recent_topics: str = ""
    open_threads: str = ""

    # Secrets (hidden from LLM, used for server tool auth)
    secret__user_id: str = ""
    secret__signed_token: str = ""

# EVERY code path MUST provide ALL fields, or ElevenLabs throws validation errors.
# Use defaults generously - None values cause failures.
```

### Pre-Call Webhook Response

```python
@router.post("/api/v1/voice/pre-call")
async def pre_call_webhook(request: Request) -> dict:
    """Handle inbound call from Twilio → ElevenLabs."""

    # Accept the call
    return {
        "accept_call": True,
        "agent_id": agent_id,
        "dynamic_variables": variables.to_dict_with_secrets(),
        "conversation_config_override": {
            "agent": {
                "prompt": {"prompt": system_prompt},
                "first_message": first_message,
            },
            "tts": {
                "stability": 0.55,
                "similarity_boost": 0.80,
                "speed": 1.05,
            },
        },
    }
```

### Meta-Nikita Onboarding Agent (Spec 028) ✅ DEPLOYED (Jan 2026)

**Purpose**: Voice onboarding for new users - collects profile, sets preferences, hands off to Nikita

**Architecture**: ElevenLabs Conversational AI 2.0 with Server Tools (same pattern as Nikita voice agent)

**Configuration**:

| Setting | Value |
|---------|-------|
| Agent ID | `agent_4801kewekhxgekzap1bqdr62dxvc` |
| Persona | Underground Game Hostess (seductive, playful provocateur) |
| Stability | 0.40 (dynamic, emotional voice) |
| Similarity | 0.70 |
| Speed | 0.95 (seductive pacing) |

**API Endpoints** (`/api/v1/onboarding/*`):
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/status` | POST | Check user's onboarding status |
| `/initiate` | POST | Start voice onboarding call |
| `/server-tool` | POST | Handle ElevenLabs server tool calls |
| `/webhook` | POST | Receive ElevenLabs call events |
| `/skip` | POST | Skip voice onboarding |

**Server Tools**:

```python
# nikita/onboarding/server_tools.py

@tool("collect_profile")
async def collect_profile(field_name: str, value: str, user_id: str):
    """Store user profile data during onboarding.

    Fields: timezone, occupation, hobbies, personality_type, hangout_spots
    """
    await user_repo.update_onboarding_profile(user_id, {field_name: value})
    return {"status": "stored", "field": field_name}

@tool("configure_preferences")
async def configure_preferences(
    darkness_level: int,  # 1-5
    pacing_weeks: int,    # 4 or 8
    conversation_style: str,  # listener/balanced/sharer
    user_id: str,
):
    """Set user experience preferences."""
    await user_repo.update_onboarding_profile(user_id, {
        "darkness_level": darkness_level,
        "pacing_weeks": pacing_weeks,
        "conversation_style": conversation_style,
    })
    return {"status": "configured"}

@tool("complete_onboarding")
async def complete_onboarding(call_id: str, notes: str, user_id: str):
    """Mark onboarding complete and trigger handoff to Nikita."""
    await user_repo.complete_onboarding(user_id, call_id)
    await handoff_manager.send_first_nikita_message(user_id)
    return {"status": "completed", "handoff": "initiated"}
```

**Database Schema** (Migration 0009):

```sql
-- Added to users table
ALTER TABLE users ADD COLUMN onboarding_status VARCHAR(20)
    DEFAULT 'pending'
    CHECK (onboarding_status IN ('pending', 'in_progress', 'completed', 'skipped'));
ALTER TABLE users ADD COLUMN onboarding_profile JSONB DEFAULT '{}';
ALTER TABLE users ADD COLUMN onboarded_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN onboarding_call_id VARCHAR(100);
```

**Implementation**: `nikita/onboarding/` (8 modules, 231 tests)

## Telegram Integration

### Bot Details

| Property | Value |
|----------|-------|
| **Bot Handle** | `@Nikita_my_bot` |
| **Bot URL** | https://t.me/Nikita_my_bot |
| **Token** | Stored in `TELEGRAM_BOT_TOKEN` env var |
| **Webhook** | `https://nikita-api-1040094048579.us-central1.run.app/telegram/webhook` |

### Configuration (Phase 1 ✅)

**Settings** (`nikita/config/settings.py:55-61`):

```python
telegram_bot_token: str = Field(..., description="Telegram bot token")
telegram_webhook_url: str | None = Field(
    default=None,
    description="Webhook URL for Telegram bot",
)
```

**Environment Variables**:

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...  # Get from @BotFather on Telegram
TELEGRAM_WEBHOOK_URL=https://api.nikita.game/telegram/webhook
```

### Proactive Messaging Architecture

> **Pattern**: All scheduled communications (text, voice calls, summaries) use the `scheduled_events` table, delivered by pg_cron → Cloud Run endpoints.

**Data Flow**:
```
User message → Text Agent → Generate response
                             ↓
                  Calculate delay (ResponseTimer)
                             ↓
                  Store in scheduled_events table
                             ↓
                  pg_cron (every 30s) → POST /tasks/deliver
                             ↓
                  Deliver via Telegram API or initiate voice call
```

### scheduled_events Table (Unified)

```sql
-- Replaces pending_responses - handles ALL proactive communications
CREATE TABLE scheduled_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    channel TEXT NOT NULL CHECK (channel IN ('telegram', 'voice')),
    event_type TEXT NOT NULL CHECK (event_type IN
        ('send_message', 'outbound_call', 'daily_summary')),
    due_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    -- Payload examples:
    -- send_message: {"message_text": "...", "parse_mode": "Markdown"}
    -- outbound_call: {"context": "...", "mood": "playful", "agent_id": "..."}
    -- daily_summary: {"summary_text": "...", "score_change": -2.5}
    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'done', 'failed')),
    created_at TIMESTAMPTZ DEFAULT now(),
    processed_at TIMESTAMPTZ,
    error_message TEXT
);

-- Index for efficient polling by /tasks/deliver endpoint
CREATE INDEX idx_scheduled_events_due
ON scheduled_events (due_at, status)
WHERE status = 'pending';
```

### pg_cron Job Setup

```sql
-- Enable pg_cron extension (Supabase Dashboard → Database → Extensions)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule delivery check every minute
SELECT cron.schedule(
    'deliver-pending-messages',
    '* * * * *',  -- Every minute
    $$
    SELECT net.http_post(
        url := 'https://vlvlwmolfdpzdfmtipji.supabase.co/functions/v1/deliver-responses',
        headers := '{"Authorization": "Bearer ' || current_setting('app.service_key') || '"}'::jsonb
    );
    $$
);
```

### Edge Function: Trigger /tasks/deliver (Simplified)

> **Note**: The Edge Function just triggers the Cloud Run endpoint which handles the actual delivery logic. This keeps business logic in Python.

```typescript
// supabase/functions/trigger-deliver/index.ts
// Called by pg_cron every 30 seconds

Deno.serve(async (req) => {
  const CLOUD_RUN_URL = Deno.env.get('CLOUD_RUN_URL')!
  const CRON_SECRET = Deno.env.get('CRON_SECRET')!

  const response = await fetch(`${CLOUD_RUN_URL}/tasks/deliver`, {
    method: 'POST',
    headers: {
      'X-Cron-Secret': CRON_SECRET,
      'Content-Type': 'application/json',
    },
  })

  const result = await response.json()
  return new Response(JSON.stringify(result))
})
```

**Delivery Logic in Python** (see `nikita/api/routes/tasks.py`):
- Queries `scheduled_events` WHERE status='pending' AND due_at <= now()
- Handles telegram (send_message) vs voice (outbound_call) channels
- Marks events as 'done' or 'failed' with error_message

### Usage: Message Handler Integration

```python
# nikita/agents/text/handler.py

async def store_scheduled_event(
    user_id: UUID,
    channel: str,  # "telegram" | "voice"
    event_type: str,  # "send_message" | "outbound_call" | "daily_summary"
    due_at: datetime,
    payload: dict,
) -> None:
    """Store scheduled event for pg_cron delivery via /tasks/deliver."""
    await supabase.table('scheduled_events').insert({
        'user_id': str(user_id),
        'channel': channel,
        'event_type': event_type,
        'due_at': due_at.isoformat(),
        'payload': payload,
        'status': 'pending',
    }).execute()

# Example: Schedule a delayed Telegram message
await store_scheduled_event(
    user_id=user.id,
    channel="telegram",
    event_type="send_message",
    due_at=datetime.now() + timedelta(seconds=decision.delay_seconds),
    payload={"message_text": decision.response, "parse_mode": "Markdown"},
)
```

### Webhook Handler (aiogram IN FastAPI)

> **Architecture Note**: aiogram runs in webhook mode WITHIN FastAPI (not as separate polling process). The FastAPI app includes the aiogram Dispatcher, which processes Telegram updates via HTTP webhook.

```python
# nikita/api/main.py - aiogram integrated into FastAPI

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Message, Update

app = FastAPI()
bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()

@dp.message()
async def handle_message(message: Message):
    """Route messages to text agent"""
    user = await get_or_create_user(telegram_id=message.from_user.id)
    handler = MessageHandler()
    decision = await handler.handle(user.id, message.text)

    if decision.should_respond:
        # Store in scheduled_events for delayed delivery
        await store_scheduled_event(
            user_id=user.id,
            channel="telegram",
            event_type="send_message",
            due_at=decision.scheduled_at,
            payload={"message_text": decision.response},
        )

# api/routes/telegram.py
@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Receive updates from Telegram - aiogram webhook handler"""
    update = Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}
```

## Background Tasks (pg_cron + Edge Functions)

> **Nov 2025 Update**: **Celery + Redis removed**. All background tasks now use
> **pg_cron → Supabase Edge Functions → Cloud Run API endpoints**.
> This eliminates infrastructure complexity while maintaining full functionality.

### Architecture

```
pg_cron (Supabase) → Edge Function → Cloud Run API
      ↓                   ↓               ↓
  Schedule job     Make HTTP call    Execute task
  (SQL cron)       (authenticated)   (Python logic)
```

### Configuration

**pg_cron schedules** (SQL in Supabase Dashboard):

```sql
-- Daily decay at 3am UTC
SELECT cron.schedule(
    'apply-daily-decay',
    '0 3 * * *',
    $$SELECT net.http_post(
        url := 'https://nikita-api-xxxx.run.app/tasks/decay',
        headers := '{"Authorization": "Bearer SERVICE_KEY"}'::jsonb,
        body := '{}'::jsonb
    );$$
);

-- Deliver pending messages every 30 seconds
SELECT cron.schedule(
    'deliver-pending-msgs',
    '*/30 * * * * *',  -- Every 30 seconds (pg_cron 1.5+ supports seconds)
    $$SELECT net.http_post(
        url := 'https://nikita-api-xxxx.run.app/tasks/deliver',
        headers := '{"Authorization": "Bearer SERVICE_KEY"}'::jsonb,
        body := '{}'::jsonb
    );$$
);

-- Daily summaries at 4am UTC
SELECT cron.schedule(
    'generate-daily-summaries',
    '0 4 * * *',
    $$SELECT net.http_post(
        url := 'https://nikita-api-xxxx.run.app/tasks/summary',
        headers := '{"Authorization": "Bearer SERVICE_KEY"}'::jsonb,
        body := '{}'::jsonb
    );$$
);
```

### Cloud Run Task Endpoints

```python
# nikita/api/routes/tasks.py

from fastapi import APIRouter, Depends, HTTPException
from nikita.db.dependencies import get_user_repo

router = APIRouter(prefix="/tasks", tags=["background-tasks"])

@router.post("/decay")
async def apply_daily_decay(
    user_repo: UserRepository = Depends(get_user_repo),
):
    """Apply decay to all users who haven't interacted past grace period"""
    # Called by pg_cron via Edge Function
    affected = await user_repo.apply_decay_to_inactive_users()
    return {"ok": True, "affected_users": affected}

@router.post("/deliver")
async def deliver_pending_messages(
    msg_repo: MessageRepository = Depends(get_message_repo),
):
    """Deliver messages whose scheduled_at has passed"""
    # Called every 30s by pg_cron via Edge Function
    delivered = await msg_repo.deliver_due_messages()
    return {"ok": True, "delivered": delivered}

@router.post("/summary")
async def generate_daily_summaries(
    summary_repo: SummaryRepository = Depends(get_summary_repo),
):
    """Generate Nikita's in-character daily recap for all active users"""
    # Called daily at 4am by pg_cron via Edge Function
    generated = await summary_repo.generate_for_yesterday()
    return {"ok": True, "generated": generated}
```

### Why Not Celery/Redis?

| Factor | Celery + Redis | pg_cron + Edge Functions |
|--------|----------------|--------------------------|
| **Infra** | Redis server required | Built into Supabase |
| **Cost** | ~$5-15/mo for Redis | $0 (included) |
| **Ops** | Monitor broker, workers | Zero maintenance |
| **Scaling** | Worker pool sizing | Cloud Run auto-scales |
| **Complexity** | Celery Beat, workers, broker | SQL cron + HTTP |

**Decision**: For our MVP load (<1000 users), pg_cron + Edge Functions is simpler and free.

## Critical Files

| File | Purpose | Status |
|------|---------|--------|
| `nikita/config/settings.py` | All service configs (Neo4j, Supabase, etc.) | ✅ Complete |
| `nikita/config/elevenlabs.py` | Agent ID abstraction | ✅ Complete |
| `nikita/memory/graphiti_client.py` | Neo4j Aura/Graphiti wrapper | ✅ Complete |
| `nikita/agents/text/handler.py` | Message handler + scheduling | ✅ Complete (156 tests) |
| `nikita/agents/text/skip.py` | Skip decision logic | ✅ Complete |
| `nikita/agents/text/timing.py` | Response timing | ✅ Complete |
| `nikita/platforms/telegram/bot.py` | Telegram bot setup | ✅ DEPLOYED (Cloud Run) |
| `nikita/platforms/telegram/message_handler.py` | Message processing | ✅ DEPLOYED (86 tests) |
| `nikita/api/routes/tasks.py` | Background task endpoints | ✅ Complete (pg_cron) |
| `nikita/api/routes/telegram.py` | Webhook handler | ✅ DEPLOYED |
| `nikita/agents/voice/` | ElevenLabs Conversational AI 2.0 | ✅ DEPLOYED (14 modules, 186 tests, Jan 2026) |
| `nikita/api/routes/voice.py` | Voice server tools (5 endpoints) | ✅ DEPLOYED |

## Environment Variables Template

```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_SERVICE_KEY=eyJhbGci...
DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres

# Neo4j Aura (replaces FalkorDB)
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...  # From Aura console

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# OpenAI (embeddings only)
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small

# ElevenLabs
ELEVENLABS_API_KEY=...

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_WEBHOOK_URL=https://nikita-api-xxxxx.run.app/telegram/webhook

# Cloud Run (API deployment)
CLOUD_RUN_URL=https://nikita-api-xxxxx.run.app
GCP_PROJECT_ID=nikita-game
GCP_REGION=us-central1

# API
API_HOST=0.0.0.0
API_PORT=8080  # Cloud Run default
CORS_ORIGINS=["http://localhost:3000","https://portal.nikita.game"]

# Game
STARTING_SCORE=50.0
MAX_BOSS_ATTEMPTS=3

# REMOVED (Nov 2025):
# REDIS_URL - Replaced by pg_cron + Edge Functions
# FALKORDB_URL - Replaced by Neo4j Aura
```
