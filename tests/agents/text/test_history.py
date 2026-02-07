"""Unit tests for HistoryLoader (Spec 030: Text Agent Message History).

Tests message history loading, conversion, token budgeting, and tool call pairing.
"""

import pytest
from uuid import uuid4

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from nikita.agents.text.history import (
    HistoryLoader,
    load_message_history,
    DEFAULT_TOKEN_BUDGET,
)
from nikita.context.utils.token_counter import get_token_estimator


class TestHistoryLoaderBasics:
    """Test basic HistoryLoader functionality."""

    def test_empty_conversation_returns_none(self):
        """Test that empty conversation returns None for fresh prompt generation."""
        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=[])
        result = loader.load()
        assert result is None

    def test_none_messages_returns_none(self):
        """Test that None messages returns None."""
        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=None)
        result = loader.load()
        assert result is None

    def test_load_user_messages(self):
        """Test loading user messages as ModelRequest."""
        raw_messages = [
            {"role": "user", "content": "Hello", "timestamp": "2026-01-01T10:00:00Z"},
        ]
        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], ModelRequest)
        assert isinstance(result[0].parts[0], UserPromptPart)
        assert result[0].parts[0].content == "Hello"

    def test_load_nikita_messages(self):
        """Test loading nikita messages as ModelResponse."""
        raw_messages = [
            {"role": "nikita", "content": "Hey babe!", "timestamp": "2026-01-01T10:00:00Z"},
        ]
        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], ModelResponse)
        assert isinstance(result[0].parts[0], TextPart)
        assert result[0].parts[0].content == "Hey babe!"

    def test_load_assistant_role_converted(self):
        """Test that 'assistant' role is also converted to ModelResponse."""
        raw_messages = [
            {"role": "assistant", "content": "Hi there!", "timestamp": "2026-01-01T10:00:00Z"},
        ]
        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], ModelResponse)

    def test_load_mixed_conversation(self):
        """Test loading a mixed user/nikita conversation."""
        raw_messages = [
            {"role": "user", "content": "Hello", "timestamp": "2026-01-01T10:00:00Z"},
            {"role": "nikita", "content": "Hey!", "timestamp": "2026-01-01T10:01:00Z"},
            {"role": "user", "content": "How are you?", "timestamp": "2026-01-01T10:02:00Z"},
            {"role": "nikita", "content": "I'm good!", "timestamp": "2026-01-01T10:03:00Z"},
        ]
        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        assert result is not None
        assert len(result) == 4
        assert isinstance(result[0], ModelRequest)  # user
        assert isinstance(result[1], ModelResponse)  # nikita
        assert isinstance(result[2], ModelRequest)  # user
        assert isinstance(result[3], ModelResponse)  # nikita

    def test_preserves_message_order(self):
        """Test that message order is preserved (oldest first)."""
        raw_messages = [
            {"role": "user", "content": "First", "timestamp": "2026-01-01T10:00:00Z"},
            {"role": "nikita", "content": "Second", "timestamp": "2026-01-01T10:01:00Z"},
            {"role": "user", "content": "Third", "timestamp": "2026-01-01T10:02:00Z"},
        ]
        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        assert result is not None
        assert result[0].parts[0].content == "First"
        assert result[1].parts[0].content == "Second"
        assert result[2].parts[0].content == "Third"


class TestHistoryLoaderLimit:
    """Test message limit functionality."""

    def test_respects_limit_parameter(self):
        """Test that limit parameter restricts message count."""
        # Create 20 messages
        raw_messages = []
        for i in range(20):
            role = "user" if i % 2 == 0 else "nikita"
            raw_messages.append(
                {"role": role, "content": f"Message {i}", "timestamp": f"2026-01-01T10:{i:02d}:00Z"}
            )

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load(limit=5)

        assert result is not None
        # Should have last 5 messages
        assert len(result) <= 5
        # Should be the most recent messages
        assert result[-1].parts[0].content == "Message 19"

    def test_limit_zero_loads_all(self):
        """Test that limit=0 loads all messages (subject to token budget)."""
        raw_messages = [
            {"role": "user", "content": "Hello", "timestamp": "2026-01-01T10:00:00Z"},
            {"role": "nikita", "content": "Hi!", "timestamp": "2026-01-01T10:01:00Z"},
        ]
        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load(limit=0)

        # limit=0 means load all (but respects token budget)
        assert result is not None
        assert len(result) == 2


