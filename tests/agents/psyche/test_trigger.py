"""Tests for Spec 056 Trigger Detector (Phase 4: T13, T14).

Tests the 3-tier trigger detector: rule-based message classification,
keyword matching, conflict state detection, boss adjacency,
score delta checks, circuit breaker.

AC refs: AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-3.5
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.psyche.trigger import (
    MAX_TIER3_PER_DAY,
    TIER2_EMOTIONAL_KEYWORDS,
    TIER3_EMOTIONAL_KEYWORDS,
    TriggerTier,
    check_tier3_circuit_breaker,
    detect_trigger_tier,
)


# ============================================================================
# TriggerTier enum
# ============================================================================


class TestTriggerTierEnum:
    """TriggerTier IntEnum with 3 levels."""

    def test_cached_is_1(self):
        assert TriggerTier.CACHED == 1

    def test_quick_is_2(self):
        assert TriggerTier.QUICK == 2

    def test_deep_is_3(self):
        assert TriggerTier.DEEP == 3

    def test_ordering(self):
        assert TriggerTier.CACHED < TriggerTier.QUICK < TriggerTier.DEEP


# ============================================================================
# AC-3.1: Default Tier 1 (CACHED) for normal messages
# ============================================================================


class TestDefaultTier1:
    """Normal messages route to Tier 1 (CACHED)."""

    def test_normal_greeting(self):
        assert detect_trigger_tier("hey") == TriggerTier.CACHED

    def test_casual_message(self):
        assert detect_trigger_tier("what are you up to?") == TriggerTier.CACHED

    def test_question_about_day(self):
        assert detect_trigger_tier("how was your day?") == TriggerTier.CACHED

    def test_emoji_only(self):
        assert detect_trigger_tier("haha lol") == TriggerTier.CACHED

    def test_empty_message(self):
        assert detect_trigger_tier("") == TriggerTier.CACHED


# ============================================================================
# AC-3.2: Tier 2 (QUICK) triggers
# ============================================================================


class TestTier2Triggers:
    """Moderate emotional content routes to Tier 2."""

    @pytest.mark.parametrize("keyword", list(TIER2_EMOTIONAL_KEYWORDS)[:5])
    def test_tier2_keyword_triggers(self, keyword: str):
        assert detect_trigger_tier(f"I said {keyword} to you") == TriggerTier.QUICK

    def test_first_message_of_day(self):
        assert detect_trigger_tier(
            "good morning",
            is_first_message_today=True,
        ) == TriggerTier.QUICK

    def test_score_drop_over_5(self):
        assert detect_trigger_tier(
            "hmm",
            score_delta=-6.0,
        ) == TriggerTier.QUICK

    def test_score_drop_exactly_5_is_tier1(self):
        """Score drop of exactly 5 does NOT trigger Tier 2."""
        assert detect_trigger_tier(
            "hmm",
            score_delta=-5.0,
        ) == TriggerTier.CACHED

    def test_case_insensitive_keywords(self):
        assert detect_trigger_tier("I'M SCARED") == TriggerTier.QUICK


# ============================================================================
# AC-3.3: Tier 3 (DEEP) triggers
# ============================================================================


class TestTier3Triggers:
    """Critical emotional content routes to Tier 3."""

    @pytest.mark.parametrize("keyword", list(TIER3_EMOTIONAL_KEYWORDS)[:5])
    def test_tier3_keyword_triggers(self, keyword: str):
        assert detect_trigger_tier(keyword) == TriggerTier.DEEP

    def test_horseman_in_conflict_state(self):
        assert detect_trigger_tier(
            "whatever",
            conflict_state={"horseman": "contempt"},
        ) == TriggerTier.DEEP

    def test_boss_fight_status(self):
        assert detect_trigger_tier(
            "I think we should talk",
            game_status="boss_fight",
        ) == TriggerTier.DEEP

    def test_horseman_none_is_not_tier3(self):
        """horseman='none' does not trigger Tier 3."""
        assert detect_trigger_tier(
            "hello",
            conflict_state={"horseman": "none"},
        ) != TriggerTier.DEEP


# ============================================================================
# AC-3.4: Tier 3 takes priority over Tier 2
# ============================================================================


class TestTierPriority:
    """Tier 3 triggers override Tier 2 triggers."""

    def test_crisis_keyword_overrides_first_message(self):
        """Tier 3 keyword + first message of day -> still Tier 3."""
        result = detect_trigger_tier(
            "i can't do this anymore",
            is_first_message_today=True,
        )
        assert result == TriggerTier.DEEP

    def test_boss_fight_overrides_score_drop(self):
        result = detect_trigger_tier(
            "hmm",
            score_delta=-10.0,
            game_status="boss_fight",
        )
        assert result == TriggerTier.DEEP


# ============================================================================
# AC-3.5: Circuit breaker (max 5 Tier 3 per user per day)
# ============================================================================


class TestCircuitBreaker:
    """Tier 3 circuit breaker limits deep analysis."""

    def test_max_tier3_per_day_is_5(self):
        assert MAX_TIER3_PER_DAY == 5

    @pytest.mark.asyncio
    async def test_allowed_when_under_limit(self):
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_tier3_count_today = AsyncMock(return_value=3)

        mock_repo_cls = MagicMock(return_value=mock_repo)
        with patch.dict(
            "sys.modules",
            {"nikita.db.repositories.psyche_state_repository": MagicMock(PsycheStateRepository=mock_repo_cls)},
        ):
            # Re-call after module dict patched
            from nikita.agents.psyche.trigger import check_tier3_circuit_breaker as fn

            result = await fn(uuid4(), mock_session)

        assert result is True

    @pytest.mark.asyncio
    async def test_blocked_when_at_limit(self):
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_tier3_count_today = AsyncMock(return_value=5)

        mock_repo_cls = MagicMock(return_value=mock_repo)
        with patch.dict(
            "sys.modules",
            {"nikita.db.repositories.psyche_state_repository": MagicMock(PsycheStateRepository=mock_repo_cls)},
        ):
            from nikita.agents.psyche.trigger import check_tier3_circuit_breaker as fn

            result = await fn(uuid4(), mock_session)

        assert result is False

    @pytest.mark.asyncio
    async def test_blocked_when_over_limit(self):
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_tier3_count_today = AsyncMock(return_value=10)

        mock_repo_cls = MagicMock(return_value=mock_repo)
        with patch.dict(
            "sys.modules",
            {"nikita.db.repositories.psyche_state_repository": MagicMock(PsycheStateRepository=mock_repo_cls)},
        ):
            from nikita.agents.psyche.trigger import check_tier3_circuit_breaker as fn

            result = await fn(uuid4(), mock_session)

        assert result is False

    @pytest.mark.asyncio
    async def test_fails_open_on_db_error(self):
        """DB error -> allow Tier 3 (fail open)."""
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_tier3_count_today = AsyncMock(
            side_effect=Exception("DB down")
        )

        mock_repo_cls = MagicMock(return_value=mock_repo)
        with patch.dict(
            "sys.modules",
            {"nikita.db.repositories.psyche_state_repository": MagicMock(PsycheStateRepository=mock_repo_cls)},
        ):
            from nikita.agents.psyche.trigger import check_tier3_circuit_breaker as fn

            result = await fn(uuid4(), mock_session)

        assert result is True


# ============================================================================
# Keyword sets
# ============================================================================


class TestKeywordSets:
    """Keyword sets are non-empty and disjoint."""

    def test_tier3_keywords_non_empty(self):
        assert len(TIER3_EMOTIONAL_KEYWORDS) > 0

    def test_tier2_keywords_non_empty(self):
        assert len(TIER2_EMOTIONAL_KEYWORDS) > 0

    def test_keyword_sets_are_disjoint(self):
        """No overlap between Tier 2 and Tier 3 keywords."""
        overlap = TIER3_EMOTIONAL_KEYWORDS & TIER2_EMOTIONAL_KEYWORDS
        assert len(overlap) == 0, f"Overlapping keywords: {overlap}"
