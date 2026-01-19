"""Strategic Silence for Proactive Touchpoint System (Spec 025, Phase D: T017-T020).

Implements strategic silence logic to make Nikita feel more human by
intentionally skipping some touchpoints. This creates unpredictability
and prevents robotic message patterns.

Key Features:
- 10-20% of touchpoints skipped (chapter-dependent)
- Emotional state integration (more silence when upset)
- Random factor for unpredictability
- Skip reasons recorded for analytics
"""

import random
from dataclasses import dataclass
from enum import Enum
from typing import Any


class SilenceReason(Enum):
    """Reasons for strategic silence."""

    RANDOM = "random"  # Random skip for unpredictability
    EMOTIONAL = "emotional"  # Upset or in conflict
    CONFLICT = "conflict"  # Active conflict state
    CHAPTER_RATE = "chapter_rate"  # Chapter-based probability
    RECENT_CONTACT = "recent_contact"  # Already contacted recently


@dataclass
class SilenceDecision:
    """Result of strategic silence evaluation."""

    should_skip: bool
    reason: SilenceReason | None = None
    probability_used: float = 0.0
    emotional_modifier: float = 1.0
    random_value: float = 0.0

    def __str__(self) -> str:
        if self.should_skip:
            return f"SKIP ({self.reason.value if self.reason else 'unknown'})"
        return "PROCEED"


