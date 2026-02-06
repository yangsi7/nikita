"""Context package models for Hierarchical Prompt Composition (Spec 021).

This module defines the ContextPackage Pydantic model that stores
pre-computed context for fast injection at conversation start.

The package is created during post-processing after each conversation
and loaded at the start of the next conversation (<50ms target).
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EmotionalState(BaseModel):
    """4-dimensional emotional state for Nikita.

    Based on the PAD (Pleasure-Arousal-Dominance) model with added
    intimacy dimension for relationship context.
    """

    arousal: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Energy level: 0.0 (tired/calm) to 1.0 (energetic/excited)",
    )
    valence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Mood: 0.0 (sad/negative) to 1.0 (happy/positive)",
    )
    dominance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Control: 0.0 (submissive) to 1.0 (dominant/assertive)",
    )
    intimacy: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Openness: 0.0 (guarded) to 1.0 (vulnerable/open)",
    )

    def to_description(self) -> str:
        """Generate natural language description of emotional state."""
        # Arousal
        if self.arousal >= 0.7:
            energy = "energetic and animated"
        elif self.arousal >= 0.4:
            energy = "calm and steady"
        else:
            energy = "tired and subdued"

        # Valence
        if self.valence >= 0.7:
            mood = "happy and upbeat"
        elif self.valence >= 0.4:
            mood = "neutral"
        else:
            mood = "a bit down"

        # Dominance
        if self.dominance >= 0.7:
            stance = "confident and assertive"
        elif self.dominance >= 0.4:
            stance = "balanced"
        else:
            stance = "yielding and accommodating"

        # Intimacy
        if self.intimacy >= 0.7:
            openness = "emotionally open and vulnerable"
        elif self.intimacy >= 0.4:
            openness = "appropriately guarded"
        else:
            openness = "keeping emotional distance"

        return f"Feeling {mood}, {energy}, {stance}, and {openness}."


class ActiveThread(BaseModel):
    """An unresolved conversation thread."""

    topic: str
    status: str = "open"  # open, pending, resolved
    last_mentioned: datetime | None = None
    notes: str | None = None


class ContextPackage(BaseModel):
    """Pre-computed context package for fast conversation startup.

    This package is created during post-processing after each conversation
    and stored for retrieval at the start of the next conversation.

    Target: Load + parse in <50ms for <150ms total injection latency.
    """

    # Identity
    user_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC) + timedelta(hours=24)
    )

    # Pre-computed prompt layers (Layers 2-3)
    chapter_layer: str = Field(
        default="",
        description="Layer 2: Chapter-specific behavioral overlay (~300 tokens)",
    )
    emotional_state_layer: str = Field(
        default="",
        description="Layer 3: Emotional state prompt (~150 tokens)",
    )

    # Situation hints for Layer 4 computation at conversation start
    situation_hints: dict[str, Any] = Field(
        default_factory=dict,
        description="Hints for computing Layer 4 (time patterns, last gap, etc.)",
    )

    # Context data for Layer 5 injection
    user_facts: list[str] = Field(
        default_factory=list,
        description="Top 20 relevant facts about the user",
    )
    relationship_events: list[str] = Field(
        default_factory=list,
        description="Recent 10 relationship events/milestones",
    )
    active_threads: list[ActiveThread] = Field(
        default_factory=list,
        description="Unresolved conversation threads",
    )
    today_summary: str | None = Field(
        default=None,
        description="Summary of today's conversations",
    )
    week_summaries: list[str] = Field(
        default_factory=list,
        description="Summaries from past 7 days",
    )

    # Nikita state metadata
    nikita_mood: EmotionalState = Field(
        default_factory=EmotionalState,
        description="Nikita's current emotional state (4 dimensions)",
    )
    nikita_energy: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Nikita's overall energy level",
    )
    life_events_today: list[str] = Field(
        default_factory=list,
        description="What happened to Nikita today (from life simulation)",
    )

    # Package metadata
    version: str = Field(
        default="1.0.0",
        description="Package schema version for cache invalidation",
    )

    @field_validator("user_facts")
    @classmethod
    def limit_user_facts(cls, v: list[str]) -> list[str]:
        """Ensure user_facts doesn't exceed 20 items."""
        return v[:20] if len(v) > 20 else v

    @field_validator("relationship_events")
    @classmethod
    def limit_relationship_events(cls, v: list[str]) -> list[str]:
        """Ensure relationship_events doesn't exceed 10 items."""
        return v[:10] if len(v) > 10 else v

    @field_validator("week_summaries")
    @classmethod
    def limit_week_summaries(cls, v: list[str]) -> list[str]:
        """Ensure week_summaries doesn't exceed 7 items."""
        return v[:7] if len(v) > 7 else v

    @field_validator("life_events_today")
    @classmethod
    def limit_life_events(cls, v: list[str]) -> list[str]:
        """Ensure life_events_today doesn't exceed 3 items (AC-T015.3)."""
        return v[:3] if len(v) > 3 else v

    def is_expired(self) -> bool:
        """Check if the package has expired."""
        return datetime.now(UTC) > self.expires_at

    def get_token_estimate(self) -> int:
        """Estimate total tokens in this package.

        Rough estimate: 4 characters = 1 token.
        """
        total_chars = (
            len(self.chapter_layer)
            + len(self.emotional_state_layer)
            + sum(len(f) for f in self.user_facts)
            + sum(len(e) for e in self.relationship_events)
            + sum(len(t.topic) + len(t.notes or "") for t in self.active_threads)
            + len(self.today_summary or "")
            + sum(len(s) for s in self.week_summaries)
            + sum(len(e) for e in self.life_events_today)
        )
        return total_chars // 4


class ComposedPrompt(BaseModel):
    """Output of HierarchicalPromptComposer.compose()."""

    full_text: str = Field(description="The complete system prompt")
    total_tokens: int = Field(description="Total token count")
    layer_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="Token count per layer (layer_name -> count)",
    )
    package_version: str | None = Field(
        default=None,
        description="Version of the context package used",
    )
    degraded: bool = Field(
        default=False,
        description="True if fallback/degraded mode was used",
    )
    composition_time_ms: float = Field(
        default=0.0,
        description="Time taken to compose the prompt",
    )


class ProcessingResult(BaseModel):
    """Output of PostProcessingPipeline.process()."""

    user_id: UUID
    conversation_id: UUID
    success: bool = False
    steps_completed: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    package_stored: bool = False

    def add_step(self, step_name: str) -> None:
        """Mark a step as completed."""
        self.steps_completed.append(step_name)

    def add_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error)
        self.success = False
