"""Main text pattern processor for Spec 026 (Phase F).

Orchestrates all text behavioral pattern components to transform
raw LLM responses into naturally-formatted text messages.
"""

import re
from typing import Any

import yaml

from nikita.text_patterns.emoji_processor import EmojiProcessor
from nikita.text_patterns.length_adjuster import LengthAdjuster
from nikita.text_patterns.message_splitter import MessageSplitter
from nikita.text_patterns.punctuation import PunctuationProcessor
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


class TextPatternProcessor:
    """Orchestrates all text pattern components.

    Transforms raw LLM responses into naturally-formatted text that
    feels like real girlfriend texting:
    1. Detects message context (casual, emotional, conflict, etc.)
    2. Adjusts length to match context
    3. Applies punctuation quirks
    4. Adds context-appropriate emojis
    5. Splits into multiple messages

    Attributes:
        emoji_processor: Handles emoji selection/validation.
        length_adjuster: Adjusts message length.
        message_splitter: Splits messages.
        punctuation_processor: Applies punctuation patterns.
        context_keywords: Keywords for context detection.
    """

    def __init__(
        self,
        emoji_config: EmojiConfig | None = None,
        split_config: SplitConfig | None = None,
        punctuation_config: PunctuationConfig | None = None,
        length_configs: dict[MessageContext, LengthConfig] | None = None,
    ):
        """Initialize text pattern processor.

        Args:
            emoji_config: Emoji configuration.
            split_config: Message splitting configuration.
            punctuation_config: Punctuation configuration.
            length_configs: Length configurations per context.
        """
        self.emoji_processor = EmojiProcessor(emoji_config)
        self.length_adjuster = LengthAdjuster(length_configs)
        self.message_splitter = MessageSplitter(split_config)
        self.punctuation_processor = PunctuationProcessor(punctuation_config)

        # Default context detection keywords
        self.context_keywords = {
            MessageContext.EMOTIONAL: [
                "feel",
                "hurt",
                "sad",
                "happy",
                "love",
                "miss",
                "sorry",
                "worried",
                "scared",
                "excited",
            ],
            MessageContext.CONFLICT: [
                "upset",
                "angry",
                "annoyed",
                "frustrated",
                "disappointed",
                "mad",
                "whatever",
                "fine",
            ],
            MessageContext.FLIRTY: [
                "cute",
                "hot",
                "sexy",
                "kiss",
                "date",
                "tonight",
                "bed",
                "wish you were here",
            ],
            MessageContext.DEEP: [
                "think about",
                "future",
                "relationship",
                "together",
                "important",
                "serious",
                "us",
            ],
        }

    def process(
        self,
        text: str,
        context: MessageContext | None = None,
        emoji_context: EmojiContext | None = None,
    ) -> TextPatternResult:
        """Process text through all pattern components.

        Args:
            text: Raw input text from LLM.
            context: Override for message context (auto-detected if None).
            emoji_context: Override for emoji context.

        Returns:
            TextPatternResult with processed messages.
        """
        original_text = text

        # Step 1: Detect context if not provided
        if context is None:
            context = self._detect_context(text)

        # Step 2: Adjust length for context
        text = self.length_adjuster.adjust(text, context)

        # Step 3: Apply punctuation patterns
        is_casual = context in (MessageContext.CASUAL, MessageContext.FLIRTY)
        text = self.punctuation_processor.apply(text, is_casual=is_casual)

        # Step 4: Process emojis
        if emoji_context is None:
            emoji_context = self._context_to_emoji_context(context)
        text, emoji_count = self.emoji_processor.process(text, emoji_context)

        # Step 5: Split into multiple messages
        split_messages = self.message_splitter.split(text)
        was_split = len(split_messages) > 1
        total_delay = self.message_splitter.get_total_delay(split_messages)

        return TextPatternResult(
            original_text=original_text,
            processed_text=text,
            messages=split_messages,
            context=context,
            emoji_count=emoji_count,
            was_split=was_split,
            total_delay_ms=total_delay,
        )

    def _detect_context(self, text: str) -> MessageContext:
        """Detect message context from text content.

        Args:
            text: Input text.

        Returns:
            Detected MessageContext.
        """
        text_lower = text.lower()

        # Check each context's keywords
        scores = {}
        for context, keywords in self.context_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                scores[context] = score

        # Return highest scoring context
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]

        # Default to casual
        return MessageContext.CASUAL

    def _context_to_emoji_context(self, context: MessageContext) -> EmojiContext:
        """Map message context to emoji context.

        Args:
            context: Message context.

        Returns:
            Appropriate emoji context.
        """
        mapping = {
            MessageContext.CASUAL: EmojiContext.NEUTRAL,
            MessageContext.FLIRTY: EmojiContext.FLIRTATION,
            MessageContext.EMOTIONAL: EmojiContext.AFFECTION,
            MessageContext.CONFLICT: EmojiContext.SARCASM,
            MessageContext.DEEP: EmojiContext.AFFECTION,
        }
        return mapping.get(context, EmojiContext.NEUTRAL)

    def process_for_sending(
        self,
        text: str,
        context: MessageContext | None = None,
    ) -> list[tuple[str, int]]:
        """Process text and return ready-to-send messages.

        Convenience method that returns (content, delay_ms) tuples.

        Args:
            text: Raw input text.
            context: Optional context override.

        Returns:
            List of (message_content, delay_ms) tuples.
        """
        result = self.process(text, context)
        return result.get_messages_for_sending()

    @classmethod
    def from_yaml_config(
        cls,
        emoji_path: str | None = None,
        patterns_path: str | None = None,
    ) -> "TextPatternProcessor":
        """Create processor from YAML config files.

        Args:
            emoji_path: Path to emojis.yaml.
            patterns_path: Path to patterns.yaml.

        Returns:
            Configured TextPatternProcessor.
        """
        emoji_config = None
        split_config = None
        punctuation_config = None

        if emoji_path:
            with open(emoji_path) as f:
                emoji_data = yaml.safe_load(f)
                emoji_config = EmojiConfig(**emoji_data)

        if patterns_path:
            with open(patterns_path) as f:
                pattern_data = yaml.safe_load(f)

                if "splitting" in pattern_data:
                    split_config = SplitConfig(**pattern_data["splitting"])

                if "punctuation" in pattern_data:
                    punctuation_config = PunctuationConfig(**pattern_data["punctuation"])

        return cls(
            emoji_config=emoji_config,
            split_config=split_config,
            punctuation_config=punctuation_config,
        )
