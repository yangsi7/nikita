"""Tests for /admin/pipeline-health endpoint.

Spec 037 T3.2: Verify pipeline health endpoint returns circuit breaker
states, stage statistics, and recent failures.
"""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.api.schemas.admin import (
    CircuitBreakerStatus,
    PipelineHealthResponse,
    StageFailure,
    StageStats,
)


class TestPipelineHealthEndpoint:
    """Test the /admin/pipeline-health endpoint."""

    @pytest.mark.asyncio
    async def test_returns_circuit_breaker_states(self):
        """Verify circuit breaker states schema is valid (schema-only test)."""
        # NOTE: Circuit breaker modules deleted in Spec 042.
        # This test validates the schema without patching deleted modules.
        cb = CircuitBreakerStatus(
            name="test_circuit_breaker",
            state="closed",
            failure_count=0,
            last_failure_time=None,
            recovery_timeout_seconds=120.0,
        )

        assert cb.name == "test_circuit_breaker"
        assert cb.state == "closed"
        assert cb.failure_count == 0
class TestPipelineHealthSchema:
    """Test the PipelineHealthResponse schema."""

    def test_creates_valid_response(self):
        """Verify schema accepts valid data."""
        response = PipelineHealthResponse(
            status="healthy",
            circuit_breakers=[],
            stage_stats=[],
            recent_failures=[],
            total_runs_24h=0,
            overall_success_rate=0.0,
            avg_pipeline_duration_ms=0.0,
        )

        assert response.status == "healthy"
        assert response.total_runs_24h == 0

    def test_circuit_breaker_status_schema(self):
        """Verify CircuitBreakerStatus schema."""
        cb = CircuitBreakerStatus(
            name="test_cb",
            state="closed",
            failure_count=5,
            last_failure_time=datetime.now(UTC),
            recovery_timeout_seconds=60.0,
        )

        assert cb.name == "test_cb"
        assert cb.state == "closed"
        assert cb.failure_count == 5

    def test_stage_stats_schema(self):
        """Verify StageStats schema."""
        stats = StageStats(
            name="extraction",
            avg_duration_ms=1500.5,
            success_rate=98.5,
            runs_24h=100,
            failures_24h=2,
        )

        assert stats.name == "extraction"
        assert stats.avg_duration_ms == 1500.5
        assert stats.success_rate == 98.5

    def test_stage_failure_schema(self):
        """Verify StageFailure schema."""
        failure = StageFailure(
            stage_name="graph_updates",
            conversation_id=uuid4(),
            error_message="Neo4j connection timeout",
            occurred_at=datetime.now(UTC),
        )

        assert failure.stage_name == "graph_updates"
        assert "timeout" in failure.error_message.lower()
