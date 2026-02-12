"""
Performance benchmark tests for unified pipeline (TX.3).

These tests verify the pipeline meets performance requirements for production use.
Uses generous margins (2x-3x expected) to avoid flaky CI failures.

All tests use mocks only - no real DB, LLM, or external services required.
"""

import asyncio
import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.pipeline.models import PipelineContext
from nikita.pipeline.stages.base import StageResult
from nikita.pipeline.orchestrator import PipelineOrchestrator


# ====================================================================================
# FAKE STAGE FOR TESTING
# ====================================================================================


class FakeStage:
    """Quick-completing stage for pipeline performance tests."""

    def __init__(self, name="fake", delay=0.001, is_critical=False, session=None, **kwargs):
        self.name = name
        self._delay = delay
        self.is_critical = is_critical
        self.timeout_seconds = 5.0
        self._session = session

    async def execute(self, ctx: PipelineContext) -> StageResult:
        """Simulate stage execution with configurable delay."""
        await asyncio.sleep(self._delay)
        ctx.stage_timings[self.name] = self._delay * 1000
        return StageResult(success=True, data={"stage": self.name})


# ====================================================================================
# 1. TEMPLATE RENDERING PERFORMANCE (2 tests)
# ====================================================================================


@pytest.mark.skipif(
    __import__("importlib.util").util.find_spec("jinja2") is None,
    reason="jinja2 not installed (Phase 3)"
)
@pytest.mark.asyncio
async def test_jinja2_render_under_5ms():
    """Jinja2 template rendering should complete under 5ms for text platform."""
    from jinja2 import Template

    # Simple template similar to production (no complex logic)
    template_str = """
Hello {{ name }}, your score is {{ score }}.
Chapter: {{ chapter }}
Facts: {{ facts|length }}
Threads: {{ threads|length }}
"""
    template = Template(template_str)

    context_data = {
        "name": "Test User",
        "score": 75,
        "chapter": 2,
        "facts": ["fact1", "fact2", "fact3"],
        "threads": ["thread1", "thread2"],
    }

    start = time.perf_counter()
    result = template.render(**context_data)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result is not None
    assert "Test User" in result
    # Generous margin: 3x expected (5ms → 15ms)
    assert elapsed_ms < 15.0, f"Expected <15ms, got {elapsed_ms:.1f}ms"


@pytest.mark.skipif(
    __import__("importlib.util").util.find_spec("jinja2") is None,
    reason="jinja2 not installed (Phase 3)"
)
@pytest.mark.asyncio
async def test_voice_template_render_under_5ms():
    """Jinja2 template rendering should complete under 5ms for voice platform."""
    from jinja2 import Template

    # Voice template is typically shorter
    template_str = """
Score: {{ score }}
Chapter: {{ chapter }}
Mood: {{ mood }}
"""
    template = Template(template_str)

    context_data = {
        "score": 75,
        "chapter": 2,
        "mood": "playful",
    }

    start = time.perf_counter()
    result = template.render(**context_data)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result is not None
    assert "75" in result
    # Generous margin: 3x expected
    assert elapsed_ms < 15.0, f"Expected <15ms, got {elapsed_ms:.1f}ms"


# ====================================================================================
# 2. MEMORY OPERATION PERFORMANCE (2 tests)
# ====================================================================================


@pytest.mark.asyncio
async def test_memory_search_under_100ms(mock_session):
    """SupabaseMemory.search should complete under 100ms (mocked)."""
    from nikita.memory.supabase_memory import SupabaseMemory

    user_id = uuid4()
    memory = SupabaseMemory(mock_session, user_id=user_id, openai_api_key="test-key")

    # Mock the embedding generation and DB query
    with patch.object(memory, "_generate_embedding", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1] * 1536

        # Mock session.execute to return empty results
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        start = time.perf_counter()
        results = await memory.search(query="test query", limit=5)
        elapsed_ms = (time.perf_counter() - start) * 1000

    # Generous margin: 3x expected (100ms → 300ms)
    assert elapsed_ms < 300.0, f"Expected <300ms, got {elapsed_ms:.1f}ms"


