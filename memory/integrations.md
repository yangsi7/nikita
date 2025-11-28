# External Integrations

## Current State

All integrations configured in `nikita/config/settings.py` and `nikita/config/elevenlabs.py`, but **not yet implemented** in application code (awaiting Phases 2-5).

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

### Usage Patterns (TODO Phase 2)

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
-- Portal users can only access their own data
CREATE POLICY "Users see own data" ON users
    FOR ALL USING (auth.uid() = id);

-- API uses service_key to bypass RLS for internal operations
-- Backend uses direct PostgreSQL connection (no RLS)
```

**3. Authentication Flow**:

```python
# Portal: OTP sign-in
response = supabase.auth.sign_in_with_otp({
    "phone": "+1234567890"
})
# User receives SMS code → enters → JWT token issued

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

## FalkorDB Integration (Graphiti)

### Configuration (Phase 1 ✅)

**Settings** (`nikita/config/settings.py:32-36`):

```python
falkordb_url: str = Field(
    default="falkordb://localhost:6379",
    description="FalkorDB connection URL",
)
```

**Installation**:

```bash
pip install graphiti-core[falkordb]

# Local development:
docker run -p 6379:6379 -it --rm falkordb/falkordb:latest

# Production: FalkorDB Cloud
# Free tier: 1 GB, 1 shard
# Upgrade: Startup plan $73/GB/mo
```

### Graphiti Client (Phase 1 ✅)

**Implemented** in `nikita/memory/graphiti_client.py:13-243`:

```python
class NikitaMemory:
    def __init__(self, user_id: str):
        self.graphiti = Graphiti(
            uri=settings.falkordb_url,
            llm_client=AnthropicClient(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model,
            ),
            embedder=OpenAIEmbedder(
                api_key=settings.openai_api_key,
                model=settings.embedding_model,
            ),
        )

    async def add_episode(
        self,
        content: str,
        source: str,
        graph_type: str = "relationship",  # nikita | user | relationship
    ) -> None:
        """Add temporal episode to knowledge graph"""

    async def search_memory(
        self,
        query: str,
        graph_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Hybrid search across graphs"""

    async def get_context_for_prompt(
        self,
        user_message: str,
        max_memories: int = 5,
    ) -> str:
        """Build context string for LLM prompt injection"""
```

### Three-Graph Architecture

```
nikita_graph_{user_id}
├─ Nodes: WorkProject, LifeEvent, Opinion, Memory
├─ Example: "Nikita finished 36-hour security audit for finance client"
└─ Purpose: Her simulated life, exists independently of player

user_graph_{user_id}
├─ Nodes: UserFact, UserPreference, UserPattern, UserHistory
├─ Example: "User works in finance, high stress job, mentioned layoffs"
└─ Purpose: What Nikita knows about the player

relationship_graph_{user_id}
├─ Nodes: Episode, Milestone, InsideJoke, Conflict
├─ Example: "We joked about her 'Trust me, I'm a hacker' mug"
└─ Purpose: Shared history between Nikita and player
```

### Usage Patterns (TODO Phase 2-3)

```python
# After user message
memory = NikitaMemory(user_id)

# Search relevant memories for context
context = await memory.get_context_for_prompt(user_message)
# Returns: "[2025-01-14] (Our history) We joked about..."

# Add new fact learned
await memory.add_user_fact(
    fact="User is learning Python",
    confidence=0.85,
    source_message=user_message,
)

# Add relationship episode
await memory.add_relationship_episode(
    description="User asked about my work, genuinely curious",
    episode_type="milestone",
)

# Add to Nikita's life
await memory.add_nikita_event(
    description="Started new client project, healthcare HIPAA compliance",
    event_type="work_project",
)
```

## Anthropic (Claude) Integration

### Configuration (Phase 1 ✅)

**Settings** (`nikita/config/settings.py:38-43`):

```python
anthropic_api_key: str = Field(..., description="Anthropic API key")
anthropic_model: str = Field(
    default="claude-sonnet-4-20250514",
    description="Claude model for text agent",
)
```

**Environment Variables**:

```bash
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

### Usage: Pydantic AI Text Agent (TODO Phase 2)

```python
from pydantic_ai import Agent, RunContext

nikita_agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
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

### Usage: Response Scoring (TODO Phase 3)

