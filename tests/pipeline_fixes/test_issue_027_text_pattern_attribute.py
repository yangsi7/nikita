"""TDD tests for Issue #27: TextPatternResult missing attribute.

The bug: handler.py:207 uses `pattern_result.detected_context` but the
TextPatternResult model uses `context` as the attribute name.

The fix: Change `detected_context` to `context` in message_handler.py.
"""

import pytest
from nikita.text_patterns.models import TextPatternResult, MessageContext


class TestTextPatternResultAttribute:
    """Verify TextPatternResult uses 'context' not 'detected_context'."""

    def test_text_pattern_result_has_context_attribute(self):
        """TextPatternResult should have 'context' attribute."""
        result = TextPatternResult(
            original_text="hello there",
            processed_text="hello there",
            messages=[],
            context=MessageContext.CASUAL,  # Use valid enum value
            emoji_count=0,
            was_split=False,
            total_delay_ms=0,
        )

        # The attribute is 'context', NOT 'detected_context'
        assert hasattr(result, 'context')
        assert result.context == MessageContext.CASUAL

    def test_text_pattern_result_no_detected_context(self):
        """TextPatternResult should NOT have 'detected_context' attribute."""
        result = TextPatternResult(
            original_text="test",
            processed_text="test",
            messages=[],
            context=MessageContext.CASUAL,
            emoji_count=0,
            was_split=False,
            total_delay_ms=0,
        )

        # This is the bug - code tries to access 'detected_context' which doesn't exist
        assert not hasattr(result, 'detected_context')

    def test_context_values(self):
        """Verify context can take various MessageContext values."""
        for context_value in MessageContext:
            result = TextPatternResult(
                original_text="test",
                processed_text="test",
                messages=[],
                context=context_value,
                emoji_count=0,
                was_split=False,
                total_delay_ms=0,
            )
            assert result.context == context_value
