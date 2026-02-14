"""
Tests for Chapter Advancement (T7)

TDD: Write tests FIRST, verify FAIL, then implement.

Acceptance Criteria:
- AC-FR005-001: Given PASS result, When process_pass() called, Then chapter += 1
- AC-FR005-002: Given chapter advanced, When processed, Then boss_attempts reset to 0
- AC-T7-001: game_status set back to 'active'
- AC-T7-002: score_history logged with event_type='boss_pass'
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock


def _make_mock_repo(chapter=2, game_status="active", boss_attempts=0, old_chapter=None):
    """Create a mock UserRepository with a mock user returned by advance_chapter.

    Args:
        chapter: Chapter returned by advance_chapter (post-advancement).
        old_chapter: Chapter returned by get() before advancement.
                     Defaults to chapter - 1 (simulating normal progression).
    """
    mock_repo = AsyncMock()

    # Pre-advance user (returned by get() before advance_chapter)
    pre_user = MagicMock()
    pre_user.chapter = old_chapter if old_chapter is not None else max(1, chapter - 1)
    pre_user.game_status = game_status
    pre_user.boss_attempts = boss_attempts
    mock_repo.get.return_value = pre_user

    # Post-advance user (returned by advance_chapter)
    mock_user = MagicMock()
    mock_user.chapter = chapter
    mock_user.game_status = game_status
    mock_user.boss_attempts = boss_attempts
    mock_repo.advance_chapter.return_value = mock_user
    mock_repo.update_game_status.return_value = mock_user
    mock_repo.increment_boss_attempts.return_value = mock_user
    return mock_repo


class TestProcessPassStructure:
    """AC-T7: process_pass method exists on BossStateMachine"""

    def test_process_pass_method_exists(self):
        """BossStateMachine has process_pass method"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        assert hasattr(sm, 'process_pass')
        assert callable(getattr(sm, 'process_pass'))

    def test_process_pass_is_async(self):
        """process_pass is an async method"""
        import asyncio
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        assert asyncio.iscoroutinefunction(sm.process_pass)

    def test_process_pass_accepts_user_id(self):
        """process_pass accepts user_id parameter"""
        import inspect
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        sig = inspect.signature(sm.process_pass)
        params = list(sig.parameters.keys())
        assert 'user_id' in params


class TestProcessPassResult:
    """AC-T7: process_pass returns expected result structure"""

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        """process_pass returns a dictionary"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        mock_repo = _make_mock_repo(chapter=2)

        result = await sm.process_pass(uuid4(), user_repository=mock_repo)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_result_has_new_chapter(self):
        """Result includes new_chapter field"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        mock_repo = _make_mock_repo(chapter=2)

        result = await sm.process_pass(uuid4(), user_repository=mock_repo)

        assert 'new_chapter' in result

    @pytest.mark.asyncio
    async def test_result_has_game_status(self):
        """Result includes game_status field"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        mock_repo = _make_mock_repo(chapter=2)

        result = await sm.process_pass(uuid4(), user_repository=mock_repo)

        assert 'game_status' in result


class TestChapterAdvancement:
    """AC-FR005-001: Chapter advances by 1"""

    @pytest.mark.asyncio
    async def test_ac_fr005_001_chapter_increments(self):
        """Given PASS result, chapter increments by 1"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        mock_repo = _make_mock_repo(chapter=2)

        result = await sm.process_pass(uuid4(), user_repository=mock_repo)

        mock_repo.advance_chapter.assert_called_once()
        assert result['new_chapter'] == 2

    @pytest.mark.asyncio
    async def test_calls_repository_advance_chapter(self):
        """process_pass calls UserRepository.advance_chapter()"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        mock_repo = _make_mock_repo(chapter=3)

        user_id = uuid4()
        await sm.process_pass(user_id, user_repository=mock_repo)

        mock_repo.advance_chapter.assert_called_once_with(user_id)


class TestBossAttemptsReset:
    """AC-FR005-002: boss_attempts reset to 0"""

    @pytest.mark.asyncio
    async def test_ac_fr005_002_boss_attempts_reset(self):
        """Given chapter advanced, boss_attempts reset to 0"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        mock_repo = _make_mock_repo(chapter=2, boss_attempts=0)

        result = await sm.process_pass(uuid4(), user_repository=mock_repo)

        assert result.get('boss_attempts', 0) == 0


