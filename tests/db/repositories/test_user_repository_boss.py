"""Tests for UserRepository Boss Methods (Spec 004 - Task T5).

TDD tests for boss-related repository methods.
Tests cover AC-T5-001 through AC-T5-004.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


# ==============================================================================
# T5: Add UserRepository Boss Methods
# ==============================================================================


class TestSetBossFightStatus:
    """Tests for AC-T5-001: set_boss_fight_status(user_id) method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    def test_ac_t5_001_method_exists(self):
        """AC-T5-001: UserRepository has set_boss_fight_status method."""
        from nikita.db.repositories.user_repository import UserRepository

        assert hasattr(UserRepository, "set_boss_fight_status")

    @pytest.mark.asyncio
    async def test_ac_t5_001_sets_status_to_boss_fight(self, mock_session: AsyncMock):
        """AC-T5-001: Method sets game_status to 'boss_fight'."""
        from nikita.db.models.user import User, UserMetrics
        from nikita.db.repositories.user_repository import UserRepository

        user_id = uuid4()
        user = User(
            id=user_id,
            telegram_id=12345,
            game_status="active",
            relationship_score=Decimal("55.00"),
            chapter=1,
        )
        user.metrics = UserMetrics(id=uuid4(), user_id=user_id)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.set_boss_fight_status(user_id)

        assert result.game_status == "boss_fight"

    @pytest.mark.asyncio
    async def test_ac_t5_004_logs_to_score_history(self, mock_session: AsyncMock):
        """AC-T5-004: Method logs event to score_history."""
        from nikita.db.models.user import User, UserMetrics
        from nikita.db.repositories.user_repository import UserRepository

        user_id = uuid4()
        user = User(
            id=user_id,
            telegram_id=12345,
            game_status="active",
            relationship_score=Decimal("55.00"),
            chapter=1,
        )
        user.metrics = UserMetrics(id=uuid4(), user_id=user_id)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        await repo.set_boss_fight_status(user_id)

        # Verify session.add was called (for ScoreHistory)
        assert mock_session.add.called


class TestAdvanceChapter:
    """Tests for AC-T5-002: advance_chapter(user_id) method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    def test_ac_t5_002_method_exists(self):
        """AC-T5-002: UserRepository has advance_chapter method."""
        from nikita.db.repositories.user_repository import UserRepository

        assert hasattr(UserRepository, "advance_chapter")

    @pytest.mark.asyncio
    async def test_ac_t5_002_increments_chapter(self, mock_session: AsyncMock):
        """AC-T5-002: Method increments chapter by 1."""
        from nikita.db.models.user import User, UserMetrics
        from nikita.db.repositories.user_repository import UserRepository

        user_id = uuid4()
        user = User(
            id=user_id,
            telegram_id=12345,
            chapter=1,
            boss_attempts=2,
            relationship_score=Decimal("55.00"),
        )
        user.metrics = UserMetrics(id=uuid4(), user_id=user_id)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.advance_chapter(user_id)

        assert result.chapter == 2
        assert result.boss_attempts == 0  # Reset on advance


class TestIncrementBossAttempts:
    """Tests for AC-T5-003: increment_boss_attempts(user_id) method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    def test_ac_t5_003_method_exists(self):
        """AC-T5-003: UserRepository has increment_boss_attempts method."""
        from nikita.db.repositories.user_repository import UserRepository

        assert hasattr(UserRepository, "increment_boss_attempts")

    @pytest.mark.asyncio
    async def test_ac_t5_003_increments_boss_attempts(self, mock_session: AsyncMock):
        """AC-T5-003: Method increments boss_attempts by 1."""
        from nikita.db.models.user import User, UserMetrics
        from nikita.db.repositories.user_repository import UserRepository

        user_id = uuid4()
        user = User(
            id=user_id,
            telegram_id=12345,
            boss_attempts=1,
            chapter=1,
            relationship_score=Decimal("55.00"),
        )
        user.metrics = UserMetrics(id=uuid4(), user_id=user_id)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.increment_boss_attempts(user_id)

        assert result.boss_attempts == 2

    @pytest.mark.asyncio
    async def test_ac_t5_004_logs_boss_failed_event(self, mock_session: AsyncMock):
        """AC-T5-004: Method logs 'boss_failed' event to score_history."""
        from nikita.db.models.user import User, UserMetrics
        from nikita.db.repositories.user_repository import UserRepository

        user_id = uuid4()
        user = User(
            id=user_id,
            telegram_id=12345,
            boss_attempts=0,
            chapter=1,
            relationship_score=Decimal("55.00"),
        )
        user.metrics = UserMetrics(id=uuid4(), user_id=user_id)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        await repo.increment_boss_attempts(user_id)

        # Verify session.add was called (for ScoreHistory)
        assert mock_session.add.called
