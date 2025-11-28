"""Tests for Nikita Agent Tools - TDD for T2.2 and T6.2.

T2.2 Acceptance Criteria (recall_memory):
- AC-2.2.1: Tool decorated with `@agent.tool(retries=2)`
- AC-2.2.2: Tool accepts query: str parameter
- AC-2.2.3: Tool calls `memory.search_memory(query, limit=5)`
- AC-2.2.4: Tool returns formatted string of results
- AC-2.2.5: Tool handles empty results gracefully

T6.2 Acceptance Criteria (note_user_fact):
- AC-6.2.1: Tool decorated with `@agent.tool`
- AC-6.2.2: Tool accepts fact: str and confidence: float parameters
- AC-6.2.3: Tool calls `memory.add_user_fact(fact, confidence)`
- AC-6.2.4: Tool returns confirmation string
"""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


class TestRecallMemoryTool:
    """Tests for recall_memory agent tool."""

    def test_tools_module_importable(self):
        """Tools module should be importable."""
        from nikita.agents.text import tools

        assert hasattr(tools, "recall_memory")

    def test_ac_2_2_1_tool_is_decorated(self):
        """AC-2.2.1: Tool should be decorated with @agent.tool(retries=2)."""
        from nikita.agents.text.tools import recall_memory

        # The tool should be a callable (the decorated function)
        assert callable(recall_memory)
        # The function should have the tool metadata
        # Note: In Pydantic AI, tools have specific attributes after decoration

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_ac_2_2_1_tool_registered_with_agent(self):
        """AC-2.2.1: Tool is registered with the agent with retries=2."""
        from nikita.agents.text.agent import get_nikita_agent

        # Clear the cache to get a fresh agent with tools
        get_nikita_agent.cache_clear()
        agent = get_nikita_agent()

        # Check that recall_memory is in the agent's tools
        tool_names = [tool.name for tool in agent._function_tools.values()]
        assert "recall_memory" in tool_names

        # Clean up
        get_nikita_agent.cache_clear()

    def test_ac_2_2_2_accepts_query_parameter(self):
        """AC-2.2.2: Tool accepts query: str parameter."""
        from nikita.agents.text.tools import recall_memory
        import inspect

        sig = inspect.signature(recall_memory)
        params = list(sig.parameters.keys())

        # Should have ctx and query parameters
        assert "ctx" in params
        assert "query" in params

    @pytest.mark.asyncio
    async def test_ac_2_2_3_calls_search_memory(self):
        """AC-2.2.3: Tool calls memory.search_memory(query, limit=5)."""
        from nikita.agents.text.tools import recall_memory

        # Create mock context with memory
        mock_memory = MagicMock()
        mock_memory.search_memory = AsyncMock(return_value=[])

        mock_user = MagicMock()
        mock_user.chapter = 2

        mock_deps = MagicMock()
        mock_deps.memory = mock_memory
        mock_deps.user = mock_user

        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        # Call the tool
        await recall_memory(mock_ctx, "test query")

        # Verify search_memory was called with correct args
        mock_memory.search_memory.assert_called_once_with("test query", limit=5)

    @pytest.mark.asyncio
    async def test_ac_2_2_4_returns_formatted_results(self):
        """AC-2.2.4: Tool returns formatted string of results."""
        from nikita.agents.text.tools import recall_memory

        # Create mock results
        mock_results = [
            {
                "graph_type": "user",
                "fact": "User works at Tesla",
                "created_at": datetime(2025, 1, 15, tzinfo=timezone.utc),
                "source": "user_message",
                "relevance_score": 0.95,
            },
            {
                "graph_type": "relationship",
                "fact": "We discussed their engineering background",
                "created_at": datetime(2025, 1, 14, tzinfo=timezone.utc),
                "source": "system_event",
                "relevance_score": 0.82,
            },
        ]

        mock_memory = MagicMock()
        mock_memory.search_memory = AsyncMock(return_value=mock_results)

        mock_deps = MagicMock()
        mock_deps.memory = mock_memory

        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        # Call the tool
        result = await recall_memory(mock_ctx, "work")

        # Verify result is a string
        assert isinstance(result, str)

        # Verify results are formatted
        assert "Tesla" in result
        assert "engineering" in result
        assert "2025-01-15" in result or "2025-01-14" in result

    @pytest.mark.asyncio
    async def test_ac_2_2_5_handles_empty_results(self):
        """AC-2.2.5: Tool handles empty results gracefully."""
        from nikita.agents.text.tools import recall_memory

        mock_memory = MagicMock()
        mock_memory.search_memory = AsyncMock(return_value=[])

        mock_deps = MagicMock()
        mock_deps.memory = mock_memory

        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        # Call the tool with query that returns no results
        result = await recall_memory(mock_ctx, "something I've never mentioned")

        # Should return a graceful message, not crash
        assert isinstance(result, str)
        assert len(result) > 0
        # Should indicate no results found
        assert "no" in result.lower() or "nothing" in result.lower() or "found" in result.lower()


