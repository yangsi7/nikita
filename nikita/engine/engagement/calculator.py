"""Calibration calculator for engagement scoring (spec 014).

This module calculates the calibration score that determines engagement state.

Components:
- OptimalFrequencyCalculator: Calculates optimal messaging frequency per chapter/day
- CalibrationCalculator: Computes calibration score from player metrics
- map_score_to_state: Maps calibration score to engagement state

Score Components (weighted):
- Frequency (40%): How close to optimal messaging rate
- Timing (30%): Response time patterns
- Content (30%): Message quality indicators
"""

from decimal import Decimal

from nikita.config.enums import EngagementState
from nikita.engine.engagement.models import CalibrationResult

# Base optimal messages per day by chapter
# Decreases as relationship deepens (less frequent but deeper conversations)
BASE_OPTIMAL_FREQUENCY = {
    1: 15,  # Curiosity - getting to know each other
    2: 12,  # Intrigue - building interest
    3: 10,  # Investment - deepening connection
    4: 8,   # Intimacy - comfortable conversations
    5: 6,   # Established - quality over quantity
}

# Day-of-week modifiers (0=Monday, 6=Sunday)
DAY_MODIFIERS = {
    0: Decimal("0.9"),   # Monday - busy workday
    1: Decimal("0.95"),  # Tuesday
    2: Decimal("1.0"),   # Wednesday
    3: Decimal("1.0"),   # Thursday
    4: Decimal("1.05"),  # Friday - more social
    5: Decimal("1.2"),   # Saturday - most available
    6: Decimal("1.1"),   # Sunday - relaxed
}

# Tolerance bands per chapter (±percentage)
# Later chapters are more forgiving
TOLERANCE_BANDS = {
    1: Decimal("0.10"),  # ±10% in early phase
    2: Decimal("0.15"),  # ±15%
    3: Decimal("0.20"),  # ±20%
    4: Decimal("0.25"),  # ±25%
    5: Decimal("0.30"),  # ±30% in established phase
}

# Component weights for calibration score
CALIBRATION_WEIGHTS = {
    "frequency": Decimal("0.40"),  # 40%
    "timing": Decimal("0.30"),     # 30%
    "content": Decimal("0.30"),    # 30%
}

# Response time boundaries (in seconds)
IDEAL_RESPONSE_MIN = 60   # 1 minute - don't be too eager
IDEAL_RESPONSE_MAX = 3600  # 1 hour - don't be too slow
SLOW_RESPONSE_THRESHOLD = 4 * 3600  # 4 hours - neglect boundary

# Score thresholds for state mapping
STATE_THRESHOLDS = {
    "in_zone": Decimal("0.8"),      # >= 0.8 = IN_ZONE
    "drifting": Decimal("0.5"),     # >= 0.5 = DRIFTING
    "problematic": Decimal("0.3"),  # >= 0.3 = CLINGY/DISTANT
    # < 0.3 = OUT_OF_ZONE
}


def _clamp(value: Decimal, min_val: Decimal = Decimal("0"), max_val: Decimal = Decimal("1")) -> Decimal:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


