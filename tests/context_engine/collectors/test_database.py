"""Tests for DatabaseCollector (Spec 039 Phase 1)."""

import uuid
from decimal import Decimal
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nikita.context_engine.collectors.database import (
    DatabaseCollector,
    DatabaseCollectorOutput,
    EngagementData,
    MetricsData,
    UserData,
)
from nikita.context_engine.collectors.base import CollectorContext
from nikita.context_engine.models import ViceProfile


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = MagicMock()
    # Configure execute to return a result with scalar() returning 0
    mock_result = MagicMock()
    mock_result.scalar.return_value = 0
    session.execute = AsyncMock(return_value=mock_result)
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
    """Create mock User model."""
    user = MagicMock()
    user.chapter = 3
    user.relationship_score = Decimal("75.50")
    user.boss_attempts = 2
    user.game_status = "active"
    user.days_played = 15
    user.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    user.last_interaction_at = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)
    user.onboarded_at = datetime(2024, 1, 2, tzinfo=UTC)
    user.timezone = "America/New_York"
    user.notifications_enabled = True
    user.onboarding_status = "complete"
    user.onboarding_profile = {"name": "Test User"}
    # Mock metrics relationship
    user.metrics = MagicMock()
    user.metrics.intimacy = Decimal("60.00")
    user.metrics.passion = Decimal("55.00")
    user.metrics.trust = Decimal("70.00")
    user.metrics.secureness = Decimal("65.00")
    return user


class TestUserData:
    """Tests for UserData model."""

    def test_default_values(self):
        """Test default values for new user."""
        data = UserData()
        assert data.chapter == 1
        assert data.chapter_name == "Curiosity"
        assert data.relationship_score == Decimal("50.00")
        assert data.boss_attempts == 0
        assert data.game_status == "active"
        assert data.days_played == 0
        assert data.timezone == "UTC"
        assert data.notifications_enabled is True
        assert data.onboarding_status == "pending"

    def test_chapter_names_mapping(self, mock_user):
        """Test chapter names are correctly mapped."""
        for chapter, expected_name in [
            (1, "Curiosity"),
            (2, "Testing"),
            (3, "Depth"),
            (4, "Authenticity"),
            (5, "Commitment"),
        ]:
            mock_user.chapter = chapter
            data = UserData.from_model(mock_user)
            assert data.chapter_name == expected_name

    def test_from_model(self, mock_user):
        """Test UserData.from_model() creates correct instance."""
        data = UserData.from_model(mock_user)
        assert data.chapter == 3
        assert data.chapter_name == "Depth"
        assert data.relationship_score == Decimal("75.50")
        assert data.boss_attempts == 2
        assert data.game_status == "active"
        assert data.days_played == 15
        assert data.timezone == "America/New_York"
        assert data.notifications_enabled is True
        assert data.onboarding_status == "complete"


class TestMetricsData:
    """Tests for MetricsData model."""

    def test_default_values(self):
        """Test default values for metrics."""
        data = MetricsData()
        assert data.intimacy == Decimal("50.00")
        assert data.passion == Decimal("50.00")
        assert data.trust == Decimal("50.00")
        assert data.secureness == Decimal("50.00")

    def test_from_model(self, mock_user):
        """Test MetricsData.from_model() with actual metrics."""
        data = MetricsData.from_model(mock_user.metrics)
        assert data.intimacy == Decimal("60.00")
        assert data.passion == Decimal("55.00")
        assert data.trust == Decimal("70.00")
        assert data.secureness == Decimal("65.00")

    def test_from_model_with_none(self):
        """Test MetricsData.from_model() with None returns defaults."""
        data = MetricsData.from_model(None)
        assert data.intimacy == Decimal("50.00")
        assert data.passion == Decimal("50.00")


class TestEngagementData:
    """Tests for EngagementData model."""

    def test_default_values(self):
        """Test default engagement values."""
        data = EngagementData()
        assert data.state == "calibrating"
        assert data.calibration_score == Decimal("0.50")
        assert data.multiplier == Decimal("0.90")
        assert data.consecutive_in_zone == 0
        assert data.last_transition is None


class TestDatabaseCollectorOutput:
    """Tests for DatabaseCollectorOutput model."""

    def test_default_values(self):
        """Test output with default nested models."""
        output = DatabaseCollectorOutput(
            user=UserData(),
            metrics=MetricsData(),
            vice_profile=ViceProfile(),
            engagement=EngagementData(),
        )
        assert output.user.chapter == 1
        assert output.metrics.intimacy == Decimal("50.00")
        assert output.total_conversations == 0
        assert output.total_words_exchanged == 0


