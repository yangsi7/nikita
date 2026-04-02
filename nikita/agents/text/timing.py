"""Response timing module for Nikita text agent.

Spec 204: Engagement-Aware Response Timing.

This module implements timing logic for response delays,
creating natural, unpredictable response patterns that vary
by relationship chapter AND engagement state.

Key changes (Spec 204):
- Timing ranges recalibrated: Ch1 fast (5-45s), Ch5 slow (2min-1hr)
- Engagement multiplier: 6 states scale the base delay
- First-message path: new users get 5-30s response
- Feature flag: engagement_aware_timing gates the multiplier
- Clamping: final delay clamped to [0, chapter_max * 2]

Uses gaussian distribution to cluster delays around a mean
with random jitter to prevent exact patterns.

Development Mode:
    When ENVIRONMENT=development or DEBUG=true, delays are set to 0
    for faster testing. Use production environment for real delays.
"""

import logging
import random
from typing import Final

from nikita.config.settings import get_settings

logger = logging.getLogger(__name__)


# Timing ranges by chapter: (min_seconds, max_seconds)
# Spec 204: Recalibrated for engagement-first design.
# Ch1: Near-instant to hook the user
# Ch5: Established relationship, comfortable silences
TIMING_RANGES: Final[dict[int, tuple[int, int]]] = {
    1: (5, 45),        # 5s-45s — near-instant, hook the user
    2: (15, 180),      # 15s-3min — slight anticipation builds
    3: (30, 600),      # 30s-10min — realistic texting rhythm
    4: (60, 1800),     # 1min-30min — mature relationship pacing
    5: (120, 3600),    # 2min-1hr — established, comfortable silences
}

# Default timing range for invalid chapters
DEFAULT_TIMING_RANGE: Final[tuple[int, int]] = TIMING_RANGES[1]

# Spec 204 T1: First message from a brand-new user always gets fast response
FIRST_MESSAGE_DELAY: Final[tuple[int, int]] = (5, 30)

# Spec 204 T2: Engagement state multipliers on the calculated delay
ENGAGEMENT_TIMING_MULTIPLIERS: Final[dict[str, float]] = {
    "calibrating": 0.5,     # Faster while learning player's style
    "in_zone":     1.0,     # Normal chapter timing
    "drifting":    0.3,     # Much faster — re-engage them
    "clingy":      1.5,     # Slower — create breathing room
    "distant":     0.1,     # Near-instant — pull them back
    "out_of_zone": 0.2,     # Fast — recovery mode
}


class ResponseTimer:
    """
    Calculates response delays using gaussian distribution.

    Creates natural-feeling response timing that:
    - Clusters around the midpoint of the chapter's range
    - Uses gaussian distribution (not uniform) for more natural feel
    - Adds random jitter to prevent exact patterns
    - Varies by chapter (earlier chapters have shorter, more instant delays)
    - Applies engagement state multiplier (Spec 204)
    - Supports first-message fast path for new users

    Example usage:
        timer = ResponseTimer()
        delay_seconds = timer.calculate_delay(chapter=1)
        delay_seconds = timer.calculate_delay(chapter=3, engagement_state="drifting")
        delay_seconds = timer.calculate_delay(chapter=1, is_first_message=True)
    """

    def __init__(self, jitter_factor: float = 0.1):
        """
        Initialize the ResponseTimer.

        Args:
            jitter_factor: Amount of jitter to add (0-1, default 0.1 = 10%)
        """
        self.jitter_factor = jitter_factor

    def calculate_delay(
        self,
        chapter: int,
        engagement_state: str | None = None,
        is_first_message: bool = False,
    ) -> int:
        """
        Calculate a response delay in seconds for the given chapter.

        Uses gaussian distribution centered on the range midpoint,
        with standard deviation set to capture most values within range.
        Adds random jitter to prevent exact patterns.

        Spec 204 additions:
        - engagement_state: Multiplies base delay (e.g., clingy=1.5x, distant=0.1x)
        - is_first_message: Overrides to FIRST_MESSAGE_DELAY range (5-30s)

        Development Mode:
            When ENVIRONMENT=development or DEBUG=true, returns 0 for instant
            testing. Set ENVIRONMENT=production for real chapter-based delays.

        Args:
            chapter: The user's current chapter (1-5)
            engagement_state: Current engagement state (str) or None for default (1.0x)
            is_first_message: True for brand-new users (overrides to fast response)

        Returns:
            Delay in seconds as an integer
        """
        # Check for development/debug mode - bypass delays for testing
        settings = get_settings()
        if settings.environment == "development" or settings.debug:
            logger.info(
                "[TIMING] Development mode: bypassing delay for chapter %d",
                chapter,
            )
            return 0

        # First-message fast path (Spec 204 T1)
        if is_first_message:
            fm_min, fm_max = FIRST_MESSAGE_DELAY
            delay = random.uniform(fm_min, fm_max)
            logger.info(
                "[TIMING] First message: delay=%.1fs (range %d-%ds)",
                delay, fm_min, fm_max,
            )
            return int(delay)

        # Get timing range for chapter (default to Ch1 if invalid)
        min_sec, max_sec = TIMING_RANGES.get(chapter, DEFAULT_TIMING_RANGE)

        # Calculate gaussian parameters
        # Mean is the midpoint of the range
        mean = (min_sec + max_sec) / 2

        # Standard deviation: set so ~99% of values fall within range
        # For normal distribution, 99% falls within ~2.5 standard deviations
        range_size = max_sec - min_sec
        std_dev = range_size / 5  # ~2.5 std devs from mean to edge

        # Generate gaussian-distributed delay
        base_delay = random.gauss(mean, std_dev)

        # Add jitter to prevent exact patterns
        jitter = random.uniform(-self.jitter_factor, self.jitter_factor)
        base_delay = base_delay * (1 + jitter)

        # Clamp base delay to chapter range
        base_delay = max(min_sec, min(max_sec, base_delay))

        # Apply engagement multiplier (Spec 204 T2)
        multiplier = 1.0
        if settings.engagement_aware_timing and engagement_state is not None:
            multiplier = ENGAGEMENT_TIMING_MULTIPLIERS.get(engagement_state, 1.0)

        final_delay = base_delay * multiplier

        # Clamp final to [0, chapter_max * 2] (Spec 204 AC-T2.4)
        upper_bound = max_sec * 2
        final_delay = max(0, min(upper_bound, final_delay))

        logger.info(
            "[TIMING] chapter=%d, engagement=%s, multiplier=%.1f, "
            "base_delay=%.1fs, final_delay=%.1fs",
            chapter, engagement_state or "none", multiplier,
            base_delay, final_delay,
        )
        return int(final_delay)

    def calculate_delay_human_readable(
        self,
        chapter: int,
        engagement_state: str | None = None,
        is_first_message: bool = False,
    ) -> str:
        """
        Calculate delay and return in human-readable format.

        Args:
            chapter: The user's current chapter (1-5)
            engagement_state: Current engagement state or None
            is_first_message: True for brand-new users

        Returns:
            Human-readable string like "2 hours 15 minutes"
        """
        seconds = self.calculate_delay(chapter, engagement_state, is_first_message)

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if remaining_seconds > 0 and not parts:
            parts.append(f"{remaining_seconds} second{'s' if remaining_seconds != 1 else ''}")

        return " ".join(parts) if parts else "0 seconds"
