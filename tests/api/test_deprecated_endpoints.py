"""Tests for deprecated task endpoints — PR 76 Review R2.

Verifies deprecated endpoints return HTTP 410 Gone (not 200).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDeprecatedEndpoints:
    """Both /detect-stuck and /recover-stuck should return 410."""

    @pytest.mark.asyncio
    async def test_detect_stuck_returns_410(self):
        """R2: POST /tasks/detect-stuck returns 410 Gone."""
        from fastapi import HTTPException
        from nikita.api.routes.tasks import detect_stuck_conversations

        with pytest.raises(HTTPException) as exc_info:
            await detect_stuck_conversations()

        assert exc_info.value.status_code == 410
        assert "recover" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_recover_stuck_returns_410(self):
        """R2: POST /tasks/recover-stuck returns 410 Gone."""
        from fastapi import HTTPException
        from nikita.api.routes.tasks import recover_stuck_conversations

        with pytest.raises(HTTPException) as exc_info:
            await recover_stuck_conversations()

        assert exc_info.value.status_code == 410
        assert "recover" in exc_info.value.detail.lower()
