"""E2E tests for the unified pipeline (TX.2).

Tests complete pipeline flows end-to-end using FakeStages with deterministic
behavior. Validates full pipeline execution paths, multi-platform parity,
error cascading, and feature flag behavior.

AC-X.2.1: Full pipeline text flow (9 stages, context propagation)
AC-X.2.2: Full pipeline voice flow (same stages, "voice" platform)
AC-X.2.3: Critical failure early abort (extraction fails → pipeline stops)
AC-X.2.4: Non-critical failure continuation (life_sim fails → pipeline continues)
AC-X.2.5: Mixed critical/non-critical failure handling
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.pipeline.models import PipelineContext, PipelineResult
from nikita.pipeline.orchestrator import PipelineOrchestrator
from nikita.pipeline.stages.base import BaseStage, StageResult

pytestmark = pytest.mark.usefixtures("mock_load_context")


# ── FakeStage implementations ────────────────────────────────────────────

class FakeStage(BaseStage):
    """Configurable fake stage for E2E testing."""

    def __init__(self, name: str, critical: bool = False, fail: bool = False,
                 timeout: bool = False, delay: float = 0, ctx_updates: dict | None = None,
                 session=None):
        self.name = name
        self.is_critical = critical
        self._should_fail = fail
        self._should_timeout = timeout
        self._delay = delay
        self._ctx_updates = ctx_updates or {}
        super().__init__(session=session)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        if self._should_timeout:
            await asyncio.sleep(999)  # Will trigger timeout
        if self._should_fail:
            raise Exception(f"{self.name} failed deliberately")
        # Apply context updates
        for key, value in self._ctx_updates.items():
            setattr(ctx, key, value)
        return {"stage": self.name, "status": "ok"}


def make_pipeline(session, stages_config):
    """Build a PipelineOrchestrator with FakeStages.

    Args:
        session: Mock session
        stages_config: List of tuples (name, is_critical, **kwargs for FakeStage)
    """
    stages = []
    for config in stages_config:
        name = config["name"]
        critical = config.get("critical", False)
        stage = FakeStage(
            name=name,
            critical=critical,
            fail=config.get("fail", False),
            timeout=config.get("timeout", False),
            delay=config.get("delay", 0),
            ctx_updates=config.get("ctx_updates", {}),
            session=session,
        )
        stages.append((name, stage, critical))
    return PipelineOrchestrator(session, stages=stages)


# ── E2E Test: Full Pipeline Flow ─────────────────────────────────────────

class TestFullPipelineE2E:
    """AC-X.2.1/X.2.2: End-to-end full pipeline execution."""

    @pytest.fixture
    def session(self):
        s = MagicMock()
        s.execute = AsyncMock()
        s.commit = AsyncMock()
        s.rollback = AsyncMock()
        return s

    @pytest.fixture
    def all_stages_config(self):
        """9 stages matching real pipeline definition."""
        return [
            {"name": "extraction", "critical": True, "ctx_updates": {
                "extracted_facts": [{"content": "likes cats"}],
                "extraction_summary": "Cat discussion",
            }},
            {"name": "memory_update", "critical": True, "ctx_updates": {
                "facts_stored": 1,
                "facts_deduplicated": 0,
            }},
            {"name": "life_sim", "critical": False, "ctx_updates": {
                "life_events": [{"type": "coffee", "desc": "Had coffee"}],
            }},
            {"name": "emotional", "critical": False, "ctx_updates": {
                "emotional_state": {"arousal": 0.5, "valence": 0.6},
            }},
            {"name": "game_state", "critical": False, "ctx_updates": {
                "score_delta": Decimal("1.5"),
                "chapter_changed": False,
            }},
            {"name": "conflict", "critical": False, "ctx_updates": {
                "active_conflict": False,
            }},
            {"name": "touchpoint", "critical": False, "ctx_updates": {
                "touchpoint_scheduled": False,
            }},
            {"name": "summary", "critical": False, "ctx_updates": {
                "daily_summary_updated": True,
            }},
            {"name": "prompt_builder", "critical": False, "ctx_updates": {
                "generated_prompt": "You are Nikita...",
            }},
        ]

    @pytest.mark.asyncio
    async def test_full_text_pipeline(self, session, all_stages_config):
        """AC-X.2.1: Full 9-stage text pipeline completes successfully."""
        pipeline = make_pipeline(session, all_stages_config)
        result = await pipeline.process(uuid4(), uuid4(), "text")

        assert result.success is True
        assert result.error_stage is None
        assert len(result.context.stage_timings) == 9
        assert result.context.extracted_facts == [{"content": "likes cats"}]
        assert result.context.facts_stored == 1
        assert result.context.daily_summary_updated is True
        assert result.context.generated_prompt == "You are Nikita..."

    @pytest.mark.asyncio
    async def test_full_voice_pipeline(self, session, all_stages_config):
        """AC-X.2.2: Full 9-stage voice pipeline works identically."""
        pipeline = make_pipeline(session, all_stages_config)
        result = await pipeline.process(uuid4(), uuid4(), "voice")

        assert result.success is True
        assert result.context.platform == "voice"
        assert len(result.context.stage_timings) == 9

    @pytest.mark.asyncio
    async def test_context_propagation_across_stages(self, session, all_stages_config):
        """Context data set by earlier stages is available to later stages."""
        pipeline = make_pipeline(session, all_stages_config)
        result = await pipeline.process(uuid4(), uuid4(), "text")

        # All stage updates should be in the final context
        assert result.context.extracted_facts is not None
        assert result.context.emotional_state is not None
        assert result.context.score_delta is not None
        assert result.context.generated_prompt is not None

    @pytest.mark.asyncio
    async def test_stage_timings_recorded(self, session, all_stages_config):
        """Each stage's execution time is recorded."""
        pipeline = make_pipeline(session, all_stages_config)
        result = await pipeline.process(uuid4(), uuid4(), "text")

        for name, ms in result.context.stage_timings.items():
            assert isinstance(ms, float)
            assert ms >= 0

    @pytest.mark.asyncio
    async def test_pipeline_with_user_and_conversation_ids(self, session, all_stages_config):
        """Pipeline correctly propagates conversation_id and user_id."""
        conv_id = uuid4()
        user_id = uuid4()
        pipeline = make_pipeline(session, all_stages_config)
        result = await pipeline.process(conv_id, user_id, "text")

        assert result.context.conversation_id == conv_id
        assert result.context.user_id == user_id