class TestFormatMemoryResults:
    """Tests for the format_memory_results helper function."""

    def test_format_function_exists(self):
        """format_memory_results helper should exist."""
        from nikita.agents.text.tools import format_memory_results

        assert callable(format_memory_results)

    def test_format_with_multiple_results(self):
        """Should format multiple memory results nicely."""
        from nikita.agents.text.tools import format_memory_results

        results = [
            {
                "graph_type": "user",
                "fact": "User is an engineer",
                "created_at": datetime(2025, 1, 15, tzinfo=timezone.utc),
                "source": "user_message",
                "relevance_score": 0.9,
            },
            {
                "graph_type": "nikita",
                "fact": "I was stressed about work deadline",
                "created_at": datetime(2025, 1, 14, tzinfo=timezone.utc),
                "source": "system_event",
                "relevance_score": 0.7,
            },
        ]

        formatted = format_memory_results(results)

        assert isinstance(formatted, str)
        assert "engineer" in formatted
        assert "stressed" in formatted
        # Should include labels for graph types
        assert "About them" in formatted or "user" in formatted.lower()

    def test_format_empty_results(self):
        """Should return appropriate message for empty results."""
        from nikita.agents.text.tools import format_memory_results

        formatted = format_memory_results([])

        assert isinstance(formatted, str)
        assert "no" in formatted.lower() or "nothing" in formatted.lower()

    def test_format_single_result(self):
        """Should format a single result correctly."""
        from nikita.agents.text.tools import format_memory_results

        results = [
            {
                "graph_type": "relationship",
                "fact": "We shared a joke about my cat",
                "created_at": datetime(2025, 1, 10, tzinfo=timezone.utc),
                "source": "system_event",
                "relevance_score": 0.85,
            },
        ]

        formatted = format_memory_results(results)

        assert "cat" in formatted
        assert "joke" in formatted

    def test_format_handles_missing_created_at(self):
        """Should handle results with missing created_at."""
        from nikita.agents.text.tools import format_memory_results

        results = [
            {
                "graph_type": "user",
                "fact": "User mentioned a deadline",
                "created_at": None,
                "source": "user_message",
                "relevance_score": 0.8,
            },
        ]

        # Should not crash
        formatted = format_memory_results(results)
        assert isinstance(formatted, str)
        assert "deadline" in formatted