class StrategicSilence:
    """Evaluates whether to apply strategic silence to a touchpoint.

    Strategic silence makes Nikita feel more human by intentionally
    skipping some touchpoints. The skip rate varies by chapter and
    is influenced by emotional state.

    Attributes:
        base_rates: Base silence rates per chapter.
        emotional_thresholds: Valence thresholds for emotional silence.
    """

    # Chapter-based silence rates (FR-010): 10-20%
    DEFAULT_RATES = {
        1: 0.10,  # Chapter 1: 10% silence
        2: 0.12,  # Chapter 2: 12% silence
        3: 0.15,  # Chapter 3: 15% silence
        4: 0.18,  # Chapter 4: 18% silence
        5: 0.20,  # Chapter 5: 20% silence
    }

    # Emotional thresholds
    UPSET_THRESHOLD = 0.3  # Valence below this = upset
    CONFLICT_AROUSAL_THRESHOLD = 0.6  # High arousal + low valence = conflict

    def __init__(self, custom_rates: dict[int, float] | None = None):
        """Initialize strategic silence evaluator.

        Args:
            custom_rates: Optional custom silence rates per chapter.
        """
        self.base_rates = custom_rates or self.DEFAULT_RATES.copy()

    def apply_strategic_silence(
        self,
        chapter: int,
        emotional_state: dict[str, Any] | None = None,
        conflict_active: bool = False,
        random_seed: int | None = None,
    ) -> SilenceDecision:
        """Determine whether to apply strategic silence.

        Args:
            chapter: Current relationship chapter (1-5).
            emotional_state: Current emotional state (valence, arousal, dominance).
            conflict_active: Whether there's an active conflict.
            random_seed: Optional seed for reproducible testing.

        Returns:
            SilenceDecision with skip status and reason.
        """
        # Seed random for testing if provided
        if random_seed is not None:
            random.seed(random_seed)

        # Check conflict state first (highest priority)
        if conflict_active:
            return SilenceDecision(
                should_skip=True,
                reason=SilenceReason.CONFLICT,
                probability_used=1.0,
                emotional_modifier=1.0,
                random_value=0.0,
            )

        # Check emotional state
        emotional_modifier = self._compute_emotional_modifier(emotional_state)
        if emotional_state and emotional_modifier > 1.4:
            # High emotional modifier means upset - more likely to skip
            return SilenceDecision(
                should_skip=True,
                reason=SilenceReason.EMOTIONAL,
                probability_used=1.0,
                emotional_modifier=emotional_modifier,
                random_value=0.0,
            )

        # Get base rate for chapter
        base_rate = self.base_rates.get(chapter, self.DEFAULT_RATES.get(3, 0.15))

        # Apply emotional modifier to rate
        adjusted_rate = min(base_rate * emotional_modifier, 0.5)  # Cap at 50%

        # Generate random value for decision
        random_value = random.random()

        if random_value < adjusted_rate:
            # Determine if emotional or random
            if emotional_modifier > 1.0:
                reason = SilenceReason.EMOTIONAL
            else:
                reason = SilenceReason.RANDOM

            return SilenceDecision(
                should_skip=True,
                reason=reason,
                probability_used=adjusted_rate,
                emotional_modifier=emotional_modifier,
                random_value=random_value,
            )

        return SilenceDecision(
            should_skip=False,
            reason=None,
            probability_used=adjusted_rate,
            emotional_modifier=emotional_modifier,
            random_value=random_value,
        )

    def _compute_emotional_modifier(
        self, emotional_state: dict[str, Any] | None
    ) -> float:
        """Compute silence modifier based on emotional state.

        Low valence (upset) increases silence probability.
        High arousal with low valence (agitated) increases it further.

        Args:
            emotional_state: Emotional state dict with valence, arousal, dominance.

        Returns:
            Modifier value (1.0 = no change, >1.0 = more silence).
        """
        if not emotional_state:
            return 1.0

        valence = emotional_state.get("valence", 0.5)
        arousal = emotional_state.get("arousal", 0.5)
        dominance = emotional_state.get("dominance", 0.5)

        modifier = 1.0

        # Low valence increases silence
        if valence < self.UPSET_THRESHOLD:
            # Very upset: significant silence increase
            modifier += (self.UPSET_THRESHOLD - valence) * 3.0

        elif valence < 0.4:
            # Somewhat negative: mild increase
            modifier += (0.4 - valence) * 1.5

        # High arousal with low valence = agitated
        if valence < 0.4 and arousal > self.CONFLICT_AROUSAL_THRESHOLD:
            modifier += 0.5

        # Low dominance (vulnerable) slightly increases silence
        if dominance < 0.3:
            modifier += 0.2

        return modifier

    def get_silence_rate(self, chapter: int) -> float:
        """Get the base silence rate for a chapter.

        Args:
            chapter: Chapter number (1-5).

        Returns:
            Base silence rate as a float (0.10 - 0.20).
        """
        return self.base_rates.get(chapter, self.DEFAULT_RATES.get(3, 0.15))

    def should_skip_for_emotional_state(
        self, emotional_state: dict[str, Any] | None
    ) -> bool:
        """Check if emotional state alone warrants silence.

        Args:
            emotional_state: Emotional state dict.

        Returns:
            True if should skip due to emotional state.
        """
        if not emotional_state:
            return False

        valence = emotional_state.get("valence", 0.5)

        # Very upset = definitely skip
        if valence < self.UPSET_THRESHOLD:
            return True

        return False

    def record_skip(
        self,
        decision: SilenceDecision,
        touchpoint_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a skip record for analytics.

        Args:
            decision: The silence decision made.
            touchpoint_id: Optional touchpoint ID.

        Returns:
            Dict with skip details for storage.
        """
        return {
            "touchpoint_id": touchpoint_id,
            "skipped": decision.should_skip,
            "reason": decision.reason.value if decision.reason else None,
            "probability_used": decision.probability_used,
            "emotional_modifier": decision.emotional_modifier,
            "random_value": decision.random_value,
        }


# Convenience function
def should_apply_silence(
    chapter: int,
    emotional_state: dict[str, Any] | None = None,
    conflict_active: bool = False,
) -> SilenceDecision:
    """Check if strategic silence should be applied.

    Convenience function for simple usage.

    Args:
        chapter: Current chapter (1-5).
        emotional_state: Optional emotional state.
        conflict_active: Whether conflict is active.

    Returns:
        SilenceDecision.
    """
    silence = StrategicSilence()
    return silence.apply_strategic_silence(
        chapter=chapter,
        emotional_state=emotional_state,
        conflict_active=conflict_active,
    )
