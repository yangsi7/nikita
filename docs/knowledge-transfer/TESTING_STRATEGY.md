# Testing Strategy

```yaml
context_priority: high
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - PIPELINE_STAGES.md
  - DATABASE_SCHEMA.md
  - ANTI_PATTERNS.md
```

## Overview

The Nikita test suite contains 4000+ tests covering:
- Unit tests for individual components
- Integration tests for database operations
- E2E tests for full workflows
- Chaos tests for circuit breaker behavior

---

## Test Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           TEST ARCHITECTURE                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  UNIT TESTS (3500+)                                                  │   │
│  │  tests/                                                              │   │
│  │  ├── agents/                 # Text and voice agents                │   │
│  │  ├── api/                    # FastAPI routes and schemas           │   │
│  │  ├── context/                # Context engine and stages            │   │
│  │  ├── context_engine/         # New context engine v2                │   │
│  │  ├── db/                     # Models and repositories              │   │
│  │  ├── engine/                 # Game engine (scoring, chapters)      │   │
│  │  ├── emotional_state/        # Mood computation                     │   │
│  │  ├── life_simulation/        # Daily events                         │   │
│  │  ├── memory/                 # Graphiti client                      │   │
│  │  ├── meta_prompts/           # Prompt generation                    │   │
│  │  ├── onboarding/             # Onboarding flows                     │   │
│  │  ├── platforms/              # Telegram integration                 │   │
│  │  └── touchpoints/            # Proactive messaging                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  INTEGRATION TESTS (200+)                                            │   │
│  │  tests/db/integration/       # Database with real Supabase          │   │
│  │  tests/e2e/                  # End-to-end workflows                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  CHAOS TESTS (50+)                                                   │   │
│  │  tests/context/stages/chaos/ # Circuit breaker, timeouts, failures  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Test Configuration

### pytest.ini

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
markers =
    integration: marks tests as integration tests (require database)
    e2e: marks tests as end-to-end tests (require all services)
    slow: marks tests as slow running
    chaos: marks tests for chaos engineering
```

### conftest.py Structure

**Root conftest.py**: `tests/conftest.py`

```python
# tests/conftest.py

import pytest
from unittest.mock import AsyncMock, MagicMock

# Clear singletons before each test
@pytest.fixture(autouse=True)
def clear_singleton_caches():
    """Clear all singleton caches to ensure test isolation."""
    from nikita.config.loader import ConfigLoader
    from nikita.memory.graphiti_client import NikitaMemory

    ConfigLoader._instance = None
    NikitaMemory._instance = None
    NikitaMemory._graphiti_instances = {}

    yield

    # Cleanup after test
    ConfigLoader._instance = None
    NikitaMemory._instance = None

# Mock external services
@pytest.fixture
def mock_llm():
    """Mock LLM calls."""
    mock = AsyncMock()
    mock.return_value = '{"result": "mocked"}'
    return mock

@pytest.fixture
def mock_neo4j():
    """Mock Neo4j connections."""
    mock = MagicMock()
    mock.query = AsyncMock(return_value=[])
    return mock

@pytest.fixture
def mock_telegram():
    """Mock Telegram bot."""
    mock = AsyncMock()
    mock.send_message = AsyncMock(return_value=True)
    return mock
```

---

## Async Testing Patterns

### NullPool for Isolation

**File**: `tests/db/integration/conftest.py:170-200`

```python
# tests/db/integration/conftest.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool

@pytest.fixture(scope="function")
async def db_session():
    """Create isolated database session for each test."""

    # NullPool ensures each test gets fresh connection
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )

    async with engine.begin() as conn:
        async with AsyncSession(bind=conn) as session:
            yield session
            # Rollback any changes
            await session.rollback()

    await engine.dispose()