```python
# LLM-based scoring analyzer
scoring_agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
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

### Usage: Message Embeddings (TODO Phase 2)

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

### Usage: Voice Agent (TODO Phase 4)

```python
from elevenlabs import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, ClientTools

client = ElevenLabs(api_key=settings.elevenlabs_api_key)

# Register server tools
client_tools = ClientTools()
client_tools.register("get_context", get_context_callback)
client_tools.register("get_memory", get_memory_callback)
client_tools.register("score_turn", score_turn_callback)
client_tools.register("update_memory", update_memory_callback)

# Create conversation
agent_id = get_agent_id(user.chapter, user.game_status == 'boss_fight')
conversation = Conversation(
    client=client,
    agent_id=agent_id,
    client_tools=client_tools,
    callback_agent_response=on_agent_response,
    callback_user_transcript=on_user_transcript,
)

# Start session (WebSocket)
await conversation.start()
```

### Server Tools (TODO Phase 4)

```python
# api/routes/voice.py

@router.post("/voice/elevenlabs/server-tool")
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

## Telegram Integration

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

### Delayed Message Delivery Architecture

**Strategy**: Supabase pg_cron + Edge Functions (replacing Celery/Redis)

**Why This Approach**:
- Native Supabase integration (no separate Redis/Celery infrastructure)
- Edge Functions can call Telegram API directly
- pg_cron provides reliable scheduled execution
- Serverless scaling for delivery workers
- Simpler deployment and monitoring

**Data Flow**:
```
User message → Text Agent → Generate response → Store in pending_responses table
                                                        ↓
                                               pg_cron (every minute)
                                                        ↓
                                               Edge Function: deliver_responses
                                                        ↓
                                               Telegram Bot API (sendMessage)
                                                        ↓
                                               Mark response as delivered
```

### Pending Responses Table

```sql
-- Migration: pending_responses table
CREATE TABLE pending_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    telegram_chat_id BIGINT NOT NULL,
    response_text TEXT NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    delivered_at TIMESTAMPTZ,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'delivered', 'failed')),
    created_at TIMESTAMPTZ DEFAULT now(),
    error_message TEXT
);

-- Index for efficient polling
CREATE INDEX idx_pending_responses_delivery
ON pending_responses (scheduled_at, status)
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

### Edge Function: deliver-responses

```typescript
// supabase/functions/deliver-responses/index.ts

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const TELEGRAM_BOT_TOKEN = Deno.env.get('TELEGRAM_BOT_TOKEN')!
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SUPABASE_SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

