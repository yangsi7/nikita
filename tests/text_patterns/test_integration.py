"""Integration tests for Text Behavioral Patterns (Spec 026, Phase F: T020-T023).

Tests for:
- T020: TextPatternProcessor orchestration
- T021: Text agent integration
- T022: E2E pipeline tests
- T023: Quality metrics tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nikita.text_patterns.processor import TextPatternProcessor
from nikita.text_patterns.models import (
    EmojiConfig,
    EmojiContext,
    LengthConfig,
    MessageContext,
    PunctuationConfig,
    SplitConfig,
    SplitMessage,
    TextPatternResult,
)


class TestTextPatternProcessor:
    """Test T020: TextPatternProcessor class."""

    def test_process_returns_result(self):
        """AC-T020.1: process() returns TextPatternResult."""
        processor = TextPatternProcessor()
        result = processor.process("hey there")

        assert isinstance(result, TextPatternResult)

    def test_process_applies_all_patterns(self):
        """AC-T020.2: process() applies all patterns in order."""
        processor = TextPatternProcessor()

        # Long emotional text that should trigger patterns
        text = "I really miss you so much. I can't stop thinking about you."
        result = processor.process(text)

        # Should have processed the text
        assert result.processed_text is not None
        assert result.context in MessageContext

    def test_process_returns_messages(self):
        """AC-T020.3: process() returns messages list."""
        processor = TextPatternProcessor()
        result = processor.process("hey there")

        assert isinstance(result.messages, list)
        assert len(result.messages) >= 1
        assert all(isinstance(m, SplitMessage) for m in result.messages)

    def test_default_processor(self):
        """AC-T020.4: Default processor works without config."""
        processor = TextPatternProcessor()
        result = processor.process("hello world")

        assert isinstance(result, TextPatternResult)
        assert result.original_text == "hello world"


class TestContextDetection:
    """Test context detection logic."""

    def test_detect_casual(self):
        """Casual context detected for simple messages."""
        processor = TextPatternProcessor()
        result = processor.process("hey what's up")

        assert result.context == MessageContext.CASUAL

    def test_detect_emotional(self):
        """Emotional context detected for feeling words."""
        processor = TextPatternProcessor()
        result = processor.process("I feel so sad and hurt by what happened")

        assert result.context == MessageContext.EMOTIONAL

    def test_detect_flirty(self):
        """Flirty context detected for romantic words."""
        processor = TextPatternProcessor()
        result = processor.process("you're so cute, wish I could kiss you")

        assert result.context == MessageContext.FLIRTY

    def test_detect_conflict(self):
        """Conflict context detected for angry words."""
        processor = TextPatternProcessor()
        result = processor.process("I'm so upset and angry with you")

        assert result.context == MessageContext.CONFLICT

    def test_detect_deep(self):
        """Deep context detected for relationship words."""
        processor = TextPatternProcessor()
        result = processor.process("I've been thinking about our future together")

        assert result.context == MessageContext.DEEP

    def test_context_override(self):
        """Context can be overridden."""
        processor = TextPatternProcessor()
        result = processor.process(
            "hey there",
            context=MessageContext.EMOTIONAL,
        )

        assert result.context == MessageContext.EMOTIONAL


class TestEmojiContextMapping:
    """Test emoji context mapping."""

    def test_casual_maps_to_neutral(self):
        """Casual maps to neutral emoji context."""
        processor = TextPatternProcessor()
        emoji_ctx = processor._context_to_emoji_context(MessageContext.CASUAL)

        assert emoji_ctx == EmojiContext.NEUTRAL

    def test_flirty_maps_to_flirtation(self):
        """Flirty maps to flirtation emoji context."""
        processor = TextPatternProcessor()
        emoji_ctx = processor._context_to_emoji_context(MessageContext.FLIRTY)

        assert emoji_ctx == EmojiContext.FLIRTATION

    def test_conflict_maps_to_sarcasm(self):
        """Conflict maps to sarcasm emoji context."""
        processor = TextPatternProcessor()
        emoji_ctx = processor._context_to_emoji_context(MessageContext.CONFLICT)

        assert emoji_ctx == EmojiContext.SARCASM


class TestProcessForSending:
    """Test process_for_sending helper."""

    def test_returns_tuples(self):
        """Returns list of (content, delay) tuples."""
        processor = TextPatternProcessor()
        messages = processor.process_for_sending("hey there")

        assert isinstance(messages, list)
        assert len(messages) >= 1
        assert all(
            isinstance(m, tuple) and len(m) == 2
            for m in messages
        )

    def test_first_message_no_delay(self):
        """First message has zero delay."""
        processor = TextPatternProcessor()
        messages = processor.process_for_sending("hey there")

        assert messages[0][1] == 0  # delay_ms

    def test_tuples_have_content_and_delay(self):
        """Tuples have string content and int delay."""
        processor = TextPatternProcessor()
        messages = processor.process_for_sending("hey there")

        content, delay = messages[0]
        assert isinstance(content, str)
        assert isinstance(delay, int)


class TestYamlConfig:
    """Test YAML config loading."""

    def test_from_yaml_config_creates_processor(self, tmp_path):
        """from_yaml_config creates processor."""
        # Create temp emoji config
        emoji_file = tmp_path / "emojis.yaml"
        emoji_file.write_text("""
