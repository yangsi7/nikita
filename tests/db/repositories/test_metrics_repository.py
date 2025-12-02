"""Tests for UserMetricsRepository class.

TDD Tests for T3: Create UserMetricsRepository

Acceptance Criteria:
- AC-T3.1: get(user_id) returns UserMetrics for user
- AC-T3.2: update_metrics(user_id, intimacy_delta, passion_delta, ...) updates metrics atomically
- AC-T3.3: calculate_composite(user_id) returns calculated composite score
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, PropertyMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.user import UserMetrics
from nikita.db.repositories.metrics_repository import UserMetricsRepository


class TestUserMetricsRepository:
    """Test suite for UserMetricsRepository - T3 ACs."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def sample_metrics(self) -> UserMetrics:
        """Create a sample UserMetrics entity."""
        user_id = uuid4()
        metrics = MagicMock(spec=UserMetrics)
        metrics.id = uuid4()
        metrics.user_id = user_id
        metrics.intimacy = Decimal("60.00")
        metrics.passion = Decimal("55.00")
        metrics.trust = Decimal("70.00")
        metrics.secureness = Decimal("50.00")
        metrics.calculate_composite_score = MagicMock(return_value=Decimal("59.25"))
        return metrics

    # ========================================
    # AC-T3.1: get(user_id) returns UserMetrics for user
    # ========================================
    @pytest.mark.asyncio
    async def test_get_by_user_id_returns_metrics(
        self, mock_session: AsyncMock, sample_metrics: UserMetrics
    ):
        """AC-T3.1: get_by_user_id returns UserMetrics for user."""
        # Setup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_metrics)
        mock_session.execute.return_value = mock_result

        repo = UserMetricsRepository(mock_session)
        result = await repo.get_by_user_id(sample_metrics.user_id)

        # Verify
        assert result is sample_metrics
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_user_id_returns_none_if_not_found(
        self, mock_session: AsyncMock
    ):
        """AC-T3.1: get_by_user_id returns None if user not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        repo = UserMetricsRepository(mock_session)
        result = await repo.get_by_user_id(uuid4())

        assert result is None

    # ========================================
    # AC-T3.2: update_metrics updates metrics atomically
    # ========================================
    @pytest.mark.asyncio
    async def test_update_metrics_applies_deltas(
        self, mock_session: AsyncMock
    ):
        """AC-T3.2: update_metrics applies deltas to metrics."""
        user_id = uuid4()

        # Create a real-ish metrics object with mutable attributes
        class MockMetrics:
            def __init__(self):
                self.user_id = user_id
                self.intimacy = Decimal("60.00")
                self.passion = Decimal("55.00")
                self.trust = Decimal("70.00")
                self.secureness = Decimal("50.00")

        metrics = MockMetrics()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=metrics)
        mock_session.execute.return_value = mock_result

        repo = UserMetricsRepository(mock_session)
        result = await repo.update_metrics(
            user_id,
            intimacy_delta=Decimal("5.00"),
            passion_delta=Decimal("-3.00"),
            trust_delta=Decimal("2.00"),
            secureness_delta=Decimal("0.00"),
        )

        # Verify deltas were applied
        assert result.intimacy == Decimal("65.00")
        assert result.passion == Decimal("52.00")
        assert result.trust == Decimal("72.00")
        assert result.secureness == Decimal("50.00")

        # Verify session operations
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_metrics_clamps_to_bounds(
        self, mock_session: AsyncMock
    ):
        """AC-T3.2: update_metrics clamps values to 0-100."""
        user_id = uuid4()

        class MockMetrics:
            def __init__(self):
                self.user_id = user_id
                self.intimacy = Decimal("95.00")
                self.passion = Decimal("5.00")
                self.trust = Decimal("50.00")
                self.secureness = Decimal("50.00")

        metrics = MockMetrics()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=metrics)
        mock_session.execute.return_value = mock_result

        repo = UserMetricsRepository(mock_session)
        result = await repo.update_metrics(
            user_id,
            intimacy_delta=Decimal("10.00"),  # Would exceed 100
            passion_delta=Decimal("-10.00"),  # Would go below 0
        )

        # Verify clamping
        assert result.intimacy == Decimal("100.00")
        assert result.passion == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_update_metrics_raises_if_not_found(
        self, mock_session: AsyncMock
    ):
        """AC-T3.2: update_metrics raises ValueError if user not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        repo = UserMetricsRepository(mock_session)

        with pytest.raises(ValueError, match="Metrics not found"):
            await repo.update_metrics(uuid4(), intimacy_delta=Decimal("5.00"))

    # ========================================
    # AC-T3.3: calculate_composite returns composite score
    # ========================================
    @pytest.mark.asyncio
    async def test_calculate_composite_returns_score(
        self, mock_session: AsyncMock, sample_metrics: UserMetrics
    ):
        """AC-T3.3: calculate_composite returns calculated score."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_metrics)
        mock_session.execute.return_value = mock_result

        repo = UserMetricsRepository(mock_session)
        result = await repo.calculate_composite(sample_metrics.user_id)

        # Verify composite score calculation was called
        assert result == Decimal("59.25")
        sample_metrics.calculate_composite_score.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_composite_raises_if_not_found(
        self, mock_session: AsyncMock
    ):
        """AC-T3.3: calculate_composite raises ValueError if not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        repo = UserMetricsRepository(mock_session)

        with pytest.raises(ValueError, match="Metrics not found"):
            await repo.calculate_composite(uuid4())


class TestUserMetricsRepositoryHelpers:
    """Test helper methods of UserMetricsRepository."""

    def test_clamp_values(self):
        """Verify _clamp helper clamps values correctly."""
        assert UserMetricsRepository._clamp(Decimal("50.00")) == Decimal("50.00")
        assert UserMetricsRepository._clamp(Decimal("0.00")) == Decimal("0.00")
        assert UserMetricsRepository._clamp(Decimal("100.00")) == Decimal("100.00")
        assert UserMetricsRepository._clamp(Decimal("-5.00")) == Decimal("0.00")
        assert UserMetricsRepository._clamp(Decimal("105.00")) == Decimal("100.00")
