"""Tests for Spec 058 backward compatibility (flag OFF).

AC-8.2, AC-8.4: All existing boss behavior preserved when flag OFF.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from nikita.engine.chapters.boss import BossStateMachine
from nikita.engine.chapters.judgment import BossResult, JudgmentResult


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
        chapter=3, boss_attempts=2,
    )
    return repo


class TestBossResultBackwardCompat:
    """BossResult enum backward compat."""

    def test_pass_exists(self):
        assert BossResult.PASS.value == "PASS"

    def test_fail_exists(self):
        assert BossResult.FAIL.value == "FAIL"

    def test_partial_does_not_break_existing(self):
        # PARTIAL exists but doesn't affect PASS/FAIL usage
        assert BossResult("PASS") == BossResult.PASS
        assert BossResult("FAIL") == BossResult.FAIL


class TestProcessOutcomeBackwardCompat:
    """process_outcome with passed: bool (legacy) still works."""

    @pytest.mark.asyncio
    async def test_passed_true_advances_chapter(self, boss, mock_user_repo):
        result = await boss.process_outcome(
            user_id="test-user",
            passed=True,
            user_repository=mock_user_repo,
        )
        assert result["passed"] is True
        assert "new_chapter" in result
        mock_user_repo.advance_chapter.assert_called_once()

    @pytest.mark.asyncio
    async def test_passed_false_increments_attempts(self, boss, mock_user_repo):
        result = await boss.process_outcome(
            user_id="test-user",
            passed=False,
            user_repository=mock_user_repo,
        )
        assert result["passed"] is False
        assert "attempts" in result
        mock_user_repo.increment_boss_attempts.assert_called_once()


class TestSingleTurnFlowPreserved:
    """Single-turn flow unchanged when flag OFF."""

    @pytest.mark.asyncio
    async def test_no_partial_behavior_when_flag_off(self, boss, mock_user_repo):
        """process_outcome with passed=bool has no PARTIAL logic."""
        # Legacy call: only PASS or FAIL
        pass_result = await boss.process_outcome(
            user_id="test-user", passed=True,
            user_repository=mock_user_repo,
        )
        assert "outcome" not in pass_result  # no outcome key in legacy
        assert pass_result["passed"] is True

    @pytest.mark.asyncio
    async def test_should_trigger_boss_unchanged(self, boss):
        """should_trigger_boss pure function unchanged."""
        from decimal import Decimal
        assert boss.should_trigger_boss(Decimal("55"), 1, "active") is True
        assert boss.should_trigger_boss(Decimal("54"), 1, "active") is False
        assert boss.should_trigger_boss(Decimal("55"), 1, "boss_fight") is False

    @pytest.mark.asyncio
    async def test_initiate_boss_unchanged(self, boss):
        """initiate_boss returns prompt dict as before."""
        result = await boss.initiate_boss("test-user", chapter=3)
        assert "chapter" in result
        assert "challenge_context" in result
        assert "success_criteria" in result
        assert "in_character_opening" in result


class TestJudgmentResultBackwardCompat:
    """JudgmentResult model backward compat."""

    def test_judgment_result_without_confidence(self):
        """Old code that doesn't pass confidence still works."""
        result = JudgmentResult(outcome="PASS", reasoning="Good job")
        assert result.outcome == "PASS"
        assert result.confidence == 1.0  # default

    def test_judgment_result_with_confidence(self):
        """New code with confidence field works."""
        result = JudgmentResult(outcome="PARTIAL", reasoning="Effort", confidence=0.6)
        assert result.confidence == 0.6
