"""Emoji processor for Text Behavioral Patterns (Spec 026, Phase B).

Handles selective emoji insertion, validation, and context-based selection.
"""

import random
import re
from typing import Any

from nikita.text_patterns.models import EmojiConfig, EmojiContext


class EmojiProcessor:
    """Processes emoji usage in Nikita's messages.

    Ensures emojis are:
    - Used selectively (max 1-2 per message)
    - Context-appropriate (flirtation, sarcasm, etc.)
    - Never sequential (no 😂😂😂)
    - From the approved list only

    Attributes:
        config: Emoji configuration.
    """

    # Regex to find sequential emojis
    SEQUENTIAL_EMOJI_PATTERN = re.compile(r"([\U0001F300-\U0001F9FF])\1+")

    # Regex to find all emojis
    EMOJI_PATTERN = re.compile(
        r"[\U0001F300-\U0001F9FF]|"  # Misc symbols and pictographs
        r"[\U0001F600-\U0001F64F]|"  # Emoticons
        r"[\U0001F680-\U0001F6FF]|"  # Transport and map
        r"[\U0001F1E0-\U0001F1FF]|"  # Flags
        r"[\U00002702-\U000027B0]|"  # Dingbats
        r"[\U0001F900-\U0001F9FF]"   # Supplemental symbols
    )

    def __init__(self, config: EmojiConfig | None = None):
        """Initialize emoji processor.

        Args:
            config: Emoji configuration. Uses defaults if not provided.
        """
        self.config = config or EmojiConfig()

    def process(
        self,
        text: str,
        context: EmojiContext = EmojiContext.NEUTRAL,
    ) -> tuple[str, int]:
        """Process text for emoji usage.

        Args:
            text: Input text to process.
            context: Emotional context for emoji selection.

        Returns:
            Tuple of (processed text, emoji count added).
        """
        # First, validate and clean existing emojis
        text, removed_count = self._validate_existing_emojis(text)

        # Count current emojis
        current_count = self._count_emojis(text)

        # Possibly add an emoji if under limit
        added_count = 0
        if current_count < self.config.max_per_message:
            if random.random() < self.config.selection_probability:
                text, added_count = self._add_emoji(text, context)

        return text, added_count

    def _validate_existing_emojis(self, text: str) -> tuple[str, int]:
        """Validate and clean existing emojis in text.

        Args:
            text: Input text.

        Returns:
            Tuple of (cleaned text, count of removed emojis).
        """
        removed = 0

        # Remove sequential emojis (keep only first)
        while self.SEQUENTIAL_EMOJI_PATTERN.search(text):
            text = self.SEQUENTIAL_EMOJI_PATTERN.sub(r"\1", text)
            removed += 1

        # Remove unapproved emojis
        allowed = set(self.config.get_all_allowed())
        emojis_in_text = self.EMOJI_PATTERN.findall(text)

        for emoji in emojis_in_text:
            if emoji not in allowed:
                text = text.replace(emoji, "", 1)
                removed += 1

        # Enforce max count
        current_count = self._count_emojis(text)
        while current_count > self.config.max_per_message:
            # Remove from end
            emojis = self.EMOJI_PATTERN.findall(text)
            if emojis:
                last_emoji = emojis[-1]
                # Find last occurrence and remove
                idx = text.rfind(last_emoji)
                if idx >= 0:
                    text = text[:idx] + text[idx + len(last_emoji) :]
                    removed += 1
            current_count = self._count_emojis(text)

        return text, removed

    def _count_emojis(self, text: str) -> int:
        """Count emojis in text.

        Args:
            text: Input text.

        Returns:
            Number of emojis found.
        """
        emoji_count = len(self.EMOJI_PATTERN.findall(text))
        # Also count classic emoticons
        emoticon_count = sum(
            text.count(emoticon) for emoticon in self.config.classic_emoticons
        )
        return emoji_count + emoticon_count

    def _add_emoji(
        self,
        text: str,
        context: EmojiContext,
    ) -> tuple[str, int]:
        """Add an appropriate emoji to text.

        Args:
            text: Input text.
            context: Emotional context.

        Returns:
            Tuple of (text with emoji, count added).
        """
        context_emojis = self.config.get_context_emojis(context)
        if not context_emojis:
            return text, 0

        emoji = random.choice(context_emojis)

        # Add at end of message (after punctuation)
        text = text.rstrip()
        if text and text[-1] in ".!?":
            text = text[:-1] + " " + emoji + text[-1]
        else:
            text = text + " " + emoji

        return text, 1

    def validate_only(self, text: str) -> tuple[str, bool]:
        """Only validate emojis without adding new ones.

        Args:
            text: Input text.

        Returns:
            Tuple of (cleaned text, whether any changes were made).
        """
        cleaned, removed = self._validate_existing_emojis(text)
        return cleaned, removed > 0
