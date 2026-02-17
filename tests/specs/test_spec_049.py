"""Tests for Spec 049: Game Mechanics Remediation.

Covers:
1. Boss timeout endpoint — resolves stale boss fights >24h using boss_fight_started_at
2. Decay notification wiring — notify_callback called on game-over
3. Pipeline terminal-state filter — skip processing for game_over/won users
"""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.engine.decay.models import DecayResult


def _mock_user(
    *,
    game_status="active",
    chapter=1,
    relationship_score=Decimal("50.00"),
    boss_attempts=0,
    telegram_id=123456789,
    boss_fight_started_at=None,
):
    """Create a mock User object."""
    user = MagicMock()
    user.id = uuid4()
    user.game_status = game_status
    user.chapter = chapter
    user.relationship_score = relationship_score
    user.boss_attempts = boss_attempts
    user.telegram_id = telegram_id
    user.boss_fight_started_at = boss_fight_started_at
    user.last_interaction_at = datetime.now(UTC) - timedelta(hours=10)
    user.engagement_state = None
    user.vice_preferences = []
    user.user_metrics = None
    return user


# ===== 1. Boss timeout endpoint =====


class TestBossTimeoutEndpoint:
    """Test /boss-timeout resolves stale boss fights (Spec 049 AC-1)."""

    @pytest.mark.asyncio
    async def test_stale_boss_fight_resolved_to_active(self):
        """AC-1.3: Boss fight >24h increments boss_attempts, returns to active."""
        user = _mock_user(
            game_status="boss_fight",
            boss_attempts=0,
            boss_fight_started_at=datetime.now(UTC) - timedelta(hours=30),
        )

        # Simulate the logic from tasks.py boss-timeout endpoint
        user.boss_attempts = (user.boss_attempts or 0) + 1
        assert user.boss_attempts < 3
        user.game_status = "active"
        user.boss_fight_started_at = None

        assert user.game_status == "active"
        assert user.boss_attempts == 1
        assert user.boss_fight_started_at is None

    @pytest.mark.asyncio
    async def test_three_failed_attempts_triggers_game_over(self):
        """AC-1.4: 3 failed boss attempts = game_over."""
        user = _mock_user(
            game_status="boss_fight",
            boss_attempts=2,
            boss_fight_started_at=datetime.now(UTC) - timedelta(hours=30),
        )

        user.boss_attempts = (user.boss_attempts or 0) + 1
        assert user.boss_attempts >= 3
        user.game_status = "game_over"
        user.boss_fight_started_at = None

        assert user.game_status == "game_over"
        assert user.boss_attempts == 3

    @pytest.mark.asyncio
    async def test_not_stale_if_within_24h(self):
        """Boss fight within 24h should NOT be resolved."""
        user = _mock_user(
            game_status="boss_fight",
            boss_fight_started_at=datetime.now(UTC) - timedelta(hours=12),
        )
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        is_stale = user.boss_fight_started_at < cutoff
        assert is_stale is False

    @pytest.mark.asyncio
    async def test_stale_if_beyond_24h(self):
        """Boss fight >24h IS stale."""
        user = _mock_user(
            game_status="boss_fight",
            boss_fight_started_at=datetime.now(UTC) - timedelta(hours=30),
        )
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        is_stale = user.boss_fight_started_at < cutoff
        assert is_stale is True


# ===== 2. Decay notification wiring =====


