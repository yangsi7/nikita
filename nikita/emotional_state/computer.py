"""State Computer for Emotional State Engine (Spec 023, T005-T009).

Computes emotional state from multiple sources:
- Base state (time of day, day of week)
- Life event deltas (from LifeSimulator 022)
- Conversation deltas (LLM-detected tone)
- Relationship modifiers (chapter, score)

AC-T005: Base state calculation with time/day factors
AC-T006: Life event delta application
AC-T007: Conversation delta detection (LLM)
AC-T008: Relationship modifier application
AC-T009: StateComputer.compute() orchestration
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from nikita.emotional_state.models import (
    ConflictState,
    EmotionalStateModel,
)

logger = logging.getLogger(__name__)


class TimeOfDay(str, Enum):
    """Time periods affecting base mood."""

    EARLY_MORNING = "early_morning"  # 5-8
    MORNING = "morning"  # 8-12
    AFTERNOON = "afternoon"  # 12-17
    EVENING = "evening"  # 17-21
    NIGHT = "night"  # 21-24
    LATE_NIGHT = "late_night"  # 0-5


class DayOfWeek(str, Enum):
    """Day categories affecting base mood."""

    WEEKDAY = "weekday"
    FRIDAY = "friday"  # Special: anticipation
    WEEKEND = "weekend"


class ConversationTone(str, Enum):
    """Detected conversation tones from LLM analysis."""

    SUPPORTIVE = "supportive"  # Increases valence, intimacy
    DISMISSIVE = "dismissive"  # Decreases valence, intimacy
    ROMANTIC = "romantic"  # Increases intimacy, valence
    COLD = "cold"  # Decreases intimacy, valence
    PLAYFUL = "playful"  # Increases arousal, valence
    ANXIOUS = "anxious"  # Increases arousal, decreases dominance
    APOLOGETIC = "apologetic"  # Affects conflict recovery
    NEUTRAL = "neutral"  # Minimal effect


class LifeEventImpact(BaseModel):
    """Emotional impact from a life event."""

    arousal_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    valence_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    dominance_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    intimacy_delta: float = Field(default=0.0, ge=-1.0, le=1.0)


class StateComputer:
    """Computes emotional state from multiple sources.

    The emotional state formula is:
    final_state = base_state + life_deltas + conv_deltas + relationship_mod

    All dimensions are clamped to 0.0-1.0.
    """

    # Time-of-day base adjustments (relative to 0.5)
    TIME_ADJUSTMENTS: dict[TimeOfDay, dict[str, float]] = {
        TimeOfDay.EARLY_MORNING: {"arousal": -0.1, "valence": -0.05},
        TimeOfDay.MORNING: {"arousal": 0.15, "valence": 0.1},
        TimeOfDay.AFTERNOON: {"arousal": 0.05, "valence": 0.0},
        TimeOfDay.EVENING: {"arousal": -0.05, "valence": 0.05},
        TimeOfDay.NIGHT: {"arousal": -0.15, "valence": 0.0},
        TimeOfDay.LATE_NIGHT: {"arousal": -0.2, "valence": -0.1},
    }

    # Day-of-week adjustments
    DAY_ADJUSTMENTS: dict[DayOfWeek, dict[str, float]] = {
        DayOfWeek.WEEKDAY: {"valence": 0.0, "dominance": 0.05},
        DayOfWeek.FRIDAY: {"valence": 0.1, "arousal": 0.1},
        DayOfWeek.WEEKEND: {"valence": 0.1, "dominance": -0.05, "arousal": -0.05},
    }

    # Conversation tone to delta mapping
    TONE_DELTAS: dict[ConversationTone, dict[str, float]] = {
        ConversationTone.SUPPORTIVE: {
            "valence": 0.15,
            "intimacy": 0.1,
            "dominance": 0.05,
        },
        ConversationTone.DISMISSIVE: {
            "valence": -0.15,
            "intimacy": -0.1,
            "dominance": -0.1,
        },
        ConversationTone.ROMANTIC: {
            "valence": 0.2,
            "intimacy": 0.2,
            "arousal": 0.1,
        },
        ConversationTone.COLD: {
            "valence": -0.2,
            "intimacy": -0.2,
            "arousal": -0.05,
        },
        ConversationTone.PLAYFUL: {
            "valence": 0.15,
            "arousal": 0.15,
            "intimacy": 0.05,
        },
        ConversationTone.ANXIOUS: {
            "arousal": 0.2,
            "dominance": -0.15,
            "valence": -0.1,
        },
        ConversationTone.APOLOGETIC: {
            "valence": 0.05,
            "intimacy": 0.1,
            "dominance": -0.1,
        },
        ConversationTone.NEUTRAL: {
            "valence": 0.0,
            "arousal": 0.0,
            "dominance": 0.0,
            "intimacy": 0.0,
        },
    }

    # Chapter-based relationship modifiers
    CHAPTER_MODIFIERS: dict[int, dict[str, float]] = {
        1: {"intimacy": 0.0, "dominance": 0.1},  # Early: more guarded
        2: {"intimacy": 0.05, "dominance": 0.05},  # Opening up
        3: {"intimacy": 0.1, "dominance": 0.0},  # Comfortable
        4: {"intimacy": 0.15, "dominance": -0.05},  # Deep connection
        5: {"intimacy": 0.2, "dominance": -0.1},  # Very vulnerable
    }

    def __init__(self) -> None:
        """Initialize StateComputer."""
        pass

    def compute(
        self,
        user_id: UUID,
        current_state: EmotionalStateModel | None = None,
        timestamp: datetime | None = None,
        life_events: list[LifeEventImpact] | None = None,
        conversation_tones: list[ConversationTone] | None = None,
        chapter: int = 1,
        relationship_score: float = 0.5,
    ) -> EmotionalStateModel:
        """Compute emotional state from all sources.

        Formula: base + life_deltas + conv_deltas + relationship_mod

        Args:
            user_id: User ID for the state.
            current_state: Optional existing state to modify.
            timestamp: Time to compute for (defaults to now).
            life_events: List of life event impacts.
            conversation_tones: List of detected conversation tones.
            chapter: Current game chapter (1-5).
            relationship_score: Current relationship score (0.0-1.0).

        Returns:
            Computed EmotionalStateModel.
        """
        ts = timestamp or datetime.now(timezone.utc)

        # Start with base state
        base = self._compute_base_state(ts)

        # Start from current state or base
        if current_state:
            state = EmotionalStateModel(
                user_id=user_id,
                arousal=current_state.arousal,
                valence=current_state.valence,
                dominance=current_state.dominance,
                intimacy=current_state.intimacy,
                conflict_state=current_state.conflict_state,
                conflict_started_at=current_state.conflict_started_at,
                conflict_trigger=current_state.conflict_trigger,
                ignored_message_count=current_state.ignored_message_count,
            )
        else:
            state = EmotionalStateModel(
                user_id=user_id,
                arousal=base["arousal"],
                valence=base["valence"],
                dominance=base["dominance"],
                intimacy=base["intimacy"],
            )

        # Apply life event deltas
        if life_events:
            life_deltas = self._apply_life_event_deltas(life_events)
            state = state.apply_deltas(**life_deltas)

        # Apply conversation deltas
        if conversation_tones:
            conv_deltas = self._apply_conversation_deltas(conversation_tones)
            state = state.apply_deltas(**conv_deltas)

        # Apply relationship modifier
        rel_mod = self._apply_relationship_modifier(chapter, relationship_score)
        state = state.apply_deltas(**rel_mod)

        logger.debug(
            f"Computed state for {user_id}: "
            f"A={state.arousal:.2f} V={state.valence:.2f} "
            f"D={state.dominance:.2f} I={state.intimacy:.2f}"
        )

        return state

    def _compute_base_state(self, timestamp: datetime) -> dict[str, float]:
        """Compute base emotional state from time factors.

        AC-T005.1: _compute_base_state() method
        AC-T005.2: Time-of-day affects arousal (morning high, night low)
        AC-T005.3: Day-of-week affects valence (weekend slightly higher)

        Args:
            timestamp: Current timestamp.

        Returns:
            Dict with arousal, valence, dominance, intimacy values.
        """
        # Start at neutral
        state = {
            "arousal": 0.5,
            "valence": 0.5,
            "dominance": 0.5,
            "intimacy": 0.5,
        }

        # Determine time of day
        hour = timestamp.hour
        if 0 <= hour < 5:
            time_period = TimeOfDay.LATE_NIGHT
        elif 5 <= hour < 8:
            time_period = TimeOfDay.EARLY_MORNING
        elif 8 <= hour < 12:
            time_period = TimeOfDay.MORNING
        elif 12 <= hour < 17:
            time_period = TimeOfDay.AFTERNOON
        elif 17 <= hour < 21:
            time_period = TimeOfDay.EVENING
        else:
            time_period = TimeOfDay.NIGHT

        # Apply time adjustments
        time_adj = self.TIME_ADJUSTMENTS.get(time_period, {})
        for dim, delta in time_adj.items():
            state[dim] = self._clamp(state[dim] + delta)

        # Determine day category
        weekday = timestamp.weekday()
        if weekday == 4:  # Friday
            day_cat = DayOfWeek.FRIDAY
        elif weekday >= 5:  # Sat, Sun
            day_cat = DayOfWeek.WEEKEND
        else:
            day_cat = DayOfWeek.WEEKDAY

        # Apply day adjustments
        day_adj = self.DAY_ADJUSTMENTS.get(day_cat, {})
        for dim, delta in day_adj.items():
            state[dim] = self._clamp(state[dim] + delta)

        return state

    def _apply_life_event_deltas(
        self, events: list[LifeEventImpact]
    ) -> dict[str, float]:
        """Apply deltas from life events.

        AC-T006.1: _apply_life_event_deltas() method
        AC-T006.2: Receives events from LifeSimulator (022)
        AC-T006.3: Maps event emotional_impact to state deltas

        Args:
            events: List of life event impacts.

        Returns:
            Combined deltas for all dimensions.
        """
        total = {
            "arousal_delta": 0.0,
            "valence_delta": 0.0,
            "dominance_delta": 0.0,
            "intimacy_delta": 0.0,
        }

        for event in events:
            total["arousal_delta"] += event.arousal_delta
            total["valence_delta"] += event.valence_delta
            total["dominance_delta"] += event.dominance_delta
            total["intimacy_delta"] += event.intimacy_delta

        # Clamp total deltas to prevent extreme swings
        for key in total:
            total[key] = max(-0.3, min(0.3, total[key]))

        return total

    def _apply_conversation_deltas(
        self, tones: list[ConversationTone]
    ) -> dict[str, float]:
        """Apply deltas from detected conversation tones.

        AC-T007.3: Maps detected tone to dimension deltas
        AC-T007.4: Handles supportive, dismissive, romantic, cold, etc.

        Args:
            tones: List of detected conversation tones.

        Returns:
            Combined deltas for all dimensions.
        """
        total = {
            "arousal_delta": 0.0,
            "valence_delta": 0.0,
            "dominance_delta": 0.0,
            "intimacy_delta": 0.0,
        }

        for tone in tones:
            tone_deltas = self.TONE_DELTAS.get(tone, {})
            for dim, delta in tone_deltas.items():
                key = f"{dim}_delta"
                if key in total:
                    total[key] += delta

        # Clamp to prevent extreme swings
        for key in total:
            total[key] = max(-0.4, min(0.4, total[key]))

        return total

    def _apply_relationship_modifier(
        self, chapter: int, relationship_score: float
    ) -> dict[str, float]:
        """Apply relationship-based modifiers.

        AC-T008.1: _apply_relationship_modifier() method
        AC-T008.2: Higher chapters = higher baseline intimacy
        AC-T008.3: Relationship score affects valence baseline

        Args:
            chapter: Current game chapter (1-5).
            relationship_score: Current relationship score (0.0-1.0).

        Returns:
            Modifier deltas for dimensions.
        """
        mods = {
            "arousal_delta": 0.0,
            "valence_delta": 0.0,
            "dominance_delta": 0.0,
            "intimacy_delta": 0.0,
        }

        # Chapter-based intimacy/dominance modifier
        chapter_mod = self.CHAPTER_MODIFIERS.get(chapter, {})
        for dim, delta in chapter_mod.items():
            key = f"{dim}_delta"
            if key in mods:
                mods[key] += delta

        # Relationship score affects valence
        # Score 0.5 = no effect, higher = positive, lower = negative
        valence_mod = (relationship_score - 0.5) * 0.2
        mods["valence_delta"] += valence_mod

        return mods

    @staticmethod
    def _clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Clamp value to range."""
        return max(min_val, min(max_val, value))


# Singleton
_computer_instance: StateComputer | None = None


def get_state_computer() -> StateComputer:
    """Get singleton StateComputer instance."""
    global _computer_instance
    if _computer_instance is None:
        _computer_instance = StateComputer()
    return _computer_instance