```

### Why NullPool?

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        NULLPOOL vs DEFAULT POOL                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  DEFAULT POOL (Problem):                                                     │
│  ┌─────────────┐                                                            │
│  │  Test 1     │──┐                                                         │
│  └─────────────┘  │     ┌─────────────┐                                     │
│                   ├────▶│ Connection  │──▶ "prepared statement exists"      │
│  ┌─────────────┐  │     │    Pool     │     ERROR! Connection reused        │
│  │  Test 2     │──┘     └─────────────┘     with stale state               │
│  └─────────────┘                                                            │
│                                                                              │
│  NULLPOOL (Solution):                                                        │
│  ┌─────────────┐        ┌─────────────┐                                     │
│  │  Test 1     │───────▶│ Connection 1│──▶ Clean, isolated                  │
│  └─────────────┘        └─────────────┘                                     │
│                                                                              │
│  ┌─────────────┐        ┌─────────────┐                                     │
│  │  Test 2     │───────▶│ Connection 2│──▶ Clean, isolated                  │
│  └─────────────┘        └─────────────┘                                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Async Context Managers

```python
# Pattern for async fixtures
@pytest.fixture
async def user_with_metrics(db_session):
    """Create test user with metrics."""
    repo = UserRepository(db_session)

    user = await repo.create_with_metrics(
        telegram_id=123456789,
        display_name="Test User"
    )

    yield user

    # Cleanup handled by session rollback
```

---

## Test Fixtures

### User State Fixtures

**File**: `tests/fixtures/users.py`

```python
# tests/fixtures/users.py

import pytest
from uuid import uuid4
from nikita.db.models import User, UserMetrics

@pytest.fixture
def new_user():
    """User at start of game."""
    return create_user_fixture(
        chapter_number=1,
        relationship_score=50.0,
        engagement_state="CALIBRATING"
    )

@pytest.fixture
def mid_game_user():
    """User in middle of game."""
    return create_user_fixture(
        chapter_number=3,
        relationship_score=67.5,
        engagement_state="IN_ZONE"
    )

@pytest.fixture
def boss_fight_user():
    """User in boss fight."""
    return create_user_fixture(
        chapter_number=2,
        relationship_score=60.5,
        engagement_state="IN_ZONE",
        in_boss_fight=True
    )

@pytest.fixture
def game_over_user():
    """User who has lost."""
    return create_user_fixture(
        chapter_number=6,
        relationship_score=0.0,
        engagement_state="OUT_OF_ZONE"
    )

def create_user_fixture(**kwargs) -> tuple[User, UserMetrics]:
    """Factory for user fixtures."""
    user_id = uuid4()
    user = User(
        id=user_id,
        telegram_id=kwargs.get("telegram_id", 123456789),
        display_name=kwargs.get("display_name", "Test User"),
        phone_number=kwargs.get("phone_number", "+1234567890"),
        onboarding_status="completed"
    )
    metrics = UserMetrics(
        id=uuid4(),
        user_id=user_id,
        relationship_score=kwargs.get("relationship_score", 50.0),
        chapter_number=kwargs.get("chapter_number", 1),
        engagement_state=kwargs.get("engagement_state", "CALIBRATING"),
        in_boss_fight=kwargs.get("in_boss_fight", False)
    )
    return user, metrics
```

### Conversation Fixtures

**File**: `tests/fixtures/conversations.py`

```python
@pytest.fixture
def active_conversation():
    """Active conversation with messages."""
    return Conversation(
        id=uuid4(),
        user_id=uuid4(),
        status="active",
        message_count=4,
        messages=[
            Message(role="user", content="Hey Nikita!"),
            Message(role="assistant", content="Hey! How are you?"),
            Message(role="user", content="Good, just got home from work"),
            Message(role="assistant", content="Long day? Tell me about it!")
        ]
    )

@pytest.fixture
def stuck_conversation():
    """Conversation stuck in processing."""
    return Conversation(
        id=uuid4(),
        user_id=uuid4(),
        status="processing",
        processing_started_at=datetime.now(UTC) - timedelta(minutes=30)
    )
```

---

## Mocking Patterns

### LLM Mocking

```python
# tests/engine/scoring/test_analyzer.py

@pytest.fixture
def mock_claude_response():
    """Mock Claude API response."""
    return AsyncMock(return_value=json.dumps({
        "intimacy": 3,
        "passion": 2,
        "trust": 4,
        "secureness": 2,
        "reasoning": "Good emotional sharing"
    }))

async def test_analyze_positive_message(mock_claude_response, monkeypatch):
    """Test analysis of positive message."""
    analyzer = ResponseAnalyzer()
    monkeypatch.setattr(analyzer, "_call_llm", mock_claude_response)

    result = await analyzer.analyze(
        message="I really enjoyed our conversation yesterday",
        context=ConversationContext(chapter=2)
    )

    assert result.deltas.intimacy > 0
    assert result.deltas.trust > 0
