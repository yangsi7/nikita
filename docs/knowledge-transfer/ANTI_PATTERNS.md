# Anti-Patterns

```yaml
context_priority: high
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - ARCHITECTURE_ALTERNATIVES.md
  - CONTEXT_ENGINE.md
  - TESTING_STRATEGY.md
```

## Overview

This document captures lessons learned, common mistakes, and patterns to avoid when working with the Nikita codebase. Following these guidelines prevents known bugs and performance issues.

---

## Database Anti-Patterns

### AP-1: Using datetime.utcnow()

**Problem**: `datetime.utcnow()` returns a naive datetime (no timezone info), causing TypeError when compared with timezone-aware database timestamps.

**Bad**:
```python
# WRONG - returns naive datetime
from datetime import datetime
now = datetime.utcnow()
hours_since = (now - user.last_interaction).total_seconds() / 3600  # TypeError!
```

**Good**:
```python
# CORRECT - use timezone-aware datetime
from datetime import datetime, UTC
now = datetime.now(UTC)
hours_since = (now - user.last_interaction).total_seconds() / 3600  # Works!
```

**Files affected**: All files using datetime comparisons. Fixed in 2026-01-20.

**Reference**: `tests/meta_prompts/test_timezone_safety.py` - 10 regression tests

---

### AP-2: Missing Session Rollback After Exceptions

**Problem**: SQLAlchemy sessions left in "prepared state" after exceptions, causing subsequent operations to fail.

**Bad**:
```python
async def process_message(user_id: UUID, session: AsyncSession):
    try:
        result = await some_operation(session)
    except Exception:
        # Session still in bad state!
        pass  # Next operation will fail
```

**Good**:
```python
async def process_message(user_id: UUID, session: AsyncSession):
    try:
        result = await some_operation(session)
    except Exception:
        await session.rollback()  # Clean up session state
        raise
```

**Reference**: `nikita/platforms/telegram/message_handler.py:150-160` - Fixed in PR #38

---

### AP-3: Decimal/Float Division

**Problem**: Mixing Decimal (from database) with float (from Python) causes TypeError.

**Bad**:
```python
# WRONG - relationship_score is Decimal from DB
decay_amount = user.relationship_score * 0.1  # TypeError!
```

**Good**:
```python
# CORRECT - convert to float first
decay_amount = float(user.relationship_score) * 0.1
```

**Reference**: `nikita/emotional_state/computer.py` - Fixed in PR #26

---

### AP-4: Forgetting FK Constraints

**Problem**: Creating records without required foreign keys causes NotNullViolationError.

**Bad**:
```python
# WRONG - conversation_id is required
prompt = GeneratedPrompt(
    user_id=user.id,
    system_prompt=prompt_text,
    # Missing conversation_id!
)
```

**Good**:
```python
# CORRECT - include all required FKs
prompt = GeneratedPrompt(
    user_id=user.id,
    conversation_id=conversation.id,  # Required!
    system_prompt=prompt_text,
)
```

**Reference**: `nikita/db/models/generated_prompt.py:20-30` - conversation_id NOT NULL

---

## Async Anti-Patterns

### AP-5: Blocking Calls in Async Context

**Problem**: Blocking I/O calls block the entire event loop.

**Bad**:
```python
async def get_user_data():
    # WRONG - blocking call in async function
    result = requests.get("https://api.example.com")  # Blocks event loop!
    return result.json()
```

**Good**:
```python
async def get_user_data():
    # CORRECT - use async HTTP client
    async with httpx.AsyncClient() as client:
        result = await client.get("https://api.example.com")
        return result.json()
```

---

### AP-6: Missing await on Async Operations

**Problem**: Forgetting `await` returns a coroutine instead of the result.

**Bad**:
```python
async def process():
    user = repo.get_by_id(user_id)  # Returns coroutine, not User!
    print(user.name)  # AttributeError: 'coroutine' has no attribute 'name'
```

**Good**:
```python
async def process():
    user = await repo.get_by_id(user_id)  # Returns User
    print(user.name)  # Works!
```

