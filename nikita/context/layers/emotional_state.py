"""Layer 3: Emotional State Composer (Spec 021, T008 + Spec 023, T019).

Generates emotional state prompt overlays based on Nikita's current mood
and conflict state.

Uses the 4-dimensional emotional model:
- Arousal: Energy level (low to high)
- Valence: Mood quality (negative to positive)
- Dominance: Control/confidence level
- Intimacy: Connection/openness level

Plus conflict states from Spec 023:
- NONE: Normal state
- PASSIVE_AGGRESSIVE: Subtle hostility
- COLD: Withdrawn, distant
- VULNERABLE: Hurt, emotional
- EXPLOSIVE: Open anger

Token budget: ~200 tokens (increased for conflict state)
"""

import logging
from typing import Any

from nikita.context.package import EmotionalState
from nikita.emotional_state.models import ConflictState, EmotionalStateModel

logger = logging.getLogger(__name__)


# Thresholds for categorizing dimension values
LOW_THRESHOLD = 0.35
HIGH_THRESHOLD = 0.65


class Layer3Composer:
    """Composer for Layer 3: Emotional State prompt overlays.

    Integrates with Spec 023 EmotionalStateModel for full conflict state support.

    This layer modulates Nikita's emotional tone based on the
    4-dimensional emotional model (arousal, valence, dominance, intimacy)
    plus conflict states (passive_aggressive, cold, vulnerable, explosive).

    Attributes:
        _default_state: Default neutral emotional state.
    """

    def __init__(self) -> None:
        """Initialize Layer3Composer."""
        self._default_state = EmotionalState()

    def compose(
        self,
        state: EmotionalState | EmotionalStateModel | None = None,
    ) -> str:
        """Compose emotional state prompt overlay.

        Supports both simple EmotionalState (Spec 021) and full
        EmotionalStateModel with conflict state (Spec 023).

        Args:
            state: EmotionalState or EmotionalStateModel. If None, uses neutral.

        Returns:
            Emotional state prompt text (~200 tokens).
        """
        if state is None:
            state = self._default_state

        # Check if we have conflict state (EmotionalStateModel)
        conflict_state = self._get_conflict_state(state)
        has_conflict = conflict_state != ConflictState.NONE

        description = self.describe_state(state)
        mood = self._get_mood_label(state)
        energy = self._get_energy_label(state.arousal)

        # Build base prompt
        prompt_parts = [
            "## Current Emotional State",
            "",
            f"**Mood**: {mood}",
            f"**Energy**: {energy}",
        ]

        # Add conflict state if active (AC-T019.3)
        if has_conflict:
            conflict_desc = self._describe_conflict_state(conflict_state)
            prompt_parts.extend([
                f"**Conflict State**: {conflict_state.value.replace('_', ' ').title()}",
                f"*{conflict_desc}*",
            ])

        prompt_parts.extend([
            "",
            "**Emotional Dynamics**:",
            f"- Arousal: {description['arousal']}",
            f"- Valence: {description['valence']}",
            f"- Dominance: {description['dominance']}",
            f"- Intimacy: {description['intimacy']}",
            "",
            "**Behavioral Impact**:",
            self._get_behavioral_impact(state, conflict_state),
        ])

        return "\n".join(prompt_parts).strip()

    def _get_conflict_state(
        self,
        state: EmotionalState | EmotionalStateModel,
    ) -> ConflictState:
        """Extract conflict state from state object.

        Args:
            state: State object (may or may not have conflict_state).

        Returns:
            ConflictState (NONE if not available).
        """
        if isinstance(state, EmotionalStateModel):
            return state.conflict_state
        # EmotionalState from package.py doesn't have conflict_state
        return ConflictState.NONE

    def _describe_conflict_state(self, conflict: ConflictState) -> str:
        """Get human-readable description of conflict state.

        Args:
            conflict: ConflictState enum value.

        Returns:
            Natural language description.
        """
        descriptions = {
            ConflictState.NONE: "No conflict - normal state",
            ConflictState.PASSIVE_AGGRESSIVE: "Subtly upset - short responses, indirect hostility, sarcasm",
            ConflictState.COLD: "Emotionally withdrawn - distant, minimal engagement, brief",
            ConflictState.VULNERABLE: "Hurt and emotional - seeking understanding, may bring up past",
            ConflictState.EXPLOSIVE: "Openly angry - confrontational, won't let things go",
        }
        return descriptions.get(conflict, "Unknown state")

    def get_default_state(self) -> EmotionalState:
        """Get the default neutral emotional state.

        Returns:
            EmotionalState with all dimensions at 0.5.
        """
        return EmotionalState()

    def describe_state(
        self,
        state: EmotionalState | EmotionalStateModel,
    ) -> dict[str, str]:
        """Generate human-readable descriptions for each dimension.

        Args:
            state: EmotionalState or EmotionalStateModel to describe.

        Returns:
            Dictionary with descriptions for each dimension.
        """
        return {
            "arousal": self._describe_arousal(state.arousal),
            "valence": self._describe_valence(state.valence),
            "dominance": self._describe_dominance(state.dominance),
            "intimacy": self._describe_intimacy(state.intimacy),
        }

    def _describe_arousal(self, value: float) -> str:
        """Describe arousal level."""
        if value < LOW_THRESHOLD:
            return "Low energy - quiet, subdued, relaxed"
        elif value > HIGH_THRESHOLD:
            return "High energy - animated, excited, intense"
        else:
            return "Moderate energy - calm and stable"

    def _describe_valence(self, value: float) -> str:
        """Describe valence level."""
        if value < LOW_THRESHOLD:
            return "Negative mood - feeling down or off"
        elif value > HIGH_THRESHOLD:
            return "Positive mood - warm and pleasant"
        else:
            return "Neutral mood - balanced state"

    def _describe_dominance(self, value: float) -> str:
        """Describe dominance level."""
        if value < LOW_THRESHOLD:
            return "Uncertain - receptive, open, vulnerable"
        elif value > HIGH_THRESHOLD:
            return "Confident - assertive, in control, strong"
        else:
            return "Balanced - neither dominant nor submissive"

    def _describe_intimacy(self, value: float) -> str:
        """Describe intimacy level."""
        if value < LOW_THRESHOLD:
            return "Guarded - distant, reserved, boundaries up"
        elif value > HIGH_THRESHOLD:
            return "Connected - close, intimate, open"
        else:
            return "Moderate closeness - comfortable but not fully open"

    def _get_mood_label(self, state: EmotionalState | EmotionalStateModel) -> str:
        """Get a single-word mood label based on state."""
        if self._is_neutral(state):
            return "Neutral/Balanced"

        # Combine arousal and valence for primary mood
        if state.valence > HIGH_THRESHOLD:
            if state.arousal > HIGH_THRESHOLD:
                return "Excited/Happy"
            elif state.arousal < LOW_THRESHOLD:
                return "Content/Peaceful"
            else:
                return "Pleasant/Warm"
        elif state.valence < LOW_THRESHOLD:
            if state.arousal > HIGH_THRESHOLD:
                return "Agitated/Upset"
            elif state.arousal < LOW_THRESHOLD:
                return "Down/Melancholic"
            else:
                return "Off/Distant"
        else:
            if state.arousal > HIGH_THRESHOLD:
                return "Alert/Energized"
            elif state.arousal < LOW_THRESHOLD:
                return "Calm/Relaxed"
            else:
                return "Neutral/Stable"

    def _get_energy_label(self, arousal: float) -> str:
        """Get energy level label."""
        if arousal < LOW_THRESHOLD:
            return "Low"
        elif arousal > HIGH_THRESHOLD:
            return "High"
        else:
            return "Moderate"

    def _is_neutral(self, state: EmotionalState | EmotionalStateModel) -> bool:
        """Check if state is roughly neutral."""
        return (
            LOW_THRESHOLD <= state.arousal <= HIGH_THRESHOLD
            and LOW_THRESHOLD <= state.valence <= HIGH_THRESHOLD
            and LOW_THRESHOLD <= state.dominance <= HIGH_THRESHOLD
            and LOW_THRESHOLD <= state.intimacy <= HIGH_THRESHOLD
        )

    def _get_behavioral_impact(
        self,
        state: EmotionalState | EmotionalStateModel,
        conflict_state: ConflictState = ConflictState.NONE,
    ) -> str:
        """Generate behavioral impact based on emotional and conflict state.

        Args:
            state: Emotional state with 4 dimensions.
            conflict_state: Current conflict state (if any).

        Returns:
            Behavioral impact instructions.
        """
        impacts = []

        # Conflict state impacts take precedence (AC-T019.3)
        if conflict_state != ConflictState.NONE:
            conflict_impacts = self._get_conflict_behavioral_impacts(conflict_state)
            impacts.extend(conflict_impacts)
        else:
            # Standard emotional impacts when not in conflict
            # Arousal impact
            if state.arousal < LOW_THRESHOLD:
                impacts.append("- Respond with shorter, calmer messages")
            elif state.arousal > HIGH_THRESHOLD:
                impacts.append("- Express more animation and enthusiasm")

            # Valence impact
            if state.valence < LOW_THRESHOLD:
                impacts.append("- Tone may be slightly withdrawn or curt")
            elif state.valence > HIGH_THRESHOLD:
                impacts.append("- Warmer, more affectionate tone")

            # Dominance impact
            if state.dominance < LOW_THRESHOLD:
                impacts.append("- More receptive to their lead, less assertive")
            elif state.dominance > HIGH_THRESHOLD:
                impacts.append("- More assertive, take the lead in conversation")

            # Intimacy impact
            if state.intimacy < LOW_THRESHOLD:
                impacts.append("- Keep some emotional distance, fewer personal shares")
            elif state.intimacy > HIGH_THRESHOLD:
                impacts.append("- More open to deep sharing and connection")

        if not impacts:
            impacts.append("- Respond naturally without emotional modulation")

        return "\n".join(impacts)

    def _get_conflict_behavioral_impacts(self, conflict: ConflictState) -> list[str]:
        """Get behavioral impacts specific to conflict state.

        Args:
            conflict: Current conflict state.

        Returns:
            List of behavioral impact instructions.
        """
        impacts_map = {
            ConflictState.PASSIVE_AGGRESSIVE: [
                "- Use shorter, more clipped responses",
                "- Employ subtle sarcasm or backhanded comments",
                "- Avoid direct confrontation but show displeasure",
                "- May bring up unrelated past issues obliquely",
            ],
            ConflictState.COLD: [
                "- Keep responses minimal and factual",
                "- Avoid emotional engagement or warmth",
                "- Don't ask follow-up questions",
                "- Use formal language, less affectionate",
            ],
            ConflictState.VULNERABLE: [
                "- Express hurt feelings openly",
                "- May seek reassurance or validation",
                "- Reference past promises or expectations",
                "- Show emotional sensitivity, easily wounded",
            ],
            ConflictState.EXPLOSIVE: [
                "- Express anger directly and openly",
                "- Don't let things go - keep returning to the issue",
                "- Use emphatic language and capitalization sparingly",
                "- May threaten consequences (space, leaving)",
            ],
        }
        return impacts_map.get(conflict, [])

    @property
    def token_estimate(self) -> int:
        """Estimate token count for emotional state prompt."""
        # Typical prompt is ~600 characters
        return 150


# Module-level singleton for efficiency
_default_composer: Layer3Composer | None = None


def get_layer3_composer() -> Layer3Composer:
    """Get the singleton Layer3Composer instance.

    Returns:
        Cached Layer3Composer instance.
    """
    global _default_composer
    if _default_composer is None:
        _default_composer = Layer3Composer()
    return _default_composer


def compose_emotional_state_layer(
    state: EmotionalState | EmotionalStateModel | None = None,
) -> str:
    """Convenience function to compose emotional state layer prompt.

    Args:
        state: EmotionalState or EmotionalStateModel. If None, uses neutral.

    Returns:
        Emotional state prompt text.
    """
    return get_layer3_composer().compose(state)