```

### Database Mocking

```python
# tests/api/routes/test_telegram.py

@pytest.fixture
def mock_user_repo():
    """Mock UserRepository."""
    mock = AsyncMock()
    mock.get_by_telegram_id = AsyncMock(return_value=create_user_fixture()[0])
    return mock

async def test_webhook_existing_user(mock_user_repo, client):
    """Test webhook for existing user."""
    with patch("nikita.api.routes.telegram.UserRepository", return_value=mock_user_repo):
        response = await client.post("/webhook", json={
            "message": {"from": {"id": 123}, "text": "Hello"}
        })
        assert response.status_code == 200
```

### External Service Mocking

```python
# tests/memory/test_graphiti_client.py

@pytest.fixture
def mock_graphiti():
    """Mock Graphiti client."""
    mock = MagicMock()
    mock.search = AsyncMock(return_value=[
        {"fact": "User likes hiking", "score": 0.9},
        {"fact": "User works as engineer", "score": 0.85}
    ])
    mock.add_episode = AsyncMock()
    return mock

async def test_search_memory(mock_graphiti, monkeypatch):
    """Test memory search."""
    memory = NikitaMemory()
    monkeypatch.setattr(memory, "_get_graphiti", AsyncMock(return_value=mock_graphiti))

    results = await memory.search_memory(
        query="user facts",
        graph_name="user_123",
        limit=10
    )

    assert len(results) == 2
    assert "hiking" in results[0]["fact"]
```

---

## Chaos Testing

### Circuit Breaker Tests

**File**: `tests/context/stages/chaos/test_circuit_breaker.py`

```python
# tests/context/stages/chaos/test_circuit_breaker.py

import pytest
from nikita.context.stages.base import CircuitBreaker

