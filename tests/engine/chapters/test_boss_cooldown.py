"""Tests for boss PARTIAL cooldown persistence (Spec 101 FR-001)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from nikita.engine.chapters.boss import BossStateMachine


class TestShouldTriggerBossCooldown:
    """Tests for cooldown check in should_trigger_boss()."""

    def setup_method(self):
        self.boss = BossStateMachine()

    def test_cooldown_blocks_boss_trigger(self):
        """Active cooldown should prevent boss trigger."""
        future = datetime.now(UTC) + timedelta(hours=12)
        result = self.boss.should_trigger_boss(
            relationship_score=Decimal("60.00"),
            chapter=1,
            game_status="active",
            cool_down_until=future,
        )
        assert result is False

    def test_expired_cooldown_allows_trigger(self):
        """Expired cooldown should allow boss trigger."""
        past = datetime.now(UTC) - timedelta(hours=1)
        result = self.boss.should_trigger_boss(
            relationship_score=Decimal("60.00"),
            chapter=1,
            game_status="active",
            cool_down_until=past,
        )
        assert result is True

    def test_none_cooldown_allows_trigger(self):
        """No cooldown (None) should allow boss trigger."""
        result = self.boss.should_trigger_boss(
            relationship_score=Decimal("60.00"),
            chapter=1,
            game_status="active",
            cool_down_until=None,
        )
        assert result is True

    def test_default_parameter_allows_trigger(self):
        """Default parameter (omitted) should allow boss trigger."""
        result = self.boss.should_trigger_boss(
            relationship_score=Decimal("60.00"),
            chapter=1,
            game_status="active",
        )
        assert result is True


class TestProcessPartialPersistsCooldown:
    """Tests for cooldown persistence in process_partial()."""

    @pytest.mark.asyncio
    async def test_process_partial_calls_set_cool_down(self):
        """process_partial() should call set_cool_down on repository."""
        boss = BossStateMachine()
        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 1
        mock_repo.get.return_value = mock_user

        result = await boss.process_partial(
            user_id="test-user-id",
            user_repository=mock_repo,
        )

        # Verify set_cool_down was called
        mock_repo.set_cool_down.assert_awaited_once()
        call_args = mock_repo.set_cool_down.call_args
        assert call_args[0][0] == "test-user-id"
        # Verify cooldown is ~24h in the future
        cool_down = call_args[0][1]
        assert isinstance(cool_down, datetime)
        expected = datetime.now(UTC) + timedelta(hours=24)
        # Allow 5 seconds tolerance
        assert abs((cool_down - expected).total_seconds()) < 5

    @pytest.mark.asyncio
    async def test_process_partial_returns_cooldown_in_response(self):
        """process_partial() should include cool_down_until in response."""
        boss = BossStateMachine()
        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 0
        mock_repo.get.return_value = mock_user

        result = await boss.process_partial(
            user_id="test-user-id",
            user_repository=mock_repo,
        )

        assert "cool_down_until" in result
        assert result["game_status"] == "active"
