"""Emoji processor tests for Text Behavioral Patterns (Spec 026, Phase B: T005-T008).

Tests for:
- T005: EmojiProcessor class
- T006: Context-based selection
- T007: Validation rules
- T008: Coverage
"""

import pytest
import random

from nikita.text_patterns.emoji_processor import EmojiProcessor
from nikita.text_patterns.models import EmojiConfig, EmojiContext


class TestEmojiProcessor:
    """Test T005: EmojiProcessor class."""

    def test_process_returns_tuple(self):
        """AC-T005.1: process() returns (text, count) tuple."""
        processor = EmojiProcessor()
        result = processor.process("hey there")

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], int)

    def test_process_adds_emoji_probabilistically(self):
        """AC-T005.2: process() may add emoji based on probability."""
        processor = EmojiProcessor()

        # Run multiple times to verify probabilistic behavior
        added_count = 0
        for _ in range(100):
            random.seed(_)  # Reproducible randomness
            _, count = processor.process("hey there")
            added_count += count

        # Should add some but not all (probability ~0.4)
        assert 20 < added_count < 80

    def test_process_loads_config(self):
        """AC-T005.3: Loads approved list from config."""
        config = EmojiConfig(
            approved_emojis=["👍"],
            classic_emoticons=[":)"],
            contexts={"neutral": ["👍", ":)"]},  # Explicit context mapping
            selection_probability=1.0,
        )
        processor = EmojiProcessor(config)

        text, count = processor.process("hey", context=EmojiContext.NEUTRAL)

        # With probability 1.0, should add emoji
        if count > 0:
            assert "👍" in text or ":)" in text

    def test_default_processor(self):
        """AC-T005.4: Default processor works."""
        processor = EmojiProcessor()

        # Should not raise
        text, count = processor.process("hello world")
        assert isinstance(text, str)


class TestContextBasedSelection:
    """Test T006: Context-based emoji selection."""

    def test_flirtation_context(self):
        """AC-T006.1: Flirtation context uses appropriate emojis."""
        config = EmojiConfig(selection_probability=1.0)
        processor = EmojiProcessor(config)

        # Run multiple times
        flirt_emojis_used = set()
        for _ in range(50):
            random.seed(_)
            text, _ = processor.process("hey cutie", context=EmojiContext.FLIRTATION)
            # Extract emojis from text
            for emoji in ["😏", "😘", "🍆", ";)"]:
                if emoji in text:
                    flirt_emojis_used.add(emoji)

        # Should use at least one flirtation emoji
        flirt_allowed = {"😏", "😘", "🍆", ";)"}
        assert flirt_emojis_used.intersection(flirt_allowed)

    def test_sarcasm_context(self):
        """AC-T006.1: Sarcasm context uses appropriate emojis."""
        config = EmojiConfig(selection_probability=1.0)
        processor = EmojiProcessor(config)

        sarcasm_emojis_used = set()
        for _ in range(50):
            random.seed(_)
            text, _ = processor.process("sure, whatever", context=EmojiContext.SARCASM)
            for emoji in ["🙄", ":/"]:
                if emoji in text:
                    sarcasm_emojis_used.add(emoji)

        sarcasm_allowed = {"🙄", ":/"}
        assert sarcasm_emojis_used.intersection(sarcasm_allowed)

    def test_affection_context(self):
        """AC-T006.1: Affection context uses appropriate emojis."""
        config = EmojiConfig(selection_probability=1.0)
        processor = EmojiProcessor(config)

        affection_emojis_used = set()
        for _ in range(50):
            random.seed(_)
            text, _ = processor.process("I miss you", context=EmojiContext.AFFECTION)
            for emoji in ["🥲", "😘", ":)"]:
                if emoji in text:
                    affection_emojis_used.add(emoji)

        affection_allowed = {"🥲", "😘", ":)"}
        assert affection_emojis_used.intersection(affection_allowed)

    def test_probability_based_selection(self):
        """AC-T006.2: Selection is probability-based."""
        # Low probability
        config_low = EmojiConfig(selection_probability=0.1)
        processor_low = EmojiProcessor(config_low)

        # High probability
        config_high = EmojiConfig(selection_probability=0.9)
        processor_high = EmojiProcessor(config_high)

        low_count = sum(
            processor_low.process("test")[1]
            for _ in range(100)
        )

        high_count = sum(
            processor_high.process("test")[1]
            for _ in range(100)
        )

        # High probability should add more
        assert high_count > low_count

    def test_zero_probability(self):
        """AC-T006.3: Zero probability never adds emojis."""
        config = EmojiConfig(selection_probability=0.0)
        processor = EmojiProcessor(config)

        for _ in range(50):
            _, count = processor.process("hello")
            assert count == 0


