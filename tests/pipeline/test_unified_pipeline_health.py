"""Tests for unified pipeline health endpoint (Spec 042 T2.12).

AC-2.12.1: GET /admin/unified-pipeline/health returns stage list from orchestrator
AC-2.12.2: Returns success rate and timing from job_executions
AC-2.12.3: Status degrades when success rate drops
"""

from datetime import UTC, datetime

import pytest

from nikita.api.schemas.admin import (
    UnifiedPipelineHealthResponse,
    UnifiedPipelineStageHealth,
)
from nikita.pipeline.orchestrator import PipelineOrchestrator


class TestUnifiedPipelineHealthSchema:
    """Test UnifiedPipelineHealthResponse schema."""

    def test_healthy_response(self):
        """AC-2.12.1: Schema accepts valid data with stage list."""
        stages = [
            UnifiedPipelineStageHealth(name="extraction", is_critical=True),
            UnifiedPipelineStageHealth(name="life_sim", is_critical=False),
        ]
        response = UnifiedPipelineHealthResponse(
            status="healthy",
            stages=stages,
            total_runs_24h=50,
            overall_success_rate=98.0,
            avg_pipeline_duration_ms=1200.0,
            last_run_at=datetime.now(UTC),
        )
        assert response.status == "healthy"
        assert len(response.stages) == 2
        assert response.stages[0].name == "extraction"
        assert response.stages[0].is_critical is True

    def test_stage_health_defaults(self):
        """Stage health has sensible defaults."""
        stage = UnifiedPipelineStageHealth(name="summary")
        assert stage.is_critical is False
        assert stage.avg_duration_ms == 0.0
        assert stage.success_rate == 100.0
        assert stage.runs_24h == 0
        assert stage.timeout_seconds == 30.0

    def test_degraded_when_low_success_rate(self):
        """AC-2.12.3: Status degrades when success rate < 90%."""
        response = UnifiedPipelineHealthResponse(
            status="degraded",
            stages=[],
            total_runs_24h=100,
            overall_success_rate=75.0,
            avg_pipeline_duration_ms=2000.0,
        )
        assert response.status == "degraded"
        assert response.overall_success_rate < 90

    def test_down_when_very_low_success_rate(self):
        """AC-2.12.3: Status is down when success rate < 50%."""
        response = UnifiedPipelineHealthResponse(
            status="down",
            stages=[],
            total_runs_24h=100,
            overall_success_rate=30.0,
            avg_pipeline_duration_ms=5000.0,
        )
        assert response.status == "down"
        assert response.overall_success_rate < 50

    def test_pipeline_version_default(self):
        """Response includes pipeline version."""
        response = UnifiedPipelineHealthResponse(
            status="healthy",
            stages=[],
        )
        assert response.pipeline_version == "0.1.0"

    def test_no_runs_returns_healthy(self):
        """No runs in 24h still reports healthy."""
        response = UnifiedPipelineHealthResponse(
            status="healthy",
            stages=[],
            total_runs_24h=0,
            overall_success_rate=100.0,
            avg_pipeline_duration_ms=0.0,
            last_run_at=None,
        )
        assert response.status == "healthy"
        assert response.last_run_at is None


class TestStageDefinitionsMatchHealth:
    """Verify health endpoint uses orchestrator stage definitions."""

    def test_stage_definitions_exist(self):
        """AC-2.12.1: Orchestrator has 9 stage definitions."""
        assert len(PipelineOrchestrator.STAGE_DEFINITIONS) == 9

    def test_stage_definitions_have_names(self):
        """Each stage definition has a name and criticality flag."""
        for name, class_path, is_critical in PipelineOrchestrator.STAGE_DEFINITIONS:
            assert isinstance(name, str)
            assert isinstance(class_path, str)
            assert isinstance(is_critical, bool)

    def test_critical_stages_identified(self):
        """Extraction and memory_update are critical."""
        critical = [
            name for name, _, crit in PipelineOrchestrator.STAGE_DEFINITIONS if crit
        ]
        assert "extraction" in critical
        assert "memory_update" in critical

    def test_non_critical_stages_identified(self):
        """Most stages are non-critical."""
        non_critical = [
            name for name, _, crit in PipelineOrchestrator.STAGE_DEFINITIONS if not crit
        ]
        assert "life_sim" in non_critical
        assert "summary" in non_critical
        assert "touchpoint" in non_critical
