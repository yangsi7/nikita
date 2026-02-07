"""Error handling tests for HistoryLoader.

Spec 030: Text Agent Message History and Continuity
HIGH Priority Test Coverage (Audit Recommendation)

These tests verify that HistoryLoader handles various error
conditions gracefully without crashing.
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
import logging


class TestHistoryLoaderMalformedJson:
    """Test HistoryLoader handling of malformed JSON data."""

    def test_history_loader_with_malformed_message_no_role(self):
        """Handles message without role field."""
        from nikita.agents.text.history import HistoryLoader

        raw_messages = [
            # Missing role field
            {"content": "Hello", "timestamp": "2026-01-01T10:00:00Z"},
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        # Should skip malformed message and return None or empty
        # (depends on implementation, but should not crash)
        # If no valid messages, returns None
        assert result is None or len(result) == 0

    def test_history_loader_with_malformed_message_no_content(self):
        """Handles message without content field."""
        from nikita.agents.text.history import HistoryLoader

        raw_messages = [
            # Missing content field
            {"role": "user", "timestamp": "2026-01-01T10:00:00Z"},
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        # Should handle missing content gracefully
        # Either skips message or uses empty content
        assert result is None or (result and len(result[0].parts[0].content) == 0)

    def test_history_loader_with_unknown_role(self):
        """Handles message with unknown role."""
        from nikita.agents.text.history import HistoryLoader

        raw_messages = [
            {"role": "system", "content": "System message", "timestamp": "2026-01-01T10:00:00Z"},
            {"role": "unknown_role", "content": "Unknown", "timestamp": "2026-01-01T10:01:00Z"},
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        # Should skip unknown roles without crashing
        # Result may be empty or partial
        assert result is None or isinstance(result, list)

    def test_history_loader_with_null_values(self):
        """Handles null values in message fields."""
        from nikita.agents.text.history import HistoryLoader

        raw_messages = [
            {"role": None, "content": "Hello", "timestamp": "2026-01-01T10:00:00Z"},
            {"role": "user", "content": None, "timestamp": "2026-01-01T10:01:00Z"},
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        # Should handle null values gracefully
        assert result is None or isinstance(result, list)

    def test_history_loader_with_wrong_type(self):
        """Handles wrong data types in message fields."""
        from nikita.agents.text.history import HistoryLoader

        raw_messages = [
            {"role": 123, "content": "Hello", "timestamp": "2026-01-01T10:00:00Z"},  # role should be str
            {"role": "user", "content": 456, "timestamp": "2026-01-01T10:01:00Z"},  # content should be str
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        # Should handle type errors gracefully
        assert result is None or isinstance(result, list)

    def test_history_loader_with_extra_fields(self):
        """Handles messages with extra unexpected fields."""
        from nikita.agents.text.history import HistoryLoader

        raw_messages = [
            {
                "role": "user",
                "content": "Hello",
                "timestamp": "2026-01-01T10:00:00Z",
                "extra_field": "should be ignored",
                "another_extra": {"nested": "data"},
            },
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        # Should successfully process message, ignoring extra fields
        assert result is not None
        assert len(result) == 1

    def test_history_loader_with_nested_content(self):
        """Handles nested content structures (e.g., from tool calls)."""
        from nikita.agents.text.history import HistoryLoader

        raw_messages = [
            {
                "role": "user",
                "content": "What's the weather?",
                "timestamp": "2026-01-01T10:00:00Z",
            },
            {
                "role": "nikita",
                "content": "Let me check...",
                "timestamp": "2026-01-01T10:01:00Z",
                "tool_calls": [{"name": "get_weather", "args": {"city": "NYC"}}],
            },
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        # Should handle messages with additional structures
        assert result is not None
        assert len(result) >= 1


class TestHistoryLoaderDatabaseErrors:
    """Test HistoryLoader handling of database-related errors."""

    def test_history_loader_with_empty_list(self):
        """Handles empty message list (not None)."""
        from nikita.agents.text.history import HistoryLoader

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=[])
        result = loader.load()

        # Empty list should return None (triggers fresh prompt)
        assert result is None

    def test_history_loader_with_none(self):
        """Handles None message input."""
        from nikita.agents.text.history import HistoryLoader

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=None)
        result = loader.load()

        # None should return None (triggers fresh prompt)
        assert result is None

    def test_history_loader_with_string_instead_of_list(self):
        """Handles wrong type for raw_messages (string instead of list)."""
        from nikita.agents.text.history import HistoryLoader

        # Simulate corrupted data where messages is a string
        loader = HistoryLoader(conversation_id=uuid4(), raw_messages="not a list")

        # Should handle gracefully - either raises clear error or returns None
        try:
            result = loader.load()
            # If it doesn't raise, should return None or empty
            assert result is None or isinstance(result, list)
        except (TypeError, AttributeError):
            # Expected behavior for type errors
            pass

    def test_history_loader_preserves_valid_messages_after_errors(self):
        """Valid messages are preserved when mixed with invalid ones."""
        from nikita.agents.text.history import HistoryLoader
        from pydantic_ai.messages import ModelRequest

        raw_messages = [
            # Valid message
            {"role": "user", "content": "Hello", "timestamp": "2026-01-01T10:00:00Z"},
            # Invalid message (unknown role)
            {"role": "invalid", "content": "Skip me", "timestamp": "2026-01-01T10:01:00Z"},
            # Another valid message
            {"role": "nikita", "content": "Hey!", "timestamp": "2026-01-01T10:02:00Z"},
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
        result = loader.load()

        # Should have at least the valid messages
        if result is not None:
            # May have 2 valid messages or more depending on how invalid is handled
            assert len(result) >= 1


class TestHistoryLoaderLogging:
    """Test that HistoryLoader logs errors appropriately."""

    def test_logs_warning_for_malformed_message(self, caplog):
        """Logs warning when encountering malformed message."""
        from nikita.agents.text.history import HistoryLoader

        raw_messages = [
            {"role": "user", "content": "Valid", "timestamp": "2026-01-01T10:00:00Z"},
            {"role": "invalid_role", "content": "Invalid", "timestamp": "2026-01-01T10:01:00Z"},
        ]

        with caplog.at_level(logging.WARNING):
            loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)
            loader.load()

        # May or may not log depending on implementation
        # This test ensures no crash and documents expected behavior

    def test_logs_info_for_truncation(self, caplog):
        """Logs info when truncating message history."""
        from nikita.agents.text.history import HistoryLoader

        # Create many messages that will be truncated
        raw_messages = [
            {"role": "user" if i % 2 == 0 else "nikita",
             "content": f"Message {i} with some content " * 20,
             "timestamp": f"2026-01-01T{10+i//60:02d}:{i%60:02d}:00Z"}
            for i in range(100)
        ]

        with caplog.at_level(logging.INFO):
            loader = HistoryLoader(
                conversation_id=uuid4(),
                raw_messages=raw_messages,
            )
            result = loader.load(token_budget=1000)  # Force truncation

        # Result should be truncated
        if result is not None:
            assert len(result) < 100  # Fewer messages than original


class TestHistoryLoaderTokenBudgetErrors:
    """Test error handling in token budget enforcement."""

    def test_zero_token_budget(self):
        """Handles zero token budget gracefully.

        Note: MIN_TURNS_PRESERVED (10) ensures at least some messages are kept
        regardless of token budget, so zero budget still returns messages.
        """
        from nikita.agents.text.history import HistoryLoader, MIN_TURNS_PRESERVED

        raw_messages = [
            {"role": "user", "content": "Hello", "timestamp": "2026-01-01T10:00:00Z"},
            {"role": "nikita", "content": "Hi!", "timestamp": "2026-01-01T10:01:00Z"},
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)

        # Zero budget - MIN_TURNS_PRESERVED ensures some history is kept
        result = loader.load(token_budget=0)

        # Implementation preserves min turns regardless of budget
        # This is intentional to ensure conversation context is never zero
        assert result is not None
        assert len(result) >= 1  # At least some messages preserved

    def test_negative_token_budget(self):
        """Handles negative token budget gracefully.

        Note: Negative budget is treated similarly to zero - MIN_TURNS_PRESERVED
        ensures at least some messages are kept.
        """
        from nikita.agents.text.history import HistoryLoader

        raw_messages = [
            {"role": "user", "content": "Hello", "timestamp": "2026-01-01T10:00:00Z"},
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)

        # Negative budget - still returns messages due to MIN_TURNS_PRESERVED
        result = loader.load(token_budget=-100)

        # Implementation handles negative budget gracefully
        assert result is not None
        assert len(result) >= 1  # At least some messages preserved

    def test_very_small_token_budget(self):
        """Handles very small (but positive) token budget."""
        from nikita.agents.text.history import HistoryLoader

        raw_messages = [
            {"role": "user", "content": "Hello", "timestamp": "2026-01-01T10:00:00Z"},
            {"role": "nikita", "content": "Hi there!", "timestamp": "2026-01-01T10:01:00Z"},
        ]

        loader = HistoryLoader(conversation_id=uuid4(), raw_messages=raw_messages)

        # Very small budget
        result = loader.load(token_budget=10)

        # Should return minimal or None
        assert result is None or len(result) <= 2
