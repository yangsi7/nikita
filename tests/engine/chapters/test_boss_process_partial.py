"""Tests for Spec 058 process_partial and 3-way process_outcome.

Tests PARTIAL outcome processing and the three-way dispatch in process_outcome.

AC refs: AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-3.5, AC-8.2, AC-8.3
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.engine.chapters.boss import BossStateMachine
from nikita.engine.chapters.judgment import BossResult


# ============================================================================
# process_partial — AC-3.2, AC-3.3, AC-3.4, AC-3.5
# ============================================================================


class TestProcessPartial:
    """PARTIAL outcome: no increment, status active, cool-down."""

    @pytest.fixture
    def boss_sm(self):
        return BossStateMachine()

    @pytest.fixture
    def mock_user_repo(self):
        repo = AsyncMock()
        user = MagicMock()
        user.boss_attempts = 2
        repo.get = AsyncMock(return_value=user)
        repo.update_game_status = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_returns_active_status(self, boss_sm, mock_user_repo):
        result = await boss_sm.process_partial(uuid4(), user_repository=mock_user_repo)
        assert result["game_status"] == "active"

    @pytest.mark.asyncio
    async def test_does_not_increment_attempts(self, boss_sm, mock_user_repo):
        result = await boss_sm.process_partial(uuid4(), user_repository=mock_user_repo)
        # attempts unchanged from user.boss_attempts
        assert result["attempts"] == 2

    @pytest.mark.asyncio
    async def test_has_cool_down_until(self, boss_sm, mock_user_repo):
        result = await boss_sm.process_partial(uuid4(), user_repository=mock_user_repo)
        assert "cool_down_until" in result
        assert isinstance(result["cool_down_until"], str)

    @pytest.mark.asyncio
    async def test_cool_down_is_24h(self, boss_sm, mock_user_repo):
        before = datetime.now(timezone.utc)
        result = await boss_sm.process_partial(uuid4(), user_repository=mock_user_repo)
        cool_down = datetime.fromisoformat(result["cool_down_until"])
        # Should be approximately 24h from now
        delta_hours = (cool_down - before).total_seconds() / 3600
        assert 23.9 < delta_hours < 24.1

    @pytest.mark.asyncio
    async def test_sets_game_status_to_active(self, boss_sm, mock_user_repo):
        uid = uuid4()
        await boss_sm.process_partial(uid, user_repository=mock_user_repo)
        mock_user_repo.update_game_status.assert_called_once_with(uid, "active")

    @pytest.mark.asyncio
    async def test_requires_user_repository(self, boss_sm):
        with pytest.raises(ValueError, match="user_repository"):
            await boss_sm.process_partial(uuid4())


# ============================================================================
# process_outcome — 3-way dispatch (AC-3.1, AC-8.2, AC-8.3)
# ============================================================================


class TestProcessOutcomeThreeWay:
    """process_outcome dispatches to pass/fail/partial based on outcome string."""

    @pytest.fixture
    def boss_sm(self):
        return BossStateMachine()

    @pytest.fixture
    def mock_user_repo(self):
        repo = AsyncMock()
        user = MagicMock()
        user.id = uuid4()
        user.chapter = 2
        user.boss_attempts = 1
        repo.get = AsyncMock(return_value=user)
        repo.advance_chapter = AsyncMock(return_value=user)
        repo.increment_boss_attempts = AsyncMock(return_value=user)
        repo.update_game_status = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_outcome_pass_dispatches_correctly(self, boss_sm, mock_user_repo):
        result = await boss_sm.process_outcome(
            uuid4(),
            user_repository=mock_user_repo,
            outcome="PASS",
        )
        assert result["passed"] is True
        assert result["outcome"] == "PASS"

    @pytest.mark.asyncio
    async def test_outcome_fail_dispatches_correctly(self, boss_sm, mock_user_repo):
        mock_user_repo.increment_boss_attempts.return_value.boss_attempts = 1
        result = await boss_sm.process_outcome(
            uuid4(),
            user_repository=mock_user_repo,
            outcome="FAIL",
        )
        assert result["passed"] is False
        assert result["outcome"] == "FAIL"

    @pytest.mark.asyncio
    async def test_outcome_partial_dispatches_correctly(self, boss_sm, mock_user_repo):
        result = await boss_sm.process_outcome(
            uuid4(),
            user_repository=mock_user_repo,
            outcome="PARTIAL",
        )
        assert result["passed"] is False
        assert result["outcome"] == "PARTIAL"
        assert "cool_down_until" in result

    @pytest.mark.asyncio
    async def test_legacy_bool_true_still_works(self, boss_sm, mock_user_repo):
        """Backward compat: passed=True still works when outcome not provided."""
        result = await boss_sm.process_outcome(
            uuid4(),
            passed=True,
            user_repository=mock_user_repo,
        )
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_legacy_bool_false_still_works(self, boss_sm, mock_user_repo):
        """Backward compat: passed=False still works when outcome not provided."""
        mock_user_repo.increment_boss_attempts.return_value.boss_attempts = 1
        result = await boss_sm.process_outcome(
            uuid4(),
            passed=False,
            user_repository=mock_user_repo,
        )
        assert result["passed"] is False

    @pytest.mark.asyncio
    async def test_outcome_takes_priority_over_passed(self, boss_sm, mock_user_repo):
        """outcome= kwarg takes priority over passed= when both provided."""
        mock_user_repo.increment_boss_attempts.return_value.boss_attempts = 1
        result = await boss_sm.process_outcome(
            uuid4(),
            passed=True,  # Would normally be pass
            user_repository=mock_user_repo,
            outcome="FAIL",  # But outcome overrides
        )
        assert result["outcome"] == "FAIL"
        assert result["passed"] is False


# ============================================================================
# BossResult.PARTIAL enum value
# ============================================================================


class TestBossResultPartial:
    """BossResult enum has PARTIAL value (AC-3.1)."""

    def test_partial_value_exists(self):
        assert hasattr(BossResult, "PARTIAL")
        assert BossResult.PARTIAL.value == "PARTIAL"

    def test_all_three_outcomes(self):
        assert BossResult.PASS.value == "PASS"
        assert BossResult.FAIL.value == "FAIL"
        assert BossResult.PARTIAL.value == "PARTIAL"

    def test_exactly_three_members(self):
        assert len(BossResult) == 3