@pytest.mark.asyncio
async def test_memory_store_under_100ms(mock_session):
    """SupabaseMemory.add_fact should complete under 100ms (mocked)."""
    from nikita.memory.supabase_memory import SupabaseMemory

    user_id = uuid4()
    memory = SupabaseMemory(mock_session, user_id=user_id, openai_api_key="test-key")

    # Mock the embedding generation and DB operations
    with patch.object(memory, "_generate_embedding", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1] * 1536

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No duplicate
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        start = time.perf_counter()
        await memory.add_fact(
            fact="User likes coffee",
            graph_type="user",
            source="test",
            confidence=0.9,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

    # Generous margin: 3x expected (100ms → 300ms)
    assert elapsed_ms < 300.0, f"Expected <300ms, got {elapsed_ms:.1f}ms"


# ====================================================================================
# 3. FULL PIPELINE PERFORMANCE (3 tests)
# ====================================================================================


@pytest.mark.asyncio
async def test_full_pipeline_with_fake_stages_under_1s(mock_session, make_context):
    """Full pipeline with 9 FakeStages should complete under 1s."""
    # Create 9 fake stages as (name, instance, is_critical) tuples
    fake_stages = [
        ("extraction", FakeStage(name="extraction", delay=0.010, is_critical=True), True),
        ("memory_update", FakeStage(name="memory_update", delay=0.010, is_critical=True), True),
        ("life_sim", FakeStage(name="life_sim", delay=0.020, is_critical=False), False),
        ("emotional", FakeStage(name="emotional", delay=0.020, is_critical=False), False),
        ("game_state", FakeStage(name="game_state", delay=0.020, is_critical=False), False),
        ("conflict", FakeStage(name="conflict", delay=0.020, is_critical=False), False),
        ("touchpoint", FakeStage(name="touchpoint", delay=0.020, is_critical=False), False),
        ("summary", FakeStage(name="summary", delay=0.020, is_critical=False), False),
        ("prompt_builder", FakeStage(name="prompt_builder", delay=0.020, is_critical=False), False),
    ]

    orchestrator = PipelineOrchestrator(session=mock_session, stages=fake_stages)
    ctx = make_context()

    start = time.perf_counter()
    result = await orchestrator.process(
        conversation_id=ctx.conversation_id,
        user_id=ctx.user_id,
        platform="text",
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result.success
    assert result.stages_completed == 9
    # Generous margin: 2x expected (1s → 2s)
    assert elapsed_ms < 2000.0, f"Expected <2000ms, got {elapsed_ms:.1f}ms"


@pytest.mark.asyncio
async def test_pipeline_overhead_minimal(mock_session, make_context):
    """Pipeline orchestrator overhead should be under 50ms."""
    # Use near-zero delay stages to measure pure orchestration overhead
    fake_stages = [
        (f"stage{i}", FakeStage(name=f"stage{i}", delay=0.0001, is_critical=False), False)
        for i in range(9)
    ]

    orchestrator = PipelineOrchestrator(session=mock_session, stages=fake_stages)
    ctx = make_context()

    start = time.perf_counter()
    result = await orchestrator.process(
        conversation_id=ctx.conversation_id,
        user_id=ctx.user_id,
        platform="text",
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result.success
    # Total time should be minimal (stages do almost nothing)
    # Generous margin: 3x expected (50ms → 150ms)
    assert elapsed_ms < 150.0, f"Expected <150ms overhead, got {elapsed_ms:.1f}ms"


@pytest.mark.asyncio
async def test_critical_stage_failure_fast_abort(mock_session, make_context):
    """Critical stage failure should abort pipeline quickly (< 100ms)."""

    class FailingCriticalStage(FakeStage):
        """Stage that always fails."""

        def __init__(self, **kwargs):
            super().__init__(is_critical=True, **kwargs)

        async def execute(self, ctx):
            await asyncio.sleep(0.001)  # Minimal delay
            return StageResult(success=False, error="Critical failure")

    fake_stages = [
        ("extraction", FakeStage(name="extraction", delay=0.001, is_critical=True), True),
        ("memory_update", FailingCriticalStage(name="memory_update"), True),  # Fails here
        ("life_sim", FakeStage(name="life_sim", delay=0.001), False),  # Should not run
    ]

    orchestrator = PipelineOrchestrator(session=mock_session, stages=fake_stages)
    ctx = make_context()

    start = time.perf_counter()
    result = await orchestrator.process(
        conversation_id=ctx.conversation_id,
        user_id=ctx.user_id,
        platform="text",
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert not result.success
    assert result.stages_completed == 2  # Only first 2 ran
    # Should abort quickly
    # Generous margin: 3x expected (100ms → 300ms)
    assert elapsed_ms < 300.0, f"Expected <300ms abort, got {elapsed_ms:.1f}ms"


# ====================================================================================
# 4. READY PROMPT LOADING PERFORMANCE (2 tests)
# ====================================================================================


@pytest.mark.asyncio
async def test_ready_prompt_load_under_100ms(mock_session):
    """ReadyPromptRepository.get_current should complete under 100ms (mocked)."""
    from unittest.mock import AsyncMock, MagicMock
    from nikita.db.repositories.ready_prompt_repository import ReadyPromptRepository

    repo = ReadyPromptRepository(mock_session)

    # Mock the DB query to return a prompt-like result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock(
        prompt_text="You are Nikita...",
        token_count=1500,
        version="v045",
    )
    mock_session.execute = AsyncMock(return_value=mock_result)

    start = time.perf_counter()
    prompt = await repo.get_current(user_id=uuid4(), platform="text")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert prompt is not None
    # Generous margin: 3x expected (100ms → 300ms)
    assert elapsed_ms < 300.0, f"Expected <300ms, got {elapsed_ms:.1f}ms"


@pytest.mark.asyncio
async def test_ready_prompt_vs_generation_speedup(mock_session, make_context):
    """Loading ready prompt should be faster than full generation path (mocked)."""
    from unittest.mock import AsyncMock, MagicMock
    from nikita.db.repositories.ready_prompt_repository import ReadyPromptRepository

    repo = ReadyPromptRepository(mock_session)

    # Mock ready prompt load (fast path)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock(
        prompt_text="You are Nikita, a cybersecurity expert...",
        token_count=2000,
        version="v045",
    )
    mock_session.execute = AsyncMock(return_value=mock_result)

    start = time.perf_counter()
    prompt = await repo.get_current(user_id=uuid4(), platform="text")
    load_ms = (time.perf_counter() - start) * 1000

    # Simulate generation path (slower — uses asyncio.sleep to approximate)
    start = time.perf_counter()
    await asyncio.sleep(0.05)  # Simulate 50ms generation
    gen_ms = (time.perf_counter() - start) * 1000

    assert prompt is not None
    # Ready prompt load should be faster than generation
    assert load_ms < gen_ms, f"Load ({load_ms:.1f}ms) should be faster than gen ({gen_ms:.1f}ms)"


# ====================================================================================
# 5. TOKEN COUNTING PERFORMANCE (1 test)
# ====================================================================================


@pytest.mark.asyncio
async def test_token_counting_under_10ms():
    """Token counting for 6000-token prompt should complete under 10ms (after warm-up)."""
    from nikita.context.utils.token_counter import count_tokens

    # Generate a long prompt (~6000 tokens worth of text)
    prompt = "You are Nikita, a cybersecurity expert girlfriend. " * 300

    # Warm-up call: tiktoken lazy-loads encoding on first use (~100ms)
    count_tokens("warm up")

    start = time.perf_counter()
    token_count = count_tokens(prompt)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert token_count > 0
    # Generous margin: 5x expected (10ms → 50ms)
    assert elapsed_ms < 50.0, f"Expected <50ms, got {elapsed_ms:.1f}ms"
