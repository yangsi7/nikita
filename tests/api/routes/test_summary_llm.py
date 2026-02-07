"""Tests for Spec 043 T2.3: Daily summary LLM generation.

Verifies Claude Haiku generates summaries from conversation data,
with fallback to basic summary on failure.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDailySummaryLLM:
    """T3.5: Daily summary LLM tests."""

    @pytest.fixture
    def conversations_data(self):
        return [
            {"summary": "Talked about weekend plans", "emotional_tone": "warm"},
            {"summary": "Discussed favorite movies", "emotional_tone": "playful"},
        ]

    @pytest.fixture
    def new_threads(self):
        return [
            {"type": "topic", "content": "Weekend hiking trip"},
            {"type": "question", "content": "Favorite movie genre"},
        ]

    @pytest.fixture
    def nikita_thoughts(self):
        return [
            "He seems more relaxed today",
            "Should bring up the hiking trip again",
        ]

    @pytest.mark.asyncio
    async def test_llm_generates_summary(self, conversations_data, new_threads, nikita_thoughts):
        """AC-3.5.1: LLM generates summary from conversation data (mocked)."""
        from nikita.api.routes.tasks import _generate_summary_with_llm

        mock_result = MagicMock()
        mock_result.data = (
            "SUMMARY: We had such a fun time talking about weekend plans and movies today!\n"
            "KEY_MOMENTS: Planning hiking trip | Bonding over movie tastes\n"
            "EMOTIONAL_TONE: warm"
        )

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        with patch("nikita.config.settings.get_settings") as mock_settings_fn, \
             patch("pydantic_ai.Agent", return_value=mock_agent), \
             patch("pydantic_ai.models.anthropic.AnthropicModel"):
            mock_settings = MagicMock()
            mock_settings.anthropic_api_key = "test-key"
            mock_settings_fn.return_value = mock_settings

            result = await _generate_summary_with_llm(
                conversations_data=conversations_data,
                new_threads=new_threads,
                nikita_thoughts=nikita_thoughts,
                user_chapter=3,
            )

        assert "fun time" in result["summary_text"]
        assert len(result["key_moments"]) == 2
        assert result["emotional_tone"] == "warm"

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self, conversations_data, new_threads, nikita_thoughts):
        """AC-3.5.2: Fallback to basic summary on LLM failure."""
        from nikita.api.routes.tasks import _generate_summary_with_llm

        with patch("nikita.config.settings.get_settings") as mock_settings_fn, \
             patch("pydantic_ai.Agent", side_effect=Exception("API Error")):
            mock_settings = MagicMock()
            mock_settings.anthropic_api_key = "test-key"
            mock_settings_fn.return_value = mock_settings

            result = await _generate_summary_with_llm(
                conversations_data=conversations_data,
                new_threads=new_threads,
                nikita_thoughts=nikita_thoughts,
                user_chapter=3,
            )

        assert "2 conversations" in result["summary_text"]
        assert result["key_moments"] == []

    @pytest.mark.asyncio
    async def test_fallback_on_missing_api_key(self, conversations_data, new_threads, nikita_thoughts):
        """AC-3.5.2b: Fallback when anthropic_api_key is None."""
        from nikita.api.routes.tasks import _generate_summary_with_llm

        with patch("nikita.config.settings.get_settings") as mock_settings_fn:
            mock_settings = MagicMock()
            mock_settings.anthropic_api_key = None
            mock_settings_fn.return_value = mock_settings

            result = await _generate_summary_with_llm(
                conversations_data=conversations_data,
                new_threads=new_threads,
                nikita_thoughts=nikita_thoughts,
                user_chapter=3,
            )

        assert "2 conversations" in result["summary_text"]

    def test_summary_includes_key_moments_and_tone(self):
        """AC-3.5.3: Summary includes key_moments and emotional_tone."""
        from nikita.api.routes.tasks import _parse_summary_response

        response = (
            "SUMMARY: Had a deep conversation about life goals.\n"
            "KEY_MOMENTS: Shared childhood memory | Discussed future plans | Laughed together\n"
            "EMOTIONAL_TONE: passionate"
        )

        result = _parse_summary_response(response)

        assert result["summary_text"] == "Had a deep conversation about life goals."
        assert len(result["key_moments"]) == 3
        assert "childhood memory" in result["key_moments"][0]
        assert result["emotional_tone"] == "passionate"

    @pytest.mark.asyncio
    async def test_llm_timeout_prevents_blocking(self, conversations_data, new_threads, nikita_thoughts):
        """AC-3.5.4: LLM timeout (10s) prevents blocking."""
        import asyncio

        from nikita.api.routes.tasks import _generate_summary_with_llm

        async def slow_run(*args, **kwargs):
            await asyncio.sleep(15)  # Exceeds 10s timeout
            return MagicMock(data="SUMMARY: late\nKEY_MOMENTS:\nEMOTIONAL_TONE: neutral")

        mock_agent = MagicMock()
        mock_agent.run = slow_run

        with patch("nikita.config.settings.get_settings") as mock_settings_fn, \
             patch("pydantic_ai.Agent", return_value=mock_agent), \
             patch("pydantic_ai.models.anthropic.AnthropicModel"):
            mock_settings = MagicMock()
            mock_settings.anthropic_api_key = "test-key"
            mock_settings_fn.return_value = mock_settings

            result = await _generate_summary_with_llm(
                conversations_data=conversations_data,
                new_threads=new_threads,
                nikita_thoughts=nikita_thoughts,
                user_chapter=3,
            )

        # Should fall back due to timeout
        assert "2 conversations" in result["summary_text"]
        assert result["key_moments"] == []

    def test_fallback_summary_with_single_conversation(self):
        """Test fallback summary grammar for single conversation."""
        from nikita.api.routes.tasks import _fallback_summary

        result = _fallback_summary([{"emotional_tone": "warm"}])
        assert "1 conversation today" in result["summary_text"]
        assert result["emotional_tone"] == "warm"

    def test_fallback_summary_dominant_tone(self):
        """Test fallback summary picks dominant emotional tone."""
        from nikita.api.routes.tasks import _fallback_summary

        convs = [
            {"emotional_tone": "warm"},
            {"emotional_tone": "playful"},
            {"emotional_tone": "warm"},
        ]
        result = _fallback_summary(convs)
        assert result["emotional_tone"] == "warm"
