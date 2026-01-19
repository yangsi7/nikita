"""Length adjuster tests for Text Behavioral Patterns (Spec 026, Phase C: T009-T012).

Tests for:
- T009: LengthAdjuster class
- T010: Context-based length targets
- T011: Truncation
- T012: Coverage
"""

import pytest

from nikita.text_patterns.length_adjuster import LengthAdjuster
from nikita.text_patterns.models import LengthConfig, MessageContext, get_length_config


class TestLengthAdjuster:
    """Test T009: LengthAdjuster class."""

    def test_adjust_returns_string(self):
        """AC-T009.1: adjust() returns string."""
        adjuster = LengthAdjuster()
        result = adjuster.adjust("hello there")

        assert isinstance(result, str)

    def test_within_bounds_unchanged(self):
        """AC-T009.2: Text within bounds is unchanged."""
        adjuster = LengthAdjuster()

        # Casual: 10-50 chars
        text = "hey what's up"  # 13 chars
        result = adjuster.adjust(text, MessageContext.CASUAL)

        assert result == text

    def test_loads_config(self):
        """AC-T009.3: Loads length config."""
        configs = {
            MessageContext.CASUAL: LengthConfig(
                context=MessageContext.CASUAL,
                min_chars=5,
                max_chars=20,
            )
        }
        adjuster = LengthAdjuster(configs)

        # Text too long for custom config
        text = "this is a much longer message that should be truncated"
        result = adjuster.adjust(text, MessageContext.CASUAL)

        assert len(result) <= 20

    def test_default_adjuster(self):
        """AC-T009.4: Default adjuster works."""
        adjuster = LengthAdjuster()

        result = adjuster.adjust("hello world")
        assert isinstance(result, str)


class TestContextLengthTargets:
    """Test T010: Context-based length targets."""

    def test_casual_10_50_chars(self):
        """AC-T010.1: casual: 10-50 chars."""
        config = get_length_config(MessageContext.CASUAL)

        assert config.min_chars == 10
        assert config.max_chars == 50

    def test_emotional_100_300_chars(self):
        """AC-T010.2: emotional: 100-300 chars."""
        config = get_length_config(MessageContext.EMOTIONAL)

        assert config.min_chars == 100
        assert config.max_chars == 300

    def test_conflict_50_150_chars(self):
        """AC-T010.3: conflict: 50-150 chars."""
        config = get_length_config(MessageContext.CONFLICT)

        assert config.min_chars == 50
        assert config.max_chars == 150

    def test_deep_150_400_chars(self):
        """AC-T010.4: deep: 150-400 chars."""
        config = get_length_config(MessageContext.DEEP)

        assert config.min_chars == 150
        assert config.max_chars == 400

    def test_flirty_config(self):
        """AC-T010.5: Flirty config exists."""
        config = get_length_config(MessageContext.FLIRTY)

        assert config.min_chars == 15
        assert config.max_chars == 80


class TestTruncation:
    """Test T011: Truncation behavior."""

    def test_truncate_at_sentence(self):
        """AC-T011.1: Truncate at natural break points."""
        adjuster = LengthAdjuster()

        # Text with two sentences, second makes it too long
        text = "This is first. This is a second sentence that makes it way too long."
        result = adjuster._truncate(text, 20)

        # Should truncate at sentence boundary
        assert len(result) <= 20

    def test_never_cut_mid_word(self):
        """AC-T011.2: Never cut mid-word."""
        adjuster = LengthAdjuster()

        text = "hello wonderful beautiful world"
        result = adjuster._truncate(text, 15)

        # Should not cut a word mid-way (no partial words)
        words_in_result = result.rstrip("...").split()
        assert all(word in text.split() or word == "" for word in words_in_result)

    def test_preserve_meaning(self):
        """AC-T011.3: Preserve meaning in truncation."""
        adjuster = LengthAdjuster()

        text = "I love you so much. You mean everything to me."
        result = adjuster._truncate(text, 30)

        # Should preserve at least the first sentence
        assert "love" in result or result.startswith("I")

    def test_add_ellipsis(self):
        """Ellipsis added when cutting mid-thought."""
        adjuster = LengthAdjuster()

        text = "this is a very long sentence without any punctuation at all whatsoever"
        result = adjuster._truncate(text, 30)

        assert result.endswith("...")


class TestLengthHelpers:
    """Test helper methods."""

    def test_get_target_length(self):
        """get_target_length returns correct range."""
        adjuster = LengthAdjuster()

        min_len, max_len = adjuster.get_target_length(MessageContext.CASUAL)
        assert min_len == 10
        assert max_len == 50

        min_len, max_len = adjuster.get_target_length(MessageContext.EMOTIONAL)
        assert min_len == 100
        assert max_len == 300

    def test_is_within_bounds_true(self):
        """is_within_bounds returns True for valid length."""
        adjuster = LengthAdjuster()

        # 25 chars is within casual (10-50)
        text = "hey what are you up to?"
        assert adjuster.is_within_bounds(text, MessageContext.CASUAL)

    def test_is_within_bounds_false_too_long(self):
        """is_within_bounds returns False when too long."""
        adjuster = LengthAdjuster()

        # Way too long for casual
        text = "x" * 100
        assert not adjuster.is_within_bounds(text, MessageContext.CASUAL)

    def test_is_within_bounds_false_too_short(self):
        """is_within_bounds returns False when too short."""
        adjuster = LengthAdjuster()

        # Too short for emotional
        text = "hi"
        assert not adjuster.is_within_bounds(text, MessageContext.EMOTIONAL)


class TestLengthEdgeCases:
    """Test edge cases."""

    def test_empty_text(self):
        """Empty text returns empty."""
        adjuster = LengthAdjuster()

        result = adjuster.adjust("")
        assert result == ""

    def test_exact_max_length(self):
        """Text at exact max length is unchanged."""
        adjuster = LengthAdjuster()

        # Exactly 50 chars (casual max)
        text = "x" * 50
        result = adjuster.adjust(text, MessageContext.CASUAL)

        assert result == text

    def test_one_char_over(self):
        """Text 1 char over is truncated."""
        adjuster = LengthAdjuster()

        # 51 chars (casual max is 50)
        text = "x" * 51
        result = adjuster.adjust(text, MessageContext.CASUAL)

        # Truncation adds "..." but base should be <= max
        # Result may have ellipsis
        assert len(result) <= 53  # Allow for "..."

    def test_short_text_not_padded(self):
        """Short text is not padded."""
        adjuster = LengthAdjuster()

        text = "hi"  # 2 chars, casual min is 10
        result = adjuster.adjust(text, MessageContext.CASUAL)

        # Should return as-is (no padding)
        assert result == text

    def test_text_with_unicode(self):
        """Unicode text handled correctly."""
        adjuster = LengthAdjuster()

        text = "café résumé naïve"
        result = adjuster.adjust(text, MessageContext.CASUAL)

        assert isinstance(result, str)

    def test_truncate_single_long_word(self):
        """Single very long word truncated gracefully."""
        adjuster = LengthAdjuster()

        text = "a" * 200
        result = adjuster._truncate(text, 50)

        # Should truncate but add ellipsis
        assert len(result) <= 53  # Allow for "..."
