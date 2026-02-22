"""Tests for psyche cost control (Spec 056 T24).

AC coverage: AC-7.1, AC-7.3, AC-7.4
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.psyche.models import PsycheState
from nikita.agents.psyche.trigger import MAX_TIER3_PER_DAY, TriggerTier


class TestCostLimits:
    """Test cost control mechanisms."""

    def test_tier3_daily_limit_constant(self):
        """AC-7.3: Max 5 Tier 3 calls/user/day."""
        assert MAX_TIER3_PER_DAY == 5

    def test_tier_distribution_hypothesis(self):
        """AC-7.1: Validate tier distribution hypothesis (90/8/2%).

        Not a strict enforcement test, but verifies that common messages
        route to Tier 1 (CACHED) and only specific triggers elevate.
        """
        # 100 common messages should all be Tier 1
        common_messages = [
            "hey", "what's up", "how are you", "cool", "nice",
            "lol", "that's funny", "ok", "sure", "interesting",
            "tell me more", "I see", "really?", "haha", "yes",
            "no", "maybe", "I think so", "probably", "definitely",
        ]

        from nikita.agents.psyche.trigger import detect_trigger_tier

        tier1_count = sum(
            1 for msg in common_messages
            if detect_trigger_tier(msg) == TriggerTier.CACHED
        )

        # At least 90% should be Tier 1
        assert tier1_count >= len(common_messages) * 0.9, (
            f"Only {tier1_count}/{len(common_messages)} messages were Tier 1 "
            f"(expected >=90%)"
        )

    @pytest.mark.asyncio
    async def test_token_tracking_in_generate(self):
        """AC-7.4: Token count returned from generate_psyche_state."""
        sample_state = PsycheState(
            attachment_activation="secure",
            defense_mode="open",
            behavioral_guidance="Be warm.",
            internal_monologue="Good day.",
            vulnerability_level=0.5,
            emotional_tone="warm",
        )

        mock_result = MagicMock()
        mock_result.output = sample_state
        mock_usage = MagicMock()
        mock_usage.input_tokens = 400
        mock_usage.output_tokens = 200
        mock_result.usage.return_value = mock_usage

        with patch("nikita.agents.psyche.agent.get_psyche_agent") as mock_get:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_get.return_value = mock_agent

            from nikita.agents.psyche.agent import generate_psyche_state
            from nikita.agents.psyche.deps import PsycheDeps

            deps = PsycheDeps(user_id=uuid4())
            state, tokens = await generate_psyche_state(deps)

        assert tokens == 600
        assert isinstance(state, PsycheState)

    @pytest.mark.asyncio
    async def test_token_tracking_in_quick_analyze(self):
        """AC-7.4: Token count from quick_analyze."""
        sample_state = PsycheState(
            attachment_activation="anxious",
            defense_mode="guarded",
            behavioral_guidance="Be careful.",
            internal_monologue="Hmm.",
            vulnerability_level=0.3,
            emotional_tone="serious",
        )

        mock_result = MagicMock()
        mock_result.output = sample_state
        mock_usage = MagicMock()
        mock_usage.input_tokens = 250
        mock_usage.output_tokens = 100
        mock_result.usage.return_value = mock_usage

        with patch("nikita.agents.psyche.agent.get_psyche_agent") as mock_get:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_get.return_value = mock_agent

            from nikita.agents.psyche.agent import quick_analyze
            from nikita.agents.psyche.deps import PsycheDeps

            deps = PsycheDeps(user_id=uuid4())
            state, tokens = await quick_analyze(deps, "I miss you")

        assert tokens == 350

    @pytest.mark.asyncio
    async def test_token_tracking_in_deep_analyze(self):
        """AC-7.4: Token count from deep_analyze."""
        sample_state = PsycheState(
            attachment_activation="disorganized",
            defense_mode="withdrawing",
            behavioral_guidance="Give space.",
            internal_monologue="Crisis mode.",
            vulnerability_level=0.1,
            emotional_tone="volatile",
        )

        mock_result = MagicMock()
        mock_result.output = sample_state
        mock_usage = MagicMock()
        mock_usage.input_tokens = 800
        mock_usage.output_tokens = 300
        mock_result.usage.return_value = mock_usage

        with patch("nikita.agents.psyche.agent._create_psyche_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            from nikita.agents.psyche.agent import deep_analyze
            from nikita.agents.psyche.deps import PsycheDeps

            deps = PsycheDeps(user_id=uuid4())
            state, tokens = await deep_analyze(deps, "I can't do this anymore")

        assert tokens == 1100

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_excessive_tier3(self):
        """AC-7.3: Circuit breaker blocks after 5 Tier 3 calls."""
        from nikita.agents.psyche.trigger import check_tier3_circuit_breaker

        mock_session = AsyncMock()
        mock_repo = AsyncMock()

        # 5 calls already today
        mock_repo.get_tier3_count_today.return_value = 5

        with patch(
            "nikita.db.repositories.psyche_state_repository.PsycheStateRepository",
            return_value=mock_repo,
        ):
            allowed = await check_tier3_circuit_breaker(uuid4(), mock_session)

        assert allowed is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_allows_under_limit(self):
        """AC-7.3: Circuit breaker allows at 4 calls."""
        from nikita.agents.psyche.trigger import check_tier3_circuit_breaker

        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_tier3_count_today.return_value = 4

        with patch(
            "nikita.db.repositories.psyche_state_repository.PsycheStateRepository",
            return_value=mock_repo,
        ):
            allowed = await check_tier3_circuit_breaker(uuid4(), mock_session)