---

### AP-7: Concurrent Session Access

**Problem**: Multiple async tasks using the same SQLAlchemy session causes race conditions.

**Bad**:
```python
async def process_all(user_ids: List[UUID], session: AsyncSession):
    # WRONG - concurrent access to same session
    tasks = [process_user(uid, session) for uid in user_ids]
    await asyncio.gather(*tasks)  # Race condition!
```

**Good**:
```python
async def process_all(user_ids: List[UUID]):
    # CORRECT - each task gets its own session
    async def process_with_session(uid):
        async with get_db_session() as session:
            await process_user(uid, session)

    tasks = [process_with_session(uid) for uid in user_ids]
    await asyncio.gather(*tasks)
```

---

## Context Engine Anti-Patterns

### AP-8: Bypassing ContextEngine for Voice

**Problem**: Voice agent bypasses ContextEngine, leading to inconsistent context.

**Current State** (Anti-Pattern in Production):
```python
# Voice uses direct queries with 2s timeout
async def get_context(user_id, signed_token):
    # Only ~30 fields vs 115+ in ContextEngine
    return minimal_context
```

**Recommended** (Not Yet Implemented):
```python
# Use pre-computed context cache
async def get_context(user_id, signed_token):
    # Fetch from Redis cache (computed by ContextEngine)
    return await redis.get(f"context:{user_id}")
```

**Reference**: [VOICE_IMPLEMENTATION.md](VOICE_IMPLEMENTATION.md) - NEEDS RETHINKING marker

---

### AP-9: Ignoring Collector Timeouts

**Problem**: Collector timeouts without fallback data leaves context incomplete.

**Bad**:
```python
async def collect(self, user_id):
    try:
        return await self._query_data(user_id)
    except asyncio.TimeoutError:
        return {}  # Empty! Critical fields missing
```

**Good**:
```python
async def collect(self, user_id):
    try:
        return await asyncio.wait_for(
            self._query_data(user_id),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        return self._get_fallback()  # Sensible defaults
```

**Reference**: `nikita/context_engine/collectors/base.py:50-80`

---

### AP-10: Hardcoded Token Limits

**Problem**: Hardcoding token limits prevents tuning.

**Bad**:
```python
if len(prompt) > 8000:  # Magic number!
    prompt = prompt[:8000]
```

**Good**:
```python
from nikita.config import settings

if token_count(prompt) > settings.MAX_PROMPT_TOKENS:
    prompt = truncate_to_tokens(prompt, settings.MAX_PROMPT_TOKENS)
```

---

## Testing Anti-Patterns

### AP-11: Shared Singleton State Between Tests

**Problem**: Singletons (ConfigLoader, NikitaMemory) persist state between tests.

**Bad**:
```python
def test_first():
    config = ConfigLoader.get_instance()
    config.override("key", "value")  # Modifies singleton

def test_second():
    config = ConfigLoader.get_instance()
    assert config.get("key") == "default"  # FAILS - still "value"!
```

**Good**:
```python
@pytest.fixture(autouse=True)
def clear_singletons():
    """Clear singleton state before each test."""
    ConfigLoader._instance = None
    NikitaMemory._instance = None
    yield

def test_first():
    # Fresh singleton each test
    config = ConfigLoader.get_instance()
```

**Reference**: `tests/conftest.py:20-50` - Autouse fixture for singleton clearing

---

### AP-12: Using Default AsyncSession Pool in Tests

**Problem**: Default connection pooling causes "prepared statement already exists" errors.

**Bad**:
```python
# WRONG - default pool shares connections
engine = create_async_engine(DATABASE_URL)
```

**Good**:
```python
# CORRECT - NullPool for test isolation
from sqlalchemy.pool import NullPool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool  # Each test gets fresh connection
)
```

**Reference**: `tests/db/integration/conftest.py:175-193`

---

### AP-13: Not Cleaning Up Test Data

**Problem**: Test data persists, affecting subsequent tests.

