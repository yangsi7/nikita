"""Models for Text Behavioral Patterns (Spec 026, Phase A: T002).

Pydantic models for emoji configuration, length targets, message splitting,
and punctuation patterns.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MessageContext(str, Enum):
    """Context types for message formatting decisions."""

    CASUAL = "casual"
    FLIRTY = "flirty"
    EMOTIONAL = "emotional"
    CONFLICT = "conflict"
    DEEP = "deep"


class EmojiContext(str, Enum):
    """Context types for emoji selection."""

    FLIRTATION = "flirtation"
    SARCASM = "sarcasm"
    AFFECTION = "affection"
    SELF_DEPRECATION = "self_deprecation"
    NEUTRAL = "neutral"


class EmojiConfig(BaseModel):
    """Configuration for emoji usage patterns.

    Attributes:
        approved_emojis: List of approved emojis Nikita can use.
        classic_emoticons: List of classic text emoticons.
        max_per_message: Maximum emojis allowed per message.
        contexts: Mapping of context to appropriate emojis.
        selection_probability: Probability of adding an emoji (0-1).
    """

    approved_emojis: list[str] = Field(
        default=["😏", "🙄", "🍆", "😘", "😅", "🥲", "🙂"],
        description="Emojis Nikita is allowed to use",
    )
    classic_emoticons: list[str] = Field(
        default=[":)", ":(", ":P", ";)", ":/"],
        description="Classic text emoticons",
    )
    max_per_message: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum emojis per message",
    )
    contexts: dict[str, list[str]] = Field(
        default={
            "flirtation": ["😏", "😘", "🍆", ";)"],
            "sarcasm": ["🙄", ":/"],
            "affection": ["🥲", "😘", ":)"],
            "self_deprecation": ["😅", "🥲"],
            "neutral": ["🙂", ":)"],
        },
        description="Context-appropriate emoji mapping",
    )
    selection_probability: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Probability of adding an emoji",
    )

    @field_validator("approved_emojis", "classic_emoticons")
    @classmethod
    def validate_emoji_list(cls, v: list[str]) -> list[str]:
        """Ensure emoji lists are not empty."""
        if not v:
            raise ValueError("Emoji list cannot be empty")
        return v

    @field_validator("contexts")
    @classmethod
    def validate_contexts(cls, v: dict[str, list[str]]) -> dict[str, list[str]]:
        """Ensure contexts have valid emojis."""
        if not v:
            raise ValueError("Contexts cannot be empty")
        for context_name, emojis in v.items():
            if not emojis:
                raise ValueError(f"Context '{context_name}' has no emojis")
        return v

    def get_all_allowed(self) -> list[str]:
        """Get all allowed emojis and emoticons."""
        return self.approved_emojis + self.classic_emoticons

    def get_context_emojis(self, context: EmojiContext) -> list[str]:
        """Get emojis appropriate for a context."""
        return self.contexts.get(context.value, self.contexts.get("neutral", []))


class LengthConfig(BaseModel):
    """Configuration for message length targets.

    Attributes:
        context: The message context type.
        min_chars: Minimum character count.
        max_chars: Maximum character count.
        target_splits: Expected number of message splits.
    """

    context: MessageContext = Field(
        default=MessageContext.CASUAL,
        description="Message context type",
    )
    min_chars: int = Field(
        default=10,
        ge=1,
        description="Minimum character count",
    )
    max_chars: int = Field(
        default=50,
        ge=1,
        description="Maximum character count",
    )
    target_splits: tuple[int, int] = Field(
        default=(1, 2),
        description="Min and max number of splits",
    )

    @field_validator("max_chars")
    @classmethod
    def validate_max_greater_than_min(cls, v: int, info) -> int:
        """Ensure max_chars >= min_chars."""
        min_chars = info.data.get("min_chars", 1)
        if v < min_chars:
            raise ValueError(f"max_chars ({v}) must be >= min_chars ({min_chars})")
        return v


# Pre-defined length configurations per context
LENGTH_CONFIGS: dict[MessageContext, LengthConfig] = {
    MessageContext.CASUAL: LengthConfig(
        context=MessageContext.CASUAL,
        min_chars=10,
        max_chars=50,
        target_splits=(1, 2),
    ),
    MessageContext.FLIRTY: LengthConfig(
        context=MessageContext.FLIRTY,
        min_chars=15,
        max_chars=80,
        target_splits=(1, 3),
    ),
    MessageContext.EMOTIONAL: LengthConfig(
        context=MessageContext.EMOTIONAL,
        min_chars=100,
        max_chars=300,
        target_splits=(2, 4),
    ),
    MessageContext.CONFLICT: LengthConfig(
        context=MessageContext.CONFLICT,
        min_chars=50,
        max_chars=150,
        target_splits=(1, 2),
    ),
    MessageContext.DEEP: LengthConfig(
        context=MessageContext.DEEP,
        min_chars=150,
        max_chars=400,
        target_splits=(3, 5),
    ),
}


def get_length_config(context: MessageContext) -> LengthConfig:
    """Get length configuration for a context."""
    return LENGTH_CONFIGS.get(context, LENGTH_CONFIGS[MessageContext.CASUAL])


class SplitConfig(BaseModel):
    """Configuration for message splitting.

    Attributes:
        split_threshold: Char count above which to split.
        min_split_length: Minimum chars per split message.
        split_markers: Words that indicate natural break points.
        inter_message_delay_ms: Range of delays between messages.
    """

    split_threshold: int = Field(
        default=80,
        ge=20,
        description="Char count threshold for splitting",
    )
    min_split_length: int = Field(
        default=20,
        ge=5,
        description="Minimum chars per split message",
    )
    split_markers: list[str] = Field(
        default=["but", "and", "also", "anyway", "so", "like", "honestly", "actually"],
        description="Words indicating natural break points",
    )
    inter_message_delay_ms: tuple[int, int] = Field(
        default=(50, 200),
        description="Min/max delay between split messages (ms)",
    )

    @field_validator("inter_message_delay_ms")
    @classmethod
    def validate_delay_range(cls, v: tuple[int, int]) -> tuple[int, int]:
        """Ensure delay range is valid."""
        min_delay, max_delay = v
        if min_delay < 0:
            raise ValueError("Minimum delay cannot be negative")
        if max_delay < min_delay:
            raise ValueError("Max delay must be >= min delay")
        return v


class PunctuationConfig(BaseModel):
    """Configuration for punctuation patterns.

    Attributes:
        lowercase_probability: Chance of using lowercase.
        trailing_dots_probability: Chance of adding "...".
        exclamation_probability: Chance of using "!".
        lol_variants: Variants of "lol" to use.
        haha_variants: Variants of "haha" to use.
    """

    lowercase_probability: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Probability of lowercase message",
    )
    trailing_dots_probability: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Probability of trailing '...'",
    )
    exclamation_probability: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Probability of exclamation point",
    )
    lol_variants: list[str] = Field(
        default=["lol", "loll", "heh"],
        description="Variants of 'lol'",
    )
    haha_variants: list[str] = Field(
        default=["haha", "hahaha", "ha"],
        description="Variants of 'haha'",
    )


class SplitMessage(BaseModel):
    """A single message in a split sequence.

    Attributes:
        content: The message text.
        delay_ms: Delay before sending this message.
        index: Position in the split sequence.
    """

    content: str = Field(description="Message text content")
    delay_ms: int = Field(
        default=0,
        ge=0,
        description="Delay before this message (ms)",
    )
    index: int = Field(
        default=0,
        ge=0,
        description="Position in split sequence",
    )


class TextPatternResult(BaseModel):
    """Result of applying text patterns to a message.

    Attributes:
        original_text: The original input text.
        processed_text: Text after emoji/punctuation processing.
        messages: List of split messages with delays.
        context: The detected message context.
        emoji_count: Number of emojis added.
        was_split: Whether the message was split.
        total_delay_ms: Total delay across all messages.
    """

    original_text: str = Field(description="Original input text")
    processed_text: str = Field(description="Text after processing")
    messages: list[SplitMessage] = Field(
        default_factory=list,
        description="Split messages with delays",
    )
    context: MessageContext = Field(
        default=MessageContext.CASUAL,
        description="Detected message context",
    )
    emoji_count: int = Field(
        default=0,
        ge=0,
        description="Number of emojis added",
    )
    was_split: bool = Field(
        default=False,
        description="Whether message was split",
    )
    total_delay_ms: int = Field(
        default=0,
        ge=0,
        description="Total delay for all messages",
    )

    @property
    def message_count(self) -> int:
        """Get the number of output messages."""
        return len(self.messages) if self.messages else 1

    def get_messages_for_sending(self) -> list[tuple[str, int]]:
        """Get messages as (content, delay_ms) tuples for sending."""
        if not self.messages:
            return [(self.processed_text, 0)]
        return [(msg.content, msg.delay_ms) for msg in self.messages]
