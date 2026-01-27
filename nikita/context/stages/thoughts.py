"""Thoughts creation stage for pipeline.

Stage 5 in the post-processing pipeline. Creates Nikita's simulated
inner thoughts about the conversation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.context.stages.base import PipelineStage

if TYPE_CHECKING:
    from nikita.context.pipeline_context import PipelineContext
    from nikita.db.models.conversation import Conversation


@dataclass
class ThoughtsInput:
    """Input for ThoughtsStage.

    Attributes:
        conversation: Source conversation model.
        thoughts: Extracted thought data with 'type' and 'content' keys.
    """

    conversation: Conversation
    thoughts: list[dict[str, str]]


class ThoughtsStage(PipelineStage[ThoughtsInput, int]):
    """Stage 5: Create Nikita's thoughts.

    Creates simulated inner thoughts based on LLM extraction.
    Filters by valid THOUGHT_TYPES (anticipation, reflection, desire, etc.).

    Non-critical: Pipeline continues if this stage fails.
    """

    name = "thoughts"
    is_critical = False
    timeout_seconds = 10.0
    max_retries = 2

    def __init__(
        self,
        session: AsyncSession,
        logger: structlog.BoundLogger | None = None,
    ):
        """Initialize ThoughtsStage.

        Args:
            session: Database session.
            logger: Optional pre-bound logger.
        """
        super().__init__(session, logger)
        # Lazy import to avoid circular dependency
        from nikita.db.repositories.thought_repository import NikitaThoughtRepository

        self._thought_repo = NikitaThoughtRepository(session)

    async def _run(
        self,
        context: PipelineContext,
        input: ThoughtsInput,
    ) -> int:
        """Execute thought creation stage.

        Args:
            context: Pipeline context with conversation data.
            input: ThoughtsInput with conversation and thoughts.

        Returns:
            Number of thoughts created.
        """
        conversation = input.conversation
        thoughts = input.thoughts

        # Filter by valid thought types
        from nikita.db.models.context import THOUGHT_TYPES

        thoughts_data = [
            {"thought_type": t["type"], "content": t["content"]}
            for t in thoughts
            if "type" in t and "content" in t and t["type"] in THOUGHT_TYPES
        ]

        if not thoughts_data:
            self._logger.debug("no_valid_thoughts", raw_count=len(thoughts))
            return 0

        # Bulk create thoughts
        await self._thought_repo.bulk_create_thoughts(
            user_id=conversation.user_id,
            thoughts_data=thoughts_data,
            source_conversation_id=conversation.id,
        )

        self._logger.info(
            "thoughts_created",
            count=len(thoughts_data),
            conversation_id=str(conversation.id),
        )

        return len(thoughts_data)
