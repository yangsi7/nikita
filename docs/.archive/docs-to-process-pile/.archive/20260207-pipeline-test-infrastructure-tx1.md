# Pipeline Test Infrastructure — TX.1 Implementation Report

**Date**: 2026-02-07
**Task**: TX.1 — Create Pipeline Test Infrastructure
**Spec**: 042 Unified Pipeline Refactor
**Status**: ✅ COMPLETE

---

## Summary

Created shared test infrastructure for the unified pipeline test suite. Provides reusable fixtures and mock classes that eliminate duplication across pipeline tests and enable fast, deterministic testing without external dependencies.

**Files Created**:
- `tests/pipeline/conftest.py` (250 lines, 10 fixtures)
- `tests/pipeline/mocks.py` (200 lines, 4 mock classes)

**Key Achievement**: Zero external calls during tests (no LLM, no OpenAI, no database)

---

## AC Validation

### AC-X.1.1: Async session fixtures, PipelineContext factory, stage isolation ✅

**Implemented**:
- `make_context()` — Factory fixture with sensible defaults
- `mock_session()` — Async SQLAlchemy session mock
- Function-scoped isolation (each test gets fresh instances)

**Pattern**:
```python
def test_something(make_context, mock_session):
    ctx = make_context(chapter=3, platform="voice")
    stage = MyStage(session=mock_session)
    await stage.execute(ctx)
```

### AC-X.1.2: MockHaikuEnricher fixture ✅

**Implemented**: `mock_haiku` fixture returning deterministic enriched text

**Behavior**:
- Prepends `[Enriched]` prefix (simulates LLM processing)
- Truncates to 100 chars (simulates token limits)
- No real Claude Haiku calls

**Usage**:
```python
async def test_prompt_enrichment(mock_haiku):
    enriched = await mock_haiku.enrich("System prompt")
    assert enriched.startswith("[Enriched]")
```

### AC-X.1.3: MockEmbeddingClient fixture ✅

**Implemented**: `mock_embeddings` fixture returning deterministic 1536-dim vectors

**Behavior**:
- Uses MD5 hash of text for determinism (same text → same vector)
- Returns 1536 floats in range [0.0, 1.0]
- Supports batch embedding
- No OpenAI API calls

**Usage**:
```python
async def test_memory_embedding(mock_embeddings):
    vec = await mock_embeddings.embed("User loves cats")
    assert len(vec) == 1536
    assert all(0.0 <= v <= 1.0 for v in vec)
```

### AC-X.1.4: MockExtractionAgent fixture ✅

**Implemented**: `mock_extraction` fixture returning deterministic facts/threads/thoughts

**Behavior**:
- Returns fixed extraction structure (1 fact, 1 thread, 1 thought)
- Emotional tone always "neutral"
- No Claude or LLM calls

**Usage**:
```python
async def test_extraction(mock_extraction):
    result = await mock_extraction.extract(messages)
    assert len(result["facts"]) == 1
    assert result["emotional_tone"] == "neutral"
```

### AC-X.1.5: Stage fixtures with clean DB state per test ✅

**Implemented**: All fixtures are function-scoped with proper isolation

**Additional Fixtures**:
- `rich_context` — Pre-populated context (all 8 stages filled)
- `mock_conversation` — Conversation with 2 messages
- `mock_user` — User with metrics and game state
- `mock_prompt_repo` — In-memory ReadyPrompt repository

---

## Implementation Details

### conftest.py Structure

```python
# Factory fixture for creating contexts
@pytest.fixture
def make_context():
    def _factory(**overrides) -> PipelineContext:
        # Sensible defaults + override support
        ...
    return _factory

# Mock async session
@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    ...
    return session

# Pre-populated context (for prompt builder tests)
@pytest.fixture
def rich_context(make_context):
    return make_context(
        extracted_facts=[...],
        life_events=[...],
        emotional_state={...},
        ...
    )

# Import mock classes and expose as fixtures
from tests.pipeline.mocks import (
    MockHaikuEnricher,
    MockEmbeddingClient,
    MockExtractionAgent,
    MockReadyPromptRepo,
)

@pytest.fixture
def mock_haiku():
    return MockHaikuEnricher()

# ... (mock_embeddings, mock_extraction, mock_prompt_repo)
```

### mocks.py Structure

```python
class MockHaikuEnricher:
    """Deterministic Haiku enrichment (no LLM)."""
    async def enrich(self, raw_prompt: str, platform: str = "text") -> str:
        return f"[Enriched] {raw_prompt[:100]}..."

class MockEmbeddingClient:
    """Deterministic embeddings (no OpenAI)."""
    DIMENSION = 1536
    async def embed(self, text: str) -> list[float]:
        h = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(h >> i & 0xFF) / 255.0 for i in range(self.DIMENSION)]

class MockExtractionAgent:
    """Deterministic extraction (no LLM)."""
    async def extract(self, messages: list, user_id=None) -> dict:
        return {
            "facts": [{"content": "Mock fact", "type": "preference"}],
            "threads": [{"topic": "mock topic"}],
            "thoughts": [{"text": "mock thought"}],
            "summary": "Mock extraction summary",
            "emotional_tone": "neutral",
        }

class MockReadyPromptRepo:
    """In-memory prompt storage (no DB)."""
    def __init__(self):
        self._prompts = {}

    async def get_current(self, user_id, platform):
        return self._prompts.get((str(user_id), platform))

    async def set_current(self, user_id, platform, prompt_text, ...):
        # Store in memory dict
        ...
```

