"""Extraction Stage - LLM-based entity and fact extraction.

Spec 037 T2.6: Stage 2 of post-processing pipeline.
Uses LLM to extract facts, entities, and conversation analysis.
"""

import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.base import PipelineStage, StageError
from nikita.context.stages.circuit_breaker import CircuitBreaker
from nikita.db.models.conversation import Conversation
from nikita.db.repositories.thread_repository import ConversationThreadRepository


@dataclass
class ExtractionResult:
    """LLM extraction results."""

    # Entity extraction
    facts: list[dict[str, str]]  # [{"type": "fact", "content": "..."}]
    entities: list[dict[str, str]]  # [{"type": "person", "name": "..."}]
    preferences: list[dict[str, str]]  # [{"category": "...", "detail": "..."}]

    # Conversation analysis
    summary: str
    emotional_tone: str  # positive, neutral, negative
    key_moments: list[str]
    how_it_ended: str  # good_note, abrupt, conflict

    # Thread extraction
    threads: list[dict[str, str]]  # [{"type": "follow_up", "content": "..."}]
    resolved_threads: list[UUID]  # Thread IDs that were resolved

    # Inner life
    thoughts: list[dict[str, str]]  # [{"type": "thinking", "content": "..."}]


# Shared circuit breaker for LLM calls (module-level singleton)
_llm_circuit_breaker = CircuitBreaker(
    name="claude_extraction",
    failure_threshold=3,
    recovery_timeout=120.0,  # 2 minutes recovery
    half_open_max_calls=2,
)


class ExtractionStage(PipelineStage[Conversation, ExtractionResult]):
    """Stage 2: LLM-based entity and fact extraction.

    Spec 037 T2.6:
    - AC-T2.6.1: is_critical = True
    - AC-T2.6.2: timeout_seconds = 120.0
    - AC-T2.6.3: Uses circuit breaker (threshold=3, recovery=120s)
    - AC-T2.6.4: Validates LLM output before returning
    """

    name = "extraction"
    is_critical = True
    timeout_seconds = 120.0  # LLM calls can be slow
    max_retries = 2

    def __init__(
        self,
        session: AsyncSession,
        meta_service: Any | None = None,
    ):
        """Initialize with database session and optional meta service.

        Args:
            session: SQLAlchemy async session
            meta_service: MetaPromptService for LLM calls (injected for testing)
        """
        super().__init__(session)
        self._meta_service = meta_service
        self._thread_repo = ConversationThreadRepository(session)

    async def _get_meta_service(self):
        """Get meta prompt service, creating if needed."""
        if self._meta_service is None:
            from nikita.meta_prompts.service import MetaPromptService

            self._meta_service = MetaPromptService(self._session)
        return self._meta_service

    async def _run(
        self,
        context: PipelineContext,
        conversation: Conversation,
    ) -> ExtractionResult:
        """Extract entities and facts from conversation.

        Args:
            context: Pipeline context
            conversation: Conversation to analyze

        Returns:
            ExtractionResult with extracted data

        Raises:
            StageError: If extraction fails
        """
        self._logger.info(
            "starting_extraction",
            conversation_id=str(context.conversation_id),
            message_count=len(conversation.messages),
        )

        # Format messages for LLM
        messages_text = self._format_messages(conversation.messages)

        # Get open threads for context (with timeout)
        try:
            open_threads = await asyncio.wait_for(
                self._thread_repo.get_open_threads(conversation.user_id, limit=20),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            self._logger.warning("open_threads_timeout")
            open_threads = []

        # Format threads for extraction prompt
        thread_context = [
            {"id": str(t.id), "type": t.thread_type, "content": t.content}
            for t in open_threads
        ]

        # Call LLM via circuit breaker
        meta_service = await self._get_meta_service()

        try:
            data = await _llm_circuit_breaker.call(
                meta_service.extract_entities,
                conversation=messages_text,
                user_id=conversation.user_id,
                open_threads=thread_context,
            )
        except Exception as e:
            raise StageError(
                stage_name=self.name,
                message=f"LLM extraction failed: {e}",
                recoverable=True,
            ) from e

        # Validate and map output
        result = self._validate_and_map(data)

        # Store in context for other stages
        context.extraction_result = result

        self._logger.info(
            "extraction_complete",
            facts_count=len(result.facts),
            entities_count=len(result.entities),
            threads_count=len(result.threads),
            thoughts_count=len(result.thoughts),
        )

        return result

    def _format_messages(self, messages: list[dict]) -> str:
        """Format conversation messages for LLM.

        Args:
            messages: List of message dicts with role and content

        Returns:
            Formatted transcript string
        """
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role in ("user", "player"):
                lines.append(f"Player: {content}")
            elif role in ("assistant", "nikita"):
                lines.append(f"Nikita: {content}")
            else:
                lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _validate_and_map(self, data: Any) -> ExtractionResult:
        """Validate LLM output and map to ExtractionResult.

        Args:
            data: Raw LLM extraction output

        Returns:
            Validated ExtractionResult
        """
        # Handle various output formats
        if data is None:
            return self._empty_result()

        if isinstance(data, dict):
            return ExtractionResult(
                facts=data.get("facts", []),
                entities=data.get("entities", []),
                preferences=data.get("preferences", []),
                summary=data.get("summary", ""),
                emotional_tone=data.get("emotional_tone", "neutral"),
                key_moments=data.get("key_moments", []),
                how_it_ended=data.get("how_it_ended", "unknown"),
                threads=data.get("threads", []),
                resolved_threads=[
                    UUID(tid) for tid in data.get("resolved_threads", [])
                    if isinstance(tid, str)
                ],
                thoughts=data.get("thoughts", []),
            )

        # If data is already an ExtractionResult-like object
        if hasattr(data, "facts"):
            return ExtractionResult(
                facts=getattr(data, "facts", []),
                entities=getattr(data, "entities", []),
                preferences=getattr(data, "preferences", []),
                summary=getattr(data, "summary", ""),
                emotional_tone=getattr(data, "emotional_tone", "neutral"),
                key_moments=getattr(data, "key_moments", []),
                how_it_ended=getattr(data, "how_it_ended", "unknown"),
                threads=getattr(data, "threads", []),
                resolved_threads=getattr(data, "resolved_threads", []),
                thoughts=getattr(data, "thoughts", []),
            )

        return self._empty_result()

    def _empty_result(self) -> ExtractionResult:
        """Create empty extraction result."""
        return ExtractionResult(
            facts=[],
            entities=[],
            preferences=[],
            summary="",
            emotional_tone="neutral",
            key_moments=[],
            how_it_ended="unknown",
            threads=[],
            resolved_threads=[],
            thoughts=[],
        )
