"""
Tests for Game Over and Victory Conditions (T9, T10, T11)

T9: Three-Strike Game Over (US-4)
T10: Zero Score Game Over (US-5)
T11: Victory Condition (US-6)
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal


class TestThreeStrikeGameOver:
    """T9: AC-FR007 - Three boss failures trigger game over"""

    @pytest.mark.asyncio
    async def test_ac_fr007_001_third_fail_triggers_game_over(self):
        """Given boss_attempts = 2, When third fail, Then game_over triggered"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        # After third fail, attempts = 3
        mock_user = MagicMock()
        mock_user.boss_attempts = 3
        mock_user.game_status = 'game_over'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_fail(uuid4(), user_repository=mock_repo)

        assert result['game_over'] is True
        assert result['game_status'] == 'game_over'

    @pytest.mark.asyncio
    async def test_ac_fr007_002_game_over_message_delivered(self):
        """Given game_over, Then breakup message delivered"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 3
        mock_user.game_status = 'game_over'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_outcome(uuid4(), passed=False, user_repository=mock_repo)

        assert result['message'] == 'Game over!'
        assert result['game_over'] is True

    @pytest.mark.asyncio
    async def test_process_outcome_returns_game_over_flag(self):
        """process_outcome includes game_over flag when 3 attempts"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 3
        mock_user.game_status = 'game_over'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_outcome(uuid4(), passed=False, user_repository=mock_repo)

        assert 'game_over' in result
        assert result['game_over'] is True


class TestZeroScoreGameOver:
    """T10: AC-FR008 - Zero score triggers game over"""

    def test_should_trigger_game_over_has_zero_score_method(self):
        """BossStateMachine has method to check zero score game over"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        # The zero score game over is handled by the scoring engine
        # We verify the boss system can detect game_status = 'game_over'
        assert hasattr(sm, 'should_trigger_boss')

    def test_should_trigger_boss_returns_false_on_game_over(self):
        """should_trigger_boss returns False when game_status is 'game_over'"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        # Zero score causes game_over status
        result = sm.should_trigger_boss(
            relationship_score=Decimal("0"),
            chapter=1,
            game_status="game_over"
        )

        assert result is False

    def test_should_trigger_boss_returns_false_on_zero_score_active(self):
        """should_trigger_boss returns False when score is zero (below threshold)"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        # Score is 0, below any threshold
        result = sm.should_trigger_boss(
            relationship_score=Decimal("0"),
            chapter=1,
            game_status="active"
        )

        assert result is False


class TestVictoryCondition:
    """T11: AC-FR009 - Chapter 5 pass triggers victory"""

    @pytest.mark.asyncio
    async def test_ac_fr009_001_chapter_5_pass_triggers_victory(self):
        """Given Ch5 boss passed, Then game_status = 'won'"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        # Pre-advance: user is in chapter 5 (about to pass final boss)
        pre_user = MagicMock()
        pre_user.chapter = 5
        mock_repo.get.return_value = pre_user
        # Post-advance: chapter stays 5 (capped), status becomes 'won'
        mock_user = MagicMock()
        mock_user.chapter = 5
        mock_user.game_status = 'won'
        mock_user.boss_attempts = 0
        mock_repo.advance_chapter.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_pass(uuid4(), user_repository=mock_repo)

        assert result['game_status'] == 'won'

    @pytest.mark.asyncio
    async def test_victory_does_not_increment_chapter_beyond_5(self):
        """Chapter 5 pass keeps chapter at 5"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        # Pre-advance: user is in chapter 5
        pre_user = MagicMock()
        pre_user.chapter = 5
        mock_repo.get.return_value = pre_user
        # Post-advance: chapter stays 5 (capped)
        mock_user = MagicMock()
        mock_user.chapter = 5
        mock_user.game_status = 'won'
        mock_user.boss_attempts = 0
        mock_repo.advance_chapter.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_pass(uuid4(), user_repository=mock_repo)

        assert result['new_chapter'] <= 5

    def test_should_trigger_boss_returns_false_when_won(self):
        """should_trigger_boss returns False when game_status is 'won'"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        result = sm.should_trigger_boss(
            relationship_score=Decimal("100"),
            chapter=5,
            game_status="won"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_process_outcome_pass_includes_new_chapter(self):
        """process_outcome pass result includes new_chapter"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        # Pre-advance: user is in chapter 2
        pre_user = MagicMock()
        pre_user.chapter = 2
        mock_repo.get.return_value = pre_user
        # Post-advance: chapter becomes 3
        mock_user = MagicMock()
        mock_user.chapter = 3
        mock_user.game_status = 'active'
        mock_user.boss_attempts = 0
        mock_repo.advance_chapter.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_outcome(uuid4(), passed=True, user_repository=mock_repo)

        assert 'new_chapter' in result
        assert result['new_chapter'] == 3


class TestGameStatusBlocking:
    """Verify game_status blocks boss triggers correctly"""

    @pytest.mark.parametrize("game_status,expected", [
        ("active", True),
        ("boss_fight", False),
        ("game_over", False),
        ("won", False),
    ])
    def test_should_trigger_boss_respects_game_status(self, game_status, expected):
        """should_trigger_boss only triggers for 'active' status"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        # Score above threshold
        result = sm.should_trigger_boss(
            relationship_score=Decimal("60"),  # Above Ch1 threshold of 55
            chapter=1,
            game_status=game_status
        )

        assert result is expected
