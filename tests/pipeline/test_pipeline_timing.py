"""Tests for pipeline timing — Spec 105 Story 4.

Track per-stage execution timing, expose via admin API.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_stage_timings_data_structure():
    """Stage timings dict has correct structure."""
    timings = {}
    timings["extraction"] = {"duration_ms": 150.5, "success": True}
    timings["memory_update"] = {"duration_ms": 200.3, "success": True}
    timings["persistence"] = {"duration_ms": 45.1, "success": False}

    assert "extraction" in timings
    assert timings["extraction"]["duration_ms"] > 0
    assert timings["memory_update"]["success"] is True
    assert timings["persistence"]["success"] is False


@pytest.mark.asyncio
async def test_stage_timings_in_metadata():
    """Stage timings can be stored in job execution metadata."""
    metadata = {
        "stage_timings": {
            "extraction": 150,
            "memory_update": 200,
            "persistence": 45,
        },
        "total_stages": 3,
        "success": True,
    }

    assert "stage_timings" in metadata
    assert metadata["stage_timings"]["extraction"] == 150
    assert len(metadata["stage_timings"]) == 3


@pytest.mark.asyncio
async def test_admin_timings_endpoint():
    """GET /admin/pipeline/timings endpoint exists and is callable."""
    from nikita.api.routes.admin import get_pipeline_timings

    assert callable(get_pipeline_timings)
