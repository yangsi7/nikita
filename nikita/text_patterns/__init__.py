"""Text Behavioral Patterns module for Spec 026.

This module provides realistic texting patterns to make Nikita's responses
feel more human-like, including:
- Selective emoji usage (max 1-2 per message)
- Context-appropriate message length
- Message splitting for natural texting rhythm
- Punctuation quirks and patterns

Architecture:
    TextPatternProcessor orchestrates all components to transform raw
    LLM responses into naturally-formatted text messages.
"""

from nikita.text_patterns.models import (
    EmojiConfig,
    LengthConfig,
    MessageContext,
    PunctuationConfig,
    SplitConfig,
    SplitMessage,
    TextPatternResult,
)
from nikita.text_patterns.emoji_processor import EmojiProcessor
from nikita.text_patterns.length_adjuster import LengthAdjuster
from nikita.text_patterns.message_splitter import MessageSplitter
from nikita.text_patterns.punctuation import PunctuationProcessor
from nikita.text_patterns.processor import TextPatternProcessor

__all__ = [
    # Models
    "EmojiConfig",
    "LengthConfig",
    "MessageContext",
    "PunctuationConfig",
    "SplitConfig",
    "SplitMessage",
    "TextPatternResult",
    # Processors
    "EmojiProcessor",
    "LengthAdjuster",
    "MessageSplitter",
    "PunctuationProcessor",
    "TextPatternProcessor",
]
