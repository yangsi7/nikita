"""Tests for NikitaTextAgent - TDD for T1.3.

Acceptance Criteria:
- AC-1.3.1: Agent uses anthropic:claude-sonnet-4-5-20250929 model
- AC-1.3.2: Agent has deps_type=NikitaDeps
- AC-1.3.3: @agent.system_prompt combines NIKITA_PERSONA + CHAPTER_BEHAVIORS + memory_context
- AC-1.3.4: Agent accepts user message and returns string response
- AC-1.3.5: Agent can be invoked with `await agent.run(message, deps=deps)`
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestNikitaAgentConfiguration:
    """Tests for agent configuration."""

    def test_agent_module_importable(self):
        """Agent module should be importable without API key."""
        from nikita.agents.text import agent

        assert hasattr(agent, "nikita_agent")
        assert hasattr(agent, "MODEL_NAME")
        assert hasattr(agent, "get_nikita_agent")

    def test_ac_1_3_1_model_name_constant(self):
        """AC-1.3.1: MODEL_NAME is anthropic:claude-sonnet-4-5-20250929."""
        from nikita.agents.text.agent import MODEL_NAME

        assert MODEL_NAME == "anthropic:claude-sonnet-4-5-20250929"
        assert "sonnet" in MODEL_NAME.lower()

    def test_ac_1_3_2_uses_nikita_deps(self):
        """AC-1.3.2: Agent has deps_type=NikitaDeps."""
        from nikita.agents.text.agent import get_nikita_agent
        from nikita.agents.text.deps import NikitaDeps

        # Set fake API key to allow agent creation (no actual API calls)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-for-structural-test"}):
            get_nikita_agent.cache_clear()
            agent = get_nikita_agent()
            assert agent.deps_type is NikitaDeps
            get_nikita_agent.cache_clear()


class TestNikitaAgentSystemPrompt:
    """Tests for system prompt generation."""

    @pytest.mark.asyncio
    async def test_ac_1_3_3_system_prompt_includes_persona(self):
        """AC-1.3.3: System prompt includes NIKITA_PERSONA."""
        from nikita.agents.text.agent import build_system_prompt
        from nikita.agents.text.persona import NIKITA_PERSONA

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="Test memory context")

        mock_user = MagicMock()
        mock_user.chapter = 1

        prompt = await build_system_prompt(mock_memory, mock_user, "test message")

        # Check persona elements are included
        assert "Nikita" in prompt
        assert "Russian" in prompt or "security" in prompt

    @pytest.mark.asyncio
    async def test_ac_1_3_3_system_prompt_includes_chapter_behavior(self):
        """AC-1.3.3: System prompt includes CHAPTER_BEHAVIORS."""
        from nikita.agents.text.agent import build_system_prompt
        from nikita.engine.constants import CHAPTER_BEHAVIORS

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user = MagicMock()
        mock_user.chapter = 1

        prompt = await build_system_prompt(mock_memory, mock_user, "test")

        # Chapter 1 behavior should mention response rate, timing, etc.
        assert "60-75%" in prompt or "CURIOSITY" in prompt or "guarded" in prompt

    @pytest.mark.asyncio
    async def test_ac_1_3_3_system_prompt_includes_memory_context(self):
        """AC-1.3.3: System prompt includes memory context.

        Note: With Spec 039, build_system_prompt now routes through context_engine.router.
        The router fetches memory context from the database, so we mock the router.
        """
        from nikita.agents.text.agent import build_system_prompt

        mock_user = MagicMock()
        mock_user.chapter = 2
        mock_user.id = "test-user-id"

        # Mock router to return a prompt with memory context
        expected_prompt = (
            "You are Nikita...\n\n"
            "## MEMORY CONTEXT\n"
            "[2025-01-15] (About them) User works at Tesla as an engineer"
        )

        # Current code uses legacy path when unified pipeline is disabled
        # The memory context comes from memory.get_context_for_prompt()
        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(
            return_value="[2025-01-15] (About them) User works at Tesla as an engineer"
        )

        with patch("nikita.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.is_unified_pipeline_enabled_for_user = MagicMock(return_value=False)
            prompt = await build_system_prompt(mock_memory, mock_user, "how was work")

        assert "Tesla" in prompt or "engineer" in prompt

    @pytest.mark.asyncio
    async def test_system_prompt_varies_by_chapter(self):
        """System prompt should change based on chapter."""
        from nikita.agents.text.agent import build_system_prompt

        mock_memory = MagicMock()
        mock_memory.get_context_for_prompt = AsyncMock(return_value="")

        mock_user_ch1 = MagicMock()
        mock_user_ch1.chapter = 1

        mock_user_ch5 = MagicMock()
        mock_user_ch5.chapter = 5

        prompt_ch1 = await build_system_prompt(mock_memory, mock_user_ch1, "test")
        prompt_ch5 = await build_system_prompt(mock_memory, mock_user_ch5, "test")

        # Prompts should be different for different chapters
        assert prompt_ch1 != prompt_ch5


class TestNikitaAgentInvocation:
    """Tests for invoking the agent."""

    def test_ac_1_3_4_agent_has_run_method(self):
        """AC-1.3.4: Agent should have a run method."""
        from nikita.agents.text.agent import get_nikita_agent

        # Set fake API key to allow agent creation (no actual API calls)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-for-structural-test"}):
            get_nikita_agent.cache_clear()
            agent = get_nikita_agent()
            assert hasattr(agent, "run")
            assert callable(agent.run)
            get_nikita_agent.cache_clear()

    def test_agent_run_is_async(self):
        """Agent.run should be an async method."""
        from nikita.agents.text.agent import get_nikita_agent
        import inspect

        # Set fake API key to allow agent creation (no actual API calls)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-for-structural-test"}):
            get_nikita_agent.cache_clear()
            agent = get_nikita_agent()
            # Check if run is a coroutine function
            assert inspect.iscoroutinefunction(agent.run)
            get_nikita_agent.cache_clear()


class TestGenerateResponse:
    """Tests for the generate_response helper function."""

    def test_generate_response_exists(self):
        """generate_response function should exist."""
        from nikita.agents.text.agent import generate_response

        assert callable(generate_response)

    @pytest.mark.asyncio
    async def test_generate_response_is_async(self):
        """generate_response should be async."""
        from nikita.agents.text.agent import generate_response
        import inspect

        assert inspect.iscoroutinefunction(generate_response)


class TestUsageLimits:
    """Tests for Pydantic AI UsageLimits (Spec 041 T2.6)."""

    def test_usage_limits_defined(self):
        """DEFAULT_USAGE_LIMITS should be defined with proper values."""
        from nikita.agents.text.agent import DEFAULT_USAGE_LIMITS

        assert DEFAULT_USAGE_LIMITS is not None
        assert DEFAULT_USAGE_LIMITS.output_tokens_limit == 4000
        assert DEFAULT_USAGE_LIMITS.request_limit == 10
        assert DEFAULT_USAGE_LIMITS.tool_calls_limit == 20

    def test_usage_limits_type(self):
        """DEFAULT_USAGE_LIMITS should be a UsageLimits instance."""
        from nikita.agents.text.agent import DEFAULT_USAGE_LIMITS
        from pydantic_ai import UsageLimits

        assert isinstance(DEFAULT_USAGE_LIMITS, UsageLimits)

    def test_usage_limits_exportable(self):
        """UsageLimits should be importable from agent module."""
        from nikita.agents.text.agent import UsageLimits, DEFAULT_USAGE_LIMITS

        # Verify we can create custom limits if needed
        custom = UsageLimits(output_tokens_limit=1000)
        assert custom.output_tokens_limit == 1000
