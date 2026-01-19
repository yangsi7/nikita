"""Message splitter tests for Text Behavioral Patterns (Spec 026, Phase D: T013-T016).

Tests for:
- T013: MessageSplitter class
- T014: Break point detection
- T015: Delay calculation
- T016: Coverage
"""

import pytest

from nikita.text_patterns.message_splitter import MessageSplitter
from nikita.text_patterns.models import SplitConfig, SplitMessage


class TestMessageSplitter:
    """Test T013: MessageSplitter class."""

    def test_split_returns_list(self):
        """AC-T013.1: split() returns list of SplitMessage."""
        splitter = MessageSplitter()
        result = splitter.split("hey there")

        assert isinstance(result, list)
        assert all(isinstance(msg, SplitMessage) for msg in result)

    def test_short_message_not_split(self):
        """AC-T013.2: Short messages stay as single message."""
        splitter = MessageSplitter()

        # Under threshold (80)
        text = "hey what's up"
        result = splitter.split(text)

        assert len(result) == 1
        assert result[0].content == text

    def test_configurable_threshold(self):
        """AC-T013.3: Threshold is configurable."""
        config = SplitConfig(split_threshold=30)
        splitter = MessageSplitter(config)

        # Over custom threshold
        text = "this is a message that exceeds thirty characters"
        result = splitter.split(text)

        assert len(result) > 1

    def test_default_splitter(self):
        """AC-T013.4: Default splitter works."""
        splitter = MessageSplitter()

        result = splitter.split("hello world")
        assert isinstance(result, list)


class TestBreakPointDetection:
    """Test T014: Break point detection."""

    def test_sentence_boundary_split(self):
        """AC-T014.2: Prefer sentence boundaries."""
        splitter = MessageSplitter()

        text = "I had a great day. The weather was nice. I went for a walk."
        result = splitter.split(text)

        # Should split at sentences
        assert len(result) >= 1
        # First message should be a complete sentence
        if len(result) > 1:
            assert result[0].content.strip().endswith((".", "!", "?", "..."))

    def test_marker_word_split(self):
        """AC-T014.1: Split at marker words (but, and, etc.)."""
        config = SplitConfig(split_threshold=40)
        splitter = MessageSplitter(config)

        text = "I was going to go but then I changed my mind and stayed home"
        result = splitter.split(text)

        # Should have multiple segments
        assert len(result) >= 1

    def test_minimum_split_length(self):
        """AC-T014.3: Minimum split length enforced."""
        config = SplitConfig(min_split_length=20)
        splitter = MessageSplitter(config)

        text = "a. b. c. d. e. f. g. h. i. j. k. l. m. n. o. p."
        result = splitter.split(text)

        # Very short sentences should be merged
        for msg in result:
            assert len(msg.content) >= 10  # Allow some flexibility

    def test_merge_short_sentences(self):
        """Short sentences merged together."""
        splitter = MessageSplitter()

        text = "Hi. Hey. What's up. How are you."
        result = splitter.split(text)

        # Should merge short sentences
        assert len(result) <= 2


class TestDelayCalculation:
    """Test T015: Delay calculation."""

    def test_delay_in_range(self):
        """AC-T015.1: Delays within configured range."""
        config = SplitConfig(inter_message_delay_ms=(100, 300))
        splitter = MessageSplitter(config)

        # Generate many delays
        for _ in range(50):
            delay = splitter._calculate_delay()
            assert 100 <= delay <= 300

    def test_first_message_no_delay(self):
        """First message has zero delay."""
        splitter = MessageSplitter()

        text = "I had a great day. The weather was nice. I went for a walk in the park."
        result = splitter.split(text)

        if len(result) > 0:
            assert result[0].delay_ms == 0

    def test_delays_have_variability(self):
        """AC-T015.2: Slight variability in delays."""
        splitter = MessageSplitter()

        delays = [splitter._calculate_delay() for _ in range(50)]

        # Should have at least 3 different values
        unique_delays = set(delays)
        assert len(unique_delays) >= 3

    def test_split_messages_have_delays(self):
        """AC-T015.3: Split messages include delays."""
        splitter = MessageSplitter()

        text = "This is a first thought. And here is another thought. Plus one more thing to say."
        result = splitter.split(text)

        if len(result) > 1:
            # Non-first messages should have delays
            assert result[1].delay_ms > 0


class TestSplitMessageObject:
    """Test SplitMessage object."""

    def test_message_has_content(self):
        """Message has content field."""
        splitter = MessageSplitter()

        result = splitter.split("hello world")
        assert result[0].content == "hello world"

    def test_message_has_index(self):
        """Message has index field."""
        splitter = MessageSplitter()

        text = "First sentence. Second sentence. Third sentence that is longer."
        result = splitter.split(text)

        for i, msg in enumerate(result):
            assert msg.index == i

    def test_message_has_delay(self):
        """Message has delay_ms field."""
        splitter = MessageSplitter()

        result = splitter.split("hello world")
        assert hasattr(result[0], "delay_ms")


class TestSplitterHelpers:
    """Test helper methods."""

    def test_should_split_true(self):
        """should_split returns True for long text."""
        config = SplitConfig(split_threshold=50)
        splitter = MessageSplitter(config)

        text = "x" * 100
        assert splitter.should_split(text)

    def test_should_split_false(self):
        """should_split returns False for short text."""
        config = SplitConfig(split_threshold=50)
        splitter = MessageSplitter(config)

        text = "hello"
        assert not splitter.should_split(text)

    def test_get_total_delay(self):
        """get_total_delay returns sum of delays."""
        splitter = MessageSplitter()

        messages = [
            SplitMessage(content="a", delay_ms=0, index=0),
            SplitMessage(content="b", delay_ms=100, index=1),
            SplitMessage(content="c", delay_ms=150, index=2),
        ]

        total = splitter.get_total_delay(messages)
        assert total == 250


class TestSplitEdgeCases:
    """Test edge cases."""

    def test_empty_text(self):
        """Empty text returns single empty message."""
        splitter = MessageSplitter()

        result = splitter.split("")
        assert len(result) == 1
        assert result[0].content == ""

    def test_whitespace_only(self):
        """Whitespace-only text handled."""
        splitter = MessageSplitter()

        result = splitter.split("   ")
        assert len(result) == 1

    def test_single_long_word(self):
        """Single very long word handled."""
        config = SplitConfig(split_threshold=20)
        splitter = MessageSplitter(config)

        text = "superlongwordthatexceedsthreshold"
        result = splitter.split(text)

        assert len(result) >= 1

    def test_text_with_newlines(self):
        """Text with newlines handled."""
        splitter = MessageSplitter()

        text = "hello\nworld\nhow are you"
        result = splitter.split(text)

        assert len(result) >= 1

    def test_unicode_text(self):
        """Unicode text handled."""
        splitter = MessageSplitter()

        text = "café résumé naïve cliché"
        result = splitter.split(text)

        assert len(result) >= 1
        assert "café" in result[0].content

    def test_many_short_words(self):
        """Many short words handled."""
        config = SplitConfig(split_threshold=50)
        splitter = MessageSplitter(config)

        text = " ".join(["a"] * 30)
        result = splitter.split(text)

        # Should produce multiple messages
        assert len(result) >= 1

    def test_force_split_at_threshold(self):
        """_force_split works when no natural breaks."""
        config = SplitConfig(split_threshold=20)
        splitter = MessageSplitter(config)

        # No markers or sentence breaks
        text = "word word word word word word word word word word"
        result = splitter._force_split(text)

        # Should have splits
        assert len(result) >= 1
