"""Pipeline models for the unified pipeline (Spec 042 T2.1).

Defines the shared context and result types passed between pipeline stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass
class PipelineContext:
    """Rich shared context for the unified pipeline.

    Extended version of nikita.context.pipeline_context.PipelineContext
    with game state, emotional state, memory, and prompt generation fields.

    Passed through all 9 stages, each stage populates its section.
    """

    # Core identifiers
    conversation_id: UUID
    user_id: UUID
    started_at: datetime
    platform: str  # "text" or "voice"

    # User state (loaded at pipeline start)
    conversation: Any | None = None
    user: Any | None = None
    metrics: dict[str, Decimal] = field(default_factory=dict)
    vices: list[str] = field(default_factory=list)
    engagement_state: str | None = None
    chapter: int = 1
    game_status: str = "active"
    relationship_score: Decimal = field(default_factory=lambda: Decimal("50"))

    # Extraction results (set by ExtractionStage)
    extracted_facts: list[dict[str, Any]] = field(default_factory=list)
    extracted_threads: list[dict[str, Any]] = field(default_factory=list)
    extracted_thoughts: list[dict[str, Any]] = field(default_factory=list)
    extraction_summary: str = ""
    emotional_tone: str = "neutral"

    # Memory update results (set by MemoryUpdateStage)
    facts_stored: int = 0
    facts_deduplicated: int = 0

    # Life sim results (set by LifeSimStage)
    life_events: list[Any] = field(default_factory=list)

    # Emotional state (set by EmotionalStage)
    emotional_state: dict[str, float] = field(default_factory=dict)

    # Game state (set by GameStateStage)
    score_delta: Decimal = field(default_factory=lambda: Decimal("0"))
    score_events: list[str] = field(default_factory=list)
    chapter_changed: bool = False
    decay_applied: bool = False

    # Conflict state (set by ConflictStage)
    active_conflict: bool = False
    conflict_type: str | None = None

    # Touchpoint results (set by TouchpointStage)
    touchpoint_scheduled: bool = False

    # Summary results (set by SummaryStage)
    daily_summary_updated: bool = False

    # Enriched context (set by PromptBuilderStage._enrich_context, Spec 045)
    last_conversation_summary: str | None = None
    today_summaries: str | None = None
    week_summaries: str | None = None
    hours_since_last: float | None = None
    open_threads: list[dict[str, Any]] = field(default_factory=list)
    relationship_episodes: list[str] = field(default_factory=list)
    nikita_events: list[str] = field(default_factory=list)
    nikita_activity: str | None = None
    nikita_mood: str | None = None
    nikita_energy: str | None = None
    time_of_day: str | None = None
    inner_monologue: str | None = None
    active_thoughts: list[str] = field(default_factory=list)
    vulnerability_level: int | None = None
    nikita_daily_events: str | None = None

    # Prompt builder results (set by PromptBuilderStage, Phase 3)
    generated_prompt: str | None = None
    prompt_token_count: int = 0

    # Pipeline metadata
    stage_timings: dict[str, float] = field(default_factory=dict)
    stage_errors: dict[str, str] = field(default_factory=dict)

    def record_stage_error(self, stage_name: str, error: str) -> None:
        """Record an error from a non-critical stage."""
        self.stage_errors[stage_name] = error

    def record_stage_timing(self, stage_name: str, duration_ms: float) -> None:
        """Record execution time for a stage."""
        self.stage_timings[stage_name] = duration_ms

    def has_stage_errors(self) -> bool:
        """Check if any stage errors were recorded."""
        return len(self.stage_errors) > 0

    @property
    def total_duration_ms(self) -> float:
        """Total pipeline execution time from stage timings."""
        return sum(self.stage_timings.values())


@dataclass
class PipelineResult:
    """Final result from pipeline execution."""

    success: bool
    context: PipelineContext
    error_stage: str | None = None
    error_message: str | None = None
    total_duration_ms: float = 0.0
    stages_completed: int = 0
    stages_total: int = 9

    @classmethod
    def succeeded(cls, context: PipelineContext) -> PipelineResult:
        """Create a successful pipeline result."""
        return cls(
            success=True,
            context=context,
            total_duration_ms=context.total_duration_ms,
            stages_completed=len(context.stage_timings),
        )

    @classmethod
    def failed(
        cls, context: PipelineContext, stage: str, error: str
    ) -> PipelineResult:
        """Create a failed pipeline result."""
        return cls(
            success=False,
            context=context,
            error_stage=stage,
            error_message=error,
            total_duration_ms=context.total_duration_ms,
            stages_completed=len(context.stage_timings),
        )
