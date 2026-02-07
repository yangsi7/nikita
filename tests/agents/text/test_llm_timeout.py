"""Tests for LLM timeout handling in text agent (Spec 036 T1.2).

Tests verify that:
1. LLM calls exceeding timeout return graceful fallback message
2. Timeout errors are logged with user context
3. Normal responses work within timeout
4. Original exceptions (non-timeout) are preserved
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Set API key before any imports that might trigger agent creation
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-testing")

from nikita.agents.text.agent import (
    LLM_TIMEOUT_FALLBACK_MESSAGE,
    LLM_TIMEOUT_SECONDS,
)


class TestLLMTimeoutHandling:
    """Test timeout handling in generate_response()."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = MagicMock()
        user.id = uuid4()
        user.chapter = 1
        user.relationship_score = 50.0
        return user

    @pytest.fixture
    def mock_deps(self, mock_user):
        """Create mock NikitaDeps."""
        deps = MagicMock()
        deps.user = mock_user
        deps.memory = None
        deps.generated_prompt = None
        deps.conversation_messages = []
        deps.conversation_id = uuid4()
        return deps

    @pytest.mark.asyncio
    async def test_llm_timeout_returns_graceful_error(self, mock_deps):
        """AC-1.2.2: TimeoutError caught and returns graceful fallback message."""
        # Create a slow async function that will be timed out
        async def slow_llm_call(*args, **kwargs):
            await asyncio.sleep(200)  # Will be interrupted by timeout
            return MagicMock(output="This should never be reached")

        with patch("nikita.agents.text.agent.nikita_agent") as mock_agent:
            mock_agent.run = slow_llm_call

            with patch("nikita.agents.text.agent.build_system_prompt") as mock_prompt:
                mock_prompt.return_value = "Test system prompt"

                from nikita.agents.text.agent import generate_response

                # Use a shorter timeout for testing (patch the constant)
                with patch("nikita.agents.text.agent.LLM_TIMEOUT_SECONDS", 0.1):
                    result = await generate_response(mock_deps, "Hello")

                # Should get the graceful fallback message
                assert result == LLM_TIMEOUT_FALLBACK_MESSAGE

    @pytest.mark.asyncio
    async def test_llm_timeout_logs_error(self, mock_deps, caplog):
        """AC-1.2.3: Timeout errors logged with user_id context."""
        import logging

        async def slow_llm_call(*args, **kwargs):
            await asyncio.sleep(200)
            return MagicMock(output="This should never be reached")

        with patch("nikita.agents.text.agent.nikita_agent") as mock_agent:
            mock_agent.run = slow_llm_call

            with patch("nikita.agents.text.agent.build_system_prompt") as mock_prompt:
                mock_prompt.return_value = "Test system prompt"

                from nikita.agents.text.agent import generate_response

                with caplog.at_level(logging.ERROR):
                    with patch("nikita.agents.text.agent.LLM_TIMEOUT_SECONDS", 0.1):
                        await generate_response(mock_deps, "Hello")

                # Should log timeout error with user context
                assert any("[LLM-TIMEOUT]" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_normal_response_within_timeout(self, mock_deps):
        """Normal LLM responses complete successfully within timeout."""
        mock_result = MagicMock()
        mock_result.output = "Hello! How are you today?"

        with patch("nikita.agents.text.agent.nikita_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)

            with patch("nikita.agents.text.agent.build_system_prompt") as mock_prompt:
                mock_prompt.return_value = "Test system prompt"

                from nikita.agents.text.agent import generate_response

                result = await generate_response(mock_deps, "Hello")

                assert result == "Hello! How are you today?"

    @pytest.mark.asyncio
    async def test_non_timeout_exceptions_preserved(self, mock_deps):
        """Original exceptions (non-timeout) should be raised, not caught."""
        with patch("nikita.agents.text.agent.nikita_agent") as mock_agent:
            mock_agent.run = AsyncMock(side_effect=ValueError("API key invalid"))

            with patch("nikita.agents.text.agent.build_system_prompt") as mock_prompt:
                mock_prompt.return_value = "Test system prompt"

                from nikita.agents.text.agent import generate_response

                # Non-timeout exceptions should propagate
                with pytest.raises(ValueError, match="API key invalid"):
                    await generate_response(mock_deps, "Hello")


class TestLLMTimeoutConfiguration:
    """Test the timeout configuration and behavior."""

    def test_timeout_constant_exists(self):
        """Timeout constant should be defined."""
        assert LLM_TIMEOUT_SECONDS == 120.0

    def test_timeout_value_is_reasonable(self):
        """Timeout should be set to a reasonable value (e.g., 120 seconds)."""
        assert LLM_TIMEOUT_SECONDS <= 300  # Cloud Run max
        assert LLM_TIMEOUT_SECONDS >= 60  # Reasonable minimum

    def test_fallback_message_exists(self):
        """Fallback message constant should be defined."""
        assert LLM_TIMEOUT_FALLBACK_MESSAGE is not None
        assert len(LLM_TIMEOUT_FALLBACK_MESSAGE) > 0

    def test_graceful_fallback_message_is_user_friendly(self):
        """Fallback message should be appropriate for the game context."""
        # Should contain apologetic/friendly tone
        msg = LLM_TIMEOUT_FALLBACK_MESSAGE.lower()
        assert "sorry" in msg or "trouble" in msg or "moment" in msg
