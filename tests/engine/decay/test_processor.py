"""Tests for decay processor (spec 005).

TDD: These tests define the expected behavior for DecayProcessor.
Tests written FIRST before implementation.

Covers:
- T5: DecayProcessor batch processing
- T6: Decay history logging
- T7: Boss fight decay pause
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.engine.decay.models import DecayResult


def create_mock_user(
    *,
    user_id=None,
    chapter: int = 1,
    relationship_score: Decimal = Decimal("50.0"),
    last_interaction_at: datetime | None = None,
    game_status: str = "active",
) -> MagicMock:
    """Create a mock user with specified attributes."""
    user = MagicMock()
    user.id = user_id or uuid4()
    user.chapter = chapter
    user.relationship_score = relationship_score
    user.last_interaction_at = last_interaction_at
    user.game_status = game_status
    return user


class TestDecayProcessorShouldSkipUser:
    """Test should_skip_user() method (T7 - Boss Fight Pause)."""

    @pytest.mark.asyncio
    async def test_skip_boss_fight_status(self):
        """AC-T7.2: Skip users in boss_fight status."""
        from nikita.engine.decay.processor import DecayProcessor

        processor = DecayProcessor(
            session=AsyncMock(),
            user_repository=AsyncMock(),
            score_history_repository=AsyncMock(),
        )
        user = create_mock_user(game_status="boss_fight")

        assert processor.should_skip_user(user) is True

    @pytest.mark.asyncio
    async def test_skip_game_over_status(self):
        """AC-T7.2: Skip users in game_over status."""
        from nikita.engine.decay.processor import DecayProcessor

        processor = DecayProcessor(
            session=AsyncMock(),
            user_repository=AsyncMock(),
            score_history_repository=AsyncMock(),
        )
        user = create_mock_user(game_status="game_over")

        assert processor.should_skip_user(user) is True

    @pytest.mark.asyncio
    async def test_skip_won_status(self):
        """AC-T7.2: Skip users in won status."""
        from nikita.engine.decay.processor import DecayProcessor

        processor = DecayProcessor(
            session=AsyncMock(),
            user_repository=AsyncMock(),
            score_history_repository=AsyncMock(),
        )
        user = create_mock_user(game_status="won")

        assert processor.should_skip_user(user) is True

    @pytest.mark.asyncio
    async def test_process_active_status(self):
        """AC-T5.2: Process users with active status."""
        from nikita.engine.decay.processor import DecayProcessor

        processor = DecayProcessor(
            session=AsyncMock(),
            user_repository=AsyncMock(),
            score_history_repository=AsyncMock(),
        )
        user = create_mock_user(game_status="active")

        assert processor.should_skip_user(user) is False


class TestDecayProcessorProcessUser:
    """Test process_user() method."""

    @pytest.mark.asyncio
    async def test_process_user_applies_decay_when_overdue(self):
        """AC-T5.4: Apply decay to users past grace period."""
        from nikita.engine.decay.processor import DecayProcessor

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_history_repo = AsyncMock()

        # Ch5 grace=8h (Spec 101 FR-003), user 10h past = 2h overdue
        user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("50.0"),
            last_interaction_at=datetime.now(UTC) - timedelta(hours=10),
            game_status="active",
        )
        mock_user_repo.apply_decay = AsyncMock(return_value=user)

        processor = DecayProcessor(
            session=mock_session,
            user_repository=mock_user_repo,
            score_history_repository=mock_history_repo,
        )

        result = await processor.process_user(user)

        assert result is not None
        assert isinstance(result, DecayResult)
        mock_user_repo.apply_decay.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_user_returns_none_when_within_grace(self):
        """AC-T5.4: No decay for users within grace period."""
        from nikita.engine.decay.processor import DecayProcessor

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_history_repo = AsyncMock()

        # Ch1 grace=72h (Spec 101 FR-003), user 5h since last interaction = within grace
        user = create_mock_user(
            chapter=1,
            relationship_score=Decimal("50.0"),
            last_interaction_at=datetime.now(UTC) - timedelta(hours=5),
            game_status="active",
        )

        processor = DecayProcessor(
            session=mock_session,
            user_repository=mock_user_repo,
            score_history_repository=mock_history_repo,
        )

        result = await processor.process_user(user)

        assert result is None
        mock_user_repo.apply_decay.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_user_logs_decay_event(self):
        """AC-T6.1: Log decay event to score_history."""
        from nikita.engine.decay.processor import DecayProcessor

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_history_repo = AsyncMock()

        # Ch5 grace=8h (Spec 101 FR-003), user 10h past = 2h overdue
        user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("50.0"),
            last_interaction_at=datetime.now(UTC) - timedelta(hours=10),
            game_status="active",
        )
        mock_user_repo.apply_decay = AsyncMock(return_value=user)

        processor = DecayProcessor(
            session=mock_session,
            user_repository=mock_user_repo,
            score_history_repository=mock_history_repo,
        )

        await processor.process_user(user)

        # Should have logged to score history
        mock_history_repo.log_event.assert_called_once()
        call_kwargs = mock_history_repo.log_event.call_args[1]
        assert call_kwargs["event_type"] == "decay"

    @pytest.mark.asyncio
    async def test_process_user_skips_boss_fight(self):
        """AC-T7.1/T7.2: Skip users in boss_fight status."""
        from nikita.engine.decay.processor import DecayProcessor

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_history_repo = AsyncMock()

        # User overdue but in boss fight
        user = create_mock_user(
            chapter=1,
            relationship_score=Decimal("50.0"),
            last_interaction_at=datetime.now(UTC) - timedelta(hours=20),
            game_status="boss_fight",
        )

        processor = DecayProcessor(
            session=mock_session,
            user_repository=mock_user_repo,
            score_history_repository=mock_history_repo,
        )

        result = await processor.process_user(user)

        assert result is None
        mock_user_repo.apply_decay.assert_not_called()


class TestDecayProcessorProcessAll:
    """Test process_all() method."""

    @pytest.mark.asyncio
    async def test_process_all_returns_summary(self):
        """AC-T5.5: Return summary with processed, decayed, game_overs counts."""
        from nikita.engine.decay.processor import DecayProcessor

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_history_repo = AsyncMock()

        # Create users with various states
        # Ch5 grace=8h (Spec 101 FR-003), 20h past = overdue
        overdue_user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("50.0"),
            last_interaction_at=datetime.now(UTC) - timedelta(hours=20),
            game_status="active",
        )
        # Ch1 grace=72h (Spec 101 FR-003), 2h past = within grace
        within_grace_user = create_mock_user(
            chapter=1,
            relationship_score=Decimal("60.0"),
            last_interaction_at=datetime.now(UTC) - timedelta(hours=2),
            game_status="active",
        )

        mock_user_repo.get_active_users_for_decay = AsyncMock(
            return_value=[overdue_user, within_grace_user]
        )
        mock_user_repo.apply_decay = AsyncMock(return_value=overdue_user)

        processor = DecayProcessor(
            session=mock_session,
            user_repository=mock_user_repo,
            score_history_repository=mock_history_repo,
        )

        summary = await processor.process_all()

        assert "processed" in summary
        assert "decayed" in summary
        assert "game_overs" in summary
        assert summary["processed"] == 2  # Both users checked
        assert summary["decayed"] >= 1  # At least the overdue user

    @pytest.mark.asyncio
    async def test_process_all_filters_inactive_statuses(self):
        """AC-T5.2: Filter out boss_fight, game_over, won statuses."""
        from nikita.engine.decay.processor import DecayProcessor

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_history_repo = AsyncMock()

        # These should be filtered by repository query
        mock_user_repo.get_active_users_for_decay = AsyncMock(return_value=[])

        processor = DecayProcessor(
            session=mock_session,
            user_repository=mock_user_repo,
            score_history_repository=mock_history_repo,
        )

        summary = await processor.process_all()

        assert summary["processed"] == 0
        assert summary["decayed"] == 0

    @pytest.mark.asyncio
    async def test_process_all_tracks_game_overs(self):
        """AC-T5.5: Track game_overs count in summary."""
        from nikita.engine.decay.processor import DecayProcessor

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_history_repo = AsyncMock()

        # Ch5 grace=8h (Spec 101 FR-003), 20h past = overdue; low score hits game over
        low_score_user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("2.0"),  # Will hit 0 after decay
            last_interaction_at=datetime.now(UTC) - timedelta(hours=20),
            game_status="active",
        )
        mock_user_repo.get_active_users_for_decay = AsyncMock(
            return_value=[low_score_user]
        )
        # After applying decay, score will be 0
        updated_user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("0.0"),
            game_status="game_over",
        )
        mock_user_repo.apply_decay = AsyncMock(return_value=updated_user)
        mock_user_repo.update_game_status = AsyncMock(return_value=updated_user)

        processor = DecayProcessor(
            session=mock_session,
            user_repository=mock_user_repo,
            score_history_repository=mock_history_repo,
        )

        summary = await processor.process_all()

        assert summary["game_overs"] >= 1


class TestDecayProcessorBatchSize:
    """Test batch size configuration."""

    @pytest.mark.asyncio
    async def test_default_batch_size(self):
        """AC-T5.3: Default batch size is reasonable."""
        from nikita.engine.decay.processor import DecayProcessor

        processor = DecayProcessor(
            session=AsyncMock(),
            user_repository=AsyncMock(),
            score_history_repository=AsyncMock(),
        )

        assert processor.batch_size == 100  # Default

    @pytest.mark.asyncio
    async def test_configurable_batch_size(self):
        """AC-T5.3: Batch size is configurable."""
        from nikita.engine.decay.processor import DecayProcessor

        processor = DecayProcessor(
            session=AsyncMock(),
            user_repository=AsyncMock(),
            score_history_repository=AsyncMock(),
            batch_size=50,
        )

        assert processor.batch_size == 50


class TestDecayProcessorNoCatchUp:
    """Test no catch-up decay after boss fight (T7.3)."""

    @pytest.mark.asyncio
    async def test_no_catch_up_decay_after_boss_resolved(self):
        """AC-T7.3: No catch-up on missed decay after boss resolved."""
        from nikita.engine.decay.processor import DecayProcessor

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_history_repo = AsyncMock()

        # User was in boss fight for 48 hours, just resolved
        # Their last_interaction_at would have been updated when boss resolved
        user = create_mock_user(
            chapter=2,
            relationship_score=Decimal("70.0"),
            # Last interaction is recent (boss was just resolved)
            last_interaction_at=datetime.now(UTC) - timedelta(hours=2),
            game_status="active",
        )
        mock_user_repo.get_active_users_for_decay = AsyncMock(return_value=[user])

        processor = DecayProcessor(
            session=mock_session,
            user_repository=mock_user_repo,
            score_history_repository=mock_history_repo,
        )

        summary = await processor.process_all()

        # User should not be decayed (within ch2 16h grace)
        assert summary["decayed"] == 0
        mock_user_repo.apply_decay.assert_not_called()


class TestDecayProcessorExceptionNonPropagation:
    """PR 76 Review: touchpoint/push failures must not block decay flow."""

    @pytest.mark.asyncio
    async def test_touchpoint_failure_does_not_block_decay(self):
        """Touchpoint scheduling exception is logged but does not propagate."""
        from nikita.engine.decay.processor import DecayProcessor

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_history_repo = AsyncMock()

        # Score crosses DECAY_WARNING_THRESHOLD (40) → triggers touchpoint branch
        user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("41.0"),
            last_interaction_at=datetime.now(UTC) - timedelta(hours=10),
            game_status="active",
        )
        mock_user_repo.apply_decay = AsyncMock(return_value=user)

        processor = DecayProcessor(
            session=mock_session,
            user_repository=mock_user_repo,
            score_history_repository=mock_history_repo,
        )

        # TouchpointEngine is imported locally in the try block, so patch at source
        mock_engine = AsyncMock()
        mock_engine.schedule_decay_warning = AsyncMock(
            side_effect=RuntimeError("touchpoint DB down")
        )
        with patch(
            "nikita.touchpoints.engine.TouchpointEngine",
            return_value=mock_engine,
        ):
            # Should NOT raise — error is swallowed and logged
            result = await processor.process_user(user)

        assert result is not None
        mock_history_repo.log_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_failure_does_not_block_decay(self):
        """Push notification exception is logged but does not propagate."""
        from nikita.engine.decay.processor import DecayProcessor

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_history_repo = AsyncMock()

        # Score crosses 30 → triggers push notification branch
        user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("31.0"),
            last_interaction_at=datetime.now(UTC) - timedelta(hours=10),
            game_status="active",
        )
        mock_user_repo.apply_decay = AsyncMock(return_value=user)

        processor = DecayProcessor(
            session=mock_session,
            user_repository=mock_user_repo,
            score_history_repository=mock_history_repo,
        )

        # send_push is imported locally in the try block, patch at source
        with patch(
            "nikita.notifications.push.send_push",
            new_callable=AsyncMock,
            side_effect=RuntimeError("push service down"),
        ):
            # Should NOT raise — error is swallowed and logged
            result = await processor.process_user(user)

        assert result is not None
        mock_history_repo.log_event.assert_called_once()
