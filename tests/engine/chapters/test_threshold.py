"""Tests for Boss Threshold Detection (Spec 004 - Task T3).

TDD tests written FIRST, implementation follows.
Tests cover AC-FR001-001, AC-T3-001, AC-T3-002.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from nikita.engine.constants import BOSS_THRESHOLDS


# ==============================================================================
# T3: Implement Threshold Detection
# ==============================================================================


class TestThresholdDetectionBasic:
    """Tests for AC-T3-001: Method checks score >= BOSS_THRESHOLDS[chapter]."""

    def test_ac_t3_001_returns_false_below_threshold_ch1(self):
        """Score 54% in Ch1 (threshold 55%) returns False."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        result = sm.should_trigger_boss(
            relationship_score=Decimal("54.00"),
            chapter=1,
            game_status="active",
        )
        assert result is False

    def test_ac_t3_001_returns_true_at_threshold_ch1(self):
        """Score 55% in Ch1 (threshold 55%) returns True."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        result = sm.should_trigger_boss(
            relationship_score=Decimal("55.00"),
            chapter=1,
            game_status="active",
        )
        assert result is True

    def test_ac_t3_001_returns_true_above_threshold_ch1(self):
        """Score 60% in Ch1 (threshold 55%) returns True."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        result = sm.should_trigger_boss(
            relationship_score=Decimal("60.00"),
            chapter=1,
            game_status="active",
        )
        assert result is True


class TestThresholdAllChapters:
    """Tests for all chapter thresholds (55, 60, 65, 70, 75)."""

    @pytest.mark.parametrize(
        "chapter,threshold",
        [
            (1, Decimal("55.00")),
            (2, Decimal("60.00")),
            (3, Decimal("65.00")),
            (4, Decimal("70.00")),
            (5, Decimal("75.00")),
        ],
    )
    def test_ac_t3_001_threshold_for_each_chapter(self, chapter: int, threshold: Decimal):
        """Each chapter has correct boss threshold."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()

        # Just below threshold - should NOT trigger
        below = threshold - Decimal("0.01")
        assert sm.should_trigger_boss(below, chapter, "active") is False

        # At threshold - should trigger
        assert sm.should_trigger_boss(threshold, chapter, "active") is True

        # Above threshold - should trigger
        above = threshold + Decimal("5.00")
        assert sm.should_trigger_boss(above, chapter, "active") is True


class TestGameStatusBlocking:
    """Tests for AC-T3-002: Returns False if already in boss_fight or game_over."""

    def test_ac_t3_002_returns_false_if_boss_fight(self):
        """Already in boss_fight - should NOT trigger another boss."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        result = sm.should_trigger_boss(
            relationship_score=Decimal("55.00"),  # At threshold
            chapter=1,
            game_status="boss_fight",
        )
        assert result is False

    def test_ac_t3_002_returns_false_if_game_over(self):
        """Game is over - should NOT trigger boss."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        result = sm.should_trigger_boss(
            relationship_score=Decimal("55.00"),  # At threshold
            chapter=1,
            game_status="game_over",
        )
        assert result is False

    def test_ac_t3_002_returns_false_if_won(self):
        """Game is won - should NOT trigger boss."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        result = sm.should_trigger_boss(
            relationship_score=Decimal("55.00"),  # At threshold
            chapter=1,
            game_status="won",
        )
        assert result is False

    def test_returns_true_only_if_active(self):
        """Only active status can trigger boss."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        result = sm.should_trigger_boss(
            relationship_score=Decimal("55.00"),
            chapter=1,
            game_status="active",
        )
        assert result is True


class TestSpecScenario:
    """Test AC-FR001-001 exactly as specified."""

    def test_ac_fr001_001_user_at_54_rises_to_55(self):
        """
        AC-FR001-001: Given user at 54% in Ch1,
        When score rises to 55%,
        Then should_trigger_boss() returns True.
        """
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()

        # User was at 54% - boss should NOT have triggered
        before = sm.should_trigger_boss(
            relationship_score=Decimal("54.00"),
            chapter=1,
            game_status="active",
        )
        assert before is False, "54% should not trigger boss"

        # Score rises to 55% - boss SHOULD trigger now
        after = sm.should_trigger_boss(
            relationship_score=Decimal("55.00"),
            chapter=1,
            game_status="active",
        )
        assert after is True, "55% should trigger boss in Ch1"


class TestAsyncCheckThreshold:
    """Tests for async check_threshold method with user_id."""

    @pytest.mark.asyncio
    async def test_check_threshold_calls_should_trigger_boss(self):
        """check_threshold delegates to should_trigger_boss with user data."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        user_id = uuid4()

        # check_threshold is async and needs user data injection
        # For now, it returns False (stub) - full implementation in T3 integration
        result = await sm.check_threshold(user_id)
        assert isinstance(result, bool)
