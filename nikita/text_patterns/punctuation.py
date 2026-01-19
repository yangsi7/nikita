"""Punctuation processor for Text Behavioral Patterns (Spec 026, Phase E).

Applies punctuation quirks and patterns for personality.
"""

import random
import re
from typing import Any

from nikita.text_patterns.models import PunctuationConfig


class PunctuationProcessor:
    """Applies punctuation patterns to Nikita's messages.

    Gives consistent texting quirks:
    - Lowercase preference for casual messages
    - Trailing "..." for effect
    - Sparing but genuine exclamation use
    - "lol" and "haha" variations

    Attributes:
        config: Punctuation configuration.
    """

    # Pattern to detect formal capitalization
    SENTENCE_START = re.compile(r"(?:^|[.!?]\s+)([A-Z])")

    def __init__(self, config: PunctuationConfig | None = None):
        """Initialize punctuation processor.

        Args:
            config: Punctuation configuration. Uses defaults if not provided.
        """
        self.config = config or PunctuationConfig()

    def apply(self, text: str, is_casual: bool = True) -> str:
        """Apply punctuation patterns to text.

        Args:
            text: Input text.
            is_casual: Whether this is casual conversation.

        Returns:
            Text with punctuation patterns applied.
        """
        if not text:
            return text

        # Apply lowercase if casual
        if is_casual and random.random() < self.config.lowercase_probability:
            text = self._apply_lowercase(text)

        # Maybe add trailing dots
        if random.random() < self.config.trailing_dots_probability:
            text = self._add_trailing_dots(text)

        # Normalize lol/haha variants
        text = self._normalize_laugh(text)

        return text

    def _apply_lowercase(self, text: str) -> str:
        """Apply lowercase to casual messages.

        Args:
            text: Input text.

        Returns:
            Lowercased text (preserving proper nouns like I).
        """
        # Simple approach: lowercase everything except standalone "I"
        words = text.split()
        result = []

        for word in words:
            if word == "I" or word == "I'm" or word == "I've" or word == "I'll" or word == "I'd":
                result.append(word)
            else:
                result.append(word.lower())

        return " ".join(result)

    def _add_trailing_dots(self, text: str) -> str:
        """Add trailing "..." for effect.

        Args:
            text: Input text.

        Returns:
            Text with possible trailing dots.
        """
        text = text.rstrip()

        # Don't add if already has trailing dots or question mark
        if text.endswith("...") or text.endswith("?"):
            return text

        # Remove existing period and add dots
        if text.endswith("."):
            text = text[:-1]

        return text + "..."

    def _normalize_laugh(self, text: str) -> str:
        """Normalize laugh variants.

        Args:
            text: Input text.

        Returns:
            Text with normalized laugh patterns.
        """
        # Match "lol" variations
        lol_pattern = re.compile(r"\blol+\b", re.IGNORECASE)
        haha_pattern = re.compile(r"\bha(ha)+\b", re.IGNORECASE)

        # Replace with random variant
        if lol_pattern.search(text):
            variant = random.choice(self.config.lol_variants)
            text = lol_pattern.sub(variant, text)

        if haha_pattern.search(text):
            variant = random.choice(self.config.haha_variants)
            text = haha_pattern.sub(variant, text)

        return text

    def add_exclamation(self, text: str, force: bool = False) -> str:
        """Possibly add exclamation point.

        Args:
            text: Input text.
            force: Force adding exclamation.

        Returns:
            Text with possible exclamation.
        """
        text = text.rstrip()

        # Don't double up punctuation
        if text.endswith(("!", "?", "...")):
            return text

        should_add = force or random.random() < self.config.exclamation_probability

        if should_add:
            if text.endswith("."):
                text = text[:-1]
            return text + "!"

        return text

    def ensure_ending_punctuation(self, text: str) -> str:
        """Ensure text ends with some punctuation.

        Args:
            text: Input text.

        Returns:
            Text with ending punctuation.
        """
        text = text.rstrip()

        if not text:
            return text

        if text[-1] in ".!?":
            return text

        # Default to period
        return text + "."