class TestCircuitBreaker:
    """Test circuit breaker state transitions."""

    def test_opens_after_threshold(self):
        """Circuit opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        breaker.record_failure()
        assert not breaker.is_open

        breaker.record_failure()
        assert not breaker.is_open

        breaker.record_failure()
        assert breaker.is_open

    def test_half_open_after_timeout(self):
        """Circuit becomes half-open after recovery timeout."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        # Trip the breaker
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open

        # Wait for recovery
        import time
        time.sleep(1.1)

        # Should be half-open now
        assert not breaker.is_open
        assert breaker.state == "HALF_OPEN"

    def test_closes_on_success(self):
        """Circuit closes after successful call in half-open."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0)

        breaker.record_failure()
        breaker.record_failure()
        breaker.state = "HALF_OPEN"

        breaker.record_success()
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0
```

### Timeout Tests

**File**: `tests/context/stages/chaos/test_timeouts.py`

```python
# tests/context/stages/chaos/test_timeouts.py

import pytest
import asyncio

async def test_stage_timeout_handling():
    """Test stage handles timeout gracefully."""
    stage = GraphUpdatesStage()

    # Mock slow operation
    async def slow_operation():
        await asyncio.sleep(10)
        return "never reached"

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_operation(), timeout=0.1)

async def test_pipeline_continues_after_timeout():
    """Test pipeline continues when non-critical stage times out."""
    pipeline = PostProcessor()

    context = PipelineContext(conversation_id=uuid4())
    context.message_pairs = [create_message_pair()]

    # Mock graph stage to timeout
    with patch.object(GraphUpdatesStage, "process") as mock:
        mock.side_effect = asyncio.TimeoutError()

        result = await pipeline.process_conversation(context.conversation_id)

    # Pipeline should complete, graph stage skipped
    assert result.success
    assert "graph_updates" in result.stages_skipped
```

---

## Integration Testing

### Database Integration Tests

**File**: `tests/db/integration/test_repositories_integration.py`

```python
# tests/db/integration/test_repositories_integration.py

import pytest
from nikita.db.repositories import UserRepository

@pytest.mark.integration
async def test_create_user_with_metrics(db_session):
    """Test creating user with associated metrics."""
    repo = UserRepository(db_session)

    user = await repo.create_with_metrics(
        telegram_id=987654321,
        display_name="Integration Test User"
    )

    assert user.id is not None
    assert user.telegram_id == 987654321

    # Verify metrics created
    metrics = await repo.get_metrics(user.id)
    assert metrics is not None
    assert metrics.relationship_score == 50.0
    assert metrics.chapter_number == 1

@pytest.mark.integration
async def test_update_score(db_session):
    """Test score update."""
    repo = UserRepository(db_session)

    user = await repo.create_with_metrics(
        telegram_id=111222333,
        display_name="Score Test"
    )

    await repo.update_score(user.id, 75.5)

    metrics = await repo.get_metrics(user.id)
    assert float(metrics.relationship_score) == 75.5
```

### Running Integration Tests

```bash
# Run only integration tests
pytest tests/db/integration/ -v -m integration

# Skip integration tests
pytest tests/ -v -m "not integration"
```

---

## E2E Testing

### Full Flow Tests

**File**: `tests/e2e/test_conversation_cycle.py`

```python
# tests/e2e/test_conversation_cycle.py

@pytest.mark.e2e
async def test_full_conversation_flow(e2e_client, test_user):
    """Test complete conversation cycle."""

    # 1. Send message
    response = await e2e_client.post("/webhook", json={
        "message": {
            "from": {"id": test_user.telegram_id},
            "text": "Hey Nikita, how was your day?"
        }
    })
    assert response.status_code == 200

    # 2. Verify conversation created
    await asyncio.sleep(1)  # Wait for async processing
    conversations = await ConversationRepository.get_recent(test_user.id)
    assert len(conversations) > 0

    # 3. Verify pipeline ran
    conversation = conversations[0]
    assert conversation.status == "completed"
    assert conversation.stage_reached == "complete"

    # 4. Verify score updated
    metrics = await UserRepository.get_metrics(test_user.id)
    assert metrics.relationship_score != 50.0  # Changed from default
```

### E2E with MCP Tools

For tests involving external services (Telegram, Gmail, etc.):

```python
# tests/e2e/test_otp_flow.py

@pytest.mark.e2e
async def test_otp_verification_flow(telegram_mcp, gmail_mcp):
    """Test OTP verification using MCP tools."""

    # 1. Send /start to bot
    await telegram_mcp.send_message(
        chat_id=TEST_CHAT_ID,
        text="/start"
    )

    # 2. Share phone number
    await telegram_mcp.send_contact(
        chat_id=TEST_CHAT_ID,
        phone_number=TEST_PHONE
    )

    # 3. Get OTP from Gmail
    otp = await gmail_mcp.get_latest_otp(to=TEST_PHONE)
    assert otp is not None

    # 4. Send OTP to bot
    await telegram_mcp.send_message(
        chat_id=TEST_CHAT_ID,
        text=otp
    )

    # 5. Verify user created
    user = await UserRepository.get_by_phone(TEST_PHONE)
    assert user is not None
    assert user.onboarding_status == "completed"
```

---

## Test Commands

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/context_engine/ -v

# Specific test file
pytest tests/engine/scoring/test_calculator.py -v

# Specific test
pytest tests/engine/scoring/test_calculator.py::test_calculate_delta -v

# With coverage
pytest tests/ --cov=nikita --cov-report=term-missing

# Parallel execution
pytest tests/ -n auto  # Requires pytest-xdist

# Stop on first failure
pytest tests/ -x

# Show local variables in traceback
pytest tests/ --tb=long
```

### Markers

```bash
# Only unit tests
pytest tests/ -m "not integration and not e2e"

# Only integration tests
pytest tests/ -m integration

# Only E2E tests
pytest tests/ -m e2e

# Skip slow tests
pytest tests/ -m "not slow"
```

---

## Key File References

| File | Purpose |
|------|---------|
| `tests/conftest.py` | Root fixtures, singleton clearing |
| `tests/db/integration/conftest.py` | NullPool setup, session fixtures |
| `tests/fixtures/users.py` | User state fixtures |
| `tests/fixtures/conversations.py` | Conversation fixtures |
| `pytest.ini` | pytest configuration |

---

## Related Documentation

- **Pipeline Stages**: [PIPELINE_STAGES.md](PIPELINE_STAGES.md)
- **Database Schema**: [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
- **Anti-Patterns**: [ANTI_PATTERNS.md](ANTI_PATTERNS.md)
