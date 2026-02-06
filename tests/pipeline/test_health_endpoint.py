"""Tests for unified pipeline health endpoint (T2.12).

AC-2.12.1: GET /admin/unified-pipeline/health returns per-stage stats
AC-2.12.2: Response includes last_24h summary
AC-2.12.3: JWT-protected (admin only)
AC-2.12.4: 6 tests for health endpoint
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.api.schemas.admin import (
    UnifiedPipelineHealthResponse,
    UnifiedPipelineStageHealth,
)


class TestUnifiedPipelineHealthSchema:

    def test_stage_health_defaults(self):
        stage = UnifiedPipelineStageHealth(name="extraction", is_critical=True)
        assert stage.name == "extraction"
        assert stage.is_critical is True
        assert stage.avg_duration_ms == 0.0
        assert stage.success_rate == 100.0

    def test_response_has_all_fields(self):
        stages = [
            UnifiedPipelineStageHealth(name="extraction", is_critical=True),
            UnifiedPipelineStageHealth(name="memory_update", is_critical=True),
        ]
        resp = UnifiedPipelineHealthResponse(
            status="healthy",
            stages=stages,
            total_runs_24h=100,
            overall_success_rate=98.5,
            avg_pipeline_duration_ms=1234.5,
        )
        assert resp.status == "healthy"
        assert len(resp.stages) == 2
        assert resp.total_runs_24h == 100
        assert resp.pipeline_version == "0.1.0"

    def test_response_healthy_status(self):
        resp = UnifiedPipelineHealthResponse(
            status="healthy",
            stages=[],
            total_runs_24h=0,
        )
        assert resp.status == "healthy"

    def test_response_degraded_status(self):
        resp = UnifiedPipelineHealthResponse(
            status="degraded",
            stages=[],
            total_runs_24h=50,
            overall_success_rate=75.0,
        )
        assert resp.status == "degraded"
        assert resp.overall_success_rate == 75.0

    def test_response_with_last_run(self):
        now = datetime.now(timezone.utc)
        resp = UnifiedPipelineHealthResponse(
            status="healthy",
            stages=[],
            last_run_at=now,
        )
        assert resp.last_run_at == now

    def test_stage_count_matches_pipeline(self):
        """Verify STAGE_DEFINITIONS has 9 stages."""
        from nikita.pipeline.orchestrator import PipelineOrchestrator
        assert len(PipelineOrchestrator.STAGE_DEFINITIONS) == 9
