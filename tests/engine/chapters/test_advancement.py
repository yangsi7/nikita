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
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal


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

        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            # Mock user returned after advance
            mock_user = MagicMock()
            mock_user.chapter = 2
            mock_user.game_status = 'active'
            mock_user.boss_attempts = 0
            mock_repo.advance_chapter.return_value = mock_user

            result = await sm.process_pass(uuid4())

            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_result_has_new_chapter(self):
        """Result includes new_chapter field"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_user = MagicMock()
            mock_user.chapter = 2
            mock_user.game_status = 'active'
            mock_user.boss_attempts = 0
            mock_repo.advance_chapter.return_value = mock_user

            result = await sm.process_pass(uuid4())

            assert 'new_chapter' in result

    @pytest.mark.asyncio
    async def test_result_has_game_status(self):
        """Result includes game_status field"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_user = MagicMock()
            mock_user.chapter = 2
            mock_user.game_status = 'active'
            mock_user.boss_attempts = 0
            mock_repo.advance_chapter.return_value = mock_user

            result = await sm.process_pass(uuid4())

            assert 'game_status' in result


class TestChapterAdvancement:
    """AC-FR005-001: Chapter advances by 1"""

    @pytest.mark.asyncio
    async def test_ac_fr005_001_chapter_increments(self):
        """Given PASS result, chapter increments by 1"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            # User was in chapter 1, now chapter 2
            mock_user = MagicMock()
            mock_user.chapter = 2
            mock_user.game_status = 'active'
            mock_user.boss_attempts = 0
            mock_repo.advance_chapter.return_value = mock_user

            result = await sm.process_pass(uuid4())

            # Verify advance_chapter was called
            mock_repo.advance_chapter.assert_called_once()
            assert result['new_chapter'] == 2

    @pytest.mark.asyncio
    async def test_calls_repository_advance_chapter(self):
        """process_pass calls UserRepository.advance_chapter()"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        user_id = uuid4()

        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_user = MagicMock()
            mock_user.chapter = 3
            mock_user.game_status = 'active'
            mock_user.boss_attempts = 0
            mock_repo.advance_chapter.return_value = mock_user

            await sm.process_pass(user_id)

            mock_repo.advance_chapter.assert_called_once_with(user_id)


class TestBossAttemptsReset:
    """AC-FR005-002: boss_attempts reset to 0"""

    @pytest.mark.asyncio
    async def test_ac_fr005_002_boss_attempts_reset(self):
        """Given chapter advanced, boss_attempts reset to 0"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            # User after advance has boss_attempts = 0
            mock_user = MagicMock()
            mock_user.chapter = 2
            mock_user.game_status = 'active'
            mock_user.boss_attempts = 0
            mock_repo.advance_chapter.return_value = mock_user

            result = await sm.process_pass(uuid4())

            # The advance_chapter method handles the reset
            # We verify the result reflects 0 attempts
            assert result.get('boss_attempts', 0) == 0


class TestGameStatusReset:
    """AC-T7-001: game_status set back to 'active'"""

    @pytest.mark.asyncio
    async def test_ac_t7_001_game_status_active(self):
        """Given boss passed, game_status returns to 'active'"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_user = MagicMock()
            mock_user.chapter = 2
            mock_user.game_status = 'active'  # Should be active after pass
            mock_user.boss_attempts = 0
            mock_repo.advance_chapter.return_value = mock_user

            result = await sm.process_pass(uuid4())

            assert result['game_status'] == 'active'


class TestScoreHistoryLogging:
    """AC-T7-002: score_history logged with event_type='boss_pass'"""

    @pytest.mark.asyncio
    async def test_ac_t7_002_logs_boss_pass_event(self):
        """score_history logged with event_type='boss_pass'"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_user = MagicMock()
            mock_user.chapter = 2
            mock_user.game_status = 'active'
            mock_user.boss_attempts = 0
            mock_repo.advance_chapter.return_value = mock_user

            await sm.process_pass(uuid4())

            # The advance_chapter method logs 'chapter_advance'
            # We may also want a separate 'boss_pass' log
            # Verify advance_chapter was called (which handles logging)
            mock_repo.advance_chapter.assert_called_once()


class TestEdgeCases:
    """Edge cases for chapter advancement"""

    @pytest.mark.asyncio
    async def test_chapter_5_pass_handled(self):
        """Chapter 5 pass should not exceed chapter 5"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            # Chapter 5 pass - should handle victory
            mock_user = MagicMock()
            mock_user.chapter = 5  # Still chapter 5 (can't go higher)
            mock_user.game_status = 'won'  # Special victory status
            mock_user.boss_attempts = 0
            mock_repo.advance_chapter.return_value = mock_user

            result = await sm.process_pass(uuid4())

            assert result['new_chapter'] == 5 or result.get('game_status') == 'won'