# ── E2E Test: Critical Failure Handling ──────────────────────────────────

class TestCriticalFailureE2E:
    """AC-X.2.3: Critical stage failures abort the pipeline."""

    @pytest.fixture
    def session(self):
        s = MagicMock()
        s.execute = AsyncMock()
        s.commit = AsyncMock()
        s.rollback = AsyncMock()
        return s

    @pytest.mark.asyncio
    async def test_extraction_failure_stops_pipeline(self, session):
        """Critical extraction failure aborts before any other stage runs."""
        config = [
            {"name": "extraction", "critical": True, "fail": True},
            {"name": "memory_update", "critical": True},
            {"name": "life_sim"},
        ]
        pipeline = make_pipeline(session, config)
        result = await pipeline.process(uuid4(), uuid4(), "text")

        assert result.success is False
        assert result.error_stage == "extraction"
        # Only 1 stage timing (the failed one)
        assert len(result.context.stage_timings) == 1

    @pytest.mark.asyncio
    async def test_memory_update_failure_stops_pipeline(self, session):
        """Second critical stage failure aborts after extraction succeeds."""
        config = [
            {"name": "extraction", "critical": True},
            {"name": "memory_update", "critical": True, "fail": True},
            {"name": "life_sim"},
        ]
        pipeline = make_pipeline(session, config)
        result = await pipeline.process(uuid4(), uuid4(), "text")

        assert result.success is False
        assert result.error_stage == "memory_update"
        assert len(result.context.stage_timings) == 2  # extraction + memory_update


# ── E2E Test: Non-Critical Failure Continuation ─────────────────────────

class TestNonCriticalFailureE2E:
    """AC-X.2.4: Non-critical failures logged, pipeline continues."""

    @pytest.fixture
    def session(self):
        s = MagicMock()
        s.execute = AsyncMock()
        s.commit = AsyncMock()
        s.rollback = AsyncMock()
        return s

    @pytest.mark.asyncio
    async def test_life_sim_failure_continues(self, session):
        """Non-critical life_sim failure doesn't stop pipeline."""
        config = [
            {"name": "extraction", "critical": True},
            {"name": "memory_update", "critical": True},
            {"name": "life_sim", "fail": True},
            {"name": "emotional"},
            {"name": "prompt_builder"},
        ]
        pipeline = make_pipeline(session, config)
        result = await pipeline.process(uuid4(), uuid4(), "text")

        assert result.success is True
        assert "life_sim" in result.context.stage_errors
        assert len(result.context.stage_timings) == 5  # All 5 ran

    @pytest.mark.asyncio
    async def test_multiple_non_critical_failures(self, session):
        """Multiple non-critical failures logged, pipeline still succeeds."""
        config = [
            {"name": "extraction", "critical": True},
            {"name": "memory_update", "critical": True},
            {"name": "life_sim", "fail": True},
            {"name": "emotional", "fail": True},
            {"name": "game_state", "fail": True},
            {"name": "prompt_builder"},
        ]
        pipeline = make_pipeline(session, config)
        result = await pipeline.process(uuid4(), uuid4(), "text")

        assert result.success is True
        assert len(result.context.stage_errors) == 3
        assert "life_sim" in result.context.stage_errors
        assert "emotional" in result.context.stage_errors
        assert "game_state" in result.context.stage_errors


