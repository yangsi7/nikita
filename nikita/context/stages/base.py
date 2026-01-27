"""Base class for all pipeline stages.

This module defines the PipelineStage base class that provides:
- Timeout handling with asyncio.wait_for
- Retry logic with exponential backoff (via tenacity)
- Structured logging with conversation correlation
- OpenTelemetry tracing spans
- Consistent error handling and result formatting

Every pipeline stage should extend PipelineStage and implement _run().

Example:
    class MyStage(PipelineStage[InputType, OutputType]):
        name = "my_stage"
        is_critical = False
        timeout_seconds = 30.0
        max_retries = 2

        async def _run(self, context: PipelineContext, input: InputType) -> OutputType:
            # Stage implementation here
            return result
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import structlog
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from nikita.context.logging import log_stage_complete, log_stage_start

if TYPE_CHECKING:
    from nikita.context.pipeline_context import PipelineContext

T = TypeVar("T")  # Stage input type
R = TypeVar("R")  # Stage result type


class StageError(Exception):
    """Exception raised by pipeline stages.

    This exception is used for expected stage failures that should
    be handled by the pipeline orchestrator.
    """

    def __init__(self, stage_name: str, message: str, recoverable: bool = True):
        """Initialize stage error.

        Args:
            stage_name: Name of the stage that failed
            message: Error description
            recoverable: Whether the pipeline should continue (for non-critical stages)
        """
        self.stage_name = stage_name
        self.recoverable = recoverable
        super().__init__(f"[{stage_name}] {message}")


@dataclass
class StageResult(Generic[R]):
    """Unified result from any pipeline stage.

    Attributes:
        success: Whether the stage completed successfully
        data: The stage output (if successful)
        error: Error message (if failed)
        duration_ms: Time taken to execute
        retries: Number of retry attempts made
    """

    success: bool
    data: R | None = None
    error: str | None = None
    duration_ms: float = 0.0
    retries: int = 0

    @classmethod
    def ok(cls, data: R, duration_ms: float = 0.0, retries: int = 0) -> StageResult[R]:
        """Create a successful result."""
        return cls(success=True, data=data, duration_ms=duration_ms, retries=retries)

    @classmethod
    def fail(
        cls, error: str, duration_ms: float = 0.0, retries: int = 0
    ) -> StageResult[R]:
        """Create a failed result."""
        return cls(success=False, error=error, duration_ms=duration_ms, retries=retries)


class PipelineStage(ABC, Generic[T, R]):
    """Base class for all pipeline stages.

    Provides unified infrastructure for:
    - Timeout handling
    - Retry with exponential backoff
    - Structured logging with correlation IDs
    - OpenTelemetry tracing
    - Consistent error handling

    Subclasses must:
    - Set the `name` class attribute
    - Optionally set `is_critical`, `timeout_seconds`, `max_retries`
    - Implement the `_run()` method

    Attributes:
        name: Unique stage identifier (e.g., "extraction", "graph_updates")
        is_critical: If True, failure stops the entire pipeline
        timeout_seconds: Max execution time before timeout
        max_retries: Number of retry attempts on transient failures
    """

    name: str = "unnamed_stage"
    is_critical: bool = False
    timeout_seconds: float = 30.0
    max_retries: int = 3

    def __init__(
        self,
        session: AsyncSession,
        logger: structlog.BoundLogger | None = None,
    ):
        """Initialize the stage.

        Args:
            session: Database session for the stage
            logger: Optional pre-bound logger
        """
        self._session = session
        self._logger = (logger or structlog.get_logger()).bind(stage=self.name)
        self._tracer = trace.get_tracer(__name__)
        self._retry_count = 0

    async def execute(
        self,
        context: PipelineContext,
        input: T,
    ) -> StageResult[R]:
        """Execute the stage with full observability.

        This method wraps _run() with:
        - OpenTelemetry span
        - Timeout handling
        - Retry logic
        - Logging

        Args:
            context: Pipeline context with conversation data
            input: Input data for this stage

        Returns:
            StageResult containing success status and data/error
        """
        span_name = f"stage.{self.name}"

        with self._tracer.start_as_current_span(span_name) as span:
            # Set span attributes
            span.set_attribute("conversation_id", str(context.conversation_id))
            span.set_attribute("user_id", str(context.user_id))
            span.set_attribute("stage.name", self.name)
            span.set_attribute("stage.is_critical", self.is_critical)
            span.set_attribute("stage.timeout_seconds", self.timeout_seconds)

            log_stage_start(self._logger, self.name, self.is_critical)
            start_time = time.perf_counter()

            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    self._execute_with_retry(context, input),
                    timeout=self.timeout_seconds,
                )

                duration_ms = (time.perf_counter() - start_time) * 1000
                span.set_attribute("stage.duration_ms", duration_ms)
                span.set_status(Status(StatusCode.OK))

                log_stage_complete(self._logger, self.name, duration_ms, success=True)

                return StageResult.ok(
                    data=result,
                    duration_ms=duration_ms,
                    retries=self._retry_count,
                )

            except asyncio.TimeoutError:
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_msg = f"Stage {self.name} timed out after {self.timeout_seconds}s"

                span.set_attribute("stage.duration_ms", duration_ms)
                span.set_status(Status(StatusCode.ERROR, error_msg))

                self._logger.error(
                    "stage_timeout",
                    timeout_seconds=self.timeout_seconds,
                    duration_ms=duration_ms,
                )
                log_stage_complete(
                    self._logger, self.name, duration_ms, success=False, error=error_msg
                )

                # Record error in context for non-critical stages
                context.record_stage_error(self.name, error_msg)

                return StageResult.fail(
                    error=error_msg,
                    duration_ms=duration_ms,
                    retries=self._retry_count,
                )

            except StageError as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_msg = str(e)

                span.set_attribute("stage.duration_ms", duration_ms)
                span.set_status(Status(StatusCode.ERROR, error_msg))

                self._logger.error("stage_error", error=error_msg)
                log_stage_complete(
                    self._logger, self.name, duration_ms, success=False, error=error_msg
                )

                # Record error in context for non-critical stages
                context.record_stage_error(self.name, error_msg)

                return StageResult.fail(
                    error=error_msg,
                    duration_ms=duration_ms,
                    retries=self._retry_count,
                )

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_msg = f"Unexpected error in {self.name}: {type(e).__name__}: {e}"

                span.set_attribute("stage.duration_ms", duration_ms)
                span.set_status(Status(StatusCode.ERROR, error_msg))
                span.record_exception(e)

                self._logger.error("stage_failed", error=str(e), exc_info=True)
                log_stage_complete(
                    self._logger, self.name, duration_ms, success=False, error=error_msg
                )

                # Record error in context for non-critical stages
                context.record_stage_error(self.name, error_msg)

                return StageResult.fail(
                    error=error_msg,
                    duration_ms=duration_ms,
                    retries=self._retry_count,
                )

    async def _execute_with_retry(
        self,
        context: PipelineContext,
        input: T,
    ) -> R:
        """Execute with retry logic.

        Uses tenacity for exponential backoff with jitter.

        Args:
            context: Pipeline context
            input: Stage input

        Returns:
            Stage result
        """
        self._retry_count = 0

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential_jitter(initial=1.0, max=30.0),
            retry=retry_if_exception_type((IOError, ConnectionError)),
            reraise=True,
        )
        async def _with_retry() -> R:
            self._retry_count += 1
            if self._retry_count > 1:
                self._logger.warning(
                    "stage_retry",
                    attempt=self._retry_count,
                    max_retries=self.max_retries,
                )
            return await self._run(context, input)

        return await _with_retry()

    @abstractmethod
    async def _run(self, context: PipelineContext, input: T) -> R:
        """Implement stage logic.

        This method should be overridden by subclasses to implement
        the actual stage functionality.

        Args:
            context: Pipeline context with conversation data
            input: Input data for this stage

        Returns:
            Stage-specific output

        Raises:
            StageError: For expected failures
            Exception: For unexpected failures
        """
        ...
