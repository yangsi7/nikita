"""Mood Calculator for Life Simulation Engine (Spec 022, T005).

Computes Nikita's mood from daily life events.

AC-T005.1: MoodCalculator class
AC-T005.2: compute_from_events() returns mood dict
AC-T005.3: Mood dimensions: arousal, valence, dominance, intimacy
AC-T005.4: Correct delta application per event
AC-T005.5: Unit tests for calculator
"""

import logging
from dataclasses import dataclass

from nikita.life_simulation.models import LifeEvent

logger = logging.getLogger(__name__)


@dataclass
class MoodState:
    """Nikita's current mood state.

    Each dimension ranges from 0.0 to 1.0:
    - arousal: Energy level (low=0, high=1)
    - valence: Positivity (negative=0, positive=1)
    - dominance: Control/confidence (submissive=0, dominant=1)
    - intimacy: Openness to connection (closed=0, open=1)
    """

    arousal: float = 0.5
    valence: float = 0.5
    dominance: float = 0.5
    intimacy: float = 0.5

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "arousal": round(self.arousal, 3),
            "valence": round(self.valence, 3),
            "dominance": round(self.dominance, 3),
            "intimacy": round(self.intimacy, 3),
        }

    def __post_init__(self):
        """Clamp values to valid range."""
        self.arousal = max(0.0, min(1.0, self.arousal))
        self.valence = max(0.0, min(1.0, self.valence))
        self.dominance = max(0.0, min(1.0, self.dominance))
        self.intimacy = max(0.0, min(1.0, self.intimacy))


class MoodCalculator:
    """Calculates Nikita's mood from life events.

    Mood is derived from the cumulative emotional impact of daily events.
    Each event contributes deltas to the 4 mood dimensions.

    Formula:
    - Base mood: 0.5 for each dimension (neutral)
    - Apply event deltas in chronological order
    - Clamp final values to [0.0, 1.0]

    Example:
        calculator = MoodCalculator()
        events = [bad_meeting, coffee_with_friend, gym_session]
        mood = calculator.compute_from_events(events)
        # mood.valence might be 0.4 (slightly negative from bad meeting)
    """

    def __init__(self, base_mood: MoodState | None = None):
        """Initialize calculator with optional base mood.

        Args:
            base_mood: Starting mood state. Defaults to neutral (0.5 all).
        """
        self._base_mood = base_mood or MoodState()

    def compute_from_events(
        self, events: list[LifeEvent], decay_previous: bool = False
    ) -> MoodState:
        """Compute mood from a list of events.

        Args:
            events: List of LifeEvent objects.
            decay_previous: If True, decay effects of older events slightly.

        Returns:
            MoodState with computed values.
        """
        if not events:
            return MoodState(
                arousal=self._base_mood.arousal,
                valence=self._base_mood.valence,
                dominance=self._base_mood.dominance,
                intimacy=self._base_mood.intimacy,
            )

        # Start from base mood
        arousal = self._base_mood.arousal
        valence = self._base_mood.valence
        dominance = self._base_mood.dominance
        intimacy = self._base_mood.intimacy

        # Apply each event's emotional impact
        for i, event in enumerate(events):
            impact = event.emotional_impact

            # Optional decay for older events
            decay_factor = 1.0
            if decay_previous and len(events) > 1:
                # Most recent event has full impact, older ones decay
                position = i / (len(events) - 1)  # 0.0 to 1.0
                decay_factor = 0.5 + 0.5 * position  # 0.5 to 1.0

            arousal += impact.arousal_delta * decay_factor
            valence += impact.valence_delta * decay_factor
            dominance += impact.dominance_delta * decay_factor
            intimacy += impact.intimacy_delta * decay_factor

        return MoodState(
            arousal=arousal,
            valence=valence,
            dominance=dominance,
            intimacy=intimacy,
        )

    def compute_from_event(self, event: LifeEvent) -> MoodState:
        """Compute mood contribution from a single event.

        Args:
            event: Single LifeEvent.

        Returns:
            MoodState with computed values.
        """
        return self.compute_from_events([event])

    def describe_mood(self, mood: MoodState) -> str:
        """Generate a natural language description of the mood.

        Args:
            mood: MoodState to describe.

        Returns:
            Human-readable mood description.
        """
        descriptions = []

        # Arousal description
        if mood.arousal > 0.7:
            descriptions.append("energetic")
        elif mood.arousal < 0.3:
            descriptions.append("tired")

        # Valence description
        if mood.valence > 0.7:
            descriptions.append("happy")
        elif mood.valence > 0.55:
            descriptions.append("content")
        elif mood.valence < 0.3:
            descriptions.append("upset")
        elif mood.valence < 0.45:
            descriptions.append("a bit off")

        # Dominance description
        if mood.dominance > 0.7:
            descriptions.append("confident")
        elif mood.dominance < 0.3:
            descriptions.append("uncertain")

        # Intimacy description
        if mood.intimacy > 0.7:
            descriptions.append("open")
        elif mood.intimacy < 0.3:
            descriptions.append("guarded")

        if not descriptions:
            return "neutral"

        return ", ".join(descriptions)


# Module-level singleton
_default_calculator: MoodCalculator | None = None


def get_mood_calculator() -> MoodCalculator:
    """Get the singleton MoodCalculator instance.

    Returns:
        Cached MoodCalculator instance.
    """
    global _default_calculator
    if _default_calculator is None:
        _default_calculator = MoodCalculator()
    return _default_calculator
