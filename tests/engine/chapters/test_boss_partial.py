"""Tests for Spec 058 process_partial and three-way dispatch."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from nikita.engine.chapters.boss import BossStateMachine


@pytest.fixture
def boss():
    return BossStateMachine()


@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    user = SimpleNamespace(chapter=3, boss_attempts=1)
    repo.get.return_value = user
    repo.update_game_status.return_value = None
    repo.advance_chapter.return_value = SimpleNamespace(chapter=4, boss_attempts=0)
    repo.increment_boss_attempts.return_value = SimpleNamespace(
        chapter=3, boss_attempts=2
    )
    return repo


class TestProcessPartial:
    """AC-3.2, AC-3.3, AC-3.4, AC-3.5: PARTIAL outcome behavior."""

    @pytest.mark.asyncio
    async def test_no_attempts_increment(self, boss, mock_user_repo):
        """PARTIAL does NOT increment boss_attempts."""
        result = await boss.process_partial(
            user_id="test-user", user_repository=mock_user_repo,
        )
        mock_user_repo.increment_boss_attempts.assert_not_called()
        assert result["attempts"] == 1  # unchanged

    @pytest.mark.asyncio
    async def test_no_chapter_advance(self, boss, mock_user_repo):
        """PARTIAL does NOT advance chapter."""
        result = await boss.process_partial(
            user_id="test-user", user_repository=mock_user_repo,
        )
        mock_user_repo.advance_chapter.assert_not_called()

    @pytest.mark.asyncio
    async def test_sets_active_status(self, boss, mock_user_repo):
        """PARTIAL sets status back to 'active'."""
        result = await boss.process_partial(
            user_id="test-user", user_repository=mock_user_repo,
        )
        mock_user_repo.update_game_status.assert_called_once_with("test-user", "active")
        assert result["game_status"] == "active"

    @pytest.mark.asyncio
    async def test_cool_down_set(self, boss, mock_user_repo):
        """PARTIAL records cool-down timestamp."""
        result = await boss.process_partial(
            user_id="test-user", user_repository=mock_user_repo,
        )
        assert "cool_down_until" in result

    @pytest.mark.asyncio
    async def test_requires_user_repository(self, boss):
        """process_partial requires user_repository."""
        with pytest.raises(ValueError, match="user_repository is required"):
            await boss.process_partial(user_id="test-user")


class TestProcessOutcomeThreeWay:
    """AC-3.1, AC-8.2, AC-8.3: Three-way dispatch."""

    @pytest.mark.asyncio
    async def test_outcome_pass(self, boss, mock_user_repo):
        """outcome='PASS' dispatches to process_pass."""
        result = await boss.process_outcome(
            user_id="test-user",
            user_repository=mock_user_repo,
            outcome="PASS",
        )
        assert result["passed"] is True
        assert result["outcome"] == "PASS"
        mock_user_repo.advance_chapter.assert_called_once()

    @pytest.mark.asyncio
    async def test_outcome_fail(self, boss, mock_user_repo):
        """outcome='FAIL' dispatches to process_fail."""
        result = await boss.process_outcome(
            user_id="test-user",
            user_repository=mock_user_repo,
            outcome="FAIL",
        )
        assert result["passed"] is False
        assert result["outcome"] == "FAIL"
        mock_user_repo.increment_boss_attempts.assert_called_once()

    @pytest.mark.asyncio
    async def test_outcome_partial(self, boss, mock_user_repo):
        """outcome='PARTIAL' dispatches to process_partial."""
        result = await boss.process_outcome(
            user_id="test-user",
            user_repository=mock_user_repo,
            outcome="PARTIAL",
        )
        assert result["passed"] is False
        assert result["outcome"] == "PARTIAL"
        assert result["game_status"] == "active"
        mock_user_repo.advance_chapter.assert_not_called()
        mock_user_repo.increment_boss_attempts.assert_not_called()

    @pytest.mark.asyncio
    async def test_backward_compat_passed_true(self, boss, mock_user_repo):
        """Legacy: passed=True still works (flag OFF)."""
        result = await boss.process_outcome(
            user_id="test-user",
            passed=True,
            user_repository=mock_user_repo,
        )
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_backward_compat_passed_false(self, boss, mock_user_repo):
        """Legacy: passed=False still works (flag OFF)."""
        result = await boss.process_outcome(
            user_id="test-user",
            passed=False,
            user_repository=mock_user_repo,
        )
        assert result["passed"] is False
