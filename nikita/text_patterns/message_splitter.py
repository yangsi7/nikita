"""Message splitter for Text Behavioral Patterns (Spec 026, Phase D).

Splits long messages into multiple shorter ones for natural texting rhythm.
"""

import random
import re
from typing import Any

from nikita.text_patterns.models import SplitConfig, SplitMessage


class MessageSplitter:
    """Splits messages into natural texting chunks.

    Real texters send multiple short messages instead of one long paragraph.
    This creates more engaging, conversational rhythm.

    Attributes:
        config: Split configuration.
    """

    # Sentence boundary pattern
    SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

    def __init__(self, config: SplitConfig | None = None):
        """Initialize message splitter.

        Args:
            config: Split configuration. Uses defaults if not provided.
        """
        self.config = config or SplitConfig()

    def split(self, text: str) -> list[SplitMessage]:
        """Split text into multiple messages.

        Args:
            text: Input text to split.

        Returns:
            List of SplitMessage with content and delays.
        """
        text = text.strip()

        # Don't split short messages
        if len(text) <= self.config.split_threshold:
            return [SplitMessage(content=text, delay_ms=0, index=0)]

        # Try to split at natural break points
        splits = self._find_split_points(text)

        # Generate delays
        messages = []
        for i, content in enumerate(splits):
            delay = 0 if i == 0 else self._calculate_delay()
            messages.append(SplitMessage(content=content, delay_ms=delay, index=i))

        return messages

    def _find_split_points(self, text: str) -> list[str]:
        """Find natural split points in text.

        Args:
            text: Input text.

        Returns:
            List of text segments.
        """
        # First try sentence boundaries
        sentences = self.SENTENCE_BOUNDARY.split(text)

        if len(sentences) > 1:
            return self._merge_short_sentences(sentences)

        # No sentence boundaries, try marker words
        return self._split_at_markers(text)

    def _merge_short_sentences(self, sentences: list[str]) -> list[str]:
        """Merge sentences that are too short.

        Args:
            sentences: List of sentences.

        Returns:
            List of merged segments.
        """
        result = []
        current = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if not current:
                current = sentence
            elif len(current) < self.config.min_split_length:
                current += " " + sentence
            else:
                result.append(current)
                current = sentence

        if current:
            result.append(current)

        return result if result else [" ".join(sentences)]

    def _split_at_markers(self, text: str) -> list[str]:
        """Split text at marker words.

        Args:
            text: Input text.

        Returns:
            List of text segments.
        """
        # Create pattern from markers
        markers = self.config.split_markers
        pattern = re.compile(
            r"\s+(" + "|".join(re.escape(m) for m in markers) + r")\s+",
            re.IGNORECASE,
        )

        parts = pattern.split(text)

        # Reconstruct keeping markers with following text
        result = []
        current = ""

        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            # Check if this is a marker
            is_marker = part.lower() in [m.lower() for m in markers]

            if is_marker:
                if current and len(current) >= self.config.min_split_length:
                    result.append(current)
                    current = part
                else:
                    current += " " + part if current else part
            else:
                current += " " + part if current else part

        if current:
            result.append(current)

        # If we didn't find good splits, just return original
        if len(result) <= 1:
            return self._force_split(text)

        return result

    def _force_split(self, text: str) -> list[str]:
        """Force split at threshold if no natural points found.

        Args:
            text: Input text.

        Returns:
            List of text segments.
        """
        result = []
        words = text.split()
        current = ""

        for word in words:
            test = current + " " + word if current else word

            if len(test) >= self.config.split_threshold:
                if current:
                    result.append(current)
                    current = word
                else:
                    # Single word exceeds threshold
                    result.append(word)
                    current = ""
            else:
                current = test

        if current:
            result.append(current)

        return result

    def _calculate_delay(self) -> int:
        """Calculate random delay between messages.

        Returns:
            Delay in milliseconds.
        """
        min_delay, max_delay = self.config.inter_message_delay_ms
        return random.randint(min_delay, max_delay)

    def should_split(self, text: str) -> bool:
        """Check if text should be split.

        Args:
            text: Input text.

        Returns:
            True if text exceeds threshold.
        """
        return len(text.strip()) > self.config.split_threshold

    def get_total_delay(self, messages: list[SplitMessage]) -> int:
        """Get total delay across all messages.

        Args:
            messages: List of split messages.

        Returns:
            Total delay in milliseconds.
        """
        return sum(msg.delay_ms for msg in messages)