**Bad**:
```python
async def test_create_user():
    user = await repo.create(telegram_id=123)
    assert user.id is not None
    # No cleanup! User persists in test DB
```

**Good**:
```python
async def test_create_user(db_session):
    user = await repo.create(telegram_id=123)
    assert user.id is not None
    # Transaction rolled back automatically by fixture
```

**Reference**: `tests/conftest.py` - Session fixtures with automatic rollback

---

## Integration Anti-Patterns

### AP-14: Not Validating Webhook Signatures

**Problem**: Accepting webhooks without signature validation allows spoofing.

**Bad**:
```python
@router.post("/webhook")
async def webhook(request: Request):
    data = await request.json()  # No validation!
    await process(data)
```

**Good**:
```python
@router.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Signature")
    if not validate_signature(signature, await request.body()):
        raise HTTPException(status_code=401)
    data = await request.json()
    await process(data)
```

**Reference**: SEC-01 - `nikita/platforms/telegram/webhook.py:35-55`

---

### AP-15: Ignoring Rate Limits

**Problem**: Not implementing rate limits allows abuse and costs.

**Bad**:
```python
async def handle_message(user_id, message):
    # Process every message immediately - no limits!
    return await generate_response(message)
```

**Good**:
```python
async def handle_message(user_id, message):
    rate_limit = await check_rate_limit(user_id)
    if not rate_limit.allowed:
        return rate_limit.message

    return await generate_response(message)
```

**Reference**: SEC-02 - `nikita/platforms/telegram/rate_limiter.py`

---

## Performance Anti-Patterns

### AP-16: N+1 Queries

**Problem**: Loading related objects one at a time instead of in batch.

**Bad**:
```python
users = await session.execute(select(User))
for user in users:
    # N queries - one per user!
    metrics = await session.execute(
        select(UserMetrics).where(UserMetrics.user_id == user.id)
    )
```

**Good**:
```python
# Single query with join
result = await session.execute(
    select(User, UserMetrics)
    .join(UserMetrics, User.id == UserMetrics.user_id)
)
```

---

### AP-17: Not Using Circuit Breakers

**Problem**: Failing external services cause cascading failures.

**Bad**:
```python
async def query_neo4j():
    # If Neo4j is down, every request fails and waits for timeout
    return await neo4j_client.query(...)
```

**Good**:
```python
async def query_neo4j():
    if circuit_breaker.is_open:
        return fallback_data  # Fast fail

    try:
        result = await neo4j_client.query(...)
        circuit_breaker.record_success()
        return result
    except Exception:
        circuit_breaker.record_failure()
        return fallback_data
```

**Reference**: `nikita/context_engine/collectors/base.py:20-60`

---

### AP-18: Cold Start Ignorance

**Problem**: Not accounting for Neo4j Aura cold start (30-60s).

**Implication**: First request after inactivity times out.

**Mitigation**:
1. Warm-up endpoint called by pg_cron every 5 minutes
2. Generous timeouts (30s for Graphiti)
3. Fallback data for timeout scenarios

**Reference**: `nikita/api/routes/tasks.py:200-220` - Health check endpoint

---

## Summary Checklist

Before submitting code, verify:

- [ ] No `datetime.utcnow()` - use `datetime.now(UTC)`
- [ ] Session rollback in exception handlers
- [ ] Decimal to float conversion for math
- [ ] All required FK fields populated
- [ ] Async operations properly awaited
- [ ] No shared session across concurrent tasks
- [ ] Singleton caches cleared in tests
- [ ] NullPool for test database
- [ ] Webhook signatures validated
- [ ] Rate limits implemented
- [ ] Circuit breakers for external services
- [ ] N+1 queries avoided

---

## Related Documentation

- **Architecture Alternatives**: [ARCHITECTURE_ALTERNATIVES.md](ARCHITECTURE_ALTERNATIVES.md)
- **Testing Strategy**: [TESTING_STRATEGY.md](TESTING_STRATEGY.md)
- **Context Engine**: [CONTEXT_ENGINE.md](CONTEXT_ENGINE.md)
