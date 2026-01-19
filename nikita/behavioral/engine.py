"""Meta-Instruction Engine for Behavioral System (Spec 024, T015-T017).

Orchestrates the full behavioral instruction pipeline:
1. Detect current situation
2. Select relevant instructions
3. Format for prompt injection

Provides the main interface for integrating behavioral guidance into prompts.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from nikita.behavioral.detector import SituationDetector
from nikita.behavioral.models import InstructionSet, SituationContext, SituationType
from nikita.behavioral.selector import InstructionSelector

logger = logging.getLogger(__name__)


class MetaInstructionEngine:
    """Orchestrates behavioral meta-instruction selection.

    Main entry point for the behavioral system. Combines detection,
    selection, and formatting into a single interface.

    Example:
        engine = MetaInstructionEngine()

        # Get formatted instructions for a context
        formatted = await engine.get_instructions_for_context(
            user_id=user_id,
            conflict_state="none",
            hours_since_last=2.5,
            user_local_hour=14,
            chapter=2,
        )

        # Add to prompt
        prompt += formatted

    Attributes:
        detector: SituationDetector instance.
        selector: InstructionSelector instance.
        max_instructions: Maximum instructions per request.
    """

    def __init__(
        self,
        max_instructions: int = 5,
        detector: SituationDetector | None = None,
        selector: InstructionSelector | None = None,
    ):
        """Initialize the engine.

        Args:
            max_instructions: Maximum instructions to include. Defaults to 5.
            detector: Optional custom detector. Defaults to new instance.
            selector: Optional custom selector. Defaults to new instance.
        """
        self.max_instructions = max_instructions
        self.detector = detector or SituationDetector()
        self.selector = selector or InstructionSelector(max_instructions=max_instructions)

    def get_instructions_for_context(
        self,
        user_id: str | UUID | None = None,
        conflict_state: str = "none",
        hours_since_last_message: float = 0.0,
        user_local_hour: int | None = None,
        chapter: int = 1,
        relationship_score: float = 50.0,
        engagement_state: str = "in_zone",
        last_message_at: datetime | None = None,
        max_instructions: int | None = None,
    ) -> str:
        """Get formatted behavioral instructions for the current context.

        Main method for prompt integration. Detects situation, selects
        relevant instructions, and returns formatted guidance text.

        Args:
            user_id: User identifier.
            conflict_state: Current conflict state from EmotionalState.
            hours_since_last_message: Hours since last user message.
            user_local_hour: User's local hour (0-23). Defaults to UTC hour.
            chapter: Current relationship chapter (1-5).
            relationship_score: Current relationship score (0-100).
            engagement_state: Current engagement state.
            last_message_at: Timestamp of last message (alternative to hours).
            max_instructions: Override max instructions for this request.

        Returns:
            Formatted instruction string for prompt injection.
            Empty string if no instructions apply.
        """
        # Calculate hours from timestamp if provided
        if last_message_at is not None and hours_since_last_message == 0.0:
            hours_since_last_message = self.detector.calculate_time_since_last(
                last_message_at,
                datetime.now(timezone.utc),
            )

        # Detect situation
        context = self.detector.detect(
            conflict_state=conflict_state,
            hours_since_last_message=hours_since_last_message,
            user_local_hour=user_local_hour,
            chapter=chapter,
            relationship_score=relationship_score,
            engagement_state=engagement_state,
            user_id=str(user_id) if user_id else None,
        )

        # Select instructions
        instruction_set = self.selector.select(
            context=context,
            max_instructions=max_instructions or self.max_instructions,
        )

        # Format for prompt
        formatted = self.format_for_prompt(instruction_set)

        logger.info(
            "Generated %d instructions for situation=%s (user=%s)",
            len(instruction_set.instructions),
            context.situation_type.value,
            user_id,
        )

        return formatted

    def detect_situation(
        self,
        conflict_state: str = "none",
        hours_since_last_message: float = 0.0,
        user_local_hour: int | None = None,
        chapter: int = 1,
        relationship_score: float = 50.0,
        engagement_state: str = "in_zone",
        user_id: str | None = None,
    ) -> SituationContext:
        """Detect the current situation without selecting instructions.

        Useful for logging or analytics without full instruction selection.

        Args:
            conflict_state: Current conflict state.
            hours_since_last_message: Hours since last message.
            user_local_hour: User's local hour.
            chapter: Current chapter.
            relationship_score: Current score.
            engagement_state: Current engagement state.
            user_id: Optional user ID.

        Returns:
            SituationContext with detected situation type.
        """
        return self.detector.detect(
            conflict_state=conflict_state,
            hours_since_last_message=hours_since_last_message,
            user_local_hour=user_local_hour,
            chapter=chapter,
            relationship_score=relationship_score,
            engagement_state=engagement_state,
            user_id=user_id,
        )

    def select_instructions(
        self,
        context: SituationContext,
        max_instructions: int | None = None,
    ) -> InstructionSet:
        """Select instructions for a pre-detected context.

        Args:
            context: Pre-detected situation context.
            max_instructions: Override max instructions.

        Returns:
            InstructionSet with selected instructions.
        """
        return self.selector.select(
            context=context,
            max_instructions=max_instructions or self.max_instructions,
        )

    def format_for_prompt(self, instruction_set: InstructionSet) -> str:
        """Format an instruction set for prompt injection.

        Delegates to InstructionSet.format_for_prompt() for consistency.
        Can be overridden for custom formatting.

        Args:
            instruction_set: The instruction set to format.

        Returns:
            Formatted string ready for prompt injection.
        """
        return instruction_set.format_for_prompt()

    def get_situation_summary(self, context: SituationContext) -> dict[str, Any]:
        """Get a summary of the detected situation for logging/analytics.

        Args:
            context: The situation context.

        Returns:
            Dictionary with situation details.
        """
        return {
            "situation_type": context.situation_type.value,
            "detected_at": context.detected_at.isoformat(),
            "hours_since_last_message": context.hours_since_last_message,
            "user_local_hour": context.user_local_hour,
            "chapter": context.chapter,
            "relationship_score": context.relationship_score,
            "conflict_state": context.conflict_state,
            "engagement_state": context.engagement_state,
            "metadata": context.metadata,
        }

    def get_all_situations(self) -> list[SituationType]:
        """Get list of all situation types.

        Returns:
            List of SituationType enum values.
        """
        return list(SituationType)

    def clear_caches(self) -> None:
        """Clear all internal caches.

        Useful for testing or when instruction YAML is updated.
        """
        self.selector.clear_cache()
