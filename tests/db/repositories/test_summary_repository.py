"""Tests for DailySummaryRepository class.

TDD Tests for T6: Create DailySummaryRepository

Acceptance Criteria:
- AC-T6.4: create_summary(user_id, date, data) creates summary record
- AC-T6.5: get_by_date(user_id, date) returns summary for date
- AC-T6.6: get_range(user_id, start, end) returns summaries in date range
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.game import DailySummary
from nikita.db.repositories.summary_repository import DailySummaryRepository


class TestDailySummaryRepository:
    """Test suite for DailySummaryRepository - T6 ACs."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.execute = AsyncMock()
        session.get = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def sample_summaries(self) -> list[DailySummary]:
        """Create sample DailySummary entries."""
        user_id = uuid4()
        today = date.today()
        summaries = []
        for i in range(7):
            summary = MagicMock(spec=DailySummary)
            summary.id = uuid4()
            summary.user_id = user_id
            summary.date = today - timedelta(days=i)
            summary.score_start = Decimal(f"{50 + i}.00")
            summary.score_end = Decimal(f"{52 + i}.00")
            summary.decay_applied = Decimal("1.00")
            summary.conversations_count = 3
            summary.nikita_summary_text = f"Day {i} was interesting."
            summary.key_events = [{"type": "conversation", "count": 3}]
            summary.created_at = datetime.now(UTC)
            summaries.append(summary)
        return summaries

    # ========================================
    # AC-T6.4: create_summary creates summary record
    # ========================================
    @pytest.mark.asyncio
    async def test_create_summary_basic(self, mock_session: AsyncMock):
        """AC-T6.4: create_summary creates a new summary record."""
        user_id = uuid4()
        summary_date = date.today()

        repo = DailySummaryRepository(mock_session)
        result = await repo.create_summary(
            user_id=user_id,
            summary_date=summary_date,
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        call_args = mock_session.add.call_args[0][0]
        assert call_args.user_id == user_id
        assert call_args.date == summary_date

    @pytest.mark.asyncio
    async def test_create_summary_with_all_fields(self, mock_session: AsyncMock):
        """AC-T6.4: create_summary with all optional fields."""
        user_id = uuid4()
        summary_date = date.today()
        key_events: list[dict[str, Any]] = [
            {"type": "conversation", "count": 5},
            {"type": "boss_attempt", "result": "pass"},
        ]

        repo = DailySummaryRepository(mock_session)
        await repo.create_summary(
            user_id=user_id,
            summary_date=summary_date,
            score_start=Decimal("50.00"),
            score_end=Decimal("55.00"),
            decay_applied=Decimal("1.50"),
            conversations_count=5,
            nikita_summary_text="Today was amazing! We talked about coffee.",
            key_events=key_events,
        )

        call_args = mock_session.add.call_args[0][0]
        assert call_args.score_start == Decimal("50.00")
        assert call_args.score_end == Decimal("55.00")
        assert call_args.decay_applied == Decimal("1.50")
        assert call_args.conversations_count == 5
        assert call_args.nikita_summary_text == "Today was amazing! We talked about coffee."
        assert call_args.key_events == key_events

    @pytest.mark.asyncio
    async def test_create_summary_sets_created_at(self, mock_session: AsyncMock):
        """AC-T6.4: create_summary sets created_at timestamp."""
        user_id = uuid4()

        repo = DailySummaryRepository(mock_session)

        before = datetime.now(UTC)
        await repo.create_summary(
            user_id=user_id,
            summary_date=date.today(),
        )
        after = datetime.now(UTC)

        call_args = mock_session.add.call_args[0][0]
        assert before <= call_args.created_at <= after

    # ========================================
    # AC-T6.5: get_by_date returns summary for date
    # ========================================
    @pytest.mark.asyncio
    async def test_get_by_date_returns_summary(
        self, mock_session: AsyncMock, sample_summaries: list[DailySummary]
    ):
        """AC-T6.5: get_by_date returns summary for specific date."""
        user_id = sample_summaries[0].user_id
        expected = sample_summaries[0]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected
        mock_session.execute.return_value = mock_result

        repo = DailySummaryRepository(mock_session)
        result = await repo.get_by_date(user_id, date.today())

        assert result is expected
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_date_returns_none_if_not_found(
        self, mock_session: AsyncMock
    ):
        """AC-T6.5: get_by_date returns None if no summary for date."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = DailySummaryRepository(mock_session)
        result = await repo.get_by_date(uuid4(), date.today())

        assert result is None

    # ========================================
    # AC-T6.6: get_range returns summaries in date range
    # ========================================
    @pytest.mark.asyncio
    async def test_get_range_returns_summaries(
        self, mock_session: AsyncMock, sample_summaries: list[DailySummary]
    ):
        """AC-T6.6: get_range returns list of summaries in range."""
        user_id = sample_summaries[0].user_id
        today = date.today()
        week_ago = today - timedelta(days=7)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_summaries
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = DailySummaryRepository(mock_session)
        result = await repo.get_range(user_id, week_ago, today)

        assert len(result) == 7
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_range_returns_empty_for_no_summaries(
        self, mock_session: AsyncMock
    ):
        """AC-T6.6: get_range returns empty list if no summaries in range."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = DailySummaryRepository(mock_session)
        result = await repo.get_range(
            uuid4(),
            date.today() - timedelta(days=30),
            date.today(),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_get_range_single_day(self, mock_session: AsyncMock):
        """AC-T6.6: get_range works for single day range."""
        today = date.today()
        summary = MagicMock(spec=DailySummary)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [summary]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = DailySummaryRepository(mock_session)
        result = await repo.get_range(uuid4(), today, today)

        assert len(result) == 1


class TestDailySummaryRepositoryExtras:
    """Test additional methods of DailySummaryRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.get = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_update_summary_updates_fields(self, mock_session: AsyncMock):
        """Verify update_summary updates specified fields."""
        summary_id = uuid4()

        class MockSummary:
            def __init__(self):
                self.id = summary_id
                self.score_end = Decimal("50.00")
                self.nikita_summary_text = "Old text"
                self.key_events = []

        summary = MockSummary()
        mock_session.get.return_value = summary

        repo = DailySummaryRepository(mock_session)
        result = await repo.update_summary(
            summary_id,
            score_end=Decimal("60.00"),
            nikita_summary_text="New exciting summary!",
            key_events=[{"type": "boss_fight", "result": "pass"}],
        )

        assert result.score_end == Decimal("60.00")
        assert result.nikita_summary_text == "New exciting summary!"
        assert result.key_events == [{"type": "boss_fight", "result": "pass"}]
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_summary_partial_update(self, mock_session: AsyncMock):
        """Verify update_summary allows partial updates."""
        summary_id = uuid4()

        class MockSummary:
            def __init__(self):
                self.id = summary_id
                self.score_end = Decimal("50.00")
                self.nikita_summary_text = "Keep this"
                self.key_events = [{"old": "event"}]

        summary = MockSummary()
        mock_session.get.return_value = summary

        repo = DailySummaryRepository(mock_session)
        result = await repo.update_summary(
            summary_id,
            score_end=Decimal("55.00"),
            # nikita_summary_text and key_events not provided
        )

        assert result.score_end == Decimal("55.00")
        assert result.nikita_summary_text == "Keep this"  # Unchanged
        assert result.key_events == [{"old": "event"}]  # Unchanged

    @pytest.mark.asyncio
    async def test_update_summary_raises_if_not_found(self, mock_session: AsyncMock):
        """Verify update_summary raises ValueError if not found."""
        mock_session.get.return_value = None

        repo = DailySummaryRepository(mock_session)

        with pytest.raises(ValueError, match="not found"):
            await repo.update_summary(uuid4(), score_end=Decimal("50.00"))

    @pytest.mark.asyncio
    async def test_get_recent_returns_summaries(self, mock_session: AsyncMock):
        """Verify get_recent returns recent summaries."""
        user_id = uuid4()
        summaries = [MagicMock(spec=DailySummary) for _ in range(5)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = summaries
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = DailySummaryRepository(mock_session)
        result = await repo.get_recent(user_id, limit=5)

        assert len(result) == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_default_limit(self, mock_session: AsyncMock):
        """Verify get_recent uses default limit of 7."""
        user_id = uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = DailySummaryRepository(mock_session)
        await repo.get_recent(user_id)  # No limit specified

        mock_session.execute.assert_called_once()


class TestDailySummaryRepositoryContextEngineering:
    """Test context engineering fields (spec 012)."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.get = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_summary_with_context_fields(self, mock_session: AsyncMock):
        """AC-CE1: create_summary with context engineering fields."""
        user_id = uuid4()
        summary_date = date.today()
        key_moments = [
            {"source": str(uuid4()), "moments": ["Laughed together", "Shared a secret"]}
        ]

        repo = DailySummaryRepository(mock_session)
        await repo.create_summary(
            user_id=user_id,
            summary_date=summary_date,
            summary_text="We had a deep conversation about life goals.",
            key_moments=key_moments,
            emotional_tone="positive",
            engagement_score=Decimal("0.85"),
        )

        call_args = mock_session.add.call_args[0][0]
        assert call_args.summary_text == "We had a deep conversation about life goals."
        assert call_args.key_moments == key_moments
        assert call_args.emotional_tone == "positive"
        assert call_args.engagement_score == Decimal("0.85")

    @pytest.mark.asyncio
    async def test_update_summary_context_fields(self, mock_session: AsyncMock):
        """AC-CE2: update_summary can update context engineering fields."""
        summary_id = uuid4()

        class MockSummary:
            def __init__(self):
                self.id = summary_id
                self.summary_text = "Old summary"
                self.key_moments = []
                self.emotional_tone = "neutral"
                self.engagement_score = Decimal("0.50")
                self.updated_at = None
                # Legacy fields
                self.score_end = None
                self.nikita_summary_text = None
                self.key_events = None

        summary = MockSummary()
        mock_session.get.return_value = summary

        repo = DailySummaryRepository(mock_session)
        new_key_moments = [{"source": "conv1", "moments": ["Great joke"]}]

        result = await repo.update_summary(
            summary_id,
            summary_text="Updated summary with new insights.",
            key_moments=new_key_moments,
            emotional_tone="positive",
            engagement_score=Decimal("0.90"),
        )

        assert result.summary_text == "Updated summary with new insights."
        assert result.key_moments == new_key_moments
        assert result.emotional_tone == "positive"
        assert result.engagement_score == Decimal("0.90")
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_range_returns_ordered_by_date(self, mock_session: AsyncMock):
        """AC-CE3: get_range returns summaries ordered by date ascending."""
        user_id = uuid4()
        today = date.today()

        # Create summaries in reverse order
        summaries = []
        for i in range(3):
            summary = MagicMock(spec=DailySummary)
            summary.date = today - timedelta(days=2 - i)  # 2 days ago, 1 day ago, today
            summary.summary_text = f"Day {i}"
            summaries.append(summary)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = summaries
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = DailySummaryRepository(mock_session)
        result = await repo.get_range(user_id, today - timedelta(days=2), today)

        assert len(result) == 3
        # The repository should return them in date order (ASC)

    @pytest.mark.asyncio
    async def test_get_recent_returns_newest_first(self, mock_session: AsyncMock):
        """AC-CE4: get_recent returns summaries ordered by date descending."""
        user_id = uuid4()
        today = date.today()

        summaries = []
        for i in range(5):
            summary = MagicMock(spec=DailySummary)
            summary.date = today - timedelta(days=i)
            summary.summary_text = f"Day {i}"
            summaries.append(summary)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = summaries
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = DailySummaryRepository(mock_session)
        result = await repo.get_recent(user_id, limit=5)

        assert len(result) == 5
        # First should be today (newest)
        assert result[0].date == today
