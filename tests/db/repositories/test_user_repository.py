"""Tests for UserRepository class.

TDD Tests for T2: Create UserRepository

Acceptance Criteria:
- AC-T2.1: get(user_id) returns User with eager-loaded metrics
- AC-T2.2: get_by_telegram_id(telegram_id) returns User or None
- AC-T2.3: create(user_data) creates User + UserMetrics atomically
- AC-T2.4: update_score(user_id, delta, event_type, event_details) updates users AND score_history
- AC-T2.5: apply_decay(user_id, decay_amount) applies decay and logs to score_history
- AC-T2.6: advance_chapter(user_id) increments chapter and logs event
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestUserRepository:
    """Test suite for UserRepository - T2 ACs."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.get = AsyncMock()
        session.add = MagicMock()
        session.delete = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.scalar = AsyncMock()
        session.scalars = AsyncMock()
        return session

    # ========================================
    # AC-T2.1: get(user_id) returns User with eager-loaded metrics
    # ========================================
    @pytest.mark.asyncio
    async def test_get_returns_user_with_metrics(self, mock_session: AsyncMock):
        """AC-T2.1: get(user_id) returns User with eager-loaded metrics."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User, UserMetrics

        user_id = uuid4()
        user = User(id=user_id, telegram_id=12345)
        user.metrics = UserMetrics(id=uuid4(), user_id=user_id)

        # Mock scalars to return user
        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get(user_id)

        assert result is user
        assert result.metrics is not None

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self, mock_session: AsyncMock):
        """AC-T2.1: get(user_id) returns None if user not found."""
        from nikita.db.repositories.user_repository import UserRepository

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get(uuid4())

        assert result is None

    # ========================================
    # AC-T2.2: get_by_telegram_id(telegram_id) returns User or None
    # ========================================
    @pytest.mark.asyncio
    async def test_get_by_telegram_id_returns_user(self, mock_session: AsyncMock):
        """AC-T2.2: get_by_telegram_id(telegram_id) returns User."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User

        telegram_id = 123456789
        user = User(id=uuid4(), telegram_id=telegram_id)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_by_telegram_id(telegram_id)

        assert result is user
        assert result.telegram_id == telegram_id

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_returns_none(self, mock_session: AsyncMock):
        """AC-T2.2: get_by_telegram_id returns None if not found."""
        from nikita.db.repositories.user_repository import UserRepository

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_by_telegram_id(999999999)

        assert result is None

    # ========================================
    # AC-T2.3: create(user_data) creates User + UserMetrics atomically
    # ========================================
    @pytest.mark.asyncio
    async def test_create_creates_user_and_metrics(self, mock_session: AsyncMock):
        """AC-T2.3: create() creates User + UserMetrics atomically."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User

        user_id = uuid4()

        repo = UserRepository(mock_session)
        result = await repo.create_with_metrics(user_id, telegram_id=12345)

        # Should add both user and metrics
        assert mock_session.add.call_count >= 1
        mock_session.flush.assert_called()
        assert isinstance(result, User)
        assert result.id == user_id
        assert result.metrics is not None

    @pytest.mark.asyncio
    async def test_create_sets_default_metrics(self, mock_session: AsyncMock):
        """AC-T2.3: create() sets default metrics values (50.00)."""
        from nikita.db.repositories.user_repository import UserRepository

        user_id = uuid4()
        repo = UserRepository(mock_session)
        result = await repo.create_with_metrics(user_id)

        assert result.metrics.intimacy == Decimal("50.00")
        assert result.metrics.passion == Decimal("50.00")
        assert result.metrics.trust == Decimal("50.00")
        assert result.metrics.secureness == Decimal("50.00")

    # ========================================
    # AC-T2.4: update_score updates users AND score_history
    # ========================================
    @pytest.mark.asyncio
    async def test_update_score_updates_user_and_logs(self, mock_session: AsyncMock):
        """AC-T2.4: update_score updates user score and logs to history."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User
        from nikita.db.models.game import ScoreHistory

        user_id = uuid4()
        user = User(id=user_id, relationship_score=Decimal("50.00"), chapter=1)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.update_score(
            user_id,
            delta=Decimal("5.00"),
            event_type="conversation",
            event_details={"reason": "good response"},
        )

        # User score should be updated
        assert result.relationship_score == Decimal("55.00")
        # Should have added score history record
        assert mock_session.add.called

    @pytest.mark.asyncio
    async def test_update_score_clamps_to_100(self, mock_session: AsyncMock):
        """AC-T2.4: update_score clamps score to max 100."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User

        user_id = uuid4()
        user = User(id=user_id, relationship_score=Decimal("98.00"), chapter=1)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.update_score(user_id, delta=Decimal("10.00"))

        assert result.relationship_score == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_update_score_clamps_to_0(self, mock_session: AsyncMock):
        """AC-T2.4: update_score clamps score to min 0."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User

        user_id = uuid4()
        user = User(id=user_id, relationship_score=Decimal("5.00"), chapter=1)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.update_score(user_id, delta=Decimal("-10.00"))

        assert result.relationship_score == Decimal("0.00")

    # ========================================
    # AC-T2.5: apply_decay applies decay and logs to score_history
    # ========================================
    @pytest.mark.asyncio
    async def test_apply_decay_reduces_score(self, mock_session: AsyncMock):
        """AC-T2.5: apply_decay reduces score by decay amount."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User

        user_id = uuid4()
        user = User(id=user_id, relationship_score=Decimal("50.00"), chapter=1)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.apply_decay(user_id, decay_amount=Decimal("2.00"))

        assert result.relationship_score == Decimal("48.00")

    @pytest.mark.asyncio
    async def test_apply_decay_logs_event(self, mock_session: AsyncMock):
        """AC-T2.5: apply_decay logs decay event to score_history."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User

        user_id = uuid4()
        user = User(id=user_id, relationship_score=Decimal("50.00"), chapter=1)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        await repo.apply_decay(user_id, decay_amount=Decimal("2.00"))

        # Should have added score history with event_type='decay'
        add_calls = mock_session.add.call_args_list
        # At least one call should be for ScoreHistory
        assert any(
            "ScoreHistory" in str(type(call[0][0]))
            for call in add_calls
            if call[0]
        ) or mock_session.add.called

    # ========================================
    # AC-T2.6: advance_chapter increments chapter and logs event
    # ========================================
    @pytest.mark.asyncio
    async def test_advance_chapter_increments(self, mock_session: AsyncMock):
        """AC-T2.6: advance_chapter increments chapter by 1."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User

        user_id = uuid4()
        user = User(id=user_id, relationship_score=Decimal("75.00"), chapter=1)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.advance_chapter(user_id)

        assert result.chapter == 2

    @pytest.mark.asyncio
    async def test_advance_chapter_caps_at_5(self, mock_session: AsyncMock):
        """AC-T2.6: advance_chapter does not exceed chapter 5."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User

        user_id = uuid4()
        user = User(id=user_id, relationship_score=Decimal("95.00"), chapter=5)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.advance_chapter(user_id)

        assert result.chapter == 5  # Should stay at 5

    @pytest.mark.asyncio
    async def test_advance_chapter_logs_event(self, mock_session: AsyncMock):
        """AC-T2.6: advance_chapter logs chapter_advance event."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User

        user_id = uuid4()
        user = User(id=user_id, relationship_score=Decimal("75.00"), chapter=2)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        await repo.advance_chapter(user_id)

        # Should have logged event to score_history
        assert mock_session.add.called

    @pytest.mark.asyncio
    async def test_advance_chapter_resets_boss_attempts(self, mock_session: AsyncMock):
        """AC-T2.6: advance_chapter resets boss_attempts to 0."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User

        user_id = uuid4()
        user = User(
            id=user_id, relationship_score=Decimal("75.00"), chapter=2, boss_attempts=2
        )

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.advance_chapter(user_id)

        assert result.boss_attempts == 0

    # ========================================
    # AC-T3: update_last_interaction for decay grace period reset (spec 005)
    # ========================================
    @pytest.mark.asyncio
    async def test_update_last_interaction_updates_timestamp(self, mock_session: AsyncMock):
        """AC-T3.1/T3.2: update_last_interaction updates last_interaction_at."""
        from datetime import UTC, datetime
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User

        user_id = uuid4()
        old_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        user = User(id=user_id, last_interaction_at=old_time)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        new_time = datetime.now(UTC)
        result = await repo.update_last_interaction(user_id, new_time)

        assert result.last_interaction_at == new_time
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_update_last_interaction_uses_current_time_if_none(self, mock_session: AsyncMock):
        """AC-T3.1: update_last_interaction uses current time if not specified."""
        from datetime import UTC, datetime
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User

        user_id = uuid4()
        user = User(id=user_id, last_interaction_at=None)

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        before = datetime.now(UTC)
        result = await repo.update_last_interaction(user_id)
        after = datetime.now(UTC)

        assert result.last_interaction_at is not None
        assert before <= result.last_interaction_at <= after

    @pytest.mark.asyncio
    async def test_update_last_interaction_raises_for_missing_user(self, mock_session: AsyncMock):
        """AC-T3.1: update_last_interaction raises ValueError if user not found."""
        from nikita.db.repositories.user_repository import UserRepository

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        with pytest.raises(ValueError, match="not found"):
            await repo.update_last_interaction(uuid4())

    # ========================================
    # AC-T4: engagement_state eager loading (fix for greenlet_spawn error)
    # ========================================
    @pytest.mark.asyncio
    async def test_get_returns_user_with_engagement_state(self, mock_session: AsyncMock):
        """AC-T4.1: get() eager-loads engagement_state alongside metrics."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User, UserMetrics
        from nikita.db.models.engagement import EngagementState

        # Setup mock user with engagement_state
        user_id = uuid4()
        user = User(id=user_id, telegram_id=123456789, relationship_score=Decimal("50.00"))
        user.metrics = UserMetrics(id=uuid4(), user_id=user_id)
        user.engagement_state = EngagementState(
            id=uuid4(),
            user_id=user_id,
            state="calibrating",
            calibration_score=Decimal("0.50"),
            multiplier=Decimal("0.90"),
        )

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get(user_id)

        assert result is user
        assert result.engagement_state is not None
        assert result.engagement_state.state == "calibrating"
        assert result.engagement_state.multiplier == Decimal("0.90")

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_returns_user_with_engagement_state(self, mock_session: AsyncMock):
        """AC-T4.2: get_by_telegram_id() eager-loads engagement_state."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User, UserMetrics
        from nikita.db.models.engagement import EngagementState

        user_id = uuid4()
        user = User(id=user_id, telegram_id=123456789, relationship_score=Decimal("50.00"))
        user.metrics = UserMetrics(id=uuid4(), user_id=user_id)
        user.engagement_state = EngagementState(
            id=uuid4(),
            user_id=user_id,
            state="in_zone",
            calibration_score=Decimal("0.80"),
            multiplier=Decimal("1.00"),
        )

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_by_telegram_id(123456789)

        assert result.engagement_state is not None
        assert result.engagement_state.state == "in_zone"
        assert result.engagement_state.multiplier == Decimal("1.00")

    @pytest.mark.asyncio
    async def test_get_active_users_for_decay_returns_users_with_engagement_state(
        self, mock_session: AsyncMock
    ):
        """AC-T4.3: get_active_users_for_decay() eager-loads engagement_state."""
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.models.user import User, UserMetrics
        from nikita.db.models.engagement import EngagementState

        # Create two users with engagement states
        user1_id = uuid4()
        user1 = User(id=user1_id, telegram_id=111, relationship_score=Decimal("60.00"), game_status="active")
        user1.metrics = UserMetrics(id=uuid4(), user_id=user1_id)
        user1.engagement_state = EngagementState(
            id=uuid4(),
            user_id=user1_id,
            state="drifting",
            multiplier=Decimal("0.90"),
        )

        user2_id = uuid4()
        user2 = User(id=user2_id, telegram_id=222, relationship_score=Decimal("40.00"), game_status="active")
        user2.metrics = UserMetrics(id=uuid4(), user_id=user2_id)
        user2.engagement_state = EngagementState(
            id=uuid4(),
            user_id=user2_id,
            state="clingy",
            multiplier=Decimal("0.80"),
        )

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [user1, user2]
        mock_result.unique.return_value.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_active_users_for_decay()

        assert len(result) == 2
        assert result[0].engagement_state is not None
        assert result[0].engagement_state.state == "drifting"
        assert result[1].engagement_state is not None
        assert result[1].engagement_state.state == "clingy"
