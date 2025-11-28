"""Skip decision module for Nikita text agent.

This module implements the logic for deciding whether to skip
responding to a user message. Skipping creates unpredictability
and matches Nikita's character in earlier chapters.

Skip rates decrease as the relationship progresses through chapters.
"""

import random
from typing import Final


# Skip rates by chapter: (min_rate, max_rate) as decimals
# Chapter 1: Very unpredictable, skips many messages
# Chapter 5: Almost always responds (relationship established)
SKIP_RATES: Final[dict[int, tuple[float, float]]] = {
    1: (0.25, 0.40),    # 25-40% skip
    2: (0.15, 0.25),    # 15-25% skip
    3: (0.05, 0.15),    # 5-15% skip
    4: (0.02, 0.10),    # 2-10% skip
    5: (0.00, 0.05),    # 0-5% skip
}

# Default skip rate for invalid chapters
DEFAULT_SKIP_RATE: Final[tuple[float, float]] = SKIP_RATES[1]

# Reduction factor for consecutive skip probability
CONSECUTIVE_SKIP_REDUCTION: Final[float] = 0.5


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

    def should_skip(self, chapter: int) -> bool:
        """
        Decide whether to skip responding to a message.

        Uses randomized probability within the chapter's skip rate range.
        Reduces skip probability after a previous skip to avoid
        consecutive ignoring of the player.

        Args:
            chapter: The user's current chapter (1-5)

        Returns:
            True if the message should be skipped, False to respond
        """
        # Get skip rate range for chapter (default to Ch1 if invalid)
        min_rate, max_rate = SKIP_RATES.get(chapter, DEFAULT_SKIP_RATE)

        # Pick a random skip probability within the range
        skip_probability = random.uniform(min_rate, max_rate)

        # Reduce probability if last message was skipped
        if self.last_was_skipped:
            skip_probability *= CONSECUTIVE_SKIP_REDUCTION

        # Make the decision
        should_skip = random.random() < skip_probability

        # Track this decision for next time
        self.last_was_skipped = should_skip

        return should_skip

    def reset(self) -> None:
        """Reset the skip tracker state."""
        self.last_was_skipped = False
