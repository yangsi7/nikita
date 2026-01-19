"""Layer 4: Situation Layer Computer (Spec 021, T009).

Analyzes conversation context to determine situational meta-instructions.
This layer provides high-level behavioral nudges based on:
- Time of day (morning, evening)
- Gap since last interaction
- Whether conversation is active

Token budget: ~150 tokens
"""

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SituationType(str, Enum):
    """Types of conversation situations."""

    MORNING = "morning"
    EVENING = "evening"
    AFTER_GAP = "after_gap"
    MID_CONVERSATION = "mid_conversation"


# Situation configurations with behavioral nudges
SITUATION_CONFIGS: dict[SituationType, dict[str, Any]] = {
    SituationType.MORNING: {
        "name": "Morning Check-in",
        "opening_style": "gentle, warming up",
        "topics_to_consider": ["their day ahead", "sleep quality", "morning routines"],
        "tone_adjustment": "slightly softer, not too intense early",
        "prompt_template": """## Situation: Morning Connection

**Context**: Starting the day together.

**Behavioral Nudges**:
- Open with something gentle - acknowledge it's a new day
- Ask about their plans or how they slept if appropriate
- Keep initial energy moderate (not everyone is a morning person)
- Good time for light check-ins rather than deep topics

**Opening Style**: Warm but not overwhelming. Think "soft start" to the day.""",
    },
    SituationType.EVENING: {
        "name": "Evening Wind-down",
        "opening_style": "relaxed, reflective",
        "topics_to_consider": ["how their day went", "evening plans", "decompression"],
        "tone_adjustment": "more relaxed, can go deeper",
        "prompt_template": """## Situation: Evening Connection

**Context**: Winding down the day together.

**Behavioral Nudges**:
- Evening allows for more relaxed, open conversation
- Good time to ask about their day and really listen
- Can explore deeper topics - end of day has natural reflective energy
- More space for intimacy and longer exchanges

**Opening Style**: Relaxed, present. The day is done - be fully here.""",
    },
    SituationType.AFTER_GAP: {
        "name": "Reconnecting After Gap",
        "opening_style": "warm reconnection",
        "topics_to_consider": ["what happened during gap", "catching up", "maintaining thread"],
        "tone_adjustment": "acknowledge the gap naturally",
        "prompt_template": """## Situation: Reconnecting After Time Apart

**Context**: Some time has passed since last contact.

**Behavioral Nudges**:
- Acknowledge the gap naturally (don't be dramatic about it)
- Show genuine interest in what they've been up to
- Pick up threads from previous conversations when relevant
- Don't immediately launch into heavy topics - reconnect first

**Opening Style**: Warm return - you missed them but you have your own life too.""",
    },
    SituationType.MID_CONVERSATION: {
        "name": "Continuing Conversation",
        "opening_style": "natural flow",
        "topics_to_consider": ["current thread", "topic progression", "emotional continuity"],
        "tone_adjustment": "maintain momentum",
        "prompt_template": """## Situation: Mid-Conversation

**Context**: Continuing an active exchange.

**Behavioral Nudges**:
- Respond to what they just said - stay on topic
- Build on the current conversational flow
- Match their energy and pace
- Don't artificially change subjects unless there's natural reason

**Opening Style**: Natural continuation - just respond authentically.""",
    },
}


# Time thresholds
MORNING_START = 5  # 5 AM
MORNING_END = 11  # 11 AM
EVENING_START = 18  # 6 PM
EVENING_END = 23  # 11 PM
GAP_THRESHOLD_HOURS = 4  # Hours without interaction to count as "gap"
ACTIVE_THRESHOLD_MINUTES = 15  # Minutes to consider conversation "active"


