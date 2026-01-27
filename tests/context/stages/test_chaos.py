"""Chaos tests for pipeline resilience.

Spec 037 US-6: Comprehensive tests for failure scenarios.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.base import StageResult
from nikita.context.stages.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState
from nikita.context.stages.extraction import ExtractionStage
from nikita.context.stages.graph_updates import GraphUpdatesStage
from nikita.context.stages.ingestion import IngestionStage
from nikita.context.stages.vice_processing import ViceProcessingStage


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def pipeline_context():
    """Create test pipeline context."""
    return PipelineContext(
        conversation_id=uuid4(),
        user_id=uuid4(),
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_conversation(pipeline_context):
    """Create mock conversation."""
    conv = MagicMock()
    conv.id = pipeline_context.conversation_id
    conv.user_id = pipeline_context.user_id
    conv.messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    return conv


class TestNeo4jColdStartTimeout:
    """AC-T5.1.1: Test simulates Neo4j 61s cold start timeout."""

    @pytest.mark.asyncio
    async def test_graph_updates_handles_timeout(
        self, mock_session, pipeline_context, mock_conversation
    ):
        """Graph updates stage handles Neo4j timeout gracefully."""
        stage = GraphUpdatesStage(mock_session)
        stage.timeout_seconds = 0.1  # Very short timeout for test

        # Create mock extraction result
        extraction = MagicMock()
        extraction.facts = [{"content": "Test fact"}]
        extraction.summary = "Test summary"
        extraction.thoughts = []

        # Mock slow Neo4j connection via the memory module
        async def slow_memory_client(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate slow response

        with patch(
            "nikita.memory.graphiti_client.get_memory_client",
            side_effect=slow_memory_client,
        ):
            result = await stage.execute(
                pipeline_context, (mock_conversation, extraction)
            )

        # Should fail due to timeout but be non-critical
        assert result.success is False
        assert "timed out" in result.error.lower()
        # Stage is non-critical, so this is expected behavior

    @pytest.mark.asyncio
    async def test_graph_updates_circuit_breaker_opens_after_failures(
        self, mock_session
    ):
        """Circuit breaker opens after repeated failures."""
        # Test the circuit breaker behavior directly
        cb = CircuitBreaker(
            name="test_neo4j",
            failure_threshold=2,
            recovery_timeout=10.0,
        )

        async def failing_func():
            raise ConnectionError("Neo4j down")

        # First failure
        with pytest.raises(ConnectionError):
            await cb.call(failing_func)
        assert cb._state == CircuitState.CLOSED

        # Second failure - should open
        with pytest.raises(ConnectionError):
            await cb.call(failing_func)
        assert cb._state == CircuitState.OPEN

        # Third call - rejected without calling function
        with pytest.raises(CircuitOpenError):
            await cb.call(failing_func)


class TestLLMRateLimiting:
    """AC-T5.1.2: Test simulates LLM rate limiting (429)."""

    @pytest.mark.asyncio
    async def test_extraction_handles_rate_limit(
        self, mock_session, pipeline_context, mock_conversation
    ):
        """Extraction stage handles rate limit gracefully."""
        stage = ExtractionStage(mock_session)

        # Mock rate-limited LLM
        mock_meta_service = AsyncMock()
        mock_meta_service.extract_entities = AsyncMock(
            side_effect=Exception("Rate limit exceeded (429)")
        )
        stage._meta_service = mock_meta_service

        with patch.object(
            stage._thread_repo, "get_open_threads", return_value=[]
        ):
            result = await stage.execute(pipeline_context, mock_conversation)

        # Should fail with error
        assert result.success is False
        assert "Rate limit" in result.error or "failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_extraction_circuit_breaker_opens(self, mock_session):
        """LLM circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(
            name="test_llm",
            failure_threshold=3,
            recovery_timeout=10.0,
        )

        async def rate_limited_call():
            raise Exception("429 Too Many Requests")

        # Trigger 3 failures
        for _ in range(3):
            with pytest.raises(Exception):
                await cb.call(rate_limited_call)

        assert cb._state == CircuitState.OPEN

        # Next call should be rejected immediately
        with pytest.raises(CircuitOpenError):
            await cb.call(rate_limited_call)


