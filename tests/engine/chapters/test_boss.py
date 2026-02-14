"""Tests for Boss State Machine (Spec 004 - Task T1).

TDD tests written FIRST, implementation follows.
Tests cover AC-T1-001 through AC-T1-003.
"""

import inspect
from decimal import Decimal
from uuid import UUID, uuid4

import pytest


# ==============================================================================
# T1: Create Boss State Machine Module
# ==============================================================================


class TestBossStateMachineClassExists:
    """Tests for AC-T1-001: BossStateMachine class exists in boss.py."""

    def test_ac_t1_001_module_exists(self):
        """AC-T1-001: nikita/engine/chapters/boss.py exists."""
        from nikita.engine.chapters import boss

        assert boss is not None

    def test_ac_t1_001_class_exists(self):
        """AC-T1-001: BossStateMachine class exists in boss.py."""
        from nikita.engine.chapters.boss import BossStateMachine

        assert BossStateMachine is not None

    def test_class_is_instantiable(self):
        """BossStateMachine can be instantiated."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert sm is not None


class TestBossStateMachineMethods:
    """Tests for AC-T1-002: Required methods exist."""

    def test_ac_t1_002_has_check_threshold_method(self):
        """AC-T1-002: BossStateMachine has check_threshold() method."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert hasattr(sm, "check_threshold")
        assert callable(sm.check_threshold)

    def test_ac_t1_002_has_trigger_boss_method(self):
        """AC-T1-002: BossStateMachine has trigger_boss() method."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert hasattr(sm, "trigger_boss")
        assert callable(sm.trigger_boss)

    def test_ac_t1_002_has_process_outcome_method(self):
        """AC-T1-002: BossStateMachine has process_outcome() method."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert hasattr(sm, "process_outcome")
        assert callable(sm.process_outcome)


class TestAsyncMethods:
    """Tests for AC-T1-003: All methods are async and accept user_id."""

    def test_ac_t1_003_check_threshold_is_async(self):
        """AC-T1-003: check_threshold() is async."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert inspect.iscoroutinefunction(sm.check_threshold)

    def test_ac_t1_003_trigger_boss_is_async(self):
        """AC-T1-003: trigger_boss() is async."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert inspect.iscoroutinefunction(sm.trigger_boss)

    def test_ac_t1_003_process_outcome_is_async(self):
        """AC-T1-003: process_outcome() is async."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert inspect.iscoroutinefunction(sm.process_outcome)


class TestUserIdParameter:
    """Tests for AC-T1-003: Methods accept user_id parameter."""

    def test_ac_t1_003_check_threshold_accepts_user_id(self):
        """AC-T1-003: check_threshold() accepts user_id parameter."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        sig = inspect.signature(sm.check_threshold)
        param_names = list(sig.parameters.keys())
        assert "user_id" in param_names

    def test_ac_t1_003_trigger_boss_accepts_user_id(self):
        """AC-T1-003: trigger_boss() accepts user_id parameter."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        sig = inspect.signature(sm.trigger_boss)
        param_names = list(sig.parameters.keys())
        assert "user_id" in param_names

    def test_ac_t1_003_process_outcome_accepts_user_id(self):
        """AC-T1-003: process_outcome() accepts user_id parameter."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        sig = inspect.signature(sm.process_outcome)
        param_names = list(sig.parameters.keys())
        assert "user_id" in param_names


# ==============================================================================
# Functional Tests (behavior verification for later phases)
# ==============================================================================


class TestCheckThresholdBehavior:
    """Functional tests for check_threshold method."""

    @pytest.mark.asyncio
    async def test_check_threshold_returns_bool(self):
        """check_threshold returns a boolean."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        user_id = uuid4()
        # Initially should return False (no boss needed)
        result = await sm.check_threshold(user_id)
        assert isinstance(result, bool)


class TestTriggerBossBehavior:
    """Functional tests for trigger_boss method."""

    @pytest.mark.asyncio
    async def test_trigger_boss_returns_dict(self):
        """trigger_boss returns encounter info dict."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        user_id = uuid4()
        result = await sm.trigger_boss(user_id)
        assert isinstance(result, dict)


class TestProcessOutcomeBehavior:
    """Functional tests for process_outcome method."""

    @pytest.mark.asyncio
    async def test_process_outcome_accepts_passed_bool(self):
        """process_outcome accepts passed boolean parameter."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        user_id = uuid4()
        sig = inspect.signature(sm.process_outcome)
        param_names = list(sig.parameters.keys())
        assert "passed" in param_names

    @pytest.mark.asyncio
    async def test_process_outcome_returns_dict(self):
        """process_outcome returns result dict."""
        from nikita.engine.chapters.boss import BossStateMachine
        from unittest.mock import AsyncMock, MagicMock

        sm = BossStateMachine()
        user_id = uuid4()

        mock_repo = AsyncMock()
        # Pre-advance: user is in chapter 1
        pre_user = MagicMock()
        pre_user.chapter = 1
        mock_repo.get.return_value = pre_user
        # Post-advance: chapter becomes 2
        mock_user = MagicMock()
        mock_user.chapter = 2
        mock_user.game_status = 'active'
        mock_user.boss_attempts = 0
        mock_repo.advance_chapter.return_value = mock_user
        mock_repo.update_game_status.return_value = mock_user

        result = await sm.process_outcome(user_id, passed=True, user_repository=mock_repo)
        assert isinstance(result, dict)