class OptimalFrequencyCalculator:
    """Calculates optimal messaging frequency based on chapter and day.

    Base optimal values decrease as chapters progress (quality over quantity).
    Day modifiers adjust for weekday/weekend patterns.
    """

    def get_optimal(self, chapter: int, day_of_week: int) -> int:
        """Get optimal messages per day for given chapter and day.

        Args:
            chapter: Current game chapter (1-5)
            day_of_week: Day of week (0=Monday, 6=Sunday)

        Returns:
            Optimal number of messages for that day
        """
        base = BASE_OPTIMAL_FREQUENCY.get(chapter, BASE_OPTIMAL_FREQUENCY[1])
        modifier = DAY_MODIFIERS.get(day_of_week, Decimal("1.0"))

        optimal = Decimal(str(base)) * modifier
        return int(optimal)

    def get_tolerance_band(self, chapter: int) -> Decimal:
        """Get tolerance band percentage for chapter.

        Args:
            chapter: Current game chapter (1-5)

        Returns:
            Tolerance as decimal (e.g., 0.10 for ±10%)
        """
        return TOLERANCE_BANDS.get(chapter, TOLERANCE_BANDS[1])

    def get_bounds(self, chapter: int, day_of_week: int) -> tuple[int, int]:
        """Get lower and upper bounds for acceptable frequency.

        Args:
            chapter: Current game chapter (1-5)
            day_of_week: Day of week (0=Monday, 6=Sunday)

        Returns:
            Tuple of (lower_bound, upper_bound) as integers
        """
        optimal = self.get_optimal(chapter, day_of_week)
        tolerance = self.get_tolerance_band(chapter)

        lower = int(Decimal(str(optimal)) * (Decimal("1") - tolerance))
        upper = int(Decimal(str(optimal)) * (Decimal("1") + tolerance))

        return lower, upper


