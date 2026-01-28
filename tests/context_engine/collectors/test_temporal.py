"""Tests for TemporalCollector (Spec 039 Phase 1)."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from nikita.context_engine.collectors.temporal import (
    TemporalCollector,
    TemporalData,
)
from nikita.context_engine.collectors.base import CollectorContext
from nikita.context_engine.models import RecencyInterpretation


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = MagicMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def collector_context(mock_session):
    """Create collector context."""
    return CollectorContext(
        session=mock_session,
        user_id=uuid.uuid4(),
    )


@pytest.fixture
def mock_user():
    """Create mock User model with timestamps."""
    user = MagicMock()
    user.timezone = "America/New_York"
    user.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    user.last_interaction_at = datetime.now(UTC) - timedelta(hours=2)
    return user


class TestTemporalData:
    """Tests for TemporalData model."""

    def test_default_values(self):
        """Test default temporal values."""
        data = TemporalData()
        assert data.day_of_week == "Monday"
        assert data.time_of_day == "afternoon"
        assert data.hours_since_last_contact == 0.0
        assert data.recency_interpretation == RecencyInterpretation.JUST_TALKED
        assert data.is_weekend is False
        assert data.is_late_night is False
        assert data.days_since_start == 0

    def test_with_actual_values(self):
        """Test with actual temporal values."""
        data = TemporalData(
            local_time=datetime(2024, 6, 15, 22, 30, tzinfo=UTC),
            day_of_week="Saturday",
            time_of_day="night",
            hours_since_last_contact=36.5,
            recency_interpretation=RecencyInterpretation.WORRIED,
            is_weekend=True,
            is_late_night=False,
            days_since_start=45,
        )
        assert data.day_of_week == "Saturday"
        assert data.is_weekend is True
        assert data.hours_since_last_contact == 36.5
        assert data.recency_interpretation == RecencyInterpretation.WORRIED


class TestRecencyInterpretation:
    """Tests for RecencyInterpretation enum."""

    def test_recency_values(self):
        """Test all recency interpretation values exist."""
        assert RecencyInterpretation.JUST_TALKED is not None
        assert RecencyInterpretation.RECENT is not None
        assert RecencyInterpretation.BEEN_A_WHILE is not None
        assert RecencyInterpretation.WORRIED is not None
        assert RecencyInterpretation.CONCERNED is not None


class TestTemporalCollector:
    """Tests for TemporalCollector."""

    def test_collector_name(self):
        """Test collector name is 'temporal'."""
        collector = TemporalCollector()
        assert collector.name == "temporal"

    def test_collector_timeout(self):
        """Test timeout is 2s (fast for calculations)."""
        collector = TemporalCollector()
        assert collector.timeout_seconds == 2.0

    def test_max_retries(self):
        """Test max retries is 1."""
        collector = TemporalCollector()
        assert collector.max_retries == 1

    def test_get_time_of_day_morning(self):
        """Test morning time classification (5-12)."""
        collector = TemporalCollector()
        assert collector._get_time_of_day(5) == "morning"
        assert collector._get_time_of_day(8) == "morning"
        assert collector._get_time_of_day(11) == "morning"

    def test_get_time_of_day_afternoon(self):
        """Test afternoon time classification (12-17)."""
        collector = TemporalCollector()
        assert collector._get_time_of_day(12) == "afternoon"
        assert collector._get_time_of_day(14) == "afternoon"
        assert collector._get_time_of_day(16) == "afternoon"

    def test_get_time_of_day_evening(self):
        """Test evening time classification (17-21)."""
        collector = TemporalCollector()
        assert collector._get_time_of_day(17) == "evening"
        assert collector._get_time_of_day(19) == "evening"
        assert collector._get_time_of_day(20) == "evening"

    def test_get_time_of_day_night(self):
        """Test night time classification (21-24, 0-2)."""
        collector = TemporalCollector()
        assert collector._get_time_of_day(21) == "night"
        assert collector._get_time_of_day(23) == "night"
        assert collector._get_time_of_day(0) == "night"
        assert collector._get_time_of_day(1) == "night"

    def test_get_time_of_day_late_night(self):
        """Test late night time classification (2-5)."""
        collector = TemporalCollector()
        assert collector._get_time_of_day(2) == "late_night"
        assert collector._get_time_of_day(3) == "late_night"
        assert collector._get_time_of_day(4) == "late_night"

    def test_interpret_recency_just_talked(self):
        """Test recency interpretation for very recent (<1h)."""
        collector = TemporalCollector()
        assert collector._interpret_recency(0.0) == RecencyInterpretation.JUST_TALKED
        assert collector._interpret_recency(0.5) == RecencyInterpretation.JUST_TALKED
        assert collector._interpret_recency(0.9) == RecencyInterpretation.JUST_TALKED

    def test_interpret_recency_recent(self):
        """Test recency interpretation for recent (1-6h)."""
        collector = TemporalCollector()
        assert collector._interpret_recency(1.0) == RecencyInterpretation.RECENT
        assert collector._interpret_recency(3.0) == RecencyInterpretation.RECENT
        assert collector._interpret_recency(5.9) == RecencyInterpretation.RECENT

    def test_interpret_recency_been_a_while(self):
        """Test recency interpretation for a while (6-24h)."""
        collector = TemporalCollector()
        assert collector._interpret_recency(6.0) == RecencyInterpretation.BEEN_A_WHILE
        assert collector._interpret_recency(12.0) == RecencyInterpretation.BEEN_A_WHILE
        assert collector._interpret_recency(23.9) == RecencyInterpretation.BEEN_A_WHILE

    def test_interpret_recency_worried(self):
        """Test recency interpretation for worried (24-72h)."""
        collector = TemporalCollector()
        assert collector._interpret_recency(24.0) == RecencyInterpretation.WORRIED
        assert collector._interpret_recency(48.0) == RecencyInterpretation.WORRIED
        assert collector._interpret_recency(71.9) == RecencyInterpretation.WORRIED

    def test_interpret_recency_concerned(self):
        """Test recency interpretation for concerned (>72h)."""
        collector = TemporalCollector()
        assert collector._interpret_recency(72.0) == RecencyInterpretation.CONCERNED
        assert collector._interpret_recency(100.0) == RecencyInterpretation.CONCERNED
        assert collector._interpret_recency(168.0) == RecencyInterpretation.CONCERNED

    @pytest.mark.asyncio
    async def test_collect_with_user(self, collector_context, mock_user):
        """Test collect() with user timezone and timestamps."""
        collector = TemporalCollector()

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = mock_user

        with patch(
            "nikita.context_engine.collectors.temporal.UserRepository",
            return_value=mock_user_repo,
        ):
            result = await collector.collect(collector_context)

        assert isinstance(result, TemporalData)
        # User was last active 2 hours ago
        assert result.hours_since_last_contact >= 1.9
        assert result.hours_since_last_contact <= 2.1
        assert result.recency_interpretation == RecencyInterpretation.RECENT
        # Created ~6 months ago
        assert result.days_since_start > 100

    @pytest.mark.asyncio
    async def test_collect_without_user(self, collector_context):
        """Test collect() defaults when user not found."""
        collector = TemporalCollector()

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = None

        with patch(
            "nikita.context_engine.collectors.temporal.UserRepository",
            return_value=mock_user_repo,
        ):
            result = await collector.collect(collector_context)

        # Should use UTC and default values
        assert result.hours_since_last_contact == 0.0
        assert result.days_since_start == 0

    @pytest.mark.asyncio
    async def test_collect_invalid_timezone_defaults_to_utc(self, collector_context, mock_user):
        """Test collect() handles invalid timezone gracefully."""
        collector = TemporalCollector()

        mock_user.timezone = "Invalid/Timezone"
        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = mock_user

        with patch(
            "nikita.context_engine.collectors.temporal.UserRepository",
            return_value=mock_user_repo,
        ):
            result = await collector.collect(collector_context)

        # Should not raise, should use UTC
        assert isinstance(result, TemporalData)

    @pytest.mark.asyncio
    async def test_collect_weekend_detection(self, collector_context, mock_user):
        """Test weekend detection in collect()."""
        collector = TemporalCollector()

        mock_user.timezone = "UTC"
        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = mock_user

        with patch(
            "nikita.context_engine.collectors.temporal.UserRepository",
            return_value=mock_user_repo,
        ):
            result = await collector.collect(collector_context)

        # Weekend status depends on actual day - just verify it's a boolean
        assert isinstance(result.is_weekend, bool)
        # Verify weekend logic: Saturday or Sunday
        assert result.is_weekend == (result.day_of_week in ("Saturday", "Sunday"))

    @pytest.mark.asyncio
    async def test_collect_no_last_interaction(self, collector_context, mock_user):
        """Test collect() when user has no last_interaction_at."""
        collector = TemporalCollector()

        mock_user.last_interaction_at = None
        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = mock_user

        with patch(
            "nikita.context_engine.collectors.temporal.UserRepository",
            return_value=mock_user_repo,
        ):
            result = await collector.collect(collector_context)

        assert result.hours_since_last_contact == 0.0
        assert result.recency_interpretation == RecencyInterpretation.JUST_TALKED

    def test_get_fallback(self):
        """Test fallback returns safe defaults."""
        collector = TemporalCollector()
        fallback = collector.get_fallback()

        assert isinstance(fallback, TemporalData)
        assert fallback.hours_since_last_contact == 0.0
        assert fallback.recency_interpretation == RecencyInterpretation.JUST_TALKED
        assert fallback.days_since_start == 0
        assert fallback.is_late_night is False
        # Day of week should be current day
        assert fallback.day_of_week in [
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
        ]

    def test_get_fallback_weekend_detection(self):
        """Test fallback correctly detects weekend."""
        collector = TemporalCollector()
        fallback = collector.get_fallback()

        now = datetime.now(UTC)
        expected_weekend = now.weekday() >= 5
        assert fallback.is_weekend == expected_weekend