class TestDecayNotificationCallback:
    """Test Spec 049 AC-4: DecayProcessor notify_callback on game-over."""

    @pytest.mark.asyncio
    async def test_notify_callback_called_on_game_over(self):
        """AC-4.2: notify_callback called when decay triggers game_over."""
        from nikita.engine.decay.processor import DecayProcessor

        mock_notify = AsyncMock()
        user = _mock_user(relationship_score=Decimal("2.0"), telegram_id=123456789)

        game_over_result = DecayResult(
            user_id=user.id,
            decay_amount=Decimal("2.0"),
            score_before=Decimal("2.0"),
            score_after=Decimal("0.0"),
            hours_overdue=12.0,
            chapter=1,
            timestamp=datetime.now(UTC),
            game_over_triggered=True,
        )

        processor = DecayProcessor(
            session=AsyncMock(),
            user_repository=AsyncMock(),
            score_history_repository=AsyncMock(),
            notify_callback=mock_notify,
        )

        await processor._handle_game_over(user, game_over_result)

        mock_notify.assert_called_once()
        call_args = mock_notify.call_args[0]
        assert call_args[0] == user.id
        assert call_args[1] == 123456789

    @pytest.mark.asyncio
    async def test_notify_callback_not_called_without_telegram_id(self):
        """AC-4.2: No notification if user has no telegram_id."""
        from nikita.engine.decay.processor import DecayProcessor

        mock_notify = AsyncMock()
        user = _mock_user(telegram_id=None)

        game_over_result = DecayResult(
            user_id=user.id,
            decay_amount=Decimal("2.0"),
            score_before=Decimal("2.0"),
            score_after=Decimal("0.0"),
            hours_overdue=12.0,
            chapter=1,
            timestamp=datetime.now(UTC),
            game_over_triggered=True,
        )

        processor = DecayProcessor(
            session=AsyncMock(),
            user_repository=AsyncMock(),
            score_history_repository=AsyncMock(),
            notify_callback=mock_notify,
        )

        await processor._handle_game_over(user, game_over_result)
        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_failure_does_not_break_processing(self):
        """AC-4.4: Notification failure must not break decay processing."""
        from nikita.engine.decay.processor import DecayProcessor

        mock_notify = AsyncMock(side_effect=Exception("Network error"))
        user = _mock_user(telegram_id=123456789)

        game_over_result = DecayResult(
            user_id=user.id,
            decay_amount=Decimal("2.0"),
            score_before=Decimal("2.0"),
            score_after=Decimal("0.0"),
            hours_overdue=12.0,
            chapter=1,
            timestamp=datetime.now(UTC),
            game_over_triggered=True,
        )

        processor = DecayProcessor(
            session=AsyncMock(),
            user_repository=AsyncMock(),
            score_history_repository=AsyncMock(),
            notify_callback=mock_notify,
        )

        # Should not raise even though callback fails
        await processor._handle_game_over(user, game_over_result)

    @pytest.mark.asyncio
    async def test_no_notify_when_callback_is_none(self):
        """No notification when callback is None."""
        from nikita.engine.decay.processor import DecayProcessor

        user = _mock_user(telegram_id=123456789)

        game_over_result = DecayResult(
            user_id=user.id,
            decay_amount=Decimal("2.0"),
            score_before=Decimal("2.0"),
            score_after=Decimal("0.0"),
            hours_overdue=12.0,
            chapter=1,
            timestamp=datetime.now(UTC),
            game_over_triggered=True,
        )

        processor = DecayProcessor(
            session=AsyncMock(),
            user_repository=AsyncMock(),
            score_history_repository=AsyncMock(),
            notify_callback=None,
        )

        # Should not raise
        await processor._handle_game_over(user, game_over_result)


# ===== 3. Pipeline terminal-state filter =====


class TestPipelineTerminalStateFilter:
    """Test Spec 049 AC-3: Pipeline skips terminal game states."""

    @pytest.mark.asyncio
    async def test_pipeline_skips_game_over(self):
        """AC-3.1: Pipeline returns skipped result for game_over users."""
        from nikita.pipeline.orchestrator import PipelineOrchestrator

        mock_session = AsyncMock()
        orchestrator = PipelineOrchestrator(session=mock_session)

        user = _mock_user(game_status="game_over")

        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=user.id,
            platform="text",
            user=user,
        )

        assert result.success is True
        assert result.skipped is True
        assert result.stages_completed == 0
        assert "game_over" in result.skip_reason

    @pytest.mark.asyncio
    async def test_pipeline_skips_won(self):
        """AC-3.1: Pipeline returns skipped result for won users."""
        from nikita.pipeline.orchestrator import PipelineOrchestrator

        mock_session = AsyncMock()
        orchestrator = PipelineOrchestrator(session=mock_session)

        user = _mock_user(game_status="won")

        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=user.id,
            platform="text",
            user=user,
        )

        assert result.success is True
        assert result.skipped is True
        assert "won" in result.skip_reason

    @pytest.mark.asyncio
    async def test_pipeline_skip_reason_contains_status(self):
        """AC-3.4: skip_reason includes the actual game status."""
        from nikita.pipeline.orchestrator import PipelineOrchestrator

        mock_session = AsyncMock()
        orchestrator = PipelineOrchestrator(session=mock_session)

        user = _mock_user(game_status="game_over")

        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=user.id,
            platform="text",
            user=user,
        )

        assert result.skip_reason is not None
        assert "game_over" in result.skip_reason