class TestDatabaseCollector:
    """Tests for DatabaseCollector."""

    def test_collector_name(self):
        """Test collector name is 'database'."""
        collector = DatabaseCollector()
        assert collector.name == "database"

    def test_collector_timeout(self):
        """Test timeout is 5s for database queries."""
        collector = DatabaseCollector()
        assert collector.timeout_seconds == 5.0

    def test_max_retries(self):
        """Test max retries is 2."""
        collector = DatabaseCollector()
        assert collector.max_retries == 2

    @pytest.mark.asyncio
    async def test_collect_full_data(self, collector_context, mock_user):
        """Test collecting all user data from database."""
        collector = DatabaseCollector()

        # Mock repositories
        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = mock_user

        mock_vice_repo = AsyncMock()
        mock_vice_repo.get_active.return_value = [
            MagicMock(category="intellectual_dominance", intensity_level=3),
            MagicMock(category="dark_humor", intensity_level=2),
        ]

        mock_engagement_repo = AsyncMock()
        mock_engagement_state = MagicMock()
        mock_engagement_state.state = "in_zone"
        mock_engagement_state.calibration_score = Decimal("0.75")
        mock_engagement_state.multiplier = Decimal("1.10")
        mock_engagement_state.consecutive_in_zone = 5
        mock_engagement_state.last_calculated_at = datetime(2024, 6, 14, tzinfo=UTC)
        mock_engagement_repo.get_by_user_id.return_value = mock_engagement_state

        with (
            patch(
                "nikita.context_engine.collectors.database.UserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "nikita.context_engine.collectors.database.UserMetricsRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "nikita.context_engine.collectors.database.VicePreferenceRepository",
                return_value=mock_vice_repo,
            ),
            patch(
                "nikita.context_engine.collectors.database.EngagementStateRepository",
                return_value=mock_engagement_repo,
            ),
        ):
            result = await collector.collect(collector_context)

        assert isinstance(result, DatabaseCollectorOutput)
        assert result.user.chapter == 3
        assert result.metrics.intimacy == Decimal("60.00")
        assert result.vice_profile.intellectual_dominance == 3
        assert result.vice_profile.dark_humor == 2
        assert result.engagement.state == "in_zone"
        assert result.engagement.multiplier == Decimal("1.10")

    @pytest.mark.asyncio
    async def test_collect_user_not_found(self, collector_context):
        """Test collect raises ValueError when user not found."""
        collector = DatabaseCollector()

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = None

        with (
            patch(
                "nikita.context_engine.collectors.database.UserRepository",
                return_value=mock_user_repo,
            ),
            pytest.raises(ValueError, match="not found"),
        ):
            await collector.collect(collector_context)

    @pytest.mark.asyncio
    async def test_build_vice_profile_empty(self, collector_context, mock_user):
        """Test building vice profile with no preferences."""
        collector = DatabaseCollector()

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = mock_user

        mock_vice_repo = AsyncMock()
        mock_vice_repo.get_active.return_value = []

        mock_engagement_repo = AsyncMock()
        mock_engagement_repo.get_by_user_id.return_value = None

        with (
            patch(
                "nikita.context_engine.collectors.database.UserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "nikita.context_engine.collectors.database.UserMetricsRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "nikita.context_engine.collectors.database.VicePreferenceRepository",
                return_value=mock_vice_repo,
            ),
            patch(
                "nikita.context_engine.collectors.database.EngagementStateRepository",
                return_value=mock_engagement_repo,
            ),
        ):
            result = await collector.collect(collector_context)

        # All vices should be 0
        assert result.vice_profile.intellectual_dominance == 0
        assert result.vice_profile.risk_taking == 0
        assert result.vice_profile.substances == 0

    @pytest.mark.asyncio
    async def test_engagement_data_fallback_when_none(self, collector_context, mock_user):
        """Test engagement data defaults when no engagement state exists."""
        collector = DatabaseCollector()

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = mock_user

        mock_vice_repo = AsyncMock()
        mock_vice_repo.get_active.return_value = []

        mock_engagement_repo = AsyncMock()
        mock_engagement_repo.get_by_user_id.return_value = None

        with (
            patch(
                "nikita.context_engine.collectors.database.UserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "nikita.context_engine.collectors.database.UserMetricsRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "nikita.context_engine.collectors.database.VicePreferenceRepository",
                return_value=mock_vice_repo,
            ),
            patch(
                "nikita.context_engine.collectors.database.EngagementStateRepository",
                return_value=mock_engagement_repo,
            ),
        ):
            result = await collector.collect(collector_context)

        assert result.engagement.state == "calibrating"
        assert result.engagement.multiplier == Decimal("0.90")

    def test_get_fallback(self):
        """Test fallback returns safe defaults."""
        collector = DatabaseCollector()
        fallback = collector.get_fallback()

        assert isinstance(fallback, DatabaseCollectorOutput)
        assert fallback.user.chapter == 1
        assert fallback.user.game_status == "active"
        assert fallback.metrics.intimacy == Decimal("50.00")
        assert fallback.vice_profile.intellectual_dominance == 0
        assert fallback.engagement.state == "calibrating"
        assert fallback.total_conversations == 0
        assert fallback.total_words_exchanged == 0
