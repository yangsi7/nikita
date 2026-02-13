"""
Tests for Boss Failure Handling (T8)

TDD: Write tests FIRST, verify FAIL, then implement.

Acceptance Criteria:
- AC-FR004-002: Given user fails to demonstrate skill, When judged, Then returns BossResult.FAIL
- AC-FR006-001: Given FAIL result, When process_fail() called, Then boss_attempts += 1
- AC-FR006-002: Given FAIL and attempts < 3, When processed, Then game_status remains 'boss_fight'
- AC-T8-001: Score penalty of -10% applied to composite score
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal


class TestProcessFailStructure:
    """process_fail method exists on BossStateMachine"""

    def test_process_fail_method_exists(self):
        """BossStateMachine has process_fail method"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        assert hasattr(sm, 'process_fail')
        assert callable(getattr(sm, 'process_fail'))

    def test_process_fail_is_async(self):
        """process_fail is an async method"""
        import asyncio
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        assert asyncio.iscoroutinefunction(sm.process_fail)

    def test_process_fail_accepts_user_id(self):
        """process_fail accepts user_id parameter"""
        import inspect
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()
        sig = inspect.signature(sm.process_fail)
        params = list(sig.parameters.keys())
        assert 'user_id' in params


class TestProcessFailResult:
    """process_fail returns expected result structure"""

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        """process_fail returns a dictionary"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 1
        mock_user.game_status = 'boss_fight'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_fail(uuid4(), user_repository=mock_repo)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_result_has_attempts(self):
        """Result includes attempts field"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 1
        mock_user.game_status = 'boss_fight'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_fail(uuid4(), user_repository=mock_repo)

        assert 'attempts' in result

    @pytest.mark.asyncio
    async def test_result_has_game_over(self):
        """Result includes game_over field"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 1
        mock_user.game_status = 'boss_fight'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_fail(uuid4(), user_repository=mock_repo)

        assert 'game_over' in result

    @pytest.mark.asyncio
    async def test_result_has_game_status(self):
        """Result includes game_status field"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 1
        mock_user.game_status = 'boss_fight'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_fail(uuid4(), user_repository=mock_repo)

        assert 'game_status' in result


class TestBossAttemptsIncrement:
    """AC-FR006-001: boss_attempts increments"""

    @pytest.mark.asyncio
    async def test_ac_fr006_001_boss_attempts_increments(self):
        """Given FAIL result, boss_attempts increments by 1"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        user_id = uuid4()

        mock_repo = AsyncMock()
        # User after increment has boss_attempts = 1
        mock_user = MagicMock()
        mock_user.boss_attempts = 1
        mock_user.game_status = 'boss_fight'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_fail(user_id, user_repository=mock_repo)

        # Verify increment_boss_attempts was called
        mock_repo.increment_boss_attempts.assert_called_once_with(user_id)
        assert result['attempts'] == 1

    @pytest.mark.asyncio
    async def test_calls_repository_increment_boss_attempts(self):
        """process_fail calls UserRepository.increment_boss_attempts()"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        user_id = uuid4()

        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 2
        mock_user.game_status = 'boss_fight'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        await sm.process_fail(user_id, user_repository=mock_repo)

        mock_repo.increment_boss_attempts.assert_called_once_with(user_id)


class TestRetryMechanism:
    """AC-FR006-002: Retry allowed if attempts < 3"""

    @pytest.mark.asyncio
    async def test_ac_fr006_002_first_fail_allows_retry(self):
        """Given FAIL and attempts = 1, game_status remains 'boss_fight'"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 1  # First fail
        mock_user.game_status = 'boss_fight'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_fail(uuid4(), user_repository=mock_repo)

        assert result['game_status'] == 'boss_fight'
        assert result['game_over'] is False

    @pytest.mark.asyncio
    async def test_second_fail_allows_retry(self):
        """Given FAIL and attempts = 2, retry still allowed"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 2  # Second fail
        mock_user.game_status = 'boss_fight'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_fail(uuid4(), user_repository=mock_repo)

        assert result['game_status'] == 'boss_fight'
        assert result['game_over'] is False

    @pytest.mark.asyncio
    async def test_third_fail_triggers_game_over(self):
        """Given FAIL and attempts = 3, game_over is True"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 3  # Third fail
        mock_user.game_status = 'game_over'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_fail(uuid4(), user_repository=mock_repo)

        assert result['game_over'] is True
        assert result['game_status'] == 'game_over'


class TestProcessOutcomeFailPath:
    """process_outcome delegates to process_fail when passed=False"""

    @pytest.mark.asyncio
    async def test_process_outcome_fail_path(self):
        """process_outcome(passed=False) calls process_fail"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 1
        mock_user.game_status = 'boss_fight'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_outcome(uuid4(), passed=False, user_repository=mock_repo)

        assert result['passed'] is False
        assert 'attempts' in result

    @pytest.mark.asyncio
    async def test_process_outcome_fail_returns_correct_message(self):
        """process_outcome(passed=False) returns 'Try again!' message"""
        from nikita.engine.chapters.boss import BossStateMachine
        sm = BossStateMachine()

        mock_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user.boss_attempts = 1
        mock_user.game_status = 'boss_fight'
        mock_repo.increment_boss_attempts.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_outcome(uuid4(), passed=False, user_repository=mock_repo)

        assert result['message'] == 'Try again!'

    @pytest.mark.asyncio
    async def test_process_outcome_game_over_message(self):
        """process_outcome returns 'Game over!' when 3 attempts reached"""
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