Deno.serve(async (req) => {
  const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY)

  // Get pending responses due for delivery
  const { data: pending, error } = await supabase
    .from('pending_responses')
    .select('*')
    .eq('status', 'pending')
    .lte('scheduled_at', new Date().toISOString())
    .limit(50)

  if (error) throw error

  const results = await Promise.allSettled(
    pending.map(async (response) => {
      // Send to Telegram
      const telegramResponse = await fetch(
        `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            chat_id: response.telegram_chat_id,
            text: response.response_text,
            parse_mode: 'Markdown',
          }),
        }
      )

      if (!telegramResponse.ok) {
        const err = await telegramResponse.text()
        throw new Error(`Telegram API error: ${err}`)
      }

      // Mark as delivered
      await supabase
        .from('pending_responses')
        .update({
          status: 'delivered',
          delivered_at: new Date().toISOString()
        })
        .eq('id', response.id)

      return response.id
    })
  )

  return new Response(JSON.stringify({
    processed: results.length,
    succeeded: results.filter(r => r.status === 'fulfilled').length,
    failed: results.filter(r => r.status === 'rejected').length,
  }))
})
```

### Usage: Message Handler Integration

```python
# nikita/agents/text/handler.py

async def store_pending_response(
    user_id: UUID,
    response: str,
    scheduled_at: datetime,
    response_id: UUID,
) -> None:
    """Store pending response for Edge Function delivery."""
    # Get user's telegram_chat_id
    user = await get_user(user_id)

    await supabase.table('pending_responses').insert({
        'id': str(response_id),
        'user_id': str(user_id),
        'telegram_chat_id': user.telegram_chat_id,
        'response_text': response,
        'scheduled_at': scheduled_at.isoformat(),
        'status': 'pending',
    }).execute()
```

### Webhook Handler (Receiving Messages)

```python
# api/routes/telegram.py

from aiogram import Bot, Dispatcher
from aiogram.types import Message, Update

bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()

@dp.message()
async def handle_message(message: Message):
    """Route messages to text agent"""
    # Get or create user
    user = await get_or_create_user(telegram_id=message.from_user.id)

    # Process through MessageHandler
    handler = MessageHandler()
    decision = await handler.handle(user.id, message.text)

    # Response stored for delayed delivery via Edge Function
    # No immediate response (unless skip decision)
    if decision.was_skipped:
        # Optionally: send typing indicator, then nothing
        pass

@router.post("/webhook")
async def telegram_webhook(update: Update):
    """Receive updates from Telegram"""
    await dp.feed_update(bot, update)
    return {"ok": True}
```

## Redis Integration (Optional - Celery)

### Status: Superseded by Supabase pg_cron

**Note**: For message delivery scheduling, we now use **Supabase pg_cron + Edge Functions** instead of Redis/Celery. This simplifies the infrastructure by eliminating a separate Redis service.

Redis/Celery is still available for:
- Daily decay calculations (high CPU tasks)
- Batch processing jobs
- Heavy background tasks that benefit from worker pools

### Configuration (Phase 1 ✅)

**Settings** (`nikita/config/settings.py:62-66`):

```python
redis_url: str = Field(
    default="redis://localhost:6379/0",
    description="Redis connection URL",
)
```

### Alternative: Supabase pg_cron + Edge Functions

For simpler scheduled tasks (message delivery, notifications), prefer pg_cron:

```sql
-- Daily decay at midnight UTC
SELECT cron.schedule(
    'daily-decay',
    '0 0 * * *',
    $$SELECT net.http_post(
        url := 'https://xxx.supabase.co/functions/v1/apply-decay',
        headers := '{"Authorization": "Bearer ..."}'::jsonb
    );$$
);
```

### Usage: Celery Tasks (Optional - Phase 3)

```python
# tasks/decay_task.py (only if heavy processing needed)

from celery import Celery
from celery.schedules import crontab

app = Celery('nikita', broker=settings.redis_url)

@app.task
def apply_daily_decay():
    """Run daily at midnight UTC"""
    # Apply decay to inactive users

app.conf.beat_schedule = {
    'apply-decay': {
        'task': 'nikita.tasks.decay_task.apply_daily_decay',
        'schedule': crontab(hour=0, minute=0),
    },
}
```

## Critical Files

| File | Purpose | Status |
|------|---------|--------|
| `nikita/config/settings.py:24-66` | All service configs | ✅ Complete |
| `nikita/config/elevenlabs.py` | Agent ID abstraction | ✅ Complete |
| `nikita/memory/graphiti_client.py` | FalkorDB/Graphiti wrapper | ✅ Complete |
| `nikita/agents/text/handler.py` | Message handler + scheduling | ✅ Complete |
| `nikita/agents/text/skip.py` | Skip decision logic | ✅ Complete |
| `nikita/agents/text/timing.py` | Response timing | ✅ Complete |
| `nikita/platforms/telegram/bot.py` | Telegram bot setup | ❌ TODO Phase 2 |
| `supabase/functions/deliver-responses/` | Edge Function for delivery | ❌ TODO Phase 2 |
| `nikita/platforms/voice/elevenlabs.py` | ElevenLabs SDK wrapper | ❌ TODO Phase 4 |
| `nikita/api/routes/voice.py` | Voice server tools | ❌ TODO Phase 4 |
| `nikita/tasks/decay_task.py` | Celery background jobs (optional) | ❌ TODO Phase 3 |

## Environment Variables Template

```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_SERVICE_KEY=eyJhbGci...
DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres

# FalkorDB
FALKORDB_URL=falkordb://localhost:6379
# Production: falkordb://user:pass@cloud.falkordb.com:6379

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# OpenAI (embeddings only)
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small

# ElevenLabs
ELEVENLABS_API_KEY=...

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_WEBHOOK_URL=https://api.nikita.game/telegram/webhook

# Redis
REDIS_URL=redis://localhost:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000","https://portal.nikita.game"]

# Game
STARTING_SCORE=50.0
MAX_BOSS_ATTEMPTS=3
```