---

## Design Patterns

### 1. Factory Pattern (`make_context`)

**Why**: Each test needs different context configurations
- Default values for common scenarios (chapter=2, score=65)
- Override support for specific tests
- No mutable default arguments (each call gets fresh collections)

**Example**:
```python
# Test with default values
ctx = make_context()

# Test with specific values
ctx = make_context(chapter=5, platform="voice", game_status="boss_fight")
```

### 2. Deterministic Mocks

**Why**: Tests must be reproducible
- Same input → same output (no randomness)
- Hash-based vector generation (MD5 for embeddings)
- Fixed extraction results

**Benefit**: Tests won't flake due to LLM variations

### 3. Rich Context Fixture

**Why**: Prompt builder tests need fully-populated context
- Avoid duplication (DRY principle)
- Realistic data (mimics real pipeline execution)
- All 8 stages pre-filled

**Usage**:
```python
def test_prompt_generation(rich_context):
    # Context already has extraction, memory, emotional state, etc.
    assert len(rich_context.extracted_facts) == 3
    builder = PromptBuilderStage(session=mock_session)
    result = await builder.execute(rich_context)
```

### 4. In-Memory Repository

**Why**: Test prompt storage without database overhead
- No migrations needed
- Instant setup/teardown
- Simple dict-based storage
- `clear()` method for test cleanup

---

## Existing Test Patterns

The fixtures follow patterns already established in `test_stages.py`:

```python
# Old pattern (inline helpers)
def _make_context(**overrides) -> PipelineContext:
    defaults = dict(...)
    defaults.update(overrides)
    return PipelineContext(**defaults)

def _mock_session() -> MagicMock:
    return MagicMock()

# New pattern (fixtures)
def test_something(make_context, mock_session):
    ctx = make_context()
    stage = MyStage(session=mock_session)
```

**Migration Path**: Existing tests can continue using inline helpers OR migrate to fixtures (both work)

---

## Verification

### Import Test ✅
```bash
python -c "from tests.pipeline.conftest import *; from tests.pipeline.mocks import *; print('OK')"
# Output: OK
```

### Mock Functionality Test ✅
```python
# All mocks tested for:
# - Correct return types
# - Determinism (same input → same output)
# - No external calls
# - Batch operations (where applicable)
```

### Pytest Discovery ✅
```bash
pytest tests/pipeline/ -v --co -q
# Output: collected 92 items
```

---

## Next Steps (Not Part of TX.1)

**T3.5**: Write PromptBuilderStage integration tests (will use `rich_context`)
**T4.6**: Write PipelineOrchestrator async logging tests (will use `make_context`)
**TX.2**: Write pipeline integration tests with real DB (will use `mock_session` + real DB)

---

## Files Modified

- ✅ `tests/pipeline/conftest.py` — CREATED (250 lines)
- ✅ `tests/pipeline/mocks.py` — CREATED (200 lines)
- ✅ `event-stream.md` — Updated (5 new entries)

---

## Test Impact

**Before TX.1**:
- Each test file duplicated `_make_context()` and `_mock_session()`
- No shared mocks for Haiku, embeddings, extraction
- No rich context fixture for complex scenarios

**After TX.1**:
- Centralized fixtures (DRY principle)
- 4 deterministic mocks (no external calls)
- `rich_context` for prompt builder tests
- Function-scoped isolation (clean state per test)

**Estimated Reduction**: ~50-100 lines of duplication eliminated across test suite

---

## References

**Existing Patterns**:
- `tests/pipeline/test_stages.py:17-29` — `_make_context()` and `_mock_session()` patterns
- `tests/pipeline/test_orchestrator.py:25-52` — `FakeStage` pattern for testing orchestrator
- `tests/pipeline/test_models.py:17-25` — `_make_ctx()` helper

**Spec**: `specs/042-unified-pipeline/tasks.md` — Task TX.1

---

## Conclusion

Task TX.1 is **COMPLETE**. All acceptance criteria met:
- ✅ AC-X.1.1: Async session fixtures, PipelineContext factory, stage isolation
- ✅ AC-X.1.2: MockHaikuEnricher fixture (deterministic enriched text)
- ✅ AC-X.1.3: MockEmbeddingClient fixture (deterministic 1536-dim vectors)
- ✅ AC-X.1.4: MockExtractionAgent fixture (deterministic facts/threads/thoughts)
- ✅ AC-X.1.5: Function-scoped sessions with clean DB state per test

**Impact**: Reduced duplication, enabled fast deterministic testing, prepared infrastructure for T3.5, T4.6, TX.2.