class CalibrationCalculator:
    """Calculates calibration score from player engagement metrics.

    Components:
    - Frequency (40%): Deviation from optimal message rate
    - Timing (30%): Response time patterns
    - Content (30%): Message quality (length, needy/distracted language)

    Score Range: 0.0 (very poor) to 1.0 (perfect)
    """

    def _frequency_component(
        self,
        actual_messages: int,
        optimal_messages: int,
    ) -> Decimal:
        """Calculate frequency component of calibration score.

        Formula: 1 - |actual - optimal| / optimal
        Capped at 0 when deviation >= 100%

        Returns:
            Decimal score 0-1 (higher = closer to optimal)
        """
        if optimal_messages <= 0:
            return Decimal("0")

        actual = Decimal(str(actual_messages))
        optimal = Decimal(str(optimal_messages))

        deviation = abs(actual - optimal) / optimal

        # Deviation of 1.0 (100%) = score 0
        score = Decimal("1") - deviation

        return _clamp(score)

    def _timing_component(
        self,
        avg_response_seconds: int,
    ) -> Decimal:
        """Calculate timing component of calibration score.

        Ideal: 1-60 minutes (not too eager, not too slow)
        Penalties for:
        - < 1 min: Too eager (slight penalty)
        - > 1 hour: Too slow (increasing penalty)
        - > 4 hours: Very slow (major penalty)

        Returns:
            Decimal score 0-1 (higher = better timing)
        """
        response = Decimal(str(avg_response_seconds))

        # Perfect timing: 1-60 minutes (60-3600 seconds)
        if IDEAL_RESPONSE_MIN <= avg_response_seconds <= IDEAL_RESPONSE_MAX:
            return Decimal("1")

        # Too fast (< 1 minute): Slight penalty
        if avg_response_seconds < IDEAL_RESPONSE_MIN:
            # 0 seconds = 0.6, 60 seconds = 1.0
            score = Decimal("0.6") + (response / Decimal(str(IDEAL_RESPONSE_MIN))) * Decimal("0.4")
            return _clamp(score)

        # Too slow (> 1 hour): Increasing penalty
        if avg_response_seconds > IDEAL_RESPONSE_MAX:
            # 1 hour = 1.0, 4 hours = 0.5, 8 hours = 0
            excess = response - Decimal(str(IDEAL_RESPONSE_MAX))
            penalty = excess / Decimal(str(SLOW_RESPONSE_THRESHOLD))
            score = Decimal("1") - penalty
            return _clamp(score)

        return Decimal("0.5")

    def _content_component(
        self,
        avg_message_length: int,
        needy_score: Decimal,
        distracted_score: Decimal,
    ) -> Decimal:
        """Calculate content component of calibration score.

        Factors:
        - Message length (ideal: 50-150 chars)
        - Needy language (lower = better)
        - Distracted language (lower = better)

        Returns:
            Decimal score 0-1 (higher = better content quality)
        """
        # Length factor: 50-150 chars ideal
        length = Decimal(str(avg_message_length))
        if length < Decimal("20"):
            length_score = length / Decimal("20") * Decimal("0.5")
        elif length < Decimal("50"):
            length_score = Decimal("0.5") + (length - Decimal("20")) / Decimal("30") * Decimal("0.5")
        elif length <= Decimal("150"):
            length_score = Decimal("1")
        else:
            # Slightly too long - minor penalty
            excess = length - Decimal("150")
            length_score = Decimal("1") - (excess / Decimal("200"))
        length_score = _clamp(length_score)

        # Language quality factor: low needy + low distracted = high score
        language_score = Decimal("1") - (_clamp(needy_score) + _clamp(distracted_score)) / Decimal("2")
        language_score = _clamp(language_score)

        # Weight: 40% length, 60% language quality
        content_score = length_score * Decimal("0.4") + language_score * Decimal("0.6")

        return _clamp(content_score)

    def compute(
        self,
        actual_messages: int,
        optimal_messages: int,
        avg_response_seconds: int,
        avg_message_length: int,
        needy_score: Decimal,
        distracted_score: Decimal,
    ) -> CalibrationResult:
        """Compute calibration score and suggested state.

        Component weights:
        - Frequency: 40%
        - Timing: 30%
        - Content: 30%

        Returns:
            CalibrationResult with score, components, and suggested_state
        """
        frequency_component = self._frequency_component(actual_messages, optimal_messages)
        timing_component = self._timing_component(avg_response_seconds)
        content_component = self._content_component(
            avg_message_length, needy_score, distracted_score
        )

        # Weighted sum
        score = (
            frequency_component * CALIBRATION_WEIGHTS["frequency"] +
            timing_component * CALIBRATION_WEIGHTS["timing"] +
            content_component * CALIBRATION_WEIGHTS["content"]
        )
        score = _clamp(score)

        # Determine if clingy or neglecting based on signals
        # Clingy: fast responses, high needy score, high message count
        is_clingy = (
            avg_response_seconds < IDEAL_RESPONSE_MIN and
            needy_score > Decimal("0.5")
        ) or actual_messages > optimal_messages * 2

        # Neglecting: slow responses, high distracted score, low message count
        is_neglecting = (
            avg_response_seconds > SLOW_RESPONSE_THRESHOLD or
            distracted_score > Decimal("0.5") or
            actual_messages < optimal_messages // 2
        )

        suggested_state = map_score_to_state(score, is_clingy, is_neglecting)

        return CalibrationResult(
            score=score,
            frequency_component=frequency_component,
            timing_component=timing_component,
            content_component=content_component,
            suggested_state=suggested_state,
        )


def map_score_to_state(
    score: Decimal,
    is_clingy: bool = False,
    is_neglecting: bool = False,
) -> EngagementState:
    """Map calibration score to engagement state.

    Thresholds:
    - >= 0.8: IN_ZONE
    - 0.5-0.8: DRIFTING
    - 0.3-0.5: CLINGY (if clingy) or DISTANT (if neglecting) or DRIFTING
    - < 0.3: OUT_OF_ZONE

    Args:
        score: Calibration score 0-1
        is_clingy: True if clinginess detected
        is_neglecting: True if neglect detected

    Returns:
        Suggested EngagementState
    """
    if score >= STATE_THRESHOLDS["in_zone"]:
        return EngagementState.IN_ZONE

    if score >= STATE_THRESHOLDS["drifting"]:
        return EngagementState.DRIFTING

    if score >= STATE_THRESHOLDS["problematic"]:
        if is_clingy:
            return EngagementState.CLINGY
        if is_neglecting:
            return EngagementState.DISTANT
        return EngagementState.DRIFTING

    # Very low score
    return EngagementState.OUT_OF_ZONE
