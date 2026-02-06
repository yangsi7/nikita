"""Tests for pipeline models (T2.1).

AC-2.1.1: PipelineContext holds conversation, user, metrics, vices, engagement, stage results, timing
AC-2.1.2: PipelineResult holds success/failure, context, error info, total duration
AC-2.1.3: StageResult holds success, data dict, errors list, duration_ms (tested via import)
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from nikita.pipeline.models import PipelineContext, PipelineResult


def _make_ctx(**kwargs) -> PipelineContext:
    defaults = dict(
        conversation_id=uuid4(),
        user_id=uuid4(),
        started_at=datetime.now(timezone.utc),
        platform="text",
    )
    defaults.update(kwargs)
    return PipelineContext(**defaults)


class TestPipelineContext:
    """AC-2.1.1: PipelineContext holds conversation, user, metrics, vices,
    engagement, stage results, timing."""

    def test_create_minimal(self):
        ctx = _make_ctx()
        assert ctx.platform == "text"
        assert ctx.chapter == 1
        assert ctx.game_status == "active"
        assert ctx.relationship_score == Decimal("50")

    def test_create_voice_platform(self):
        ctx = _make_ctx(platform="voice")
        assert ctx.platform == "voice"

    def test_defaults_empty_collections(self):
        ctx = _make_ctx()
        assert ctx.metrics == {}
        assert ctx.vices == []
        assert ctx.extracted_facts == []
        assert ctx.life_events == []
        assert ctx.emotional_state == {}
        assert ctx.score_events == []
        assert ctx.stage_timings == {}
        assert ctx.stage_errors == {}

    def test_defaults_zero_values(self):
        ctx = _make_ctx()
        assert ctx.facts_stored == 0
        assert ctx.facts_deduplicated == 0
        assert ctx.score_delta == Decimal("0")
        assert ctx.chapter_changed is False
        assert ctx.decay_applied is False
        assert ctx.active_conflict is False
        assert ctx.touchpoint_scheduled is False
        assert ctx.daily_summary_updated is False
        assert ctx.prompt_token_count == 0

    def test_record_stage_error(self):
        ctx = _make_ctx()
        assert not ctx.has_stage_errors()
        ctx.record_stage_error("extraction", "LLM timeout")
        assert ctx.has_stage_errors()
        assert ctx.stage_errors["extraction"] == "LLM timeout"

    def test_record_multiple_errors(self):
        ctx = _make_ctx()
        ctx.record_stage_error("extraction", "timeout")
        ctx.record_stage_error("life_sim", "event gen failed")
        assert len(ctx.stage_errors) == 2

    def test_record_stage_timing(self):
        ctx = _make_ctx()
        ctx.record_stage_timing("extraction", 1500.0)
        ctx.record_stage_timing("memory_update", 200.0)
        assert ctx.stage_timings["extraction"] == 1500.0
        assert ctx.stage_timings["memory_update"] == 200.0

    def test_total_duration_ms(self):
        ctx = _make_ctx()
        ctx.record_stage_timing("extraction", 1500.0)
        ctx.record_stage_timing("memory_update", 200.0)
        ctx.record_stage_timing("summary", 300.0)
        assert ctx.total_duration_ms == 2000.0

    def test_total_duration_empty(self):
        ctx = _make_ctx()
        assert ctx.total_duration_ms == 0.0

    def test_extraction_fields(self):
        ctx = _make_ctx()
        ctx.extracted_facts = [{"type": "fact", "content": "User likes cats"}]
        ctx.extraction_summary = "Brief chat about pets"
        ctx.emotional_tone = "positive"
        assert len(ctx.extracted_facts) == 1
        assert ctx.extraction_summary == "Brief chat about pets"
        assert ctx.emotional_tone == "positive"

    def test_game_state_fields(self):
        ctx = _make_ctx()
        ctx.score_delta = Decimal("3.5")
        ctx.chapter_changed = True
        ctx.score_events = ["boss_triggered"]
        assert ctx.score_delta == Decimal("3.5")
        assert ctx.chapter_changed is True
        assert ctx.score_events == ["boss_triggered"]

    def test_user_state_fields(self):
        ctx = _make_ctx()
        ctx.metrics = {"intimacy": Decimal("60"), "trust": Decimal("70")}
        ctx.vices = ["jealousy", "possessiveness"]
        ctx.engagement_state = "IN_ZONE"
        ctx.chapter = 3
        ctx.game_status = "boss_fight"
        ctx.relationship_score = Decimal("72.5")
        assert ctx.metrics["intimacy"] == Decimal("60")
        assert len(ctx.vices) == 2
        assert ctx.engagement_state == "IN_ZONE"
        assert ctx.chapter == 3

    def test_mutable_defaults_isolation(self):
        """Each instance gets its own mutable containers."""
        ctx1 = _make_ctx()
        ctx2 = _make_ctx()
        ctx1.extracted_facts.append({"fact": "test"})
        ctx1.stage_timings["x"] = 100.0
        assert len(ctx2.extracted_facts) == 0
        assert len(ctx2.stage_timings) == 0


class TestPipelineResult:
    """AC-2.1.2: PipelineResult holds success/failure, context, error info,
    total duration."""

    def test_succeeded(self):
        ctx = _make_ctx()
        ctx.record_stage_timing("extraction", 1000.0)
        ctx.record_stage_timing("memory_update", 200.0)
        result = PipelineResult.succeeded(ctx)
        assert result.success is True
        assert result.error_stage is None
        assert result.error_message is None
        assert result.stages_completed == 2
        assert result.total_duration_ms == 1200.0

    def test_failed(self):
        ctx = _make_ctx()
        ctx.record_stage_timing("extraction", 500.0)
        result = PipelineResult.failed(ctx, "memory_update", "DB connection lost")
        assert result.success is False
        assert result.error_stage == "memory_update"
        assert result.error_message == "DB connection lost"
        assert result.stages_completed == 1

    def test_stages_total_default(self):
        ctx = _make_ctx()
        result = PipelineResult.succeeded(ctx)
        assert result.stages_total == 9

    def test_context_preserved(self):
        ctx = _make_ctx()
        ctx.extracted_facts = [{"fact": "test"}]
        result = PipelineResult.succeeded(ctx)
        assert result.context is ctx
        assert len(result.context.extracted_facts) == 1

    def test_failed_zero_stages(self):
        ctx = _make_ctx()
        result = PipelineResult.failed(ctx, "extraction", "immediate failure")
        assert result.stages_completed == 0
        assert result.total_duration_ms == 0.0


class TestStageResultImport:
    """AC-2.1.3: StageResult exists in pipeline.stages.base."""

    def test_stage_result_importable(self):
        from nikita.pipeline.stages.base import StageResult
        result = StageResult.ok(data={"key": "value"}, duration_ms=100.0)
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.duration_ms == 100.0

    def test_stage_result_fail(self):
        from nikita.pipeline.stages.base import StageResult
        result = StageResult.fail(error="something broke", duration_ms=50.0)
        assert result.success is False
        assert result.error == "something broke"

    def test_stage_error_importable(self):
        from nikita.pipeline.stages.base import StageError
        err = StageError("test_stage", "test error", recoverable=True)
        assert err.stage_name == "test_stage"
        assert err.recoverable is True
