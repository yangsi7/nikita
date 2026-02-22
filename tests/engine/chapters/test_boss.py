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

    def test_ac_t1_002_has_should_trigger_boss_method(self):
        """AC-T1-002: BossStateMachine has should_trigger_boss() method."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert hasattr(sm, "should_trigger_boss")
        assert callable(sm.should_trigger_boss)

    def test_ac_t1_002_has_initiate_boss_method(self):
        """AC-T1-002: BossStateMachine has initiate_boss() method."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert hasattr(sm, "initiate_boss")
        assert callable(sm.initiate_boss)

    def test_ac_t1_002_has_process_outcome_method(self):
        """AC-T1-002: BossStateMachine has process_outcome() method."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert hasattr(sm, "process_outcome")
        assert callable(sm.process_outcome)


class TestAsyncMethods:
    """Tests for AC-T1-003: All methods are async and accept user_id."""

    def test_ac_t1_003_initiate_boss_is_async(self):
        """AC-T1-003: initiate_boss() is async."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert inspect.iscoroutinefunction(sm.initiate_boss)

    def test_ac_t1_003_process_outcome_is_async(self):
        """AC-T1-003: process_outcome() is async."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert inspect.iscoroutinefunction(sm.process_outcome)


class TestUserIdParameter:
    """Tests for AC-T1-003: Methods accept user_id parameter."""

    def test_ac_t1_003_initiate_boss_accepts_user_id(self):
        """AC-T1-003: initiate_boss() accepts user_id parameter."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        sig = inspect.signature(sm.initiate_boss)
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
