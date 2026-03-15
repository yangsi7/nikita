"""Extraction checkpoint failure injection tests (devil's advocate gap).

Verifies that the PipelineOrchestrator correctly handles critical vs non-critical
stage failures by injecting mock stages with controlled outcomes:

- Non-critical stage failure: logged, pipeline continues
- Critical stage failure: pipeline stops immediately

Uses PipelineOrchestrator(session, stages=[(name, instance, is_critical), ...])
injection pattern from Spec 116 tests.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from nikita.pipeline.orchestrator import PipelineOrchestrator
from nikita.pipeline.stages.base import BaseStage


# ── Fake stages ──────────────────────────────────────────────────────────────


class FakeSuccessStage(BaseStage):
    """Stage that always succeeds."""

    name = "fake_success"
    is_critical = False
    timeout_seconds = 5.0

    def __init__(self, *, track: list | None = None, **kwargs):
        super().__init__(**kwargs)
        self._track = track

    async def _run(self, ctx):
        if self._track is not None:
            self._track.append(self.name)
        return {"status": "ok"}


class FakeFailStage(BaseStage):
    """Stage that always raises an exception."""

    name = "fake_fail"
    is_critical = True
    timeout_seconds = 5.0

    def __init__(self, *, track: list | None = None, error_msg: str = "boom", **kwargs):
        super().__init__(**kwargs)
        self._track = track
        self._error_msg = error_msg

    async def _run(self, ctx):
        if self._track is not None:
            self._track.append(self.name)
        raise RuntimeError(self._error_msg)


# ── Tests ────────────────────────────────────────────────────────────────────


class TestCriticalStageFailureStopsPipeline:
    """Verify that a critical stage failure halts the pipeline."""

    @pytest.mark.asyncio
    async def test_critical_failure_stops_pipeline(self, mock_session):
        """Pipeline stops when a critical stage fails.

        Setup:
            persistence (non-critical, succeeds) -> memory_update (critical, FAILS)
        Expectations:
            - persistence recorded as succeeded
            - memory_update recorded as failed
            - pipeline result is failed with error_stage="memory_update"
        """
        execution_order = []

        persistence = FakeSuccessStage(
            track=execution_order, session=mock_session,
        )
        persistence.name = "persistence"

        memory_update = FakeFailStage(
            track=execution_order, session=mock_session, error_msg="OpenAI outage",
        )
        memory_update.name = "memory_update"

        stages = [
            ("persistence", persistence, False),       # non-critical, succeeds
            ("memory_update", memory_update, True),     # critical, fails
        ]

        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)
        result = await orchestrator.process(uuid4(), uuid4(), "text")

        # Both stages executed in order
        assert execution_order == ["persistence", "memory_update"]

        # Pipeline failed at critical stage
        assert result.success is False
        assert result.error_stage == "memory_update"
        assert "OpenAI outage" in (result.error_message or "")

        # persistence was recorded as succeeded
        assert "persistence" in result.context.stage_results
        assert result.context.stage_results["persistence"]["success"] is True

        # memory_update was recorded as failed
        assert "memory_update" in result.context.stage_results
        assert result.context.stage_results["memory_update"]["success"] is False

    @pytest.mark.asyncio
    async def test_stages_after_critical_failure_do_not_run(self, mock_session):
        """Stages after a critical failure are never executed."""
        execution_order = []

        extraction = FakeSuccessStage(track=execution_order, session=mock_session)
        extraction.name = "extraction"

        memory_update = FakeFailStage(
            track=execution_order, session=mock_session, error_msg="DB down",
        )
        memory_update.name = "memory_update"

        life_sim = FakeSuccessStage(track=execution_order, session=mock_session)
        life_sim.name = "life_sim"

        stages = [
            ("extraction", extraction, True),           # critical, succeeds
            ("memory_update", memory_update, True),     # critical, FAILS
            ("life_sim", life_sim, False),               # should NOT run
        ]

        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)
        result = await orchestrator.process(uuid4(), uuid4(), "text")

        assert result.success is False
        assert result.error_stage == "memory_update"
        # life_sim never ran
        assert "life_sim" not in execution_order
        assert "life_sim" not in result.context.stage_results


class TestNonCriticalFailureContinues:
    """Verify that a non-critical stage failure does NOT stop the pipeline."""

    @pytest.mark.asyncio
    async def test_non_critical_failure_continues(self, mock_session):
        """Pipeline continues past a non-critical stage failure.

        Setup:
            persistence (non-critical, FAILS) -> game_state (non-critical, succeeds)
        Expectations:
            - persistence error recorded in stage_errors
            - game_state still runs and succeeds
            - pipeline result is success (no critical failures)
        """
        execution_order = []

        persistence = FakeFailStage(
            track=execution_order, session=mock_session, error_msg="write failed",
        )
        persistence.name = "persistence"

        game_state = FakeSuccessStage(track=execution_order, session=mock_session)
        game_state.name = "game_state"

        stages = [
            ("persistence", persistence, False),    # non-critical, FAILS
            ("game_state", game_state, False),      # non-critical, succeeds
        ]

        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)
        result = await orchestrator.process(uuid4(), uuid4(), "text")

        # Pipeline succeeded overall (no critical failures)
        assert result.success is True

        # Both stages executed (non-critical gets 1 retry, so persistence runs twice)
        assert execution_order == ["persistence", "persistence", "game_state"]

        # persistence error was recorded
        assert "persistence" in result.context.stage_errors

        # game_state succeeded
        assert "game_state" in result.context.stage_results
        assert result.context.stage_results["game_state"]["success"] is True
