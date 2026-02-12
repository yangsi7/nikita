"""Tests for PipelineOrchestrator (T2.2).

AC-2.2.1: process(conversation_id, session) runs 9 stages sequentially
AC-2.2.2: Critical stage failure stops pipeline, returns PipelineResult with error
AC-2.2.3: Non-critical stage failure logs error, continues to next stage
AC-2.2.4: Per-stage timing logged in PipelineContext.stage_timings
AC-2.2.5: Job execution logged in job_executions table
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.pipeline.stages.base import StageResult
from nikita.pipeline.models import PipelineContext, PipelineResult
from nikita.pipeline.orchestrator import PipelineOrchestrator


class FakeStage:
    """Fake stage for testing the orchestrator."""

    def __init__(
        self,
        name: str = "fake",
        success: bool = True,
        error: str | None = None,
        raise_error: Exception | None = None,
        delay: float = 0.0,
    ):
        self.name = name
        self._success = success
        self._error = error
        self._raise_error = raise_error
        self._delay = delay
        self.execute_called = False

    async def execute(self, context: PipelineContext):
        self.execute_called = True
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        if self._raise_error:
            raise self._raise_error
        if self._success:
            return StageResult.ok(data={"stage": self.name}, duration_ms=10.0)
        return StageResult.fail(error=self._error or "stage failed", duration_ms=5.0)


class FlakyStage(FakeStage):
    """Stage that fails N times then succeeds."""

    def __init__(
        self,
        name: str = "flaky",
        failures_before_success: int = 1,
        error: str = "transient error",
        raise_on_fail: bool = False,
    ):
        super().__init__(name=name)
        self._failures_left = failures_before_success
        self._error = error
        self._raise_on_fail = raise_on_fail
        self.call_count = 0

    async def execute(self, context: PipelineContext):
        self.call_count += 1
        self.execute_called = True
        if self._failures_left > 0:
            self._failures_left -= 1
            if self._raise_on_fail:
                raise RuntimeError(self._error)
            return StageResult.fail(error=self._error, duration_ms=5.0)
        return StageResult.ok(data={"stage": self.name}, duration_ms=10.0)


def _make_orchestrator(stages: list[tuple[str, FakeStage, bool]]) -> PipelineOrchestrator:
    """Create orchestrator with injected fake stages."""
    session = MagicMock()
    return PipelineOrchestrator(session=session, stages=stages)


@pytest.mark.asyncio
class TestPipelineOrchestratorHappyPath:

    async def test_all_stages_succeed(self):
        """AC-2.2.1: Runs stages sequentially, all succeed."""
        stages = [
            ("extraction", FakeStage("extraction"), True),
            ("memory_update", FakeStage("memory_update"), True),
            ("life_sim", FakeStage("life_sim"), False),
        ]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4(), "text")

        assert result.success is True
        assert result.stages_completed == 3
        assert "extraction" in result.context.stage_timings
        assert "memory_update" in result.context.stage_timings
        assert "life_sim" in result.context.stage_timings

    async def test_all_stages_called_in_order(self):
        """AC-2.2.1: Stages execute in declared order."""
        call_order = []

        class OrderedStage(FakeStage):
            async def execute(self, context):
                call_order.append(self.name)
                return StageResult.ok(data={}, duration_ms=1.0)

        stages = [
            ("first", OrderedStage("first"), True),
            ("second", OrderedStage("second"), False),
            ("third", OrderedStage("third"), False),
        ]
        orch = _make_orchestrator(stages)
        await orch.process(uuid4(), uuid4())

        assert call_order == ["first", "second", "third"]

    async def test_platform_passed_to_context(self):
        """Context receives the platform parameter."""
        stages = [("s1", FakeStage("s1"), False)]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4(), "voice")
        assert result.context.platform == "voice"


@pytest.mark.asyncio
class TestPipelineOrchestratorCriticalFailure:

    async def test_critical_stage_failure_stops_pipeline(self):
        """AC-2.2.2: Critical stage failure stops pipeline."""
        stages = [
            ("extraction", FakeStage("extraction", success=False, error="LLM timeout"), True),
            ("memory_update", FakeStage("memory_update"), True),
        ]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4())

        assert result.success is False
        assert result.error_stage == "extraction"
        assert result.error_message == "LLM timeout"
        # memory_update should NOT have been called
        assert not stages[1][1].execute_called
        assert result.stages_completed == 1

    async def test_critical_stage_exception_stops_pipeline(self):
        """AC-2.2.2: Unhandled exception in critical stage stops pipeline."""
        stages = [
            ("extraction", FakeStage("extraction", raise_error=RuntimeError("boom")), True),
            ("memory_update", FakeStage("memory_update"), True),
        ]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4())

        assert result.success is False
        assert result.error_stage == "extraction"
        assert "RuntimeError: boom" in result.error_message
        assert not stages[1][1].execute_called


@pytest.mark.asyncio
class TestPipelineOrchestratorNonCriticalFailure:

    async def test_non_critical_failure_continues(self):
        """AC-2.2.3: Non-critical stage failure logs error, continues."""
        stages = [
            ("extraction", FakeStage("extraction"), True),
            ("life_sim", FakeStage("life_sim", success=False, error="event gen failed"), False),
            ("emotional", FakeStage("emotional"), False),
        ]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4())

        assert result.success is True
        assert result.stages_completed == 3
        assert result.context.stage_errors["life_sim"] == "event gen failed"
        assert stages[2][1].execute_called

    async def test_non_critical_exception_continues(self):
        """AC-2.2.3: Unhandled exception in non-critical stage continues."""
        stages = [
            ("extraction", FakeStage("extraction"), True),
            ("life_sim", FakeStage("life_sim", raise_error=ValueError("bad data")), False),
            ("emotional", FakeStage("emotional"), False),
        ]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4())

        assert result.success is True
        assert "life_sim" in result.context.stage_errors
        assert stages[2][1].execute_called

    async def test_multiple_non_critical_failures(self):
        """Multiple non-critical failures are all recorded."""
        stages = [
            ("extraction", FakeStage("extraction"), True),
            ("life_sim", FakeStage("life_sim", success=False, error="fail1"), False),
            ("emotional", FakeStage("emotional", success=False, error="fail2"), False),
            ("summary", FakeStage("summary"), False),
        ]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4())

        assert result.success is True
        assert len(result.context.stage_errors) == 2
        assert result.stages_completed == 4


@pytest.mark.asyncio
class TestPipelineOrchestratorTiming:

    async def test_per_stage_timing_recorded(self):
        """AC-2.2.4: Per-stage timing logged in stage_timings."""
        stages = [
            ("fast", FakeStage("fast"), False),
            ("slow", FakeStage("slow", delay=0.05), False),
        ]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4())

        assert "fast" in result.context.stage_timings
        assert "slow" in result.context.stage_timings
        # Slow stage should take at least 40ms
        assert result.context.stage_timings["slow"] >= 40.0

    async def test_total_duration_calculated(self):
        """Total duration is sum of stage timings."""
        stages = [
            ("s1", FakeStage("s1"), False),
            ("s2", FakeStage("s2"), False),
        ]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4())

        assert result.total_duration_ms > 0
        assert result.total_duration_ms == result.context.total_duration_ms


@pytest.mark.asyncio
class TestPipelineOrchestratorRetry:
    """Tests for single-retry on non-critical stages."""

    async def test_non_critical_retries_on_result_failure_then_succeeds(self):
        """Non-critical stage: fail once (StageResult), succeed on retry."""
        flaky = FlakyStage("life_sim", failures_before_success=1, error="transient")
        stages = [
            ("extraction", FakeStage("extraction"), True),
            ("life_sim", flaky, False),
            ("summary", FakeStage("summary"), False),
        ]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4())

        assert result.success is True
        assert flaky.call_count == 2  # 1 fail + 1 success
        assert "life_sim" not in result.context.stage_errors
        assert stages[2][1].execute_called

    async def test_non_critical_retries_on_exception_then_succeeds(self):
        """Non-critical stage: raise exception once, succeed on retry."""
        flaky = FlakyStage(
            "emotional", failures_before_success=1, error="db timeout", raise_on_fail=True,
        )
        stages = [
            ("extraction", FakeStage("extraction"), True),
            ("emotional", flaky, False),
        ]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4())

        assert result.success is True
        assert flaky.call_count == 2
        assert "emotional" not in result.context.stage_errors

    async def test_non_critical_fails_both_attempts(self):
        """Non-critical stage: fail twice, error recorded, pipeline continues."""
        flaky = FlakyStage("life_sim", failures_before_success=99, error="permanent")
        stages = [
            ("extraction", FakeStage("extraction"), True),
            ("life_sim", flaky, False),
            ("summary", FakeStage("summary"), False),
        ]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4())

        assert result.success is True
        assert flaky.call_count == 2  # Tried twice
        assert "life_sim" in result.context.stage_errors
        assert stages[2][1].execute_called  # Pipeline continued

    async def test_critical_stage_does_not_retry(self):
        """Critical stage: fails once, pipeline stops immediately (no retry)."""
        flaky = FlakyStage("extraction", failures_before_success=1, error="critical fail")
        stages = [
            ("extraction", flaky, True),
            ("memory_update", FakeStage("memory_update"), True),
        ]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4())

        assert result.success is False
        assert flaky.call_count == 1  # No retry for critical
        assert result.error_stage == "extraction"
        assert not stages[1][1].execute_called

    async def test_critical_exception_does_not_retry(self):
        """Critical stage: exception once, pipeline stops (no retry)."""
        flaky = FlakyStage(
            "extraction", failures_before_success=1, error="boom", raise_on_fail=True,
        )
        stages = [
            ("extraction", flaky, True),
            ("memory_update", FakeStage("memory_update"), True),
        ]
        orch = _make_orchestrator(stages)
        result = await orch.process(uuid4(), uuid4())

        assert result.success is False
        assert flaky.call_count == 1
        assert result.error_stage == "extraction"
