"""Length adjuster for Text Behavioral Patterns (Spec 026, Phase C).

Adjusts message length based on context to match natural texting patterns.
"""

import re
from typing import Any

from nikita.text_patterns.models import (
    LengthConfig,
    MessageContext,
    get_length_config,
)


class LengthAdjuster:
    """Adjusts message length based on context.

    Ensures messages match expected length for the context:
    - Casual: short, punchy (10-50 chars)
    - Emotional: longer (100-300 chars)
    - Conflict: medium (50-150 chars)
    - Deep: longest (150-400 chars)

    Attributes:
        configs: Length configurations per context.
    """

    # Sentence boundary pattern
    SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

    def __init__(self, configs: dict[MessageContext, LengthConfig] | None = None):
        """Initialize length adjuster.

        Args:
            configs: Length configurations per context. Uses defaults if not provided.
        """
        self.configs = configs or {}

    def adjust(
        self,
        text: str,
        context: MessageContext = MessageContext.CASUAL,
    ) -> str:
        """Adjust text length for context.

        Args:
            text: Input text.
            context: Message context type.

        Returns:
            Adjusted text.
        """
        config = self._get_config(context)

        text_len = len(text)

        # If text is within bounds, return as-is
        if config.min_chars <= text_len <= config.max_chars:
            return text

        # If too long, truncate
        if text_len > config.max_chars:
            return self._truncate(text, config.max_chars)

        # If too short, we don't pad - just return as-is
        # (LLM should generate appropriate length)
        return text

    def _get_config(self, context: MessageContext) -> LengthConfig:
        """Get config for context.

        Args:
            context: Message context.

        Returns:
            Length configuration.
        """
        if context in self.configs:
            return self.configs[context]
        return get_length_config(context)

    def _truncate(self, text: str, max_chars: int) -> str:
        """Truncate text at natural break points.

        Args:
            text: Input text.
            max_chars: Maximum characters allowed.

        Returns:
            Truncated text.
        """
        if len(text) <= max_chars:
            return text

        # Try to truncate at sentence boundary
        sentences = self.SENTENCE_BOUNDARY.split(text)
        truncated = ""

        for sentence in sentences:
            if len(truncated) + len(sentence) + 1 <= max_chars:
                if truncated:
                    truncated += " "
                truncated += sentence
            else:
                break

        if truncated:
            return truncated

        # No sentence boundary found, truncate at word boundary
        truncated = text[:max_chars]
        last_space = truncated.rfind(" ")

        if last_space > max_chars * 0.5:
            truncated = truncated[:last_space]

        # Clean up trailing punctuation
        truncated = truncated.rstrip(" ,")

        # Add ellipsis if we cut mid-thought
        if not truncated.endswith((".", "!", "?", "...")):
            truncated += "..."

        return truncated

    def get_target_length(self, context: MessageContext) -> tuple[int, int]:
        """Get target length range for context.

        Args:
            context: Message context.

        Returns:
            Tuple of (min_chars, max_chars).
        """
        config = self._get_config(context)
        return config.min_chars, config.max_chars

    def is_within_bounds(self, text: str, context: MessageContext) -> bool:
        """Check if text is within length bounds for context.

        Args:
            text: Input text.
            context: Message context.

        Returns:
            True if within bounds.
        """
        config = self._get_config(context)
        return config.min_chars <= len(text) <= config.max_chars
