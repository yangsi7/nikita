"""Tests for VicePreferenceRepository class.

TDD Tests for T6: Create VicePreferenceRepository

Acceptance Criteria:
- AC-T6.1: get_active(user_id) returns active preferences ordered by engagement
- AC-T6.2: update_intensity(pref_id, delta) updates intensity_level with clamping (1-5)
- AC-T6.3: discover(user_id, category) creates new preference or returns existing
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.user import UserVicePreference
from nikita.db.repositories.vice_repository import VicePreferenceRepository


class TestVicePreferenceRepository:
    """Test suite for VicePreferenceRepository - T6 ACs."""

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
    def sample_preferences(self) -> list[UserVicePreference]:
        """Create sample UserVicePreference entries."""
        user_id = uuid4()
        prefs = []
        categories = ["jealousy_triggers", "spending_habits", "social_vices"]
        for i, category in enumerate(categories):
            pref = MagicMock(spec=UserVicePreference)
            pref.id = uuid4()
            pref.user_id = user_id
            pref.category = category
            pref.intensity_level = i + 1
            pref.engagement_score = Decimal(f"{10 + i * 5}.00")
            pref.discovered_at = datetime.now(UTC)
            prefs.append(pref)
        return prefs

    # ========================================
    # AC-T6.1: get_active returns active preferences
    # ========================================
    @pytest.mark.asyncio
    async def test_get_active_returns_preferences(
        self, mock_session: AsyncMock, sample_preferences: list[UserVicePreference]
    ):
        """AC-T6.1: get_active returns list of active preferences."""
        user_id = sample_preferences[0].user_id

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_preferences
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = VicePreferenceRepository(mock_session)
        result = await repo.get_active(user_id)

        assert len(result) == 3
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_returns_empty_for_new_user(
        self, mock_session: AsyncMock
    ):
        """AC-T6.1: get_active returns empty list for user with no preferences."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = VicePreferenceRepository(mock_session)
        result = await repo.get_active(uuid4())

        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_category_returns_preference(
        self, mock_session: AsyncMock, sample_preferences: list[UserVicePreference]
    ):
        """AC-T6.1: get_by_category returns preference for category."""
        user_id = sample_preferences[0].user_id
        expected = sample_preferences[0]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected
        mock_session.execute.return_value = mock_result

        repo = VicePreferenceRepository(mock_session)
        result = await repo.get_by_category(user_id, "jealousy_triggers")

        assert result is expected
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_category_returns_none_if_not_found(
        self, mock_session: AsyncMock
    ):
        """AC-T6.1: get_by_category returns None if not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = VicePreferenceRepository(mock_session)
        result = await repo.get_by_category(uuid4(), "nonexistent")

        assert result is None

    # ========================================
    # AC-T6.2: update_intensity updates level with clamping
    # ========================================
    @pytest.mark.asyncio
    async def test_update_intensity_applies_positive_delta(
        self, mock_session: AsyncMock
    ):
        """AC-T6.2: update_intensity applies positive delta."""
        pref_id = uuid4()

        class MockPreference:
            def __init__(self):
                self.id = pref_id
                self.intensity_level = 2

        preference = MockPreference()
        mock_session.get.return_value = preference

        repo = VicePreferenceRepository(mock_session)
        result = await repo.update_intensity(pref_id, delta=1)

        assert result.intensity_level == 3
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_intensity_applies_negative_delta(
        self, mock_session: AsyncMock
    ):
        """AC-T6.2: update_intensity applies negative delta."""
        pref_id = uuid4()

        class MockPreference:
            def __init__(self):
                self.id = pref_id
                self.intensity_level = 3

        preference = MockPreference()
        mock_session.get.return_value = preference

        repo = VicePreferenceRepository(mock_session)
        result = await repo.update_intensity(pref_id, delta=-2)

        assert result.intensity_level == 1

    @pytest.mark.asyncio
    async def test_update_intensity_clamps_to_max_5(
        self, mock_session: AsyncMock
    ):
        """AC-T6.2: update_intensity clamps to maximum of 5."""
        pref_id = uuid4()

        class MockPreference:
            def __init__(self):
                self.id = pref_id
                self.intensity_level = 4

        preference = MockPreference()
        mock_session.get.return_value = preference

        repo = VicePreferenceRepository(mock_session)
        result = await repo.update_intensity(pref_id, delta=5)

        assert result.intensity_level == 5

    @pytest.mark.asyncio
    async def test_update_intensity_clamps_to_min_1(
        self, mock_session: AsyncMock
    ):
        """AC-T6.2: update_intensity clamps to minimum of 1."""
        pref_id = uuid4()

        class MockPreference:
            def __init__(self):
                self.id = pref_id
                self.intensity_level = 2

        preference = MockPreference()
        mock_session.get.return_value = preference

        repo = VicePreferenceRepository(mock_session)
        result = await repo.update_intensity(pref_id, delta=-5)

        assert result.intensity_level == 1

    @pytest.mark.asyncio
    async def test_update_intensity_raises_if_not_found(
        self, mock_session: AsyncMock
    ):
        """AC-T6.2: update_intensity raises ValueError if not found."""
        mock_session.get.return_value = None

        repo = VicePreferenceRepository(mock_session)

        with pytest.raises(ValueError, match="not found"):
            await repo.update_intensity(uuid4(), delta=1)

    # ========================================
    # AC-T6.3: discover creates new preference
    # ========================================
    @pytest.mark.asyncio
    async def test_discover_creates_new_preference(
        self, mock_session: AsyncMock
    ):
        """AC-T6.3: discover creates new preference if not exists."""
        user_id = uuid4()

        # get_by_category returns None (not found)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = VicePreferenceRepository(mock_session)
        result = await repo.discover(user_id, "jealousy_triggers")

        # Verify add was called with new preference
        mock_session.add.assert_called_once()
        call_args = mock_session.add.call_args[0][0]
        assert call_args.user_id == user_id
        assert call_args.category == "jealousy_triggers"
        assert call_args.intensity_level == 1
        assert call_args.engagement_score == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_discover_returns_existing_preference(
        self, mock_session: AsyncMock, sample_preferences: list[UserVicePreference]
    ):
        """AC-T6.3: discover returns existing preference if already exists."""
        user_id = sample_preferences[0].user_id
        existing = sample_preferences[0]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        repo = VicePreferenceRepository(mock_session)
        result = await repo.discover(user_id, "jealousy_triggers")

        assert result is existing
        # add should NOT be called since it exists
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_discover_with_custom_intensity(
        self, mock_session: AsyncMock
    ):
        """AC-T6.3: discover with custom initial_intensity."""
        user_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = VicePreferenceRepository(mock_session)
        await repo.discover(user_id, "spending_habits", initial_intensity=3)

        call_args = mock_session.add.call_args[0][0]
        assert call_args.intensity_level == 3


class TestVicePreferenceRepositoryExtras:
    """Test additional methods of VicePreferenceRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.get = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_update_engagement_applies_delta(
        self, mock_session: AsyncMock
    ):
        """Verify update_engagement applies delta to engagement_score."""
        pref_id = uuid4()

        class MockPreference:
            def __init__(self):
                self.id = pref_id
                self.engagement_score = Decimal("10.00")

        preference = MockPreference()
        mock_session.get.return_value = preference

        repo = VicePreferenceRepository(mock_session)
        result = await repo.update_engagement(pref_id, delta=Decimal("5.00"))

        assert result.engagement_score == Decimal("15.00")
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_engagement_clamps_to_zero(
        self, mock_session: AsyncMock
    ):
        """Verify update_engagement doesn't go below zero."""
        pref_id = uuid4()

        class MockPreference:
            def __init__(self):
                self.id = pref_id
                self.engagement_score = Decimal("5.00")

        preference = MockPreference()
        mock_session.get.return_value = preference

        repo = VicePreferenceRepository(mock_session)
        result = await repo.update_engagement(pref_id, delta=Decimal("-10.00"))

        assert result.engagement_score == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_update_engagement_raises_if_not_found(
        self, mock_session: AsyncMock
    ):
        """Verify update_engagement raises ValueError if not found."""
        mock_session.get.return_value = None

        repo = VicePreferenceRepository(mock_session)

        with pytest.raises(ValueError, match="not found"):
            await repo.update_engagement(uuid4(), delta=Decimal("5.00"))
