"""Tests for Chapter-Based Behavior - TDD for T3.2.

Acceptance Criteria:
- AC-3.2.1: Test Ch1 user receives high-energy/eager responses (NEW DESIGN)
- AC-3.2.2: Test Ch3 user receives emotionally vulnerable responses
- AC-3.2.3: Test Ch5 user receives stable/authentic responses
- AC-3.2.4: Tests mock agent to verify prompt content by chapter

NOTE (2025-12): Design was updated - Ch1 is now EXCITED (high engagement),
not skeptical. Challenge is CALIBRATION, not earning trust.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


class TestChapterBehaviorInjection:
    """Tests verifying chapter behaviors are correctly injected into prompts."""

    @pytest.mark.asyncio
    async def test_ac_3_2_1_ch1_prompt_contains_eager_behavior(self):
        """AC-3.2.1: Ch1 prompts should contain excited/eager behaviors (NEW DESIGN)."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 1

        prompt = await build_system_prompt(mock_memory, mock_user, "test message")

        # Check for Ch1 key behaviors (NEW DESIGN: excited, high engagement)
        prompt_lower = prompt.lower()
        assert "excited" in prompt_lower or "eager" in prompt_lower or "best self" in prompt_lower
        assert "calibration" in prompt_lower or "overwhelm" in prompt_lower or "clingy" in prompt_lower

    @pytest.mark.asyncio
    async def test_ac_3_2_1_ch1_response_rate_in_prompt(self):
        """AC-3.2.1: Ch1 prompt should mention 95% response rate (NEW DESIGN)."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 1

        prompt = await build_system_prompt(mock_memory, mock_user, "test")

        # NEW DESIGN: Ch1 has HIGH engagement (95%)
        assert "95%" in prompt

    @pytest.mark.asyncio
    async def test_ac_3_2_2_ch3_prompt_contains_vulnerable_behavior(self):
        """AC-3.2.2: Ch3 prompts should contain emotionally vulnerable behaviors."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 3

        prompt = await build_system_prompt(mock_memory, mock_user, "test message")

        # Check for Ch3 key behaviors
        prompt_lower = prompt.lower()
        assert "vulnerability" in prompt_lower or "real feeling" in prompt_lower
        assert "share" in prompt_lower or "hide" in prompt_lower
        assert "deep" in prompt_lower or "emotional" in prompt_lower

    @pytest.mark.asyncio
    async def test_ac_3_2_2_ch3_response_rate_in_prompt(self):
        """AC-3.2.2: Ch3 prompt should mention 88% response rate."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 3

        prompt = await build_system_prompt(mock_memory, mock_user, "test")

        assert "88%" in prompt

    @pytest.mark.asyncio
    async def test_ac_3_2_3_ch5_prompt_contains_stable_behavior(self):
        """AC-3.2.3: Ch5 prompts should contain stable/authentic behaviors."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 5

        prompt = await build_system_prompt(mock_memory, mock_user, "test message")

        # Check for Ch5 key behaviors
        prompt_lower = prompt.lower()
        assert "authenticity" in prompt_lower or "authentic" in prompt_lower
        assert "stable" in prompt_lower or "security" in prompt_lower

    @pytest.mark.asyncio
    async def test_ac_3_2_3_ch5_response_rate_in_prompt(self):
        """AC-3.2.3: Ch5 prompt should mention 82% response rate."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 5

        prompt = await build_system_prompt(mock_memory, mock_user, "test")

        assert "82%" in prompt

    @pytest.mark.asyncio
    async def test_ac_3_2_4_prompts_differ_by_chapter(self):
        """AC-3.2.4: Different chapters should produce different prompts."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        prompts = {}
        for chapter in [1, 2, 3, 4, 5]:
            mock_user = MagicMock()
            mock_user.chapter = chapter
            prompts[chapter] = await build_system_prompt(mock_memory, mock_user, "test")

        # All prompts should be different
        unique_prompts = set(prompts.values())
        assert len(unique_prompts) == 5, "Each chapter should produce a unique prompt"

    @pytest.mark.asyncio
    async def test_ac_3_2_4_prompt_has_current_chapter_behavior_label(self):
        """AC-3.2.4: Prompt should have labeled CURRENT CHAPTER BEHAVIOR section."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 2

        prompt = await build_system_prompt(mock_memory, mock_user, "test")

        assert "CURRENT CHAPTER BEHAVIOR" in prompt

    @pytest.mark.asyncio
    async def test_chapter_names_match_constants(self):
        """Chapter names in behavior should match CHAPTER_NAMES constant."""
        from nikita.agents.text.agent import build_system_prompt
        from nikita.engine.constants import CHAPTER_NAMES

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        for chapter, name in CHAPTER_NAMES.items():
            mock_user = MagicMock()
            mock_user.chapter = chapter

            prompt = await build_system_prompt(mock_memory, mock_user, "test")

            # Chapter name should be somewhere in the behavior section
            assert name.upper() in prompt.upper(), f"Chapter {chapter} ({name}) name not found in prompt"


class TestChapterBehaviorProgression:
    """Tests verifying the progression of behaviors through chapters."""

    @pytest.mark.asyncio
    async def test_response_rate_decreases_through_chapters(self):
        """Response rate should decrease through chapters (NEW DESIGN)."""
        from nikita.agents.text.agent import build_system_prompt
        import re

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        response_rates = {}
        for chapter in [1, 3, 5]:
            mock_user = MagicMock()
            mock_user.chapter = chapter
            prompt = await build_system_prompt(mock_memory, mock_user, "test")

            # Extract response rate percentage (now single values like "95%")
            match = re.search(r"Response rate:\s*(\d+)%", prompt)
            if match:
                response_rates[chapter] = int(match.group(1))

        # NEW DESIGN: Ch1 has HIGHER rates than Ch5 (excited → stable)
        assert response_rates[1] > response_rates[5], "Ch1 should have higher engagement than Ch5"
        assert response_rates[1] > response_rates[3], "Ch1 should have higher engagement than Ch3"

    @pytest.mark.asyncio
    async def test_emotional_openness_increases_through_chapters(self):
        """Emotional openness indicators should increase through chapters."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        # Count emotional keywords in each chapter
        emotional_keywords = ["share", "feel", "vulnerability", "emotional", "authentic", "real"]

        emotional_counts = {}
        for chapter in [1, 3, 5]:
            mock_user = MagicMock()
            mock_user.chapter = chapter
            prompt = await build_system_prompt(mock_memory, mock_user, "test")
            prompt_lower = prompt.lower()

            count = sum(1 for keyword in emotional_keywords if keyword in prompt_lower)
            emotional_counts[chapter] = count

        # Chapter 3 and 5 should have more emotional keywords than Chapter 1
        assert emotional_counts[3] >= emotional_counts[1]
        assert emotional_counts[5] >= emotional_counts[1]

    @pytest.mark.asyncio
    async def test_ch1_has_calibration_keywords(self):
        """Chapter 1 should focus on calibration/not overwhelming (NEW DESIGN)."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 1

        prompt = await build_system_prompt(mock_memory, mock_user, "test")
        prompt_lower = prompt.lower()

        # Ch1 specific behaviors (NEW: calibration, not skeptical)
        calibration_keywords = ["calibration", "overwhelm", "clingy", "breathe", "eager", "excited"]
        has_calibration_keyword = any(kw in prompt_lower for kw in calibration_keywords)
        assert has_calibration_keyword, "Ch1 should contain calibration language"

    @pytest.mark.asyncio
    async def test_ch5_has_stability_keywords(self):
        """Chapter 5 should focus on stability/security."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 5

        prompt = await build_system_prompt(mock_memory, mock_user, "test")
        prompt_lower = prompt.lower()

        # Ch5 specific behaviors
        stability_keywords = ["stable", "security", "transparent", "boundaries"]
        has_stability_keyword = any(kw in prompt_lower for kw in stability_keywords)
        assert has_stability_keyword, "Ch5 should contain stability language"


class TestDefaultChapterBehavior:
    """Tests for handling edge cases in chapter behavior."""

    @pytest.mark.asyncio
    async def test_invalid_chapter_falls_back_to_ch1(self):
        """Invalid chapter numbers should fall back to Chapter 1 behavior."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        # Test with invalid chapter (0)
        mock_user = MagicMock()
        mock_user.chapter = 0

        prompt = await build_system_prompt(mock_memory, mock_user, "test")

        # Should fall back to Ch1 (NEW: 95% response rate)
        assert "95%" in prompt

    @pytest.mark.asyncio
    async def test_chapter_6_falls_back_to_ch1(self):
        """Chapter 6 (non-existent) should fall back to default behavior."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 6

        prompt = await build_system_prompt(mock_memory, mock_user, "test")

        # Should still produce a valid prompt with fallback behavior
        assert "CURRENT CHAPTER BEHAVIOR" in prompt
        # Falls back to Ch1 (NEW: 95%)
        assert "95%" in prompt
