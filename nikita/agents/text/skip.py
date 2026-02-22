"""Skip decision module for Nikita text agent.

This module implements the logic for deciding whether to skip
responding to a user message. Skipping creates unpredictability
and matches Nikita's character in earlier chapters.

Skip rates decrease as the relationship progresses through chapters.
"""

import random
from difflib import SequenceMatcher
from typing import Final


# Skip rates by chapter: (min_rate, max_rate) as decimals
# Gated by settings.skip_rates_enabled feature flag (default OFF).
# When flag is OFF, all rates are effectively 0 (always respond).
SKIP_RATES: Final[dict[int, tuple[float, float]]] = {
    1: (0.25, 0.40),    # Ch1 Curiosity: guarded, 25-40% skip
    2: (0.15, 0.25),    # Ch2 Intrigue: warming up, 15-25% skip
    3: (0.05, 0.15),    # Ch3 Investment: engaged, 5-15% skip
    4: (0.02, 0.10),    # Ch4 Intimacy: committed, 2-10% skip
    5: (0.00, 0.05),    # Ch5 Established: always there, 0-5% skip
}

# Zero rates used when skip feature flag is OFF
SKIP_RATES_DISABLED: Final[dict[int, tuple[float, float]]] = {
    1: (0.00, 0.00),
    2: (0.00, 0.00),
    3: (0.00, 0.00),
    4: (0.00, 0.00),
    5: (0.00, 0.00),
}

# Default skip rate for invalid chapters — always 0 (never skip for unknown chapters)
DEFAULT_SKIP_RATE: Final[tuple[float, float]] = (0.00, 0.00)

# Reduction factor for consecutive skip probability
CONSECUTIVE_SKIP_REDUCTION: Final[float] = 0.5

# Semantic repetition similarity threshold (Spec 101 FR-005)
REPETITION_SIMILARITY_THRESHOLD: Final[float] = 0.7
# Boost factor applied to skip probability when repetition detected
REPETITION_BOOST: Final[float] = 2.0


class SkipDecision:
    """
    Decides whether to skip responding to a user message.

    Creates natural unpredictability by randomly skipping messages
    based on chapter-specific probabilities. Earlier chapters have
    higher skip rates, reflecting Nikita's guarded nature.

    Tracks last skip to reduce probability of consecutive skips,
    ensuring the player doesn't feel completely ignored.

    Example usage:
        decision = SkipDecision()
        if decision.should_skip(chapter=1):
            # Don't respond to this message
            log("Skipping message for user in chapter 1")
        else:
            # Generate and send response
            response = await agent.run(message)
    """

    def __init__(self):
        """Initialize the SkipDecision tracker."""
        self.last_was_skipped = False

    def has_repetition(
        self, current_message: str, recent_messages: list[str]
    ) -> bool:
        """Detect if current message is semantically similar to any recent message."""
        if not recent_messages or not current_message:
            return False
        current_lower = current_message.lower()
        for msg in recent_messages:
            ratio = SequenceMatcher(None, current_lower, msg.lower()).ratio()
            if ratio >= REPETITION_SIMILARITY_THRESHOLD:
                return True
        return False

    def should_skip(
        self,
        chapter: int,
        recent_messages: list[str] | None = None,
        current_message: str | None = None,
    ) -> bool:
        """
        Decide whether to skip responding to a message.

        Uses randomized probability within the chapter's skip rate range.
        Reduces skip probability after a previous skip to avoid
        consecutive ignoring of the player.

        Gated by skip_rates_enabled feature flag — when OFF, always returns False.

        Args:
            chapter: The user's current chapter (1-5)

        Returns:
            True if the message should be skipped, False to respond
        """
        from nikita.config.settings import get_settings

        settings = get_settings()
        rates = SKIP_RATES if settings.skip_rates_enabled else SKIP_RATES_DISABLED

        # Get skip rate range for chapter (default to Ch1 if invalid)
        min_rate, max_rate = rates.get(chapter, DEFAULT_SKIP_RATE)

        # Pick a random skip probability within the range
        skip_probability = random.uniform(min_rate, max_rate)

        # Reduce probability if last message was skipped
        if self.last_was_skipped:
            skip_probability *= CONSECUTIVE_SKIP_REDUCTION

        # Boost probability if repetition detected
        if current_message and recent_messages:
            if self.has_repetition(current_message, recent_messages):
                skip_probability *= REPETITION_BOOST

        # Make the decision
        should_skip = random.random() < skip_probability

        # Track this decision for next time
        self.last_was_skipped = should_skip

        return should_skip

    def reset(self) -> None:
        """Reset the skip tracker state."""
        self.last_was_skipped = False
