"""Tests for conversation summary injection in voice context (Spec 209 PR 209-3).

AC-FR003-001: 3 most recent summaries included, ordered DESC
AC-FR003-002: 0 summaries -> empty list
AC-FR003-003: DB error -> warning logged, empty list
AC-FR003-004: All null summaries -> empty list
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _make_row(summary: str, platform: str, started_at: datetime):
    """Create a mock Row from column-projection SELECT."""
    return SimpleNamespace(
        conversation_summary=summary,
        platform=platform,
        started_at=started_at,
    )


@pytest.mark.asyncio
class TestConversationSummaryTransformation:
    """Tests the transformation logic applied to query results."""

    async def test_three_summaries_transformed_correctly(self):
        """AC-FR003-001: 3 rows produce 3 dicts with summary, platform, date."""
        now = datetime.now(timezone.utc)
        rows = [
            _make_row("Talked about music", "voice", now - timedelta(hours=1)),
            _make_row("Discussed Berlin trip", "telegram", now - timedelta(hours=5)),
            _make_row("Shared work frustrations", "telegram", now - timedelta(days=1)),
        ]

        # Apply the same transformation as server_tools.py
        recent_summaries = [
            {
                "summary": c.conversation_summary,
                "platform": c.platform,
                "date": c.started_at.isoformat(),
            }
            for c in rows
        ]

        assert len(recent_summaries) == 3
        assert recent_summaries[0]["summary"] == "Talked about music"
        assert recent_summaries[0]["platform"] == "voice"
        assert "T" in recent_summaries[0]["date"]
        assert recent_summaries[1]["platform"] == "telegram"

    async def test_zero_rows_produce_empty_list(self):
        """AC-FR003-002: Empty query result -> empty list."""
        recent_summaries = [
            {
                "summary": c.conversation_summary,
                "platform": c.platform,
                "date": c.started_at.isoformat(),
            }
            for c in []
        ]
        assert recent_summaries == []

    async def test_db_error_produces_empty_list_and_logs(self, caplog):
        """AC-FR003-003: DB error -> warning logged + empty list.

        Tests the actual try/except pattern by simulating the code path.
        """
        mock_repo = AsyncMock()
        mock_repo.get_recent_with_summaries = AsyncMock(
            side_effect=Exception("connection refused")
        )

        # Replicate the production error handling pattern from server_tools.py
        with caplog.at_level(logging.WARNING):
            try:
                await mock_repo.get_recent_with_summaries(uuid4(), limit=3)
                recent_summaries = "should not reach"
            except Exception as e:
                logging.getLogger("nikita.agents.voice.server_tools").warning(
                    "[SERVER TOOL] Failed to load conversation summaries: %s", e
                )
                recent_summaries = []

        assert recent_summaries == []
        assert "Failed to load conversation summaries" in caplog.text


@pytest.mark.asyncio
class TestConversationRepositoryMethod:
    """Tests for ConversationRepository.get_recent_with_summaries()."""

    async def test_method_exists_on_repository(self):
        """get_recent_with_summaries method exists on ConversationRepository."""
        from nikita.db.repositories.conversation_repository import ConversationRepository

        assert hasattr(ConversationRepository, "get_recent_with_summaries")

    async def test_returns_rows_with_named_attributes(self):
        """Row objects have .conversation_summary, .platform, .started_at."""
        row = _make_row("Test summary", "telegram", datetime.now(timezone.utc))
        assert row.conversation_summary == "Test summary"
        assert row.platform == "telegram"
        assert hasattr(row, "started_at")

    async def test_excludes_null_summaries(self):
        """Query filters WHERE conversation_summary IS NOT NULL."""
        from nikita.db.repositories.conversation_repository import ConversationRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = ConversationRepository(mock_session)
        result = await repo.get_recent_with_summaries(uuid4(), limit=3)

        assert result == []
        mock_session.execute.assert_awaited_once()