class TestTokenBudgeting:
    """Test token budget enforcement."""

    def test_estimate_tokens(self):
        """Test token estimation using TokenEstimator."""
        loader = HistoryLoader(conversation_id=uuid4())

        messages = [
            ModelRequest(parts=[UserPromptPart(content="a" * 100)]),  # 100 chars
            ModelResponse(parts=[TextPart(content="b" * 200)]),  # 200 chars
        ]

        # Test fast estimation (default)
        tokens_fast = loader._estimate_tokens(messages, accurate=False)
        # Fast estimate: 300 chars // 4 = 75 tokens
        assert tokens_fast == 75

        # Test accurate estimation
        tokens_accurate = loader._estimate_tokens(messages, accurate=True)
        # Accurate count will vary based on tiktoken, but should be close
        assert 50 <= tokens_accurate <= 150  # Reasonable range for 300 chars

    def test_truncates_oldest_when_over_budget(self):
        """Test that oldest messages are truncated when over budget."""
        # Create messages that exceed a small budget
        raw_messages = []
        for i in range(50):
            # Each message ~100 chars = ~30 tokens
            content = f"Message {i} with some padding text here to make it longer"
            role = "user" if i % 2 == 0 else "nikita"
            raw_messages.append({"role": role, "content": content, "timestamp": f"T{i}"})

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)

        # Small budget should cause truncation
        result = loader.load(limit=50, token_budget=500)

        assert result is not None
        # Should have fewer messages due to truncation
        assert len(result) < 50
        # Should preserve most recent messages
        assert "Message 49" in result[-1].parts[0].content

    def test_preserves_minimum_turns(self):
        """Test that minimum turns are preserved even if over budget."""
        # Create messages that exceed budget
        raw_messages = []
        for i in range(15):
            content = "a" * 500  # Large messages
            role = "user" if i % 2 == 0 else "nikita"
            raw_messages.append({"role": role, "content": content, "timestamp": f"T{i}"})

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)

        # Very small budget, but min_turns should preserve at least 10
        result = loader.load(limit=15, token_budget=100)

        assert result is not None
        # Should preserve minimum turns (default 10)
        assert len(result) >= 10


