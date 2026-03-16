"""Opening template data model.

Each Opening is a chess-like template that defines how Nikita approaches
the first voice interaction after onboarding. Openings are matched to
users based on their onboarding profile (darkness level, scene, etc.).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Opening(BaseModel):
    """Chess-like opening template for first voice interaction."""

    id: str = Field(description="Unique identifier, e.g. 'warm_intro'")
    name: str = Field(description="Human-readable name, e.g. 'The Warm Introduction'")

    # Matching criteria — how this opening is selected for a user
    darkness_range: tuple[int, int] = Field(
        default=(1, 5),
        description="Drug tolerance range this opening matches (inclusive)",
    )
    scene_tags: list[str] = Field(
        default_factory=list,
        description="Scene preferences this opening is tuned for. Empty = any.",
    )
    life_stage_tags: list[str] = Field(
        default_factory=list,
        description="Life stage tags this opening is tuned for. Empty = any.",
    )

    # Voice call configuration
    first_message: str = Field(
        description="Template string with {name}, {city}, {interest} placeholders"
    )
    system_prompt_addendum: str = Field(
        description="Injected into base Nikita system prompt for this call"
    )
    mood: str = Field(
        default="neutral",
        description="NikitaMood value for TTS settings (neutral, flirty, distant, etc.)",
    )
    tts_override: dict | None = Field(
        default=None,
        description="Optional TTS setting overrides (stability, similarity_boost, speed)",
    )

    # Conversation goals (meta-instructions, NOT rigid scripts)
    goals: list[str] = Field(
        default_factory=list,
        description="What Nikita should accomplish during the call",
    )
    forbidden: list[str] = Field(
        default_factory=list,
        description="What Nikita must NOT do during the call",
    )
    max_duration_hint: str = Field(
        default="5min",
        description="Suggested call duration hint for the system prompt",
    )

    # A/B testing
    weight: float = Field(
        default=1.0,
        description="Selection weight for weighted random among matching openings",
    )

    # Fallback flag
    is_fallback: bool = Field(
        default=False,
        description="If True, this opening is used when no others match",
    )

    def format_first_message(
        self,
        name: str = "there",
        city: str = "your city",
        interest: str = "life",
    ) -> str:
        """Interpolate placeholders in first_message."""
        return self.first_message.format(
            name=name,
            city=city,
            interest=interest,
        )
