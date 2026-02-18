"""PsycheState model for structured psyche agent output (Spec 056 T1).

Defines the 8-field PsycheState model that captures Nikita's psychological
disposition. Used as structured output from the psyche agent and stored
as JSONB in the psyche_states table.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PsycheState(BaseModel):
    """Structured psychological state for Nikita.

    Generated daily by the psyche agent batch job and updated
    on-demand by trigger-based analysis (Tier 2/3).

    All fields are validated:
    - Literal types for constrained string fields
    - Float bounded [0, 1] for vulnerability_level
    - Max 3 items for topic lists
    - Non-empty strings for guidance/monologue
    """

    attachment_activation: Literal["secure", "anxious", "avoidant", "disorganized"] = Field(
        description="Current attachment style activation"
    )
    defense_mode: Literal["open", "guarded", "deflecting", "withdrawing"] = Field(
        description="Active defense mechanism pattern"
    )
    behavioral_guidance: str = Field(
        min_length=1,
        max_length=500,
        description="Free-text guidance for conversation agent (~50 words)",
    )
    internal_monologue: str = Field(
        min_length=1,
        max_length=300,
        description="Nikita's inner thoughts (~30 words)",
    )
    vulnerability_level: float = Field(
        ge=0.0,
        le=1.0,
        description="0.0 (guarded) to 1.0 (fully open)",
    )
    emotional_tone: Literal["playful", "serious", "warm", "distant", "volatile"] = Field(
        description="Current emotional tone for conversation"
    )
    topics_to_encourage: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Max 3 topics to lean into",
    )
    topics_to_avoid: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Max 3 topics to avoid",
    )

    @field_validator("topics_to_encourage", "topics_to_avoid")
    @classmethod
    def validate_topic_items_non_empty(cls, v: list[str]) -> list[str]:
        """Ensure each topic string is non-empty."""
        return [item for item in v if item.strip()]

    @classmethod
    def default(cls) -> PsycheState:
        """Return safe default state for first-time users.

        AC-2.4: Default state exists for users with no psyche data yet.
        """
        return cls(
            attachment_activation="secure",
            defense_mode="open",
            behavioral_guidance="Be naturally warm and curious. Follow the player's lead.",
            internal_monologue="New connection, keeping an open mind.",
            vulnerability_level=0.3,
            emotional_tone="warm",
            topics_to_encourage=["getting to know each other"],
            topics_to_avoid=[],
        )
