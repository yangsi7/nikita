"""Full integration tests for unified pipeline (Spec 042 T4.6).

These tests verify the orchestrator's ability to run multi-stage pipelines,
handle critical vs non-critical failures, record timings, and propagate context.

All tests use fake stages (no real DB/LLM calls) to ensure fast, deterministic results.
"""
import asyncio
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from nikita.pipeline.orchestrator import PipelineOrchestrator
from nikita.pipeline.models import PipelineContext, PipelineResult
from nikita.pipeline.stages.base import BaseStage, StageResult


# ============================================================================
# Fake Stage Implementations (Deterministic, No External Calls)
# ============================================================================


class FakeOkStage(BaseStage):
    """Stage that always succeeds."""
    name = "fake_ok"
    is_critical = False
    timeout_seconds = 5.0

    async def _run(self, ctx):
        return {"status": "ok"}


class FakeCriticalOkStage(BaseStage):
    """Critical stage that always succeeds."""
    name = "fake_critical"
    is_critical = True
    timeout_seconds = 5.0

    async def _run(self, ctx):
        return {"status": "ok"}


class FakeFailStage(BaseStage):
    """Non-critical stage that always fails."""
    name = "fake_fail"
    is_critical = False
    timeout_seconds = 5.0

    async def _run(self, ctx):
        raise Exception("Stage failed")


class FakeCriticalFailStage(BaseStage):
    """Critical stage that always fails."""
    name = "fake_critical_fail"
    is_critical = True
    timeout_seconds = 5.0

    async def _run(self, ctx):
        raise Exception("Critical failure")


class FakeContextSetStage(BaseStage):
    """Stage that writes to context."""
    name = "fake_context_set"
    is_critical = False
    timeout_seconds = 5.0

    async def _run(self, ctx):
        ctx.extracted_facts = [{"content": "test fact"}]
        return {"facts_written": 1}


class FakeContextReadStage(BaseStage):
    """Stage that reads from context."""
    name = "fake_context_read"
    is_critical = False
    timeout_seconds = 5.0

    async def _run(self, ctx):
        facts_count = len(ctx.extracted_facts)
        return {"facts_read": facts_count}


class FakeSlowStage(BaseStage):
    """Stage that sleeps longer than timeout."""
    name = "fake_slow"
    is_critical = False
    timeout_seconds = 0.1  # 100ms timeout

    async def _run(self, ctx):
        await asyncio.sleep(0.5)  # Sleep 500ms (exceeds timeout)
        return {"status": "should_never_reach"}


# ============================================================================
# Integration Tests
# ============================================================================