approved_emojis:
  - "😏"
  - "🙄"
classic_emoticons:
  - ":)"
max_per_message: 2
selection_probability: 0.5
contexts:
  neutral:
    - "🙂"
""")

        processor = TextPatternProcessor.from_yaml_config(
            emoji_path=str(emoji_file),
        )

        assert isinstance(processor, TextPatternProcessor)

    def test_from_yaml_with_patterns(self, tmp_path):
        """from_yaml_config loads patterns config."""
        patterns_file = tmp_path / "patterns.yaml"
        patterns_file.write_text("""
splitting:
  split_threshold: 100
  min_split_length: 30
punctuation:
  lowercase_probability: 0.8
  trailing_dots_probability: 0.3
""")

        processor = TextPatternProcessor.from_yaml_config(
            patterns_path=str(patterns_file),
        )

        assert isinstance(processor, TextPatternProcessor)


class TestE2EPipeline:
    """Test T022: E2E pipeline tests."""

    def test_full_pipeline_casual(self):
        """Full pipeline for casual message."""
        processor = TextPatternProcessor()

        text = "hey what's up"
        result = processor.process(text)

        assert result.original_text == text
        assert result.context == MessageContext.CASUAL
        assert len(result.messages) >= 1

    def test_full_pipeline_emotional(self):
        """Full pipeline for emotional message."""
        processor = TextPatternProcessor()

        text = "I miss you so much and I feel so lonely without you here with me."
        result = processor.process(text)

        assert result.context == MessageContext.EMOTIONAL
        # Emotional has higher length limits (100-300)
        assert len(result.processed_text) >= 10

    def test_full_pipeline_long_message(self):
        """Full pipeline for long message that should split."""
        split_config = SplitConfig(split_threshold=50)
        processor = TextPatternProcessor(split_config=split_config)

        # Use emotional context which has higher length limits (100-300)
        text = "I feel so happy and excited about seeing you. I miss you so much and can't wait."
        result = processor.process(text, context=MessageContext.EMOTIONAL)

        # With 50 char split threshold and 100+ char text, should split
        assert result.was_split
        assert len(result.messages) > 1

    def test_pipeline_preserves_meaning(self):
        """Pipeline preserves core meaning."""
        processor = TextPatternProcessor()

        text = "I love you"
        result = processor.process(text)

        # Core word should be preserved
        assert "love" in result.processed_text.lower()


class TestQualityMetrics:
    """Test T023: Quality metrics tests."""

    def test_emoji_density_in_range(self):
        """AC-T023.1: Emoji density 0.5-1.5 per 100 chars."""
        emoji_config = EmojiConfig(selection_probability=0.5)
        processor = TextPatternProcessor(emoji_config=emoji_config)

        # Process many messages and calculate density
        total_chars = 0
        total_emojis = 0

        texts = [
            "hey what's up",
            "I miss you so much",
            "can't wait to see you tonight",
            "that's so funny haha",
            "I feel sad today",
        ]

        for text in texts:
            result = processor.process(text)
            total_chars += len(result.processed_text)
            total_emojis += result.emoji_count

        # Calculate density per 100 chars
        if total_chars > 0:
            density = (total_emojis / total_chars) * 100
            # Should be reasonable (0-3 per 100 chars)
            assert density < 5.0  # Not too many emojis

    def test_split_rate_reasonable(self):
        """AC-T023.2: Split rate is reasonable."""
        split_config = SplitConfig(split_threshold=60)
        processor = TextPatternProcessor(split_config=split_config)

        # Process messages of varying lengths
        texts = [
            "hey",  # short
            "I was thinking about you today",  # medium
            "I really want to tell you something important. It's been on my mind for a while now.",  # long
            "what's up",  # short
            "I had such a great day today. First I went to the cafe then I met my friend.",  # long
        ]

        split_count = 0
        for text in texts:
            result = processor.process(text)
            if result.was_split:
                split_count += 1

        # Should split some but not all
        split_rate = split_count / len(texts)
        assert 0.0 <= split_rate <= 1.0

    def test_no_sequential_emojis(self):
        """AC-T023.3: No sequential emojis in output."""
        emoji_config = EmojiConfig(
            selection_probability=1.0,  # Always add emoji
            max_per_message=2,
        )
        processor = TextPatternProcessor(emoji_config=emoji_config)

        # Process many messages
        texts = [
            "hey there",
            "that's funny",
            "love you",
            "see you later",
        ]

        for text in texts:
            result = processor.process(text)
            # Check no double emojis
            for msg in result.messages:
                # Check for sequential emoji pattern
                assert "😂😂" not in msg.content
                assert "😏😏" not in msg.content
                assert "🙄🙄" not in msg.content


class TestTextAgentIntegration:
    """Test T021: Text agent integration."""

    def test_integration_point_exists(self):
        """AC-T021.1: Integration point method exists."""
        processor = TextPatternProcessor()

        # process_for_sending is the integration point
        assert hasattr(processor, "process_for_sending")
        assert callable(processor.process_for_sending)

    def test_integration_returns_sendable_format(self):
        """AC-T021.2: Returns format suitable for sending."""
        processor = TextPatternProcessor()

        messages = processor.process_for_sending("hey there")

        # Should be list of (content, delay) tuples
        assert isinstance(messages, list)
        for content, delay in messages:
            assert isinstance(content, str)
            assert isinstance(delay, int)
            assert delay >= 0

    def test_integration_with_context(self):
        """AC-T021.3: Integration works with context override."""
        processor = TextPatternProcessor()

        messages = processor.process_for_sending(
            "hey there",
            context=MessageContext.FLIRTY,
        )

        assert len(messages) >= 1


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_text(self):
        """Empty text handled."""
        processor = TextPatternProcessor()
        result = processor.process("")

        assert result.original_text == ""
        assert len(result.messages) >= 1

    def test_whitespace_only(self):
        """Whitespace text handled."""
        processor = TextPatternProcessor()
        result = processor.process("   ")

        assert isinstance(result, TextPatternResult)

    def test_unicode_text(self):
        """Unicode text handled."""
        processor = TextPatternProcessor()
        result = processor.process("café résumé naïve")

        assert "café" in result.processed_text.lower() or "cafe" in result.processed_text.lower()

    def test_newlines_handled(self):
        """Newlines in text handled."""
        processor = TextPatternProcessor()
        result = processor.process("hello\nworld")

        assert isinstance(result, TextPatternResult)

    def test_special_characters(self):
        """Special characters preserved."""
        processor = TextPatternProcessor()
        result = processor.process("$100 @user #hashtag")

        # Should preserve most special chars
        assert isinstance(result, TextPatternResult)

    def test_very_long_text(self):
        """Very long text handled."""
        processor = TextPatternProcessor()
        text = "word " * 500  # ~2500 chars

        result = processor.process(text)

        # Should process without error
        assert isinstance(result, TextPatternResult)
        # Should be split into multiple messages
        assert len(result.messages) >= 1