class TestNoteUserFactTool:
    """Tests for note_user_fact agent tool (T6.2)."""

    def test_note_user_fact_exists(self):
        """note_user_fact function should exist in tools module."""
        from nikita.agents.text import tools

        assert hasattr(tools, "note_user_fact")

    def test_ac_6_2_1_tool_is_callable(self):
        """AC-6.2.1: Tool should be callable (decorated with @agent.tool)."""
        from nikita.agents.text.tools import note_user_fact

        # The tool should be a callable (the decorated function)
        assert callable(note_user_fact)

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_ac_6_2_1_tool_registered_with_agent(self):
        """AC-6.2.1: Tool is registered with the agent."""
        from nikita.agents.text.agent import get_nikita_agent

        # Clear the cache to get a fresh agent with tools
        get_nikita_agent.cache_clear()
        agent = get_nikita_agent()

        # Check that note_user_fact is in the agent's tools
        tool_names = [tool.name for tool in agent._function_tools.values()]
        assert "note_user_fact" in tool_names

        # Clean up
        get_nikita_agent.cache_clear()

    def test_ac_6_2_2_accepts_fact_and_confidence_parameters(self):
        """AC-6.2.2: Tool accepts fact: str and confidence: float parameters."""
        from nikita.agents.text.tools import note_user_fact
        import inspect

        sig = inspect.signature(note_user_fact)
        params = list(sig.parameters.keys())

        # Should have ctx, fact, and confidence parameters
        assert "ctx" in params
        assert "fact" in params
        assert "confidence" in params

    @pytest.mark.asyncio
    async def test_ac_6_2_3_calls_add_user_fact(self):
        """AC-6.2.3: Tool calls memory.add_user_fact(fact, confidence)."""
        from nikita.agents.text.tools import note_user_fact

        # Create mock context with memory
        mock_memory = MagicMock()
        mock_memory.add_user_fact = AsyncMock(return_value=None)

        mock_user = MagicMock()
        mock_user.id = "test-user-id"

        mock_deps = MagicMock()
        mock_deps.memory = mock_memory
        mock_deps.user = mock_user

        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        # Call the tool
        await note_user_fact(mock_ctx, "User works at Tesla", 0.9)

        # Verify add_user_fact was called with correct args
        mock_memory.add_user_fact.assert_called_once_with("User works at Tesla", 0.9)

    @pytest.mark.asyncio
    async def test_ac_6_2_4_returns_confirmation_string(self):
        """AC-6.2.4: Tool returns confirmation string."""
        from nikita.agents.text.tools import note_user_fact

        mock_memory = MagicMock()
        mock_memory.add_user_fact = AsyncMock(return_value=None)

        mock_deps = MagicMock()
        mock_deps.memory = mock_memory

        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        # Call the tool
        result = await note_user_fact(mock_ctx, "User is an engineer", 0.85)

        # Should return a confirmation string
        assert isinstance(result, str)
        assert len(result) > 0
        # Should mention something about noting/recording the fact
        assert "noted" in result.lower() or "recorded" in result.lower() or "saved" in result.lower()

    @pytest.mark.asyncio
    async def test_tool_handles_high_confidence_fact(self):
        """Tool should handle high confidence facts (explicit)."""
        from nikita.agents.text.tools import note_user_fact

        mock_memory = MagicMock()
        mock_memory.add_user_fact = AsyncMock(return_value=None)

        mock_deps = MagicMock()
        mock_deps.memory = mock_memory

        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        # High confidence explicit fact
        result = await note_user_fact(mock_ctx, "User's name is John", 0.95)

        assert isinstance(result, str)
        mock_memory.add_user_fact.assert_called_once_with("User's name is John", 0.95)

    @pytest.mark.asyncio
    async def test_tool_handles_low_confidence_fact(self):
        """Tool should handle lower confidence facts (implicit)."""
        from nikita.agents.text.tools import note_user_fact

        mock_memory = MagicMock()
        mock_memory.add_user_fact = AsyncMock(return_value=None)

        mock_deps = MagicMock()
        mock_deps.memory = mock_memory

        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        # Lower confidence implicit fact
        result = await note_user_fact(mock_ctx, "User may be stressed about work", 0.6)

        assert isinstance(result, str)
        mock_memory.add_user_fact.assert_called_once_with("User may be stressed about work", 0.6)
