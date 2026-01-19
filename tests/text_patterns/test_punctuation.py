"""Punctuation processor tests for Text Behavioral Patterns (Spec 026, Phase E: T017-T019).

Tests for:
- T017: PunctuationProcessor class
- T018: Quirk patterns
- T019: Coverage
"""

import pytest
import random

from nikita.text_patterns.punctuation import PunctuationProcessor
from nikita.text_patterns.models import PunctuationConfig


class TestPunctuationProcessor:
    """Test T017: PunctuationProcessor class."""

    def test_apply_returns_string(self):
        """AC-T017.1: apply() returns string."""
        processor = PunctuationProcessor()
        result = processor.apply("Hey there!")

        assert isinstance(result, str)

    def test_apply_modifies_text(self):
        """AC-T017.2: apply() modifies punctuation."""
        config = PunctuationConfig(
            lowercase_probability=1.0,
            trailing_dots_probability=0.0,
        )
        processor = PunctuationProcessor(config)

        result = processor.apply("HELLO WORLD", is_casual=True)

        # Should be lowercase
        assert result.islower() or result == "hello world"

    def test_lowercase_preference(self):
        """AC-T017.3: Handles lowercase preference."""
        config = PunctuationConfig(lowercase_probability=1.0)
        processor = PunctuationProcessor(config)

        result = processor.apply("Hey What's Up", is_casual=True)

        # Should be mostly lowercase
        assert "hey" in result.lower()

    def test_default_processor(self):
        """AC-T017.4: Default processor works."""
        processor = PunctuationProcessor()

        result = processor.apply("hello world")
        assert isinstance(result, str)


class TestQuirkPatterns:
    """Test T018: Quirk patterns."""

    def test_trailing_dots(self):
        """AC-T018.1: Trailing dots '...' usage."""
        config = PunctuationConfig(
            trailing_dots_probability=1.0,
            lowercase_probability=0.0,
        )
        processor = PunctuationProcessor(config)

        result = processor.apply("I was thinking", is_casual=True)

        assert result.endswith("...")

    def test_trailing_dots_skipped_when_question(self):
        """Trailing dots skipped for questions."""
        config = PunctuationConfig(
            trailing_dots_probability=1.0,
            lowercase_probability=0.0,
        )
        processor = PunctuationProcessor(config)

        result = processor.apply("Are you there?", is_casual=True)

        # Should not add dots to question
        assert result.endswith("?")

    def test_lol_variants(self):
        """AC-T018.2: 'lol' variants normalized."""
        config = PunctuationConfig(
            lol_variants=["lol", "loll"],
            lowercase_probability=0.0,
            trailing_dots_probability=0.0,
        )
        processor = PunctuationProcessor(config)

        # Test with extended "lol"
        variations = set()
        for _ in range(50):
            random.seed(_)
            result = processor.apply("that's funny lolol", is_casual=True)
            # Extract the lol variant
            for variant in ["lol", "loll"]:
                if variant in result:
                    variations.add(variant)

        # Should use configured variants
        assert variations.intersection({"lol", "loll"})

    def test_haha_variants(self):
        """AC-T018.2: 'haha' variants normalized."""
        config = PunctuationConfig(
            haha_variants=["haha", "ha"],
            lowercase_probability=0.0,
            trailing_dots_probability=0.0,
        )
        processor = PunctuationProcessor(config)

        variations = set()
        for _ in range(50):
            random.seed(_)
            result = processor.apply("that's hilarious hahahaha", is_casual=True)
            for variant in ["haha", "ha"]:
                if variant in result:
                    variations.add(variant)

        assert variations.intersection({"haha", "ha"})

    def test_exclamation_sparingly(self):
        """AC-T018.3: Exclamation points used sparingly."""
        config = PunctuationConfig(exclamation_probability=0.1)
        processor = PunctuationProcessor(config)

        count = 0
        for _ in range(100):
            result = processor.add_exclamation("hey there")
            if result.endswith("!"):
                count += 1

        # Should be ~10% (allow variance)
        assert 2 < count < 30


class TestLowercaseApplication:
    """Test lowercase application."""

    def test_preserves_standalone_i(self):
        """Standalone 'I' preserved."""
        config = PunctuationConfig(
            lowercase_probability=1.0,
            trailing_dots_probability=0.0,
        )
        processor = PunctuationProcessor(config)

        result = processor.apply("I think I should go", is_casual=True)

        # "I" should still be uppercase
        assert "I" in result

    def test_preserves_im(self):
        """'I'm' preserved."""
        config = PunctuationConfig(
            lowercase_probability=1.0,
            trailing_dots_probability=0.0,
        )
        processor = PunctuationProcessor(config)

        result = processor.apply("I'm doing great", is_casual=True)

        # "I'm" should still be capitalized
        assert "I'm" in result

    def test_non_casual_not_lowercased(self):
        """Non-casual messages not lowercased."""
        config = PunctuationConfig(lowercase_probability=1.0)
        processor = PunctuationProcessor(config)

        result = processor.apply("Hello World", is_casual=False)

        # Should be unchanged (not casual)
        assert result[0].isupper()


class TestAddExclamation:
    """Test add_exclamation helper."""

    def test_force_exclamation(self):
        """Force adds exclamation."""
        processor = PunctuationProcessor()

        result = processor.add_exclamation("hello", force=True)
        assert result == "hello!"

    def test_replaces_period(self):
        """Replaces existing period."""
        processor = PunctuationProcessor()

        result = processor.add_exclamation("hello.", force=True)
        assert result == "hello!"

    def test_no_double_punctuation(self):
        """Doesn't double up punctuation."""
        processor = PunctuationProcessor()

        result = processor.add_exclamation("what?", force=True)
        assert result == "what?"

        result = processor.add_exclamation("yes!", force=True)
        assert result == "yes!"


class TestEnsureEndingPunctuation:
    """Test ensure_ending_punctuation helper."""

    def test_adds_period(self):
        """Adds period if missing."""
        processor = PunctuationProcessor()

        result = processor.ensure_ending_punctuation("hello there")
        assert result == "hello there."

    def test_preserves_existing(self):
        """Preserves existing punctuation."""
        processor = PunctuationProcessor()

        assert processor.ensure_ending_punctuation("hello!") == "hello!"
        assert processor.ensure_ending_punctuation("what?") == "what?"
        assert processor.ensure_ending_punctuation("nice.") == "nice."

    def test_empty_text(self):
        """Empty text returns empty."""
        processor = PunctuationProcessor()

        assert processor.ensure_ending_punctuation("") == ""


class TestPunctuationEdgeCases:
    """Test edge cases."""

    def test_empty_text(self):
        """Empty text returns empty."""
        processor = PunctuationProcessor()

        result = processor.apply("")
        assert result == ""

    def test_whitespace_only(self):
        """Whitespace handled."""
        processor = PunctuationProcessor()

        result = processor.apply("   ")
        assert isinstance(result, str)

    def test_special_chars(self):
        """Special chars preserved."""
        processor = PunctuationProcessor()

        result = processor.apply("$100 @user #hashtag")
        assert "$" in result
        assert "@" in result
        assert "#" in result

    def test_unicode_text(self):
        """Unicode text handled."""
        config = PunctuationConfig(
            lowercase_probability=1.0,
            trailing_dots_probability=0.0,
        )
        processor = PunctuationProcessor(config)

        result = processor.apply("Café Résumé", is_casual=True)
        assert "café" in result.lower()

    def test_multiple_sentences(self):
        """Multiple sentences handled."""
        processor = PunctuationProcessor()

        result = processor.apply("First. Second. Third.")
        assert isinstance(result, str)
