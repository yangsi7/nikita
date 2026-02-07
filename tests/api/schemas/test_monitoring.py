"""Tests for admin monitoring schemas - T1.4 Spec 034.

TDD: Write tests FIRST, then implement.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError


class TestSystemMetricsSchema:
    """Test SystemMetrics schema."""

    def test_system_metrics_schema_validation(self):
        """AC-1.4.1: SystemMetrics schema validates correctly."""
        from nikita.api.schemas.monitoring import SystemMetrics

        metrics = SystemMetrics(
            total_users=100,
            active_users_24h=50,
            total_conversations=500,
            conversations_today=25,
            total_voice_sessions=100,
            voice_sessions_today=10,
            avg_score=75.5,
            users_in_boss_fight=5,
            users_game_over=3,
        )

        assert metrics.total_users == 100
        assert metrics.active_users_24h == 50
        assert metrics.avg_score == 75.5

    def test_system_metrics_requires_positive_counts(self):
        """SystemMetrics validates count fields are non-negative."""
        from nikita.api.schemas.monitoring import SystemMetrics

        with pytest.raises(ValidationError):
            SystemMetrics(
                total_users=-1,
                active_users_24h=0,
                total_conversations=0,
                conversations_today=0,
                total_voice_sessions=0,
                voice_sessions_today=0,
                avg_score=0,
                users_in_boss_fight=0,
                users_game_over=0,
            )


class TestMemorySnapshotSchema:
    """Test MemorySnapshot schema."""

    def test_memory_snapshot_schema_validation(self):
        """AC-1.4.1: MemorySnapshot schema validates correctly."""
        from nikita.api.schemas.monitoring import MemorySnapshot

        snapshot = MemorySnapshot(
            user_facts_count=25,
            relationship_episodes_count=15,
            nikita_events_count=10,
            total_threads=5,
            open_threads=2,
            last_sync=datetime.now(timezone.utc),
            graph_status="healthy",
        )

        assert snapshot.user_facts_count == 25
        assert snapshot.graph_status == "healthy"

    def test_memory_snapshot_graph_status_values(self):
        """MemorySnapshot graph_status must be valid value."""
        from nikita.api.schemas.monitoring import MemorySnapshot

        # Valid statuses
        for status in ["healthy", "syncing", "error", "unavailable"]:
            snapshot = MemorySnapshot(
                user_facts_count=0,
                relationship_episodes_count=0,
                nikita_events_count=0,
                total_threads=0,
                open_threads=0,
                last_sync=None,
                graph_status=status,
            )
            assert snapshot.graph_status == status


class TestPipelineStatusSchema:
    """Test PipelineStatus schema."""

    def test_pipeline_status_schema_validation(self):
        """AC-1.4.1: PipelineStatus schema validates correctly."""
        from nikita.api.schemas.monitoring import PipelineStatus, PipelineStage

        status = PipelineStatus(
            conversation_id=uuid4(),
            stages=[
                PipelineStage(
                    name="extraction",
                    status="completed",
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    error=None,
                ),
                PipelineStage(
                    name="graph_update",
                    status="in_progress",
                    started_at=datetime.now(timezone.utc),
                    completed_at=None,
                    error=None,
                ),
            ],
            overall_status="in_progress",
        )

        assert len(status.stages) == 2
        assert status.overall_status == "in_progress"

    def test_pipeline_stage_statuses(self):
        """PipelineStage status must be valid value."""
        from nikita.api.schemas.monitoring import PipelineStage

        for status in ["pending", "in_progress", "completed", "failed", "skipped"]:
            stage = PipelineStage(
                name="test",
                status=status,
                started_at=None,
                completed_at=None,
                error=None,
            )
            assert stage.status == status


class TestErrorSummarySchema:
    """Test ErrorSummary schema."""

    def test_error_summary_schema_validation(self):
        """AC-1.4.2: ErrorSummary schema validates correctly."""
        from nikita.api.schemas.monitoring import ErrorSummary, ErrorEntry

        summary = ErrorSummary(
            total_errors_24h=10,
            error_rate_percent=2.5,
            errors=[
                ErrorEntry(
                    timestamp=datetime.now(timezone.utc),
                    error_type="scoring_failure",
                    message="Failed to analyze response",
                    conversation_id=uuid4(),
                    user_id=uuid4(),
                ),
            ],
        )

        assert summary.total_errors_24h == 10
        assert summary.error_rate_percent == 2.5
        assert len(summary.errors) == 1


class TestScoreTimelineSchema:
    """Test ScoreTimeline schema."""

    def test_score_timeline_schema_validation(self):
        """AC-1.4.2: ScoreTimeline schema validates correctly."""
        from nikita.api.schemas.monitoring import ScoreTimeline, ScorePoint

        timeline = ScoreTimeline(
            user_id=uuid4(),
            points=[
                ScorePoint(
                    timestamp=datetime.now(timezone.utc),
                    score=75.5,
                    event_type="conversation",
                    delta=2.5,
                ),
                ScorePoint(
                    timestamp=datetime.now(timezone.utc),
                    score=78.0,
                    event_type="conversation",
                    delta=2.5,
                ),
            ],
            current_score=78.0,
            boss_threshold=75.0,
            chapter=3,
        )

        assert len(timeline.points) == 2
        assert timeline.current_score == 78.0
        assert timeline.boss_threshold == 75.0


class TestBossEncountersSchema:
    """Test BossEncounters schema."""

    def test_boss_encounters_schema_validation(self):
        """AC-1.4.2: BossEncounters schema validates correctly."""
        from nikita.api.schemas.monitoring import BossEncounters, BossEncounter

        encounters = BossEncounters(
            user_id=uuid4(),
            total_attempts=3,
            successful=1,
            failed=2,
            encounters=[
                BossEncounter(
                    timestamp=datetime.now(timezone.utc),
                    chapter=2,
                    attempt=1,
                    result="failed",
                    score_before=55.0,
                    score_after=45.0,
                    trigger_reason="fell_below_threshold",
                ),
            ],
        )

        assert encounters.total_attempts == 3
        assert encounters.successful == 1
        assert len(encounters.encounters) == 1


class TestAllSchemaValidation:
    """Test all schemas have proper validation."""

    def test_all_schemas_have_validators(self):
        """AC-1.4.3: All schemas have proper validation."""
        from nikita.api.schemas import monitoring

        # Verify all expected schemas exist
        assert hasattr(monitoring, "SystemMetrics")
        assert hasattr(monitoring, "MemorySnapshot")
        assert hasattr(monitoring, "PipelineStatus")
        assert hasattr(monitoring, "PipelineStage")
        assert hasattr(monitoring, "ErrorSummary")
        assert hasattr(monitoring, "ErrorEntry")
        assert hasattr(monitoring, "ScoreTimeline")
        assert hasattr(monitoring, "ScorePoint")
        assert hasattr(monitoring, "BossEncounters")
        assert hasattr(monitoring, "BossEncounter")

    def test_schemas_are_pydantic_models(self):
        """All schemas are Pydantic BaseModel subclasses."""
        from pydantic import BaseModel

        from nikita.api.schemas.monitoring import (
            BossEncounter,
            BossEncounters,
            ErrorEntry,
            ErrorSummary,
            MemorySnapshot,
            PipelineStage,
            PipelineStatus,
            ScorePoint,
            ScoreTimeline,
            SystemMetrics,
        )

        schemas = [
            SystemMetrics,
            MemorySnapshot,
            PipelineStatus,
            PipelineStage,
            ErrorSummary,
            ErrorEntry,
            ScoreTimeline,
            ScorePoint,
            BossEncounters,
            BossEncounter,
        ]

        for schema in schemas:
            assert issubclass(schema, BaseModel), f"{schema.__name__} not a Pydantic model"
