"""Pipeline context for post-processing stages.

This module defines the shared context object passed between pipeline stages.
It holds conversation data, user context, and intermediate results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class PipelineContext:
    """Shared context for pipeline stages.

    This object is passed through all stages and accumulates
    intermediate results and metadata.

    Attributes:
        conversation_id: The conversation being processed
        user_id: The user who owns the conversation
        started_at: When pipeline processing started
        conversation: The loaded conversation object (set by IngestionStage)
        extraction_result: LLM extraction output (set by ExtractionStage)
        stage_errors: Errors from non-critical stages that didn't stop pipeline
        metadata: Additional metadata for logging/tracing
    """

    conversation_id: UUID
    user_id: UUID
    started_at: datetime

    # Set by stages during execution
    conversation: Any | None = None
    extraction_result: Any | None = None

    # Track errors from non-critical stages
    stage_errors: dict[str, str] = field(default_factory=dict)

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_stage_error(self, stage_name: str, error: str) -> None:
        """Record an error from a non-critical stage.

        Args:
            stage_name: Name of the stage that failed
            error: Error message or description
        """
        self.stage_errors[stage_name] = error

    def has_stage_errors(self) -> bool:
        """Check if any stage errors were recorded."""
        return len(self.stage_errors) > 0

    @property
    def duration_ms(self) -> float:
        """Calculate duration since pipeline started."""
        return (datetime.now(self.started_at.tzinfo) - self.started_at).total_seconds() * 1000

    def update_from_result(
        self,
        stage_name: str,
        result: Any,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Update context based on stage result.

        This method allows stages to update shared context with their
        results so subsequent stages can access the data.

        Args:
            stage_name: Name of the stage that produced the result
            result: The stage result data
            success: Whether the stage succeeded
            error: Error message if stage failed
        """
        if not success and error:
            self.record_stage_error(stage_name, error)

        # Store specific results for downstream stages
        if stage_name == "ingestion":
            self.conversation = result
        elif stage_name == "extraction":
            self.extraction_result = result
        # Store in metadata for other stages
        self.metadata[f"{stage_name}_result"] = result
        self.metadata[f"{stage_name}_success"] = success
