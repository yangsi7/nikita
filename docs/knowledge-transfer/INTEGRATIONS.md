# Integrations

```yaml
context_priority: high
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - VOICE_IMPLEMENTATION.md
  - AUTHENTICATION.md
  - DATABASE_SCHEMA.md
```

## Overview

Nikita integrates with several external services:
- **Telegram Bot API** - Primary text messaging platform
- **ElevenLabs** - Voice conversations and TTS
- **Graphiti/Neo4j** - Knowledge graph memory
- **Supabase** - Database and authentication
- **Claude API** - LLM for responses

---

## Telegram Integration

### Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        TELEGRAM INTEGRATION                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐                        ┌─────────────┐                     │
│  │  Telegram   │      Webhook POST      │  Cloud Run  │                     │
│  │   Servers   │ ──────────────────────▶│  /webhook   │                     │
│  └─────────────┘                        └──────┬──────┘                     │
│                                                │                             │
│                                                ▼                             │
│                                   ┌─────────────────────────┐               │
│                                   │  Signature Validation   │               │
│                                   │  (SEC-01 HMAC-SHA256)   │               │
│                                   └────────────┬────────────┘               │
│                                                │                             │
│                                                ▼                             │
│                                   ┌─────────────────────────┐               │
│                                   │    Update Router        │               │
│                                   │    @ webhook.py:50-100  │               │
│                                   └────────────┬────────────┘               │
│                                                │                             │
│                         ┌──────────────────────┼──────────────────────┐     │
│                         │                      │                      │     │
│                         ▼                      ▼                      ▼     │
│              ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│              │ CommandHandler  │    │   OTPHandler    │    │ MessageHandler │
│              │ (/start, /help) │    │ (verification)  │    │ (conversation) │
│              └─────────────────┘    └─────────────────┘    └─────────────────┘
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Webhook Configuration

**Endpoint**: `POST /api/v1/telegram/webhook`

**File**: `nikita/api/routes/telegram.py:20-80`

```python
# nikita/api/routes/telegram.py:30-60

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    # Validate signature (SEC-01)
    signature = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not validate_telegram_signature(signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    body = await request.json()
    update = Update.model_validate(body)

    # Route to appropriate handler
    handler_chain = [
        CommandHandler(session),
        OTPHandler(session),
        OnboardingHandler(session),
        MessageHandler(session)
    ]

    for handler in handler_chain:
        if await handler.can_handle(update):
            await handler.handle(update)
            break

    return {"ok": True}
```

### Signature Validation (SEC-01)

**File**: `nikita/platforms/telegram/webhook.py:30-60`

```python
# nikita/platforms/telegram/webhook.py:35-55

def validate_telegram_signature(
    received_signature: Optional[str]
) -> bool:
    """Validate Telegram webhook signature using HMAC-SHA256."""
    if not received_signature:
        return False

    expected_signature = settings.TELEGRAM_WEBHOOK_SECRET
    return hmac.compare_digest(received_signature, expected_signature)
```

### Handler Chain

| Handler | Priority | Triggers | File |
|---------|----------|----------|------|
| CommandHandler | 1 | `/start`, `/help`, `/status` | `commands.py:1-150` |
| OTPHandler | 2 | 6-8 digit codes | `otp_handler.py:1-100` |
| OnboardingHandler | 3 | Incomplete profiles | `registration_handler.py:1-200` |
| MessageHandler | 4 | All other messages | `message_handler.py:1-300` |

### Rate Limiting

**File**: `nikita/platforms/telegram/rate_limiter.py:1-100`

| Limit | Window | Action |
|-------|--------|--------|
| 20 requests | 1 minute | Soft block with message |
| 500 requests | 24 hours | Hard block |

```python
# nikita/platforms/telegram/rate_limiter.py:30-60

async def check_rate_limit(
    user_id: UUID,
    session: AsyncSession
) -> RateLimitResult:
    """Check if user has exceeded rate limits."""
    repo = RateLimitRepository(session)
    limits = await repo.get_or_create(user_id)

    # Check minute limit
    if limits.minute_count >= 20:
        return RateLimitResult(
            allowed=False,
            message="Slow down! Too many messages. Try again in a minute."
        )

    # Check daily limit
    if limits.daily_count >= 500:
        return RateLimitResult(
            allowed=False,
            message="You've reached your daily message limit. See you tomorrow!"
        )

    # Increment counters
    await repo.increment(user_id)
    return RateLimitResult(allowed=True)
```

### Bot Commands

| Command | Description | Handler |
|---------|-------------|---------|
| `/start` | Initialize bot, start onboarding | `CommandHandler.handle_start()` |
| `/help` | Show help message | `CommandHandler.handle_help()` |
| `/status` | Show relationship status | `CommandHandler.handle_status()` |
| `/settings` | Open portal link | `CommandHandler.handle_settings()` |

---

## ElevenLabs Integration

### Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        ELEVENLABS INTEGRATION                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐                   ┌─────────────────┐                  │
│  │   Phone Call    │                   │   ElevenLabs    │                  │
│  │   (Inbound)     │ ─────────────────▶│   Platform      │                  │
│  └─────────────────┘                   └────────┬────────┘                  │
│                                                 │                            │
│                                                 │ Server Tool Calls          │
│                                                 ▼                            │
│                                   ┌─────────────────────────┐               │
│                                   │   Cloud Run API         │               │
│                                   │   /api/v1/voice/*       │               │
│                                   └────────────┬────────────┘               │
│                                                │                             │
│            ┌───────────────────────────────────┼───────────────────────┐    │
│            │                    │              │              │        │    │
│            ▼                    ▼              ▼              ▼        ▼    │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  │ get_context   │  │ get_memory    │  │ score_turn    │  │update_memory │
│  │ (2s timeout)  │  │ (2s timeout)  │  │ (2s timeout)  │  │ (2s timeout) │
│  └───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘
│                                                                              │
│  Post-Call:                                                                 │
│  ┌─────────────────┐                   ┌─────────────────┐                  │
│  │   ElevenLabs    │   Webhook POST    │   /voice/       │                  │
│  │   (call ended)  │ ─────────────────▶│   webhook       │                  │
│  └─────────────────┘                   └─────────────────┘                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Server Tools

**File**: `nikita/agents/voice/server_tools.py:1-300`

| Tool | Purpose | Timeout |
|------|---------|---------|
| `get_context` | Retrieve user context for conversation | 2s |
| `get_memory` | Search knowledge graphs | 2s |
| `score_turn` | Score user's response | 2s |
| `update_memory` | Add facts to graphs | 2s |

```python
# nikita/agents/voice/server_tools.py:50-100

@with_timeout_fallback(timeout=2.0)
async def get_context(
    user_id: str,
    signed_token: str
) -> Dict[str, Any]:
    """Get context for voice conversation."""

    # Validate signed token
    if not validate_voice_token(signed_token, user_id):
        return {"error": "Invalid token"}

    async with get_db_session() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(UUID(user_id))

        if not user:
            return {"error": "User not found"}

        metrics = await repo.get_metrics(user.id)

        return {
            "user_name": user.display_name,
            "chapter": metrics.chapter_number,
            "relationship_score": float(metrics.relationship_score),
            "engagement_state": metrics.engagement_state,
            "hours_since_last": calculate_hours_since(metrics.last_interaction),
            "nikita_mood": compute_mood(metrics),
            "nikita_energy": compute_energy(),
            "nikita_activity": compute_activity(),
            # ... 20+ more fields
        }
```

### Dynamic Variables

**File**: `nikita/agents/voice/models.py:1-100`

Variables injected into ElevenLabs agent prompt:

| Variable | Source | Example |
|----------|--------|---------|
| `user_name` | Database | "Alex" |
| `relationship_score` | Metrics | 67.5 |
| `chapter` | Metrics | 3 |
| `nikita_mood` | Computed | "content" |
| `nikita_energy` | Computed | 0.75 |
| `nikita_activity` | Computed | "watching a show" |
| `hours_since_last` | Computed | 4.5 |
| `user_id` | Hidden | UUID |
| `signed_token` | Hidden | JWT |

### Webhook Handler

**File**: `nikita/api/routes/voice.py:150-250`

```python
# nikita/api/routes/voice.py:180-230

@router.post("/webhook")
async def voice_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """Handle post-call webhook from ElevenLabs."""

    # Validate HMAC signature
    signature = request.headers.get("X-ElevenLabs-Signature")
    body = await request.body()

    if not validate_elevenlabs_signature(signature, body):
        raise HTTPException(status_code=401)

    data = await request.json()

    # Extract transcript
    transcript = data.get("transcript", [])
    user_id = data.get("metadata", {}).get("user_id")

    if transcript and user_id:
        # Process transcript via LLM for extraction
        await process_voice_transcript(
            user_id=UUID(user_id),
            transcript=transcript,
            session=session
        )

    return {"ok": True}
```

### Signed Token

**File**: `nikita/agents/voice/service.py:50-100`

```python
# nikita/agents/voice/service.py:60-90

def create_signed_token(user_id: UUID) -> str:
    """Create signed token for voice session."""
    payload = {
        "user_id": str(user_id),
        "exp": datetime.now(UTC) + timedelta(minutes=30),
        "iat": datetime.now(UTC)
    }
    return jwt.encode(payload, settings.VOICE_TOKEN_SECRET, algorithm="HS256")

def validate_voice_token(token: str, user_id: str) -> bool:
    """Validate voice session token."""
    try:
        payload = jwt.decode(
            token,
            settings.VOICE_TOKEN_SECRET,
            algorithms=["HS256"]
        )
        return payload.get("user_id") == user_id
    except jwt.InvalidTokenError:
        return False
```

---

## Graphiti/Neo4j Integration

### Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        GRAPHITI INTEGRATION                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    NikitaMemory (Singleton)                          │   │
│  │                    @ graphiti_client.py:1-200                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│              ┌─────────────────────┼─────────────────────┐                  │
│              │                     │                     │                  │
│              ▼                     ▼                     ▼                  │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐          │
│  │  nikita_graph   │   │  user_{id}      │   │ relationship_{id}│          │
│  │                 │   │                 │   │                  │          │
│  │  Nikita's life  │   │  User's facts   │   │  Shared memories │          │
│  │  events, moods  │   │  preferences    │   │  conversations   │          │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘          │
│                                                                              │
│  Connection Pool:                                                           │
│  - Max connections: 10                                                      │
│  - Idle timeout: 30s                                                        │
│  - Cold start: 30-60s (NEEDS RETHINKING)                                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Singleton Pattern

**File**: `nikita/memory/graphiti_client.py:20-80`

```python
# nikita/memory/graphiti_client.py:30-70

class NikitaMemory:
    """Singleton client for Graphiti knowledge graphs."""

    _instance: Optional["NikitaMemory"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._graphiti_instances: Dict[str, Graphiti] = {}
        self._neo4j_driver = None

    @classmethod
    async def get_instance(cls) -> "NikitaMemory":
        """Get or create singleton instance."""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                await cls._instance._initialize()
            return cls._instance

    async def _initialize(self):
        """Initialize Neo4j connection."""
        self._neo4j_driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=10,
            connection_acquisition_timeout=30.0
        )
```

### Key Methods

| Method | Purpose | Timeout |
|--------|---------|---------|
| `search_memory()` | Search graph for facts | 30s |
| `add_episode()` | Add new fact/event | 10s |
| `get_recent_episodes()` | Get recent entries | 10s |
| `clear_cache()` | Clear singleton cache | N/A |

### Cache Clearing

**File**: `tests/conftest.py:20-50`

```python
# tests/conftest.py:30-50

@pytest.fixture(autouse=True)
def clear_singleton_caches():
    """Clear all singleton caches before each test."""
    NikitaMemory._instance = None
    NikitaMemory._graphiti_instances = {}
    ConfigLoader._instance = None
    yield
```

---

## Supabase Integration

### Authentication

**File**: `nikita/api/dependencies/auth.py:1-100`

```python
# nikita/api/dependencies/auth.py:30-70

async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """Get authenticated user from JWT."""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    repo = UserRepository(session)
    user = await repo.get_by_id(UUID(user_id))

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
```

### Database Sessions

**File**: `nikita/api/dependencies/__init__.py:20-60`

```python
# nikita/api/dependencies/__init__.py:30-50

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

## Claude API Integration

### Pydantic AI Agent

**File**: `nikita/agents/text/agent.py:50-150`

```python
# nikita/agents/text/agent.py:60-100

from pydantic_ai import Agent

agent = Agent(
    model="claude-sonnet-4-5-20250929",
    system_prompt=None,  # Set dynamically
    retries=3
)

async def generate_response(
    message: str,
    context: ContextPackage,
    session: AsyncSession
) -> str:
    """Generate Nikita's response."""

    # Build system prompt from context
    system_prompt = await build_system_prompt(context)

    # Build message history
    history = await build_message_history(context)

    # Generate response
    result = await agent.run(
        message,
        system_prompt=system_prompt,
        message_history=history
    )

    return result.data
```

### Timeout Configuration

| Operation | Timeout | Retries |
|-----------|---------|---------|
| Prompt generation | 45s | 3 |
| Response generation | 45s | 3 |
| Entity extraction | 30s | 2 |

---

## Environment Variables

### Required Variables

| Variable | Service | Description |
|----------|---------|-------------|
| `DATABASE_URL` | Supabase | PostgreSQL connection string |
| `NEO4J_URI` | Neo4j | Neo4j connection URI |
| `NEO4J_USER` | Neo4j | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j | Neo4j password |
| `ANTHROPIC_API_KEY` | Claude | API key for Claude |
| `ELEVENLABS_API_KEY` | ElevenLabs | API key |
| `ELEVENLABS_AGENT_ID` | ElevenLabs | Main Nikita agent ID |
| `ELEVENLABS_AGENT_META_NIKITA` | ElevenLabs | Onboarding agent ID |
| `TELEGRAM_BOT_TOKEN` | Telegram | Bot token |
| `TELEGRAM_WEBHOOK_SECRET` | Telegram | Webhook secret |
| `SUPABASE_JWT_SECRET` | Supabase | JWT signing secret |
| `VOICE_TOKEN_SECRET` | Internal | Voice session token secret |

---

## Key File References

| File | Line | Purpose |
|------|------|---------|
| `nikita/api/routes/telegram.py` | 1-100 | Telegram webhook |
| `nikita/api/routes/voice.py` | 1-250 | Voice endpoints |
| `nikita/platforms/telegram/message_handler.py` | 1-300 | Message handling |
| `nikita/agents/voice/server_tools.py` | 1-300 | Voice server tools |
| `nikita/memory/graphiti_client.py` | 1-200 | Neo4j client |
| `nikita/agents/text/agent.py` | 1-200 | Claude agent |

---

## Related Documentation

- **Voice Details**: [VOICE_IMPLEMENTATION.md](VOICE_IMPLEMENTATION.md)
- **Authentication**: [AUTHENTICATION.md](AUTHENTICATION.md)
- **Database**: [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
- **Context Engine**: [CONTEXT_ENGINE.md](CONTEXT_ENGINE.md)
