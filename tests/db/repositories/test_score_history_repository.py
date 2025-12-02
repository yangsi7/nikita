"""Tests for ScoreHistoryRepository class.

TDD Tests for T5: Create ScoreHistoryRepository

Acceptance Criteria:
- AC-T5.1: log_event(user_id, score, chapter, event_type, event_details) creates history record
- AC-T5.2: get_history(user_id, limit=50) returns score timeline descending
- AC-T5.3: get_daily_stats(user_id, date) returns aggregated stats for date
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.game import ScoreHistory
from nikita.db.repositories.score_history_repository import ScoreHistoryRepository


class TestScoreHistoryRepository:
    """Test suite for ScoreHistoryRepository - T5 ACs."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def sample_history_entries(self) -> list[ScoreHistory]:
        """Create sample ScoreHistory entries for testing."""
        user_id = uuid4()
        entries = []
        for i in range(5):
            entry = MagicMock(spec=ScoreHistory)
            entry.id = uuid4()
            entry.user_id = user_id
            entry.score = Decimal(f"{50 + i}.00")
            entry.chapter = 1
            entry.event_type = "conversation" if i % 2 == 0 else "decay"
            entry.event_details = {"delta": Decimal("1.00")}
            entry.recorded_at = datetime.now(UTC)
            entries.append(entry)
        return entries

    # ========================================
    # AC-T5.1: log_event creates history record
    # ========================================
    @pytest.mark.asyncio
    async def test_log_event_creates_record(self, mock_session: AsyncMock):
        """AC-T5.1: log_event creates a new history record."""
        user_id = uuid4()

        repo = ScoreHistoryRepository(mock_session)
        result = await repo.log_event(
            user_id=user_id,
            score=Decimal("55.50"),
            chapter=2,
            event_type="conversation",
            event_details={"delta": Decimal("2.50")},
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # Verify the entity passed to add
        call_args = mock_session.add.call_args[0][0]
        assert call_args.user_id == user_id
        assert call_args.score == Decimal("55.50")
        assert call_args.chapter == 2
        assert call_args.event_type == "conversation"
        assert call_args.event_details == {"delta": Decimal("2.50")}

    @pytest.mark.asyncio
    async def test_log_event_without_optional_fields(self, mock_session: AsyncMock):
        """AC-T5.1: log_event works without optional event_type and event_details."""
        user_id = uuid4()

        repo = ScoreHistoryRepository(mock_session)
        await repo.log_event(
            user_id=user_id,
            score=Decimal("60.00"),
            chapter=1,
        )

        call_args = mock_session.add.call_args[0][0]
        assert call_args.event_type is None
        assert call_args.event_details is None

    @pytest.mark.asyncio
    async def test_log_event_sets_recorded_at(self, mock_session: AsyncMock):
        """AC-T5.1: log_event automatically sets recorded_at timestamp."""
        user_id = uuid4()

        repo = ScoreHistoryRepository(mock_session)

        before = datetime.now(UTC)
        await repo.log_event(
            user_id=user_id,
            score=Decimal("50.00"),
            chapter=1,
        )
        after = datetime.now(UTC)

        call_args = mock_session.add.call_args[0][0]
        assert before <= call_args.recorded_at <= after

    @pytest.mark.asyncio
    async def test_log_event_supports_all_event_types(self, mock_session: AsyncMock):
        """AC-T5.1: log_event supports all event types."""
        user_id = uuid4()
        repo = ScoreHistoryRepository(mock_session)

        event_types = ["conversation", "decay", "boss_pass", "boss_fail", "chapter_advance"]

        for event_type in event_types:
            mock_session.add.reset_mock()
            await repo.log_event(
                user_id=user_id,
                score=Decimal("50.00"),
                chapter=1,
                event_type=event_type,
            )

            call_args = mock_session.add.call_args[0][0]
            assert call_args.event_type == event_type

    # ========================================
    # AC-T5.2: get_history returns score timeline descending
    # ========================================
    @pytest.mark.asyncio
    async def test_get_history_returns_entries(
        self, mock_session: AsyncMock, sample_history_entries: list[ScoreHistory]
    ):
        """AC-T5.2: get_history returns list of history entries."""
        user_id = sample_history_entries[0].user_id

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_history_entries
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ScoreHistoryRepository(mock_session)
        result = await repo.get_history(user_id)

        assert len(result) == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_respects_limit(self, mock_session: AsyncMock):
        """AC-T5.2: get_history respects limit parameter."""
        user_id = uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ScoreHistoryRepository(mock_session)
        await repo.get_history(user_id, limit=25)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_default_limit(self, mock_session: AsyncMock):
        """AC-T5.2: get_history uses default limit of 50."""
        user_id = uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ScoreHistoryRepository(mock_session)
        await repo.get_history(user_id)  # No limit specified

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_returns_empty_for_new_user(
        self, mock_session: AsyncMock
    ):
        """AC-T5.2: get_history returns empty list for user with no history."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ScoreHistoryRepository(mock_session)
        result = await repo.get_history(uuid4())

        assert result == []

    # ========================================
    # AC-T5.3: get_daily_stats returns aggregated stats for date
    # ========================================
    @pytest.mark.asyncio
    async def test_get_daily_stats_returns_stats(self, mock_session: AsyncMock):
        """AC-T5.3: get_daily_stats returns aggregated stats."""
        user_id = uuid4()
        target_date = date.today()

        # Create mock events for the day
        events = []
        for i, (score, event_type) in enumerate([
            (Decimal("50.00"), "conversation"),
            (Decimal("52.00"), "conversation"),
            (Decimal("51.00"), "decay"),
        ]):
            event = MagicMock(spec=ScoreHistory)
            event.score = score
            event.event_type = event_type
            events.append(event)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = events
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ScoreHistoryRepository(mock_session)
        result = await repo.get_daily_stats(user_id, target_date)

        assert result["date"] == target_date
        assert result["events_count"] == 3
        assert result["score_start"] == Decimal("50.00")
        assert result["score_end"] == Decimal("51.00")
        assert result["score_change"] == Decimal("1.00")
        assert result["events_by_type"] == {"conversation": 2, "decay": 1}

    @pytest.mark.asyncio
    async def test_get_daily_stats_returns_empty_for_no_events(
        self, mock_session: AsyncMock
    ):
        """AC-T5.3: get_daily_stats returns empty stats for no events."""
        user_id = uuid4()
        target_date = date.today()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ScoreHistoryRepository(mock_session)
        result = await repo.get_daily_stats(user_id, target_date)

        assert result["date"] == target_date
        assert result["events_count"] == 0
        assert result["score_start"] is None
        assert result["score_end"] is None
        assert result["score_change"] is None
        assert result["events_by_type"] == {}

    @pytest.mark.asyncio
    async def test_get_daily_stats_handles_unknown_event_type(
        self, mock_session: AsyncMock
    ):
        """AC-T5.3: get_daily_stats handles events without event_type."""
        user_id = uuid4()
        target_date = date.today()

        event = MagicMock(spec=ScoreHistory)
        event.score = Decimal("50.00")
        event.event_type = None  # Unknown type

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [event]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ScoreHistoryRepository(mock_session)
        result = await repo.get_daily_stats(user_id, target_date)

        assert result["events_by_type"] == {"unknown": 1}


class TestScoreHistoryRepositoryExtras:
    """Test additional methods of ScoreHistoryRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_events_by_type(self, mock_session: AsyncMock):
        """Verify get_events_by_type filters by event type."""
        user_id = uuid4()
        events = [MagicMock(spec=ScoreHistory) for _ in range(3)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = events
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ScoreHistoryRepository(mock_session)
        result = await repo.get_events_by_type(user_id, "decay")

        assert len(result) == 3
        mock_session.execute.assert_called_once()
