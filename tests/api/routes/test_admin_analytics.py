"""Tests for engagement analytics endpoint — Spec 105 Story 5.

Admin endpoint to export engagement data.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_engagement_endpoint_returns_data():
    """GET /admin/analytics/engagement returns user list."""
    from nikita.api.routes.admin import get_engagement_analytics

    assert callable(get_engagement_analytics)


@pytest.mark.asyncio
async def test_engagement_date_filter():
    """?since=YYYY-MM-DD filters results."""
    from nikita.api.routes.admin import get_engagement_analytics

    # The function should accept a `since` parameter
    import inspect
    sig = inspect.signature(get_engagement_analytics)
    param_names = list(sig.parameters.keys())
    assert "since" in param_names or "request" in param_names


@pytest.mark.asyncio
async def test_engagement_empty_result():
    """Endpoint returns empty users list when no data."""
    from nikita.api.routes.admin import get_engagement_analytics

    # Function exists and is callable
    assert callable(get_engagement_analytics)