# ── E2E Test: Mixed Failure Scenarios ────────────────────────────────────

class TestMixedFailureE2E:
    """AC-X.2.5: Mixed critical and non-critical failure handling."""

    @pytest.fixture
    def session(self):
        s = MagicMock()
        s.execute = AsyncMock()
        s.commit = AsyncMock()
        s.rollback = AsyncMock()
        return s

    @pytest.mark.asyncio
    async def test_non_critical_fails_then_critical_fails(self, session):
        """Non-critical failure followed by critical failure → pipeline fails."""
        config = [
            {"name": "extraction", "critical": True},
            {"name": "life_sim", "fail": True},  # non-critical, continue
            {"name": "memory_update", "critical": True, "fail": True},  # critical, stop
            {"name": "prompt_builder"},
        ]
        pipeline = make_pipeline(session, config)
        result = await pipeline.process(uuid4(), uuid4(), "text")

        assert result.success is False
        assert result.error_stage == "memory_update"
        # life_sim failure should be in stage_errors
        assert "life_sim" in result.context.stage_errors

    @pytest.mark.asyncio
    async def test_all_non_critical_fail_critical_succeed(self, session):
        """All non-critical fail but critical stages succeed → pipeline succeeds."""
        config = [
            {"name": "extraction", "critical": True, "ctx_updates": {"extraction_summary": "ok"}},
            {"name": "memory_update", "critical": True, "ctx_updates": {"facts_stored": 1}},
            {"name": "life_sim", "fail": True},
            {"name": "emotional", "fail": True},
            {"name": "game_state", "fail": True},
            {"name": "conflict", "fail": True},
            {"name": "touchpoint", "fail": True},
            {"name": "summary", "fail": True},
            {"name": "prompt_builder", "fail": True},
        ]
        pipeline = make_pipeline(session, config)
        result = await pipeline.process(uuid4(), uuid4(), "text")

        assert result.success is True
        assert len(result.context.stage_errors) == 7  # 7 non-critical failed
        assert result.context.extraction_summary == "ok"  # Critical data preserved


# ── E2E Test: Empty Pipeline ─────────────────────────────────────────────

class TestEmptyPipelineE2E:
    """Edge cases: empty or minimal pipelines."""

    @pytest.fixture
    def session(self):
        s = MagicMock()
        s.execute = AsyncMock()
        s.commit = AsyncMock()
        s.rollback = AsyncMock()
        return s

    @pytest.mark.asyncio
    async def test_empty_pipeline(self, session):
        """Pipeline with no stages succeeds immediately."""
        pipeline = PipelineOrchestrator(session, stages=[])
        result = await pipeline.process(uuid4(), uuid4(), "text")

        assert result.success is True
        assert len(result.context.stage_timings) == 0

    @pytest.mark.asyncio
    async def test_single_stage_pipeline(self, session):
        """Pipeline with one stage works."""
        config = [{"name": "extraction", "critical": True}]
        pipeline = make_pipeline(session, config)
        result = await pipeline.process(uuid4(), uuid4(), "text")

        assert result.success is True
        assert len(result.context.stage_timings) == 1


# ── E2E Test: Stage Timeout Handling ─────────────────────────────────────

class TestTimeoutE2E:
    """Timeout handling in E2E scenarios."""

    @pytest.fixture
    def session(self):
        s = MagicMock()
        s.execute = AsyncMock()
        s.commit = AsyncMock()
        s.rollback = AsyncMock()
        return s

    @pytest.mark.asyncio
    async def test_non_critical_timeout_continues(self, session):
        """Non-critical stage timeout doesn't stop pipeline."""
        # Create stage with very short timeout
        stage = FakeStage("life_sim", critical=False, delay=0.5, session=session)
        stage.timeout_seconds = 0.1  # Will timeout

        stages = [
            ("extraction", FakeStage("extraction", critical=True, session=session), True),
            ("life_sim", stage, False),
            ("prompt_builder", FakeStage("prompt_builder", session=session), False),
        ]
        pipeline = PipelineOrchestrator(session, stages=stages)
        result = await pipeline.process(uuid4(), uuid4(), "text")

        assert result.success is True
        assert "life_sim" in result.context.stage_errors

    @pytest.mark.asyncio
    async def test_critical_timeout_stops_pipeline(self, session):
        """Critical stage timeout aborts pipeline."""
        stage = FakeStage("extraction", critical=True, delay=0.5, session=session)
        stage.timeout_seconds = 0.1

        stages = [
            ("extraction", stage, True),
            ("prompt_builder", FakeStage("prompt_builder", session=session), False),
        ]
        pipeline = PipelineOrchestrator(session, stages=stages)
        result = await pipeline.process(uuid4(), uuid4(), "text")

        assert result.success is False
        assert result.error_stage == "extraction"