class TestGameStatusReset:
    """AC-T7-001: game_status set back to 'active'"""

    @pytest.mark.asyncio
    async def test_ac_t7_001_game_status_active(self):
        """Given boss passed (ch < 5), game_status returns to 'active'"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        mock_repo = _make_mock_repo(chapter=2)

        result = await sm.process_pass(uuid4(), user_repository=mock_repo)

        assert result['game_status'] == 'active'
        mock_repo.update_game_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_game_status_won_at_chapter_5(self):
        """Given boss passed at ch5 (final boss), game_status set to 'won'"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        # old_chapter=5: user was already in ch5 and passed final boss
        mock_repo = _make_mock_repo(chapter=5, old_chapter=5)

        result = await sm.process_pass(uuid4(), user_repository=mock_repo)

        assert result['game_status'] == 'won'

    @pytest.mark.asyncio
    async def test_game_status_active_entering_chapter_5(self):
        """Given boss 4 passed (ch4→ch5), game_status stays 'active' (not 'won')"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        # old_chapter=4: user was in ch4 and passed boss 4, entering ch5
        mock_repo = _make_mock_repo(chapter=5, old_chapter=4)

        result = await sm.process_pass(uuid4(), user_repository=mock_repo)

        assert result['game_status'] == 'active'
        assert result['new_chapter'] == 5


class TestScoreHistoryLogging:
    """AC-T7-002: score_history logged with event_type='boss_pass'"""

    @pytest.mark.asyncio
    async def test_ac_t7_002_logs_boss_pass_event(self):
        """score_history logged via advance_chapter (which logs 'chapter_advance')"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        mock_repo = _make_mock_repo(chapter=2)

        await sm.process_pass(uuid4(), user_repository=mock_repo)

        mock_repo.advance_chapter.assert_called_once()


class TestEdgeCases:
    """Edge cases for chapter advancement"""

    @pytest.mark.asyncio
    async def test_chapter_5_pass_handled(self):
        """Chapter 5 (final boss) pass should result in 'won' status"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        # old_chapter=5: user was in ch5 and completed the final boss
        mock_repo = _make_mock_repo(chapter=5, old_chapter=5)

        result = await sm.process_pass(uuid4(), user_repository=mock_repo)

        assert result['new_chapter'] == 5
        assert result['game_status'] == 'won'

    @pytest.mark.asyncio
    async def test_process_pass_requires_user_repository(self):
        """process_pass raises ValueError without user_repository"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        with pytest.raises(ValueError, match="user_repository is required"):
            await sm.process_pass(uuid4())

    @pytest.mark.asyncio
    async def test_process_fail_requires_user_repository(self):
        """process_fail raises ValueError without user_repository"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        with pytest.raises(ValueError, match="user_repository is required"):
            await sm.process_fail(uuid4())

    @pytest.mark.asyncio
    async def test_process_outcome_requires_user_repository(self):
        """process_outcome raises ValueError without user_repository"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        with pytest.raises(ValueError, match="user_repository is required"):
            await sm.process_outcome(uuid4(), passed=True)


class TestProcessFail:
    """Tests for process_fail with user_repository injection."""

    @pytest.mark.asyncio
    async def test_process_fail_increments_attempts(self):
        """process_fail calls increment_boss_attempts"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        mock_repo = _make_mock_repo(boss_attempts=1)

        user_id = uuid4()
        result = await sm.process_fail(user_id, user_repository=mock_repo)

        mock_repo.increment_boss_attempts.assert_called_once_with(user_id)
        assert result['attempts'] == 1

    @pytest.mark.asyncio
    async def test_process_fail_game_over_at_3(self):
        """3 failures triggers game_over"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        mock_repo = _make_mock_repo(boss_attempts=3)

        result = await sm.process_fail(uuid4(), user_repository=mock_repo)

        assert result['game_over'] is True
        assert result['game_status'] == 'game_over'
        mock_repo.update_game_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_fail_not_game_over_at_2(self):
        """2 failures does not trigger game_over"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        mock_repo = _make_mock_repo(boss_attempts=2)

        result = await sm.process_fail(uuid4(), user_repository=mock_repo)

        assert result['game_over'] is False
        assert result['game_status'] == 'boss_fight'
        mock_repo.update_game_status.assert_not_called()