class TestFullPipelineIntegration:
    """Integration tests for the pipeline orchestrator."""

    @pytest.mark.asyncio
    async def test_full_pipeline_all_stages_succeed(self, mock_session):
        """AC: All 9 fake stages pass, result.success is True."""
        # Arrange: 9 non-critical OK stages
        stages = [
            ("stage_1", FakeOkStage(session=mock_session), False),
            ("stage_2", FakeOkStage(session=mock_session), False),
            ("stage_3", FakeOkStage(session=mock_session), False),
            ("stage_4", FakeOkStage(session=mock_session), False),
            ("stage_5", FakeOkStage(session=mock_session), False),
            ("stage_6", FakeOkStage(session=mock_session), False),
            ("stage_7", FakeOkStage(session=mock_session), False),
            ("stage_8", FakeOkStage(session=mock_session), False),
            ("stage_9", FakeOkStage(session=mock_session), False),
        ]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        # Act
        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="text",
        )

        # Assert
        assert result.success is True
        assert result.error_stage is None
        assert result.error_message is None
        assert result.stages_completed == 9
        assert len(result.context.stage_timings) == 9
        assert len(result.context.stage_errors) == 0

    @pytest.mark.asyncio
    async def test_pipeline_critical_stage_failure_stops(self, mock_session):
        """AC: Critical stage fails, pipeline stops."""
        # Arrange: 3 stages, middle one is critical and fails
        stages = [
            ("stage_1", FakeOkStage(session=mock_session), False),
            ("stage_2", FakeCriticalFailStage(session=mock_session), True),
            ("stage_3", FakeOkStage(session=mock_session), False),  # Should not run
        ]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        # Act
        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="text",
        )

        # Assert
        assert result.success is False
        assert result.error_stage == "stage_2"
        assert "Critical failure" in result.error_message
        assert result.stages_completed == 2  # stage_1 + stage_2
        assert len(result.context.stage_timings) == 2

    @pytest.mark.asyncio
    async def test_pipeline_non_critical_failure_continues(self, mock_session):
        """AC: Non-critical fails, pipeline continues."""
        # Arrange: 3 stages, middle one is non-critical and fails
        stages = [
            ("stage_1", FakeOkStage(session=mock_session), False),
            ("stage_2", FakeFailStage(session=mock_session), False),  # Fails but not critical
            ("stage_3", FakeOkStage(session=mock_session), False),
        ]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        # Act
        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="text",
        )

        # Assert
        assert result.success is True  # Pipeline succeeded overall
        assert result.stages_completed == 3  # All 3 ran
        assert len(result.context.stage_timings) == 3
        assert "stage_2" in result.context.stage_errors
        assert "Stage failed" in result.context.stage_errors["stage_2"]

    @pytest.mark.asyncio
    async def test_pipeline_context_flows_through_stages(self, mock_session):
        """AC: Stage A sets ctx field, Stage B reads it."""
        # Arrange: 2 stages, first writes, second reads
        stages = [
            ("write_stage", FakeContextSetStage(session=mock_session), False),
            ("read_stage", FakeContextReadStage(session=mock_session), False),
        ]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        # Act
        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="text",
        )

        # Assert
        assert result.success is True
        # Verify context was written and read
        assert len(result.context.extracted_facts) == 1
        assert result.context.extracted_facts[0]["content"] == "test fact"

    @pytest.mark.asyncio
    async def test_pipeline_records_all_timings(self, mock_session):
        """AC: All stage timings in result."""
        # Arrange: 5 stages
        stages = [
            ("stage_1", FakeOkStage(session=mock_session), False),
            ("stage_2", FakeOkStage(session=mock_session), False),
            ("stage_3", FakeOkStage(session=mock_session), False),
            ("stage_4", FakeOkStage(session=mock_session), False),
            ("stage_5", FakeOkStage(session=mock_session), False),
        ]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        # Act
        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="text",
        )

        # Assert
        assert result.success is True
        assert len(result.context.stage_timings) == 5
        for stage_name in ["stage_1", "stage_2", "stage_3", "stage_4", "stage_5"]:
            assert stage_name in result.context.stage_timings
            assert result.context.stage_timings[stage_name] > 0  # Some duration recorded

    @pytest.mark.asyncio
    async def test_pipeline_records_errors(self, mock_session):
        """AC: Non-critical errors recorded in stage_errors."""
        # Arrange: 4 stages, 2 fail (non-critical)
        stages = [
            ("stage_1", FakeOkStage(session=mock_session), False),
            ("stage_2", FakeFailStage(session=mock_session), False),
            ("stage_3", FakeOkStage(session=mock_session), False),
            ("stage_4", FakeFailStage(session=mock_session), False),
        ]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        # Act
        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="text",
        )

        # Assert
        assert result.success is True
        assert len(result.context.stage_errors) == 2
        assert "stage_2" in result.context.stage_errors
        assert "stage_4" in result.context.stage_errors

    @pytest.mark.asyncio
    async def test_pipeline_text_platform(self, mock_session):
        """AC: Platform 'text' passed correctly."""
        # Arrange
        stages = [("stage_1", FakeOkStage(session=mock_session), False)]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        # Act
        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="text",
        )

        # Assert
        assert result.success is True
        assert result.context.platform == "text"

    @pytest.mark.asyncio
    async def test_pipeline_voice_platform(self, mock_session):
        """AC: Platform 'voice' passed correctly."""
        # Arrange
        stages = [("stage_1", FakeOkStage(session=mock_session), False)]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        # Act
        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="voice",
        )

        # Assert
        assert result.success is True
        assert result.context.platform == "voice"

    @pytest.mark.asyncio
    async def test_pipeline_result_has_context(self, mock_session):
        """AC: PipelineResult.context has full PipelineContext."""
        # Arrange
        stages = [("stage_1", FakeOkStage(session=mock_session), False)]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        # Act
        conversation_id = uuid4()
        user_id = uuid4()
        result = await orchestrator.process(
            conversation_id=conversation_id,
            user_id=user_id,
            platform="text",
        )

        # Assert
        assert isinstance(result.context, PipelineContext)
        assert result.context.conversation_id == conversation_id
        assert result.context.user_id == user_id
        assert result.context.platform == "text"
        assert isinstance(result.context.started_at, datetime)

    @pytest.mark.asyncio
    async def test_pipeline_empty_stages(self, mock_session):
        """AC: Empty stages list returns success."""
        # Arrange: No stages
        orchestrator = PipelineOrchestrator(session=mock_session, stages=[])

        # Act
        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="text",
        )

        # Assert
        assert result.success is True
        assert result.stages_completed == 0
        assert len(result.context.stage_timings) == 0

    @pytest.mark.asyncio
    async def test_pipeline_single_critical_stage(self, mock_session):
        """AC: One critical stage, passes."""
        # Arrange
        stages = [("critical", FakeCriticalOkStage(session=mock_session), True)]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        # Act
        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="text",
        )

        # Assert
        assert result.success is True
        assert result.stages_completed == 1

    @pytest.mark.asyncio
    async def test_pipeline_stage_timeout(self, mock_session):
        """AC: Stage that sleeps too long times out."""
        # Arrange: Slow stage with 100ms timeout, sleeps 500ms
        stages = [("slow", FakeSlowStage(session=mock_session), False)]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        # Act
        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="text",
        )

        # Assert
        # Non-critical timeout continues pipeline
        assert result.success is True
        assert "slow" in result.context.stage_errors
        assert "timed out" in result.context.stage_errors["slow"]

    @pytest.mark.asyncio
    async def test_pipeline_concurrent_safety(self, mock_session):
        """AC: Two pipeline runs don't interfere (separate sessions)."""
        # Arrange: Same orchestrator, different calls
        stages = [("stage_1", FakeOkStage(session=mock_session), False)]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        conv_1 = uuid4()
        conv_2 = uuid4()
        user_1 = uuid4()
        user_2 = uuid4()

        # Act: Run 2 pipelines concurrently
        result_1, result_2 = await asyncio.gather(
            orchestrator.process(conv_1, user_1, "text"),
            orchestrator.process(conv_2, user_2, "voice"),
        )

        # Assert: Each result has correct IDs
        assert result_1.context.conversation_id == conv_1
        assert result_1.context.user_id == user_1
        assert result_1.context.platform == "text"

        assert result_2.context.conversation_id == conv_2
        assert result_2.context.user_id == user_2
        assert result_2.context.platform == "voice"

    @pytest.mark.asyncio
    async def test_pipeline_context_initialized_correctly(self, mock_session):
        """AC: Verify ctx fields after construction."""
        # Arrange
        stages = [("stage_1", FakeOkStage(session=mock_session), False)]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        # Act
        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="text",
        )

        # Assert: Check default values
        ctx = result.context
        assert ctx.chapter == 1
        assert ctx.game_status == "active"
        assert ctx.relationship_score == Decimal("50")
        assert ctx.extracted_facts == []
        assert ctx.facts_stored == 0
        assert ctx.score_delta == Decimal("0")
        assert ctx.active_conflict is False

    @pytest.mark.asyncio
    async def test_pipeline_result_succeeded_factory(self, mock_session):
        """AC: PipelineResult.succeeded() has correct fields."""
        # Arrange
        stages = [("stage_1", FakeOkStage(session=mock_session), False)]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)

        # Act
        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="text",
        )

        # Assert: Verify factory method fields
        assert result.success is True
        assert result.error_stage is None
        assert result.error_message is None
        assert result.total_duration_ms > 0
        assert result.stages_completed == 1
        assert result.stages_total == 10  # Default in PipelineResult