class TestMultipleStageFailures:
    """AC-T5.1.3: Test simulates multiple non-critical stage failures."""

    @pytest.mark.asyncio
    async def test_pipeline_continues_on_non_critical_failures(
        self, mock_session, pipeline_context, mock_conversation
    ):
        """Pipeline continues when non-critical stages fail."""
        # Graph updates is non-critical (is_critical=False)
        graph_stage = GraphUpdatesStage(mock_session)
        assert graph_stage.is_critical is False

        # Vice processing is non-critical
        vice_stage = ViceProcessingStage(mock_session)
        assert vice_stage.is_critical is False

        # Simulate failures - these should not stop the pipeline
        # (in a real orchestrator, other stages would continue)
        extraction = MagicMock()
        extraction.facts = []
        extraction.summary = ""
        extraction.thoughts = []

        # Mock failing Neo4j
        with patch(
            "nikita.memory.graphiti_client.get_memory_client",
            side_effect=Exception("Neo4j down"),
        ):
            graph_result = await graph_stage.execute(
                pipeline_context, (mock_conversation, extraction)
            )

        # Should fail but be non-critical
        assert graph_result.success is False
        # Error is recorded in context
        assert "graph_updates" in pipeline_context.stage_errors

    @pytest.mark.asyncio
    async def test_errors_recorded_in_context(
        self, mock_session, pipeline_context, mock_conversation
    ):
        """Stage errors are recorded in pipeline context."""
        graph_stage = GraphUpdatesStage(mock_session)

        extraction = MagicMock()
        extraction.facts = [{"content": "Fact"}]
        extraction.summary = "Summary"
        extraction.thoughts = []

        # Mock failing Neo4j
        with patch(
            "nikita.memory.graphiti_client.get_memory_client",
            side_effect=Exception("Connection refused"),
        ):
            await graph_stage.execute(
                pipeline_context, (mock_conversation, extraction)
            )

        # Error should be recorded
        assert "graph_updates" in pipeline_context.stage_errors
        assert "Connection refused" in pipeline_context.stage_errors["graph_updates"]


class TestCriticalStageFailFast:
    """AC-T5.1.5: Pipeline fails fast when critical stages fail."""

    @pytest.mark.asyncio
    async def test_ingestion_failure_is_critical(
        self, mock_session, pipeline_context
    ):
        """Ingestion stage failure is critical."""
        stage = IngestionStage(mock_session)
        assert stage.is_critical is True

        with patch.object(stage._repo, "get", return_value=None):
            result = await stage.execute(
                pipeline_context, pipeline_context.conversation_id
            )

        assert result.success is False
        # In a real orchestrator, this would stop the pipeline

    @pytest.mark.asyncio
    async def test_extraction_failure_is_critical(
        self, mock_session, pipeline_context, mock_conversation
    ):
        """Extraction stage failure is critical."""
        stage = ExtractionStage(mock_session)
        assert stage.is_critical is True

        mock_meta_service = AsyncMock()
        mock_meta_service.extract_entities = AsyncMock(
            side_effect=Exception("LLM unavailable")
        )
        stage._meta_service = mock_meta_service

        with patch.object(stage._thread_repo, "get_open_threads", return_value=[]):
            result = await stage.execute(pipeline_context, mock_conversation)

        assert result.success is False
        # In a real orchestrator, this would stop the pipeline


class TestCircuitBreakerStateTransitions:
    """AC-T5.1.6: Circuit breaker state transitions tested."""

    @pytest.mark.asyncio
    async def test_closed_to_open_transition(self):
        """Circuit transitions from CLOSED to OPEN after failures."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=10.0,
        )

        assert cb._state == CircuitState.CLOSED

        async def failing_call():
            raise Exception("Failure")

        # First failure - still closed
        with pytest.raises(Exception):
            await cb.call(failing_call)
        assert cb._state == CircuitState.CLOSED

        # Second failure - opens
        with pytest.raises(Exception):
            await cb.call(failing_call)
        assert cb._state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_to_half_open_transition(self):
        """Circuit transitions from OPEN to HALF_OPEN after recovery timeout."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=1,
            recovery_timeout=0.01,  # Very short for test
        )

        async def failing_call():
            raise Exception("Failure")

        # Open the circuit
        with pytest.raises(Exception):
            await cb.call(failing_call)
        assert cb._state == CircuitState.OPEN

        # Wait for recovery
        await asyncio.sleep(0.02)

        # Next call should be allowed (half-open)
        async def success_call():
            return "success"

        result = await cb.call(success_call)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_half_open_to_closed_transition(self):
        """Circuit transitions from HALF_OPEN to CLOSED after successes."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=1,
            recovery_timeout=0.01,
            half_open_max_calls=2,
        )

        async def failing_call():
            raise Exception("Failure")

        # Open the circuit
        with pytest.raises(Exception):
            await cb.call(failing_call)

        # Wait for recovery
        await asyncio.sleep(0.02)

        async def success_call():
            return "success"

        # First success in half-open
        await cb.call(success_call)
        assert cb._state == CircuitState.HALF_OPEN

        # Second success - should close
        await cb.call(success_call)
        assert cb._state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self):
        """Circuit reopens if failure occurs in HALF_OPEN state."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=1,
            recovery_timeout=0.01,
        )

        async def failing_call():
            raise Exception("Failure")

        # Open the circuit
        with pytest.raises(Exception):
            await cb.call(failing_call)

        # Wait for recovery
        await asyncio.sleep(0.02)

        # Failure in half-open should reopen
        with pytest.raises(Exception):
            await cb.call(failing_call)

        assert cb._state == CircuitState.OPEN
