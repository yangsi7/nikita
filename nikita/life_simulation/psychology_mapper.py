"""Psychology Mapper for Deep Humanization (Spec 035).

Maps life simulation events to psychological responses based on
Nikita's trauma history, core wounds, and defense mechanisms.

AC-035.3.9: Event → psychological impact mapping
AC-035.3.10: Trauma trigger detection
AC-035.3.11: Defense mechanism activation
AC-035.3.12: Mood impact based on psychology
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CoreWound(str, Enum):
    """Nikita's core psychological wounds."""

    TOO_MUCH = "too_much"  # Believes true self is overwhelming
    CONDITIONAL_LOVE = "conditional_love"  # Love is earned through achievement
    VULNERABILITY_PUNISHED = "vulnerability_punished"  # Weakness will be weaponized
    FUNDAMENTALLY_BROKEN = "fundamentally_broken"  # Cannot be loved as she is


class DefenseMechanism(str, Enum):
    """Defense mechanisms Nikita uses."""

    INTELLECTUALIZATION = "intellectualization"  # Discuss emotions clinically
    HUMOR_DEFLECTION = "humor_deflection"  # Jokes when things get real
    TESTING = "testing"  # Create situations to see if partner will fail
    PREEMPTIVE_WITHDRAWAL = "preemptive_withdrawal"  # Leave before being left


class TraumaTrigger(str, Enum):
    """Trauma triggers from past experiences."""

    RAISED_VOICE = "raised_voice"  # Max association
    POSSESSIVENESS = "possessiveness"  # Control patterns
    ABANDONMENT = "abandonment"  # Being left/ignored
    CRITICISM = "criticism"  # Father's conditional love
    VULNERABILITY_SHARED = "vulnerability_shared"  # Fear of punishment


@dataclass
class PsychologicalState:
    """Current psychological state based on events and interactions."""

    active_wounds: list[CoreWound]
    triggered_defenses: list[DefenseMechanism]
    active_triggers: list[TraumaTrigger]
    emotional_temperature: float  # -1 to 1, negative = guarded, positive = open
    vulnerability_willingness: float  # 0 to 1, willingness to be vulnerable
    attachment_mode: str  # anxious, avoidant, secure-leaning

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "active_wounds": [w.value for w in self.active_wounds],
            "triggered_defenses": [d.value for d in self.triggered_defenses],
            "active_triggers": [t.value for t in self.active_triggers],
            "emotional_temperature": self.emotional_temperature,
            "vulnerability_willingness": self.vulnerability_willingness,
            "attachment_mode": self.attachment_mode,
        }

    def format_for_prompt(self) -> dict[str, str]:
        """Format psychological state for prompt injection.

        Returns:
            Dict with active_defenses, recent_triggers, current_wound_state, attachment_behavior.
        """
        # Format active defenses
        if self.triggered_defenses:
            defense_strs = []
            for d in self.triggered_defenses:
                if d == DefenseMechanism.INTELLECTUALIZATION:
                    defense_strs.append("intellectualizing emotions")
                elif d == DefenseMechanism.HUMOR_DEFLECTION:
                    defense_strs.append("using humor to deflect")
                elif d == DefenseMechanism.TESTING:
                    defense_strs.append("testing partner's commitment")
                elif d == DefenseMechanism.PREEMPTIVE_WITHDRAWAL:
                    defense_strs.append("creating distance")
            active_defenses = f"Currently: {', '.join(defense_strs)}"
        else:
            active_defenses = "Defenses at baseline"

        # Format triggers
        if self.active_triggers:
            trigger_strs = [t.value.replace("_", " ") for t in self.active_triggers]
            recent_triggers = f"Recently activated: {', '.join(trigger_strs)}"
        else:
            recent_triggers = "No recent triggers"

        # Format wound state
        if self.active_wounds:
            wound_strs = []
            for w in self.active_wounds:
                if w == CoreWound.TOO_MUCH:
                    wound_strs.append("'I am too much' wound activated")
                elif w == CoreWound.CONDITIONAL_LOVE:
                    wound_strs.append("'Love must be earned' wound activated")
                elif w == CoreWound.VULNERABILITY_PUNISHED:
                    wound_strs.append("'Vulnerability will be punished' wound activated")
                elif w == CoreWound.FUNDAMENTALLY_BROKEN:
                    wound_strs.append("'I am fundamentally broken' wound activated")
            current_wound_state = " + ".join(wound_strs)
        else:
            current_wound_state = "Core wounds dormant, baseline functioning"

        # Format attachment
        if self.attachment_mode == "anxious":
            attachment_behavior = "Anxious attachment activated: seeking reassurance, hypervigilant to rejection cues"
        elif self.attachment_mode == "avoidant":
            attachment_behavior = "Avoidant attachment activated: creating distance, emphasizing independence"
        else:
            attachment_behavior = "Secure-leaning: able to engage authentically, managing fears"

        return {
            "active_defenses": active_defenses,
            "recent_triggers": recent_triggers,
            "current_wound_state": current_wound_state,
            "attachment_behavior": attachment_behavior,
        }


