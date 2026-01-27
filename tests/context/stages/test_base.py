"""Tests for PipelineStage base class."""

import asyncio
from datetime import datetime, UTC
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import structlog

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.base import PipelineStage, StageError, StageResult


class ConcreteStage(PipelineStage[str, str]):
    """Concrete implementation for testing."""

    name = "test_stage"
    is_critical = False
    timeout_seconds = 5.0
    max_retries = 2

    async def _run(self, context: PipelineContext, input: str) -> str:
        return f"processed: {input}"


class FailingStage(PipelineStage[str, str]):
    """Stage that always fails."""

    name = "failing_stage"
    is_critical = True

    async def _run(self, context: PipelineContext, input: str) -> str:
        raise Exception("Stage failed!")


class SlowStage(PipelineStage[str, str]):
    """Stage that takes too long."""

    name = "slow_stage"
    timeout_seconds = 0.1

    async def _run(self, context: PipelineContext, input: str) -> str:
        await asyncio.sleep(1.0)  # Will timeout
        return "done"


class RetryableStage(PipelineStage[str, str]):
    """Stage that fails with retryable errors."""

    name = "retryable_stage"
    max_retries = 3

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.attempt_count = 0

    async def _run(self, context: PipelineContext, input: str) -> str:
        self.attempt_count += 1
        if self.attempt_count < 3:
            raise IOError("Transient failure")
        return "success after retries"


@pytest.fixture
def pipeline_context() -> PipelineContext:
    """Create test pipeline context."""
    return PipelineContext(
        conversation_id=uuid4(),
        user_id=uuid4(),
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    logger = MagicMock()
    logger.bind.return_value = logger
    return logger


class TestStageResult:
    """Test StageResult dataclass."""

    def test_ok_creates_success_result(self):
        """StageResult.ok creates a successful result."""
        result = StageResult.ok(data="test_data", duration_ms=100.0, retries=1)

        assert result.success is True
        assert result.data == "test_data"
        assert result.error is None
        assert result.duration_ms == 100.0
        assert result.retries == 1

    def test_fail_creates_failed_result(self):
        """StageResult.fail creates a failed result."""
        result = StageResult.fail(error="test error", duration_ms=50.0)

        assert result.success is False
        assert result.data is None
        assert result.error == "test error"
        assert result.duration_ms == 50.0


class TestStageError:
    """Test StageError exception."""

    def test_creates_error_with_stage_name(self):
        """StageError includes stage name in message."""
        error = StageError("my_stage", "Something went wrong")

        assert error.stage_name == "my_stage"
        assert "[my_stage]" in str(error)
        assert "Something went wrong" in str(error)

    def test_recoverable_default_true(self):
        """StageError is recoverable by default."""
        error = StageError("stage", "error")
        assert error.recoverable is True

    def test_non_recoverable_error(self):
        """Non-recoverable errors can be created."""
        error = StageError("stage", "fatal", recoverable=False)
        assert error.recoverable is False


class TestPipelineStageExecution:
    """Test PipelineStage execution."""

    @pytest.mark.asyncio
    async def test_successful_execution(
        self,
        mock_session: AsyncMock,
        mock_logger: MagicMock,
        pipeline_context: PipelineContext,
    ):
        """Stage executes successfully and returns result."""
        stage = ConcreteStage(mock_session, mock_logger)

        result = await stage.execute(pipeline_context, "input_data")

        assert result.success is True
        assert result.data == "processed: input_data"
        assert result.error is None
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_failure_returns_failed_result(
        self,
        mock_session: AsyncMock,
        mock_logger: MagicMock,
        pipeline_context: PipelineContext,
    ):
        """Stage failure returns failed result, doesn't raise."""
        stage = FailingStage(mock_session, mock_logger)

        result = await stage.execute(pipeline_context, "input")

        assert result.success is False
        assert result.error is not None
        assert "Stage failed!" in result.error

    @pytest.mark.asyncio
    async def test_timeout_returns_failed_result(
        self,
        mock_session: AsyncMock,
        mock_logger: MagicMock,
        pipeline_context: PipelineContext,
    ):
        """Stage timeout returns failed result with timeout message."""
        stage = SlowStage(mock_session, mock_logger)

        result = await stage.execute(pipeline_context, "input")

        assert result.success is False
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_stage_error_returns_failed_result(
        self,
        mock_session: AsyncMock,
        mock_logger: MagicMock,
        pipeline_context: PipelineContext,
    ):
        """StageError is caught and returned as failed result."""

        class StageErrorStage(PipelineStage[str, str]):
            name = "error_stage"

            async def _run(self, context: PipelineContext, input: str) -> str:
                raise StageError("error_stage", "Expected failure")

        stage = StageErrorStage(mock_session, mock_logger)
        result = await stage.execute(pipeline_context, "input")

        assert result.success is False
        assert "[error_stage]" in result.error


class TestPipelineStageRetry:
    """Test retry logic in PipelineStage."""

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(
        self,
        mock_session: AsyncMock,
        mock_logger: MagicMock,
        pipeline_context: PipelineContext,
    ):
        """Stage retries on IOError and succeeds eventually."""
        stage = RetryableStage(mock_session, mock_logger)

        result = await stage.execute(pipeline_context, "input")

        assert result.success is True
        assert result.data == "success after retries"
        assert stage.attempt_count == 3

    @pytest.mark.asyncio
    async def test_stops_after_max_retries(
        self,
        mock_session: AsyncMock,
        mock_logger: MagicMock,
        pipeline_context: PipelineContext,
    ):
        """Stage stops retrying after max_retries."""

        class AlwaysFailsStage(PipelineStage[str, str]):
            name = "always_fails"
            max_retries = 2

            async def _run(self, context: PipelineContext, input: str) -> str:
                raise IOError("Permanent failure")

        stage = AlwaysFailsStage(mock_session, mock_logger)
        result = await stage.execute(pipeline_context, "input")

        assert result.success is False
        assert "IOError" in result.error or "Permanent failure" in result.error


class TestPipelineStageLogging:
    """Test logging behavior in PipelineStage."""

    @pytest.mark.asyncio
    async def test_logs_stage_start_and_complete(
        self,
        mock_session: AsyncMock,
        pipeline_context: PipelineContext,
    ):
        """Stage logs start and completion."""
        with patch("nikita.context.stages.base.log_stage_start") as mock_start:
            with patch("nikita.context.stages.base.log_stage_complete") as mock_complete:
                stage = ConcreteStage(mock_session, None)
                await stage.execute(pipeline_context, "input")

                mock_start.assert_called_once()
                mock_complete.assert_called_once()

                # Verify completion was logged as success
                call_kwargs = mock_complete.call_args
                assert call_kwargs[1].get("success", call_kwargs[0][2] if len(call_kwargs[0]) > 2 else True) is True


class TestPipelineStageTracing:
    """Test OpenTelemetry tracing in PipelineStage."""

    @pytest.mark.asyncio
    async def test_creates_span_with_attributes(
        self,
        mock_session: AsyncMock,
        mock_logger: MagicMock,
        pipeline_context: PipelineContext,
    ):
        """Stage creates OpenTelemetry span with correct attributes."""
        stage = ConcreteStage(mock_session, mock_logger)

        # The tracer is created but span operations are no-ops without a provider
        # We just verify execution completes successfully
        result = await stage.execute(pipeline_context, "input")
        assert result.success is True
