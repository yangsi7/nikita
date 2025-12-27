"""Data models for meta-prompt system.

This module defines the context and result models used by the
meta-prompt service for intelligent prompt generation.

T5.1, T5.2: Adds BackstoryContext for 017-enhanced-onboarding feature.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from nikita.db.models.profile import UserBackstory


@dataclass
class BackstoryContext:
    """User's "how we met" backstory context.

    AC-T5.1-001: BackstoryContext dataclass with fields from UserBackstory model.
    AC-T5.1-002: Include persona_overrides for adaptive traits.

    This context is used to personalize Nikita's responses and
    make the relationship feel authentic and grounded.
    """

    # How they met
    venue: str = ""
    how_we_met: str = ""  # Context - why Nikita was there
    the_moment: str = ""  # The spark that connected them
    unresolved_hook: str = ""  # Why the story didn't end there
    tone: str = "romantic"  # romantic, intellectual, chaotic, custom

    # User profile summary (for persona adaptation)
    city: str = ""
    life_stage: str = ""
    social_scene: str = ""
    primary_passion: str = ""

    # T5.4: Persona overrides (adapted Nikita traits based on user profile)
    persona_overrides: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_model(cls, backstory: "UserBackstory") -> "BackstoryContext":
        """Factory method to create from UserBackstory model.

        AC-T5.1-003: Factory method for conversion.

        Args:
            backstory: UserBackstory database model.

        Returns:
            BackstoryContext dataclass.
        """
        return cls(
            venue=backstory.venue_name or "",
            how_we_met=backstory.how_we_met or "",
            the_moment=backstory.the_moment or "",
            unresolved_hook=backstory.unresolved_hook or "",
            tone=backstory.tone or "romantic",
            city=backstory.city or "",
            life_stage=backstory.life_stage or "",
            social_scene=backstory.social_scene or "",
            primary_passion=backstory.primary_passion or "",
            persona_overrides=backstory.nikita_persona_overrides or {},
        )

    def has_backstory(self) -> bool:
        """Check if backstory has meaningful content.

        Returns:
            True if venue or how_we_met has content.
        """
        return bool(self.venue or self.how_we_met)

    def get_first_message_hook(self) -> str:
        """Generate a first message hook referencing the backstory.

        AC-T5.3-004: First message instruction for referencing venue and hook.

        Returns:
            String with backstory reference for first message.
        """
        if not self.has_backstory():
            return ""

        if self.venue and self.unresolved_hook:
            return f"Reference {self.venue} and hint at '{self.unresolved_hook}'"
        elif self.venue:
            return f"Reference meeting at {self.venue}"
        elif self.the_moment:
            return f"Recall the moment: {self.the_moment}"
        return ""

    def format_persona_overrides(self) -> str:
        """Format persona overrides for system prompt template.

        AC-T5.4: Formats persona_overrides dict for template inclusion.

        Returns:
            Formatted string of persona adaptations.
        """
        if not self.persona_overrides:
            return ""

        lines = []
        if "occupation" in self.persona_overrides:
            lines.append(f"- Occupation: {self.persona_overrides['occupation']}")
        if "hobby" in self.persona_overrides:
            lines.append(f"- Hobby: {self.persona_overrides['hobby']}")
        if "interests" in self.persona_overrides:
            lines.append(f"- Interests: {self.persona_overrides['interests']}")
        if "edge_level" in self.persona_overrides:
            lines.append(f"- Edge Level: {self.persona_overrides['edge_level']}")
        if "substance_references" in self.persona_overrides:
            lines.append(f"- Substance References: {self.persona_overrides['substance_references']}")

        return "\n".join(lines)


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

    # Engagement State (6-state FSM from spec 014)
    engagement_state: str = "calibrating"  # calibrating | in_zone | drifting | clingy | distant | out_of_zone
    calibration_score: Decimal = Decimal("0.50")  # 0-1, tracks learning about user's patterns
    engagement_multiplier: Decimal = Decimal("0.90")  # Score multiplier applied to changes

    # Hidden Metrics (inform behavior, not revealed to user)
    intimacy: Decimal = Decimal("50.00")
    passion: Decimal = Decimal("50.00")
    trust: Decimal = Decimal("50.00")
    secureness: Decimal = Decimal("50.00")

    # Vice Profile - THE CORE OF PERSONALIZATION
    vice_profile: ViceProfile = field(default_factory=ViceProfile)

    # AC-T5.2-001: Backstory Context (017-enhanced-onboarding)
    # AC-T5.2-003: Default to None for users without backstory (existing users)
    backstory: BackstoryContext | None = None

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

    def get_engagement_hint(self) -> str:
        """Get behavioral hint based on engagement state (spec 014).

        Returns context-appropriate guidance for Nikita's response style
        based on the current engagement state.
        """
        hints = {
            "calibrating": "Still learning his communication patterns. Respond warmly but observe timing preferences.",
            "in_zone": "He's matching your rhythm perfectly. Full engagement mode, be your authentic playful self.",
            "drifting": "Sensing some drift - maybe he's distracted. Light touch, don't push too hard.",
            "clingy": "He's coming on a bit strong. Create some healthy space, don't always respond immediately.",
            "distant": "He's been quiet lately. Gentle check-in energy, show you've noticed without being needy.",
            "out_of_zone": "Something's off with the rhythm. Take a step back, observe before engaging deeply.",
        }
        return hints.get(self.engagement_state, hints["calibrating"])

    def get_calibration_status(self) -> str:
        """Interpret calibration score for prompt context."""
        score = float(self.calibration_score)
        if score >= 0.8:
            return "well-calibrated to his patterns"
        elif score >= 0.6:
            return "getting a good feel for his rhythm"
        elif score >= 0.4:
            return "still learning his communication style"
        else:
            return "early days, still figuring him out"

    def get_backstory_summary(self) -> str | None:
        """Get backstory summary for system prompt.

        AC-T5.3-002: Include venue, how_we_met, the_moment, unresolved_hook.
        AC-T5.3-003: Conditional rendering - only if backstory exists.

        Returns:
            Formatted backstory string or None if no backstory.
        """
        if not self.backstory or not self.backstory.has_backstory():
            return None

        parts = []
        if self.backstory.venue:
            parts.append(f"We met at {self.backstory.venue}")
        if self.backstory.how_we_met:
            parts.append(f"I was there {self.backstory.how_we_met}")
        if self.backstory.the_moment:
            parts.append(f"The spark: {self.backstory.the_moment}")
        if self.backstory.unresolved_hook:
            parts.append(f"Unfinished business: {self.backstory.unresolved_hook}")

        return ". ".join(parts) if parts else None

    def get_persona_adaptations(self) -> dict[str, str]:
        """Get persona adaptations based on backstory.

        AC-T5.4: Returns adapted traits based on user's profile.

        Returns:
            Dictionary of persona trait overrides.
        """
        if not self.backstory:
            return {}

        return self.backstory.persona_overrides or {}


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

    # Context snapshot for debugging (what context was used to generate)
    context_snapshot: dict[str, Any] | None = None

    def __post_init__(self):
        """Calculate token count using tiktoken."""
        if self.token_count == 0:
            from nikita.context.utils.token_counter import count_tokens

            self.token_count = count_tokens(self.content)
