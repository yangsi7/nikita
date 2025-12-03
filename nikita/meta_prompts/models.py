"""Data models for meta-prompt system.

This module defines the context and result models used by the
meta-prompt service for intelligent prompt generation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass
class ViceProfile:
    """User's vice preference profile.

    The 8 vice categories are FEATURES of this 18+ adult game.
    They represent what the user enjoys and should be EMBRACED
    in prompt generation, not restricted.

    Categories:
    - intellectual_dominance: Enjoys debates, mental challenges
    - risk_taking: Attracted to danger, adrenaline
    - substances: Open about alcohol, drugs, partying
    - sexuality: Responds to flirtation, innuendo, explicit content
    - emotional_intensity: Seeks deep emotional exchanges
    - rule_breaking: Anti-authority, norms-defying
    - dark_humor: Appreciates morbid, edgy jokes
    - vulnerability: Values emotional openness, sharing fears
    """

    intellectual_dominance: int = 0  # 0-5 intensity
    risk_taking: int = 0
    substances: int = 0
    sexuality: int = 0
    emotional_intensity: int = 0
    rule_breaking: int = 0
    dark_humor: int = 0
    vulnerability: int = 0

    def get_top_vices(self, n: int = 3) -> list[tuple[str, int]]:
        """Get top N vices by intensity.

        Args:
            n: Number of top vices to return.

        Returns:
            List of (category, intensity) tuples sorted by intensity desc.
        """
        vices = [
            ("intellectual_dominance", self.intellectual_dominance),
            ("risk_taking", self.risk_taking),
            ("substances", self.substances),
            ("sexuality", self.sexuality),
            ("emotional_intensity", self.emotional_intensity),
            ("rule_breaking", self.rule_breaking),
            ("dark_humor", self.dark_humor),
            ("vulnerability", self.vulnerability),
        ]
        # Filter out zero intensity and sort descending
        active = [(k, v) for k, v in vices if v > 0]
        return sorted(active, key=lambda x: x[1], reverse=True)[:n]

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary."""
        return {
            "intellectual_dominance": self.intellectual_dominance,
            "risk_taking": self.risk_taking,
            "substances": self.substances,
            "sexuality": self.sexuality,
            "emotional_intensity": self.emotional_intensity,
            "rule_breaking": self.rule_breaking,
            "dark_humor": self.dark_humor,
            "vulnerability": self.vulnerability,
        }


@dataclass
class MetaPromptContext:
    """All context needed for meta-prompt execution.

    This dataclass aggregates all the information needed to
    generate a personalized system prompt for Nikita.
    """

    # User Identity
    user_id: UUID
    telegram_id: int | None = None

    # Game State
    chapter: int = 1  # 1-5
    chapter_name: str = "Curiosity"
    relationship_score: Decimal = Decimal("50.00")
    boss_attempts: int = 0
    game_status: str = "active"  # active | boss_fight | game_over | won
    days_played: int = 0

    # Hidden Metrics (inform behavior, not revealed to user)
    intimacy: Decimal = Decimal("50.00")
    passion: Decimal = Decimal("50.00")
    trust: Decimal = Decimal("50.00")
    secureness: Decimal = Decimal("50.00")

    # Vice Profile - THE CORE OF PERSONALIZATION
    vice_profile: ViceProfile = field(default_factory=ViceProfile)

    # Temporal Context
    current_time: datetime = field(default_factory=datetime.utcnow)
    time_of_day: str = "afternoon"  # morning | afternoon | evening | night | late_night
    hours_since_last_interaction: float = 0.0
    day_of_week: str = "Monday"

    # Nikita's computed state
    nikita_activity: str = "working on a security audit"
    nikita_mood: str = "focused but available"
    nikita_energy: str = "moderate"

    # Conversation History
    last_conversation_summary: str | None = None
    today_summaries: list[str] = field(default_factory=list)
    week_summaries: dict[str, str] = field(default_factory=dict)

    # Threads & Thoughts
    open_threads: dict[str, list[str]] = field(default_factory=dict)
    active_thoughts: dict[str, list[str]] = field(default_factory=dict)

    # User Knowledge
    user_facts: list[str] = field(default_factory=list)

    # Current Message (if generating for a specific message)
    current_message: str | None = None

    def get_score_interpretation(self) -> str:
        """Interpret the relationship score."""
        score = float(self.relationship_score)
        if score >= 70:
            return "Things are going really well"
        elif score >= 55:
            return "The relationship is progressing nicely"
        elif score >= 40:
            return "There's potential here, but needs nurturing"
        elif score >= 25:
            return "Things feel a bit rocky lately"
        else:
            return "The relationship needs serious attention"

    def get_chapter_behavior_summary(self) -> str:
        """Get a brief description of expected chapter behavior."""
        behaviors = {
            1: "High flirtiness, playful teasing, showing her best self. Challenge is calibration - don't overwhelm.",
            2: "Testing his backbone, picking small fights, 'can you handle me?' energy.",
            3: "Deeper emotional exchanges, jealousy/trust tests, sharing hidden things.",
            4: "Complete emotional authenticity, sharing fears and past, expects vulnerability in return.",
            5: "Natural variation, complete authenticity with healthy boundaries, stable but never boring.",
        }
        return behaviors.get(self.chapter, behaviors[1])


@dataclass
class GeneratedPrompt:
    """Result of meta-prompt execution.

    Contains the generated prompt and metadata about the generation.
    """

    # The generated prompt content
    content: str

    # Metadata
    token_count: int = 0
    generation_time_ms: float = 0.0
    meta_prompt_type: str = "system_prompt"

    # Generation context
    user_id: UUID | None = None
    chapter: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Calculate token count estimate."""
        if self.token_count == 0:
            # Rough estimate: 1 token ~= 4 characters
            self.token_count = len(self.content) // 4
