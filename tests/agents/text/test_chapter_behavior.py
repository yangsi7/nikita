"""Tests for Chapter-Based Behavior - TDD for T3.2.

Acceptance Criteria:
- AC-3.2.1: Test Ch1 user receives guarded/challenging responses
- AC-3.2.2: Test Ch3 user receives emotionally engaged responses
- AC-3.2.3: Test Ch5 user receives relaxed/affectionate responses
- AC-3.2.4: Tests mock agent to verify prompt content by chapter

NOTE (2026-03): Design corrected — Ch1 is GUARDED (low engagement 60-75%),
response rates INCREASE through chapters (Ch1=60-75% → Ch5=90-95%).

NOTE (2026-02): These tests now use _build_system_prompt_legacy() directly
since the context_engine (v2) is the production default. The legacy tests
verify that the chapter behaviors in CHAPTER_BEHAVIORS constants are correct.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


class TestChapterBehaviorInjection:
    """Tests verifying chapter behaviors are correctly injected into prompts.

    These tests use the legacy prompt builder to test CHAPTER_BEHAVIORS constants.
    """

    @pytest.mark.asyncio
    async def test_ac_3_2_1_ch1_prompt_contains_guarded_behavior(self):
        """AC-3.2.1: Ch1 prompts should contain guarded/challenging behaviors."""
        from nikita.agents.text.agent import _build_system_prompt_legacy

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 1

        prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test message")

        # Check for Ch1 key behaviors: guarded, challenging, skeptical
        prompt_lower = prompt.lower()
        assert "guarded" in prompt_lower or "challenging" in prompt_lower or "skeptical" in prompt_lower
        assert "earn" in prompt_lower or "terse" in prompt_lower or "boring" in prompt_lower

    @pytest.mark.asyncio
    async def test_ac_3_2_1_ch1_response_rate_in_prompt(self):
        """AC-3.2.1: Ch1 prompt should mention 60-75% response rate."""
        from nikita.agents.text.agent import _build_system_prompt_legacy

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 1

        prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test")

        # Ch1 has LOW engagement (60-75%)
        assert "60-75%" in prompt

    @pytest.mark.asyncio
    async def test_ac_3_2_2_ch3_prompt_contains_vulnerable_behavior(self):
        """AC-3.2.2: Ch3 prompts should contain emotionally vulnerable behaviors."""
        from nikita.agents.text.agent import _build_system_prompt_legacy

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 3

        prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test message")

        # Check for Ch3 key behaviors: warmer, emotionally engaged, trust
        prompt_lower = prompt.lower()
        assert "vulnerability" in prompt_lower or "emotionally engaged" in prompt_lower
        assert "trust" in prompt_lower or "depth" in prompt_lower
        assert "emotional" in prompt_lower or "warmer" in prompt_lower

    @pytest.mark.asyncio
    async def test_ac_3_2_2_ch3_response_rate_in_prompt(self):
        """AC-3.2.2: Ch3 prompt should mention 80-90% response rate."""
        from nikita.agents.text.agent import _build_system_prompt_legacy

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 3

        prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test")

        assert "80-90%" in prompt

    @pytest.mark.asyncio
    async def test_ac_3_2_3_ch5_prompt_contains_stable_behavior(self):
        """AC-3.2.3: Ch5 prompts should contain stable/authentic behaviors."""
        from nikita.agents.text.agent import _build_system_prompt_legacy

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 5

        prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test message")

        # Check for Ch5 key behaviors: relaxed, affectionate, confident
        prompt_lower = prompt.lower()
        assert "relaxed" in prompt_lower or "affectionate" in prompt_lower or "confident" in prompt_lower
        assert "settled" in prompt_lower or "partners" in prompt_lower or "comfortable" in prompt_lower

    @pytest.mark.asyncio
    async def test_ac_3_2_3_ch5_response_rate_in_prompt(self):
        """AC-3.2.3: Ch5 prompt should mention 90-95% response rate."""
        from nikita.agents.text.agent import _build_system_prompt_legacy

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 5

        prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test")

        assert "90-95%" in prompt

    @pytest.mark.asyncio
    async def test_ac_3_2_4_prompts_differ_by_chapter(self):
        """AC-3.2.4: Different chapters should produce different prompts."""
        from nikita.agents.text.agent import _build_system_prompt_legacy

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        prompts = {}
        for chapter in [1, 2, 3, 4, 5]:
            mock_user = MagicMock()
            mock_user.chapter = chapter
            prompts[chapter] = await _build_system_prompt_legacy(mock_memory, mock_user, "test")

        # All prompts should be different
        unique_prompts = set(prompts.values())
        assert len(unique_prompts) == 5, "Each chapter should produce a unique prompt"

    @pytest.mark.asyncio
    async def test_ac_3_2_4_prompt_has_current_chapter_behavior_label(self):
        """AC-3.2.4: Prompt should have labeled CURRENT CHAPTER BEHAVIOR section."""
        from nikita.agents.text.agent import _build_system_prompt_legacy

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 2

        prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test")

        assert "CURRENT CHAPTER BEHAVIOR" in prompt

    @pytest.mark.asyncio
    async def test_chapter_names_match_constants(self):
        """Chapter names in behavior should match CHAPTER_NAMES constant."""
        from nikita.agents.text.agent import _build_system_prompt_legacy
        from nikita.engine.constants import CHAPTER_NAMES

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        for chapter, name in CHAPTER_NAMES.items():
            mock_user = MagicMock()
            mock_user.chapter = chapter

            prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test")

            # Chapter name should be somewhere in the behavior section
            assert name.upper() in prompt.upper(), f"Chapter {chapter} ({name}) name not found in prompt"


class TestChapterBehaviorProgression:
    """Tests verifying the progression of behaviors through chapters."""

    @pytest.mark.asyncio
    async def test_response_rate_increases_through_chapters(self):
        """Response rate should increase through chapters (guarded → settled)."""
        from nikita.agents.text.agent import _build_system_prompt_legacy
        import re

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        response_rates = {}
        for chapter in [1, 3, 5]:
            mock_user = MagicMock()
            mock_user.chapter = chapter
            prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test")

            # Extract first response rate percentage from range like "60-75%"
            match = re.search(r"Response rate:\s*(\d+)", prompt)
            if match:
                response_rates[chapter] = int(match.group(1))

        # Ch1 (60) < Ch3 (80) < Ch5 (90) — engagement increases with trust
        assert response_rates[1] < response_rates[3], "Ch1 should have lower engagement than Ch3"
        assert response_rates[3] < response_rates[5], "Ch3 should have lower engagement than Ch5"

    @pytest.mark.asyncio
    async def test_emotional_openness_increases_through_chapters(self):
        """Emotional openness indicators should increase through chapters."""
        from nikita.agents.text.agent import _build_system_prompt_legacy

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        # Count emotional keywords in each chapter
        emotional_keywords = ["share", "feel", "vulnerability", "emotional", "authentic", "real"]

        emotional_counts = {}
        for chapter in [1, 3, 5]:
            mock_user = MagicMock()
            mock_user.chapter = chapter
            prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test")
            prompt_lower = prompt.lower()

            count = sum(1 for keyword in emotional_keywords if keyword in prompt_lower)
            emotional_counts[chapter] = count

        # Chapter 3 and 5 should have more emotional keywords than Chapter 1
        assert emotional_counts[3] >= emotional_counts[1]
        assert emotional_counts[5] >= emotional_counts[1]

    @pytest.mark.asyncio
    async def test_ch1_has_challenge_keywords(self):
        """Chapter 1 should focus on being guarded and challenging."""
        from nikita.agents.text.agent import _build_system_prompt_legacy

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 1

        prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test")
        prompt_lower = prompt.lower()

        # Ch1 specific behaviors: guarded, challenging, skeptical
        challenge_keywords = ["guarded", "challenging", "skeptical", "earn", "terse", "dark humor"]
        has_challenge_keyword = any(kw in prompt_lower for kw in challenge_keywords)
        assert has_challenge_keyword, "Ch1 should contain challenge/guarded language"

    @pytest.mark.asyncio
    async def test_ch5_has_settled_keywords(self):
        """Chapter 5 should focus on settled/relaxed/confident tone."""
        from nikita.agents.text.agent import _build_system_prompt_legacy

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 5

        prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test")
        prompt_lower = prompt.lower()

        # Ch5 specific behaviors: relaxed, affectionate, confident, settled
        settled_keywords = ["relaxed", "affectionate", "confident", "settled", "comfortable"]
        has_settled_keyword = any(kw in prompt_lower for kw in settled_keywords)
        assert has_settled_keyword, "Ch5 should contain settled/relaxed language"


class TestDefaultChapterBehavior:
    """Tests for handling edge cases in chapter behavior."""

    @pytest.mark.asyncio
    async def test_invalid_chapter_falls_back_to_ch1(self):
        """Invalid chapter numbers should fall back to Chapter 1 behavior."""
        from nikita.agents.text.agent import _build_system_prompt_legacy

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        # Test with invalid chapter (0)
        mock_user = MagicMock()
        mock_user.chapter = 0

        prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test")

        # Should fall back to Ch1 (60-75% response rate)
        assert "60-75%" in prompt

    @pytest.mark.asyncio
    async def test_chapter_6_falls_back_to_ch1(self):
        """Chapter 6 (non-existent) should fall back to default behavior."""
        from nikita.agents.text.agent import _build_system_prompt_legacy

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 6

        prompt = await _build_system_prompt_legacy(mock_memory, mock_user, "test")

        # Should still produce a valid prompt with fallback behavior
        assert "CURRENT CHAPTER BEHAVIOR" in prompt
        # Falls back to Ch1 (60-75%)
        assert "60-75%" in prompt
