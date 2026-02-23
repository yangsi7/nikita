"""Tests for days_played increment in decay processor (Spec 101 FR-002).

AC-T2.2: Decay cron increments days_played for each active user processed.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.engine.decay.processor import DecayProcessor


def create_mock_user(
    *,
    user_id=None,
    chapter: int = 1,
    relationship_score: Decimal = Decimal("50.0"),
    last_interaction_at: datetime | None = None,
    game_status: str = "active",
    days_played: int = 0,
) -> MagicMock:
    """Create a mock user."""
    user = MagicMock()
    user.id = user_id or uuid4()
    user.chapter = chapter
    user.relationship_score = relationship_score
    user.last_interaction_at = last_interaction_at
    user.game_status = game_status
    user.days_played = days_played
    return user


class TestDaysPlayedIncrement:
    """Test days_played increment in process_all()."""

    @pytest.mark.asyncio
    async def test_process_all_increments_days_played_for_each_user(self):
        """AC-T2.2: Each active user gets days_played incremented."""
        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_history_repo = AsyncMock()

        user1 = create_mock_user(
            chapter=1,
            last_interaction_at=datetime.now(UTC) - timedelta(hours=5),
            game_status="active",
            days_played=3,
        )
        user2 = create_mock_user(
            chapter=2,
            last_interaction_at=datetime.now(UTC) - timedelta(hours=10),
            game_status="active",
            days_played=10,
        )

        mock_user_repo.get_active_users_for_decay = AsyncMock(
            return_value=[user1, user2],
        )
        mock_user_repo.bulk_increment_days_played = AsyncMock(return_value=2)

        processor = DecayProcessor(
            session=mock_session,
            user_repository=mock_user_repo,
            score_history_repository=mock_history_repo,
        )

        await processor.process_all()

        # Both users should have days_played bulk-incremented in a single call
        mock_user_repo.bulk_increment_days_played.assert_awaited_once()
        called_ids = set(mock_user_repo.bulk_increment_days_played.call_args[0][0])
        assert user1.id in called_ids
        assert user2.id in called_ids

    @pytest.mark.asyncio
    async def test_process_all_increments_even_when_no_decay(self):
        """days_played increments even for users within grace (no decay)."""
        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_history_repo = AsyncMock()

        # User within grace — no decay applied
        user = create_mock_user(
            chapter=1,
            last_interaction_at=datetime.now(UTC) - timedelta(hours=5),
            game_status="active",
            days_played=7,
        )

        mock_user_repo.get_active_users_for_decay = AsyncMock(
            return_value=[user],
        )
        mock_user_repo.bulk_increment_days_played = AsyncMock(return_value=1)

        processor = DecayProcessor(
            session=mock_session,
            user_repository=mock_user_repo,
            score_history_repository=mock_history_repo,
        )

        summary = await processor.process_all()

        # Should still bulk-increment days_played even though no decay
        mock_user_repo.bulk_increment_days_played.assert_awaited_once_with([user.id])
        assert summary["decayed"] == 0

    @pytest.mark.asyncio
    async def test_process_all_no_increment_for_empty_user_list(self):
        """No increment calls when no users to process."""
        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_history_repo = AsyncMock()

        mock_user_repo.get_active_users_for_decay = AsyncMock(return_value=[])
        mock_user_repo.bulk_increment_days_played = AsyncMock()

        processor = DecayProcessor(
            session=mock_session,
            user_repository=mock_user_repo,
            score_history_repository=mock_history_repo,
        )

        await processor.process_all()

        mock_user_repo.bulk_increment_days_played.assert_not_called()