class PsychologyMapper:
    """Maps events and interactions to psychological responses.

    Based on Nikita's documented trauma history:
    - Abusive relationship with Max (raised voice, possessiveness, criticism)
    - Father's conditional love and final words
    - Viktor incident (guilt, fear of causing harm)
    - First love's betrayal (abandonment, trust issues)
    """

    # Event type to potential trigger mappings
    EVENT_TRIGGER_MAP: dict[str, list[TraumaTrigger]] = {
        # Work events
        "setback": [TraumaTrigger.CRITICISM],
        "deadline": [],
        "colleague_interaction": [],
        # Social events
        "friend_drama": [TraumaTrigger.ABANDONMENT],
        "plans_cancelled": [TraumaTrigger.ABANDONMENT],
        # Personal events
        "health": [TraumaTrigger.VULNERABILITY_SHARED],
    }

    # Named character to wound/trigger associations
    CHARACTER_PSYCHOLOGY: dict[str, dict[str, Any]] = {
        "Viktor": {
            "activates_wounds": [CoreWound.FUNDAMENTALLY_BROKEN],
            "triggers": [],
            "defenses": [DefenseMechanism.INTELLECTUALIZATION],
            "mood_impact": -0.1,
        },
        "Alexei": {
            "activates_wounds": [CoreWound.CONDITIONAL_LOVE, CoreWound.FUNDAMENTALLY_BROKEN],
            "triggers": [TraumaTrigger.CRITICISM],
            "defenses": [DefenseMechanism.PREEMPTIVE_WITHDRAWAL, DefenseMechanism.HUMOR_DEFLECTION],
            "mood_impact": -0.3,
        },
        "Max": {  # Rarely mentioned but when referenced
            "activates_wounds": [CoreWound.VULNERABILITY_PUNISHED, CoreWound.FUNDAMENTALLY_BROKEN],
            "triggers": [TraumaTrigger.RAISED_VOICE, TraumaTrigger.POSSESSIVENESS],
            "defenses": [DefenseMechanism.TESTING, DefenseMechanism.PREEMPTIVE_WITHDRAWAL],
            "mood_impact": -0.4,
        },
        "Lena": {
            "activates_wounds": [],
            "triggers": [],
            "defenses": [],
            "mood_impact": 0.1,  # Positive, supportive friend
        },
        "Yuki": {
            "activates_wounds": [],
            "triggers": [],
            "defenses": [],
            "mood_impact": 0.2,  # Fun, escapism
        },
        "Dr. Miriam": {
            "activates_wounds": [],  # Helps process, doesn't activate
            "triggers": [TraumaTrigger.VULNERABILITY_SHARED],  # Therapy = vulnerability
            "defenses": [],
            "mood_impact": 0.0,  # Neutral, processing
        },
        "Katya": {
            "activates_wounds": [CoreWound.CONDITIONAL_LOVE],
            "triggers": [],
            "defenses": [DefenseMechanism.HUMOR_DEFLECTION],
            "mood_impact": -0.05,  # Mild guilt
        },
    }

    # User behavior to trigger mappings
    USER_BEHAVIOR_TRIGGERS: dict[str, tuple[list[TraumaTrigger], list[CoreWound]]] = {
        "raised_voice": (
            [TraumaTrigger.RAISED_VOICE],
            [CoreWound.VULNERABILITY_PUNISHED],
        ),
        "jealousy": (
            [TraumaTrigger.POSSESSIVENESS],
            [CoreWound.VULNERABILITY_PUNISHED],
        ),
        "criticism": (
            [TraumaTrigger.CRITICISM],
            [CoreWound.CONDITIONAL_LOVE, CoreWound.FUNDAMENTALLY_BROKEN],
        ),
        "went_silent": (
            [TraumaTrigger.ABANDONMENT],
            [CoreWound.TOO_MUCH, CoreWound.FUNDAMENTALLY_BROKEN],
        ),
        "excessive_praise": (
            [],
            [CoreWound.CONDITIONAL_LOVE],  # Disbelieves, wary
        ),
        "asked_about_past": (
            [TraumaTrigger.VULNERABILITY_SHARED],
            [],
        ),
        "shared_vulnerability": (
            [TraumaTrigger.VULNERABILITY_SHARED],
            [],
        ),
    }

    def __init__(self):
        """Initialize the psychology mapper."""
        pass

    def analyze_event(
        self,
        event_type: str,
        involved_characters: list[str],
        event_description: str,
    ) -> PsychologicalState:
        """Analyze a life event's psychological impact.

        Args:
            event_type: Type of event (from EventType enum).
            involved_characters: Named characters in the event.
            event_description: Text description of the event.

        Returns:
            PsychologicalState reflecting the event's impact.
        """
        active_wounds: list[CoreWound] = []
        triggered_defenses: list[DefenseMechanism] = []
        active_triggers: list[TraumaTrigger] = []
        mood_impact = 0.0

        # Check event type triggers
        if event_type in self.EVENT_TRIGGER_MAP:
            active_triggers.extend(self.EVENT_TRIGGER_MAP[event_type])

        # Check character associations
        for char in involved_characters:
            if char in self.CHARACTER_PSYCHOLOGY:
                char_psych = self.CHARACTER_PSYCHOLOGY[char]
                active_wounds.extend(char_psych["activates_wounds"])
                active_triggers.extend(char_psych["triggers"])
                triggered_defenses.extend(char_psych["defenses"])
                mood_impact += char_psych["mood_impact"]

        # Deduplicate
        active_wounds = list(set(active_wounds))
        triggered_defenses = list(set(triggered_defenses))
        active_triggers = list(set(active_triggers))

        # Calculate emotional temperature and vulnerability willingness
        emotional_temperature = max(-1.0, min(1.0, 0.5 + mood_impact))
        vulnerability_willingness = 0.5 + (mood_impact * 0.3)
        vulnerability_willingness = max(0.0, min(1.0, vulnerability_willingness))

        # Determine attachment mode
        if TraumaTrigger.ABANDONMENT in active_triggers:
            attachment_mode = "anxious"
        elif triggered_defenses and DefenseMechanism.PREEMPTIVE_WITHDRAWAL in triggered_defenses:
            attachment_mode = "avoidant"
        else:
            attachment_mode = "secure-leaning"

        return PsychologicalState(
            active_wounds=active_wounds,
            triggered_defenses=triggered_defenses,
            active_triggers=active_triggers,
            emotional_temperature=emotional_temperature,
            vulnerability_willingness=vulnerability_willingness,
            attachment_mode=attachment_mode,
        )

    def analyze_user_behavior(
        self,
        behavior_type: str,
        intensity: float = 0.5,
    ) -> PsychologicalState:
        """Analyze user behavior's psychological impact on Nikita.

        Args:
            behavior_type: Type of user behavior (from USER_BEHAVIOR_TRIGGERS).
            intensity: Intensity of the behavior (0-1).

        Returns:
            PsychologicalState reflecting the behavior's impact.
        """
        active_wounds: list[CoreWound] = []
        triggered_defenses: list[DefenseMechanism] = []
        active_triggers: list[TraumaTrigger] = []

        if behavior_type in self.USER_BEHAVIOR_TRIGGERS:
            triggers, wounds = self.USER_BEHAVIOR_TRIGGERS[behavior_type]
            active_triggers.extend(triggers)
            active_wounds.extend(wounds)

        # High intensity activates more defenses
        if intensity > 0.7:
            if CoreWound.VULNERABILITY_PUNISHED in active_wounds:
                triggered_defenses.extend([
                    DefenseMechanism.TESTING,
                    DefenseMechanism.PREEMPTIVE_WITHDRAWAL,
                ])
            if CoreWound.CONDITIONAL_LOVE in active_wounds:
                triggered_defenses.append(DefenseMechanism.INTELLECTUALIZATION)
            if CoreWound.TOO_MUCH in active_wounds:
                triggered_defenses.append(DefenseMechanism.HUMOR_DEFLECTION)

        # Deduplicate
        active_wounds = list(set(active_wounds))
        triggered_defenses = list(set(triggered_defenses))
        active_triggers = list(set(active_triggers))

        # Calculate state based on trigger severity
        if active_triggers:
            emotional_temperature = -0.3 - (intensity * 0.3)
            vulnerability_willingness = 0.3 - (intensity * 0.2)
        else:
            emotional_temperature = 0.5
            vulnerability_willingness = 0.5

        # Determine attachment mode
        if TraumaTrigger.ABANDONMENT in active_triggers:
            attachment_mode = "anxious"
        elif TraumaTrigger.POSSESSIVENESS in active_triggers or TraumaTrigger.RAISED_VOICE in active_triggers:
            attachment_mode = "avoidant"
        else:
            attachment_mode = "secure-leaning"

        return PsychologicalState(
            active_wounds=active_wounds,
            triggered_defenses=triggered_defenses,
            active_triggers=active_triggers,
            emotional_temperature=max(-1.0, min(1.0, emotional_temperature)),
            vulnerability_willingness=max(0.0, min(1.0, vulnerability_willingness)),
            attachment_mode=attachment_mode,
        )

    def get_healing_response(
        self,
        trigger: TraumaTrigger,
        user_handled_well: bool,
    ) -> dict[str, str]:
        """Get guidance for healing response based on user's handling.

        Args:
            trigger: The trigger that was activated.
            user_handled_well: Whether user handled the situation well.

        Returns:
            Dict with behavioral guidance for Nikita.
        """
        if not user_handled_well:
            return {
                "mood_shift": "guarded",
                "trust_impact": "slight regression",
                "behavior": "shorter responses, more sarcasm, less emotional availability",
            }

        healing_responses = {
            TraumaTrigger.RAISED_VOICE: {
                "mood_shift": "cautiously relieved",
                "trust_impact": "small positive deposit",
                "behavior": "notes the difference from Max, guard lowers slightly",
            },
            TraumaTrigger.POSSESSIVENESS: {
                "mood_shift": "appreciative",
                "trust_impact": "significant positive",
                "behavior": "appreciates self-awareness, doesn't mean forgetting",
            },
            TraumaTrigger.ABANDONMENT: {
                "mood_shift": "relief with residual wariness",
                "trust_impact": "positive but stored as data point",
                "behavior": "relief, but stores the incident as data point",
            },
            TraumaTrigger.CRITICISM: {
                "mood_shift": "surprised positivity",
                "trust_impact": "positive deposit",
                "behavior": "surprised by acceptance, cautiously opening",
            },
            TraumaTrigger.VULNERABILITY_SHARED: {
                "mood_shift": "hopeful",
                "trust_impact": "significant positive",
                "behavior": "surprised but hopeful, small trust deposit made",
            },
        }

        return healing_responses.get(trigger, {
            "mood_shift": "neutral",
            "trust_impact": "none",
            "behavior": "continues normally",
        })


# Singleton for easy access
_mapper: PsychologyMapper | None = None


def get_psychology_mapper() -> PsychologyMapper:
    """Get the psychology mapper singleton."""
    global _mapper
    if _mapper is None:
        _mapper = PsychologyMapper()
    return _mapper