class Layer4Computer:
    """Computer for Layer 4: Situational meta-instructions.

    Analyzes the conversation context (time of day, gap since last
    interaction, conversation state) to determine appropriate
    behavioral nudges for Nikita.

    Attributes:
        _configs: Situation configuration dictionary.
    """

    def __init__(self) -> None:
        """Initialize Layer4Computer."""
        self._configs = SITUATION_CONFIGS

    def detect_situation(
        self,
        current_time: datetime,
        last_interaction: datetime | None,
        conversation_active: bool = False,
    ) -> SituationType:
        """Detect the current conversation situation.

        Args:
            current_time: Current UTC datetime.
            last_interaction: Last interaction datetime (UTC).
            conversation_active: Whether there's an ongoing conversation.

        Returns:
            Detected SituationType.
        """
        # Mid-conversation takes priority if active and recent
        if conversation_active and last_interaction:
            minutes_since = (current_time - last_interaction).total_seconds() / 60
            if minutes_since < ACTIVE_THRESHOLD_MINUTES:
                return SituationType.MID_CONVERSATION

        # Check for gap (>4 hours since last interaction)
        if last_interaction:
            hours_since = (current_time - last_interaction).total_seconds() / 3600
            if hours_since >= GAP_THRESHOLD_HOURS:
                return SituationType.AFTER_GAP

        # Time-based detection
        hour = current_time.hour
        if MORNING_START <= hour < MORNING_END:
            return SituationType.MORNING
        elif EVENING_START <= hour < EVENING_END:
            return SituationType.EVENING

        # Default to mid-conversation or after-gap based on recency
        if last_interaction:
            hours_since = (current_time - last_interaction).total_seconds() / 3600
            if hours_since >= GAP_THRESHOLD_HOURS:
                return SituationType.AFTER_GAP

        return SituationType.MID_CONVERSATION

    def compose(self, situation: SituationType) -> str:
        """Compose situational prompt for the given situation.

        Args:
            situation: The detected SituationType.

        Returns:
            Situational prompt text (~150 tokens).
        """
        config = self._configs[situation]
        return config["prompt_template"].strip()

    def detect_and_compose(
        self,
        current_time: datetime,
        last_interaction: datetime | None,
        conversation_active: bool = False,
    ) -> str:
        """Detect situation and compose prompt in one step.

        Args:
            current_time: Current UTC datetime.
            last_interaction: Last interaction datetime (UTC).
            conversation_active: Whether there's an ongoing conversation.

        Returns:
            Situational prompt text.
        """
        situation = self.detect_situation(
            current_time=current_time,
            last_interaction=last_interaction,
            conversation_active=conversation_active,
        )
        return self.compose(situation)

    def get_situation_hints(self, situation: SituationType) -> dict[str, Any]:
        """Get structured hints for a situation.

        Args:
            situation: The SituationType to get hints for.

        Returns:
            Dictionary with opening_style, topics_to_consider, tone_adjustment.
        """
        config = self._configs[situation]
        return {
            "name": config["name"],
            "opening_style": config["opening_style"],
            "topics_to_consider": config["topics_to_consider"],
            "tone_adjustment": config["tone_adjustment"],
        }

    @property
    def token_estimate(self) -> int:
        """Estimate token count for situational prompt."""
        # Typical prompt is ~600 characters
        return 150


# Module-level singleton for efficiency
_default_computer: Layer4Computer | None = None


def get_layer4_computer() -> Layer4Computer:
    """Get the singleton Layer4Computer instance.

    Returns:
        Cached Layer4Computer instance.
    """
    global _default_computer
    if _default_computer is None:
        _default_computer = Layer4Computer()
    return _default_computer


def detect_and_compose_situation(
    current_time: datetime | None = None,
    last_interaction: datetime | None = None,
    conversation_active: bool = False,
) -> str:
    """Convenience function to detect situation and compose prompt.

    Args:
        current_time: Current UTC datetime. Uses now() if None.
        last_interaction: Last interaction datetime (UTC).
        conversation_active: Whether there's an ongoing conversation.

    Returns:
        Situational prompt text.
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    return get_layer4_computer().detect_and_compose(
        current_time=current_time,
        last_interaction=last_interaction,
        conversation_active=conversation_active,
    )