class TestEmojiValidation:
    """Test T007: Emoji validation rules."""

    def test_max_emojis_enforced(self):
        """AC-T007.1: Max 2 emojis per message enforced."""
        config = EmojiConfig(max_per_message=2)
        processor = EmojiProcessor(config)

        # Text with 4 emojis
        text = "hey 😏 there 😘 what's 🙂 up 😅"
        cleaned, _ = processor.validate_only(text)

        # Count emojis in cleaned text
        emoji_count = sum(1 for c in cleaned if c in "😏😘🙂😅🙄🍆🥲")
        assert emoji_count <= 2

    def test_sequential_emojis_removed(self):
        """AC-T007.2: No sequential emojis (😂😂) allowed."""
        processor = EmojiProcessor()

        text = "haha that's funny 😂😂😂"
        cleaned, changed = processor.validate_only(text)

        # Should have removed repeated emojis
        assert "😂😂" not in cleaned

    def test_unapproved_emojis_removed(self):
        """AC-T007.3: Only approved emojis allowed."""
        config = EmojiConfig(approved_emojis=["😏", "🙄"])
        processor = EmojiProcessor(config)

        text = "fire 🔥 party 🎉"
        cleaned, changed = processor.validate_only(text)

        # Unapproved emojis should be removed
        assert "🔥" not in cleaned
        assert "🎉" not in cleaned
        assert changed is True

    def test_approved_emojis_kept(self):
        """Approved emojis are kept."""
        config = EmojiConfig(approved_emojis=["😏", "🙄"])
        processor = EmojiProcessor(config)

        text = "hey 😏 cool 🙄"
        cleaned, _ = processor.validate_only(text)

        assert "😏" in cleaned
        assert "🙄" in cleaned

    def test_classic_emoticons_allowed(self):
        """Classic emoticons are allowed."""
        processor = EmojiProcessor()

        text = "hey there :) how are you :P"
        cleaned, _ = processor.validate_only(text)

        assert ":)" in cleaned
        assert ":P" in cleaned


class TestEmojiProcessorHelpers:
    """Test helper methods."""

    def test_count_emojis(self):
        """_count_emojis counts correctly."""
        processor = EmojiProcessor()

        # Just emojis
        assert processor._count_emojis("😏😘") == 2

        # Mixed
        assert processor._count_emojis("hey 😏 there :)") == 2

        # None
        assert processor._count_emojis("hello world") == 0

    def test_add_emoji_at_end(self):
        """_add_emoji adds at appropriate position."""
        config = EmojiConfig(
            contexts={"neutral": ["🙂"]},
            selection_probability=1.0,
        )
        processor = EmojiProcessor(config)

        # Test with period
        text, count = processor._add_emoji("hello.", EmojiContext.NEUTRAL)
        assert count == 1
        # Should be before period or after
        assert "🙂" in text

    def test_add_emoji_without_punctuation(self):
        """_add_emoji handles text without punctuation."""
        config = EmojiConfig(
            contexts={"neutral": ["🙂"]},
            selection_probability=1.0,
        )
        processor = EmojiProcessor(config)

        text, count = processor._add_emoji("hello", EmojiContext.NEUTRAL)
        assert count == 1
        assert "🙂" in text

    def test_validate_only_no_changes(self):
        """validate_only returns changed=False when no changes needed."""
        processor = EmojiProcessor()

        text = "hey there 😏"
        cleaned, changed = processor.validate_only(text)

        assert cleaned == text
        assert changed is False


class TestEmojiEdgeCases:
    """Test edge cases."""

    def test_empty_text(self):
        """Empty text handled correctly."""
        processor = EmojiProcessor()

        text, count = processor.process("")
        assert text == ""
        assert count == 0

    def test_text_with_newlines(self):
        """Text with newlines handled correctly."""
        processor = EmojiProcessor()

        text = "hello\nworld"
        result, _ = processor.process(text)
        assert isinstance(result, str)

    def test_text_with_special_chars(self):
        """Text with special chars handled correctly."""
        processor = EmojiProcessor()

        text = "hey!! what's up??? :)"
        result, _ = processor.validate_only(text)
        assert ":)" in result

    def test_unicode_handling(self):
        """Unicode text handled correctly."""
        processor = EmojiProcessor()

        text = "café résumé 😏"
        result, _ = processor.validate_only(text)
        assert "café" in result
        assert "😏" in result