class TestToolCallPairing:
    """Test tool call/return pairing logic."""

    def test_preserves_paired_tool_calls(self):
        """Test that properly paired tool calls are preserved."""
        # Create a conversation with a paired tool call
        tool_call_id = "call_123"

        messages = [
            ModelRequest(parts=[UserPromptPart(content="What's the weather?")]),
            ModelResponse(parts=[ToolCallPart(tool_name="get_weather", tool_call_id=tool_call_id, args={})]),
            ModelRequest(parts=[ToolReturnPart(tool_call_id=tool_call_id, tool_name="get_weather", content="Sunny, 72F")]),
            ModelResponse(parts=[TextPart(content="It's sunny and 72°F!")]),
        ]

        loader = HistoryLoader(conversation_id=uuid4())
        result = loader._ensure_tool_call_pairing(messages)

        # All messages should be preserved
        assert len(result) == 4

    def test_excludes_unpaired_tool_calls(self):
        """Test that unpaired tool calls are excluded."""
        tool_call_id = "call_456"

        messages = [
            ModelRequest(parts=[UserPromptPart(content="Check something")]),
            ModelResponse(parts=[ToolCallPart(tool_name="check", tool_call_id=tool_call_id, args={})]),
            # No ToolReturnPart for this call - it's unpaired
        ]

        loader = HistoryLoader(conversation_id=uuid4())
        result = loader._ensure_tool_call_pairing(messages)

        # The response with unpaired tool call should be removed
        assert len(result) == 1
        assert isinstance(result[0], ModelRequest)

    def test_handles_multiple_tool_calls(self):
        """Test handling of multiple tool calls with some unpaired."""
        paired_id = "call_paired"
        unpaired_id = "call_unpaired"

        messages = [
            ModelRequest(parts=[UserPromptPart(content="Do stuff")]),
            ModelResponse(parts=[ToolCallPart(tool_name="paired_tool", tool_call_id=paired_id, args={})]),
            ModelRequest(parts=[ToolReturnPart(tool_call_id=paired_id, tool_name="paired_tool", content="Paired result")]),
            ModelResponse(parts=[TextPart(content="First result processed")]),
            # Unpaired tool call at the end
            ModelResponse(parts=[ToolCallPart(tool_name="unpaired_tool", tool_call_id=unpaired_id, args={})]),
        ]

        loader = HistoryLoader(conversation_id=uuid4())
        result = loader._ensure_tool_call_pairing(messages)

        # Should have 4 messages (last unpaired response removed)
        assert len(result) == 4
        assert isinstance(result[-1], ModelResponse)
        assert isinstance(result[-1].parts[0], TextPart)  # The text response, not tool call

    def test_empty_messages_unaffected(self):
        """Test that empty message list is handled."""
        loader = HistoryLoader(conversation_id=uuid4())
        result = loader._ensure_tool_call_pairing([])
        assert result == []


class TestConvenienceFunction:
    """Test the load_message_history convenience function."""

    @pytest.mark.asyncio
    async def test_convenience_function_with_messages(self):
        """Test load_message_history with valid messages."""
        raw_messages = [
            {"role": "user", "content": "Hello", "timestamp": "T1"},
            {"role": "nikita", "content": "Hi!", "timestamp": "T2"},
        ]

        result = await load_message_history(
            conversation_messages=raw_messages,
            conversation_id=uuid4(),
        )

        assert result is not None
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_convenience_function_with_none(self):
        """Test load_message_history with None messages."""
        result = await load_message_history(
            conversation_messages=None,
            conversation_id=uuid4(),
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_convenience_function_with_empty_list(self):
        """Test load_message_history with empty list."""
        result = await load_message_history(
            conversation_messages=[],
            conversation_id=uuid4(),
        )

        assert result is None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_unknown_role_logged_and_skipped(self):
        """Test that unknown roles are logged and skipped."""
        raw_messages = [
            {"role": "user", "content": "Hello", "timestamp": "T1"},
            {"role": "unknown_role", "content": "This should be skipped", "timestamp": "T2"},
            {"role": "nikita", "content": "Hi!", "timestamp": "T3"},
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        assert result is not None
        # Unknown role should be skipped
        assert len(result) == 2

    def test_missing_content_field(self):
        """Test handling of messages without content field."""
        raw_messages = [
            {"role": "user"},  # No content field
            {"role": "nikita", "content": "Hi!", "timestamp": "T2"},
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        assert result is not None
        # First message should have empty content
        assert result[0].parts[0].content == ""
        assert result[1].parts[0].content == "Hi!"

    def test_handles_analysis_field(self):
        """Test that analysis field in messages is ignored during conversion."""
        raw_messages = [
            {
                "role": "user",
                "content": "Hello",
                "timestamp": "T1",
                "analysis": {"sentiment": "positive", "deltas": {"intimacy": 0.5}},
            },
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        assert result is not None
        assert len(result) == 1
        # Analysis field should be ignored, only content matters
        assert result[0].parts[0].content == "Hello"

    def test_very_long_message_truncation(self):
        """Test that very long messages are handled."""
        # Single very long message
        raw_messages = [
            {"role": "user", "content": "x" * 10000, "timestamp": "T1"},
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        # With tiny budget, should still preserve minimum
        result = loader.load(token_budget=100)

        assert result is not None
        # Should preserve the message even if over budget (minimum turns)
        assert len(result) == 1
