"""Game enums and type definitions.

This module contains all enumeration types used across the game engine.
Numeric values and behaviors are loaded from YAML configs via ConfigLoader.
"""

from enum import Enum, IntEnum


class Chapter(IntEnum):
    """Game chapter progression (1-5).

    Chapter-specific values (thresholds, decay, behaviors) are loaded
    from chapters.yaml and decay.yaml via ConfigLoader.
    """

    CURIOSITY = 1
    INTRIGUE = 2
    INVESTMENT = 3
    INTIMACY = 4
    ESTABLISHED = 5

    @property
    def name_display(self) -> str:
        """Get display name for the chapter."""
        return self.name.title()


class GameStatus(str, Enum):
    """Game state for a player."""

    ACTIVE = "active"
    BOSS_FIGHT = "boss_fight"
    GAME_OVER = "game_over"
    WON = "won"

    @property
    def is_playable(self) -> bool:
        """Check if the game is still playable."""
        return self in (GameStatus.ACTIVE, GameStatus.BOSS_FIGHT)


class EngagementState(str, Enum):
    """Player engagement states (6-state model from spec 014).

    Each state has an associated scoring multiplier that affects
    relationship score deltas. Healthy states have higher multipliers.
    """

    CALIBRATING = "calibrating"  # Learning player's style (multiplier: 0.9)
    IN_ZONE = "in_zone"          # Sweet spot engagement (multiplier: 1.0)
    DRIFTING = "drifting"        # Off but recoverable (multiplier: 0.8)
    CLINGY = "clingy"            # Messaging too much (multiplier: 0.5)
    DISTANT = "distant"          # Not engaging enough (multiplier: 0.6)
    OUT_OF_ZONE = "out_of_zone"  # Crisis mode (multiplier: 0.2)

    @property
    def is_healthy(self) -> bool:
        """Check if this is a healthy engagement state."""
        return self in (EngagementState.CALIBRATING, EngagementState.IN_ZONE)

    def get_multiplier(self) -> "Decimal":
        """Get the scoring multiplier for this engagement state.

        Returns:
            Decimal multiplier applied to positive score deltas.
        """
        from decimal import Decimal

        multipliers = {
            EngagementState.CALIBRATING: Decimal("0.9"),
            EngagementState.IN_ZONE: Decimal("1.0"),
            EngagementState.DRIFTING: Decimal("0.8"),
            EngagementState.CLINGY: Decimal("0.5"),
            EngagementState.DISTANT: Decimal("0.6"),
            EngagementState.OUT_OF_ZONE: Decimal("0.2"),
        }
        return multipliers[self]


class Mood(str, Enum):
    """Nikita's current mood states."""

    PLAYFUL = "playful"
    FLIRTY = "flirty"
    DISTANT = "distant"
    INTENSE = "intense"
    VULNERABLE = "vulnerable"
    ANNOYED = "annoyed"
    AFFECTIONATE = "affectionate"
    CHALLENGING = "challenging"


class TimeOfDay(str, Enum):
    """Time periods for availability and response patterns."""

    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    SLEEP = "sleep"


class Availability(str, Enum):
    """Nikita's availability status."""

    AVAILABLE = "available"
    BUSY = "busy"
    SLEEPING = "sleeping"
    AWAY = "away"


class ViceCategory(str, Enum):
    """Vice categories for personalization (8 categories from spec 006)."""

    INTELLECTUAL_DOMINANCE = "intellectual_dominance"
    RISK_TAKING = "risk_taking"
    SUBSTANCES = "substances"
    SEXUALITY = "sexuality"
    EMOTIONAL_INTENSITY = "emotional_intensity"
    RULE_BREAKING = "rule_breaking"
    DARK_HUMOR = "dark_humor"
    VULNERABILITY = "vulnerability"


class ViceIntensity(str, Enum):
    """Intensity level for vice preferences."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ResponseQuality(str, Enum):
    """Quality assessment of player responses."""

    EXCELLENT = "excellent"
    GOOD = "good"
    NEUTRAL = "neutral"
    POOR = "poor"
    TERRIBLE = "terrible"


class ConflictType(str, Enum):
    """Types of conflicts Nikita can trigger."""

    INTELLECTUAL = "intellectual"
    EMOTIONAL = "emotional"
    JEALOUSY = "jealousy"
    BOUNDARIES = "boundaries"
    VALUES = "values"


class Metric(str, Enum):
    """Relationship metrics for scoring."""

    INTIMACY = "intimacy"
    PASSION = "passion"
    TRUST = "trust"
    SECURENESS = "secureness"
