"""Response timing module for Nikita text agent.

This module implements timing logic for response delays,
creating natural, unpredictable response patterns that vary
by relationship chapter.

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
# Chapter 1: Very unpredictable (10min to 8h)
# Chapter 2: Less chaotic (5min to 4h)
# Chapter 3: Mostly consistent (5min to 2h)
# Chapter 4: Consistent with delays explained (5min to 1h)
# Chapter 5: Consistent and transparent (5min to 30min)
TIMING_RANGES: Final[dict[int, tuple[int, int]]] = {
    1: (600, 28800),     # 10min - 8h
    2: (300, 14400),     # 5min - 4h
    3: (300, 7200),      # 5min - 2h
    4: (300, 3600),      # 5min - 1h
    5: (300, 1800),      # 5min - 30min
}

# Default timing range for invalid chapters
DEFAULT_TIMING_RANGE: Final[tuple[int, int]] = TIMING_RANGES[1]


class ResponseTimer:
    """
    Calculates response delays using gaussian distribution.

    Creates natural-feeling response timing that:
    - Clusters around the midpoint of the chapter's range
    - Uses gaussian distribution (not uniform) for more natural feel
    - Adds random jitter to prevent exact patterns
    - Varies by chapter (earlier chapters have longer, more unpredictable delays)

    Example usage:
        timer = ResponseTimer()
        delay_seconds = timer.calculate_delay(chapter=1)
        # Returns int in range [600, 28800] with gaussian distribution
    """

    def __init__(self, jitter_factor: float = 0.1):
        """
        Initialize the ResponseTimer.

        Args:
            jitter_factor: Amount of jitter to add (0-1, default 0.1 = 10%)
        """
        self.jitter_factor = jitter_factor

    def calculate_delay(self, chapter: int) -> int:
        """
        Calculate a response delay in seconds for the given chapter.

        Uses gaussian distribution centered on the range midpoint,
        with standard deviation set to capture most values within range.
        Adds random jitter to prevent exact patterns.

        Development Mode:
            When ENVIRONMENT=development or DEBUG=true, returns 0 for instant
            testing. Set ENVIRONMENT=production for real chapter-based delays.

        Args:
            chapter: The user's current chapter (1-5)

        Returns:
            Delay in seconds as an integer, within the chapter's timing range
        """
        # Check for development/debug mode - bypass delays for testing
        settings = get_settings()
        if settings.environment == "development" or settings.debug:
            logger.info(
                f"[TIMING] Development mode: bypassing delay for chapter {chapter}"
            )
            return 0

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
        delay = random.gauss(mean, std_dev)

        # Add jitter to prevent exact patterns
        jitter = random.uniform(-self.jitter_factor, self.jitter_factor)
        delay = delay * (1 + jitter)

        # Clamp to valid range and convert to int
        delay = max(min_sec, min(max_sec, delay))
        logger.info(
            f"[TIMING] Production mode: delay={delay}s for chapter {chapter} "
            f"(range {min_sec}-{max_sec}s)"
        )
        return int(delay)

    def calculate_delay_human_readable(self, chapter: int) -> str:
        """
        Calculate delay and return in human-readable format.

        Args:
            chapter: The user's current chapter (1-5)

        Returns:
            Human-readable string like "2 hours 15 minutes"
        """
        seconds = self.calculate_delay(chapter)

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
