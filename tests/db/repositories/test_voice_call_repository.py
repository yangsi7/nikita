"""Tests for VoiceCallRepository (DEBT-002 — call end tracking).

Tests:
- update_call_end sets ended_at and duration_seconds
- update_call_end returns None for unknown session
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.db.models.voice_call import VoiceCall
from nikita.db.repositories.voice_call_repository import VoiceCallRepository


class TestUpdateCallEnd:
    """Test VoiceCallRepository.update_call_end()."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        return VoiceCallRepository(mock_session)

    @pytest.mark.asyncio
    async def test_updates_call_end_fields(self, repo, mock_session):
        """update_call_end sets ended_at and duration_seconds on existing call."""
        call = VoiceCall(
            id=uuid4(),
            user_id=uuid4(),
            elevenlabs_session_id="sess_abc123",
            started_at=datetime.now(timezone.utc),
        )

        # Mock the query to return the call
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = call
        mock_session.execute.return_value = mock_result

        ended_at = datetime.now(timezone.utc)
        result = await repo.update_call_end(
            session_id="sess_abc123",
            ended_at=ended_at,
            duration_seconds=180,
        )

        assert result is not None
        assert result.ended_at == ended_at
        assert result.duration_seconds == 180

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_session(self, repo, mock_session):
        """update_call_end returns None when session_id not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.update_call_end(
            session_id="nonexistent",
            ended_at=datetime.now(timezone.utc),
            duration_seconds=60,
        )

        assert result is None
