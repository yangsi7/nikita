"""Post-processing pipeline for context engineering.

8-stage async pipeline that runs after conversations end:
1. Ingestion - Mark as processing, load transcript
2. Entity & Fact Extraction - Extract facts from transcript
3. Conversation Analysis - Summarize, detect tone, key moments
4. Thread Extraction - Find unresolved topics, questions, promises
5. Inner Life Generation - Simulate Nikita's thoughts
6. Graph Updates - Update Neo4j knowledge graphs
7. Summary Rollups - Update daily summaries
8. Cache Invalidation - Clear cached prompts

Total pipeline time: ~10-15 seconds (async, user doesn't wait)
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, date
from typing import Any
from uuid import UUID

from pydantic_ai import Agent
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.conversation import Conversation
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.summary_repository import DailySummaryRepository
from nikita.db.repositories.thread_repository import ConversationThreadRepository
from nikita.db.repositories.thought_repository import NikitaThoughtRepository

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of post-processing a single conversation."""

    conversation_id: UUID
    success: bool
    stage_reached: str
    error: str | None = None

    # Extracted data
    summary: str | None = None
    emotional_tone: str | None = None
    extracted_entities: dict[str, Any] | None = None
    threads_created: int = 0
    thoughts_created: int = 0


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


class PostProcessor:
    """Async post-processing pipeline for conversations.

    Extracts rich context from ended conversations:
    - Facts about the user
    - Conversation summaries
    - Unresolved threads
    - Nikita's simulated thoughts

    This data feeds the system prompt generator.
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_model: str = "claude-sonnet-4-5-20250929",
    ) -> None:
        """Initialize post-processor.

        Args:
            session: Database session.
            llm_model: Model to use for LLM extractions.
        """
        self._session = session
        self._llm_model = llm_model

        # Repositories
        self._conversation_repo = ConversationRepository(session)
        self._summary_repo = DailySummaryRepository(session)
        self._thread_repo = ConversationThreadRepository(session)
        self._thought_repo = NikitaThoughtRepository(session)

        # LLM agents for extraction (lazy init)
        self._extraction_agent: Agent | None = None

    def _get_extraction_agent(self) -> Agent:
        """Get or create the extraction agent."""
        if self._extraction_agent is None:
            self._extraction_agent = Agent(
                model=self._llm_model,
                system_prompt=self._get_extraction_system_prompt(),
            )
        return self._extraction_agent

    def _get_extraction_system_prompt(self) -> str:
        """Get system prompt for extraction agent."""
        return """You are a context extraction assistant for Nikita, an AI girlfriend.
Your job is to analyze conversations and extract structured information.

Extract the following:

1. FACTS about the user:
   - Explicit facts (things they directly stated)
   - Implicit facts (things you can infer)
   - Include: job, hobbies, family, friends, location, preferences

2. CONVERSATION ANALYSIS:
   - Summary (2-3 sentences max)
   - Emotional tone (positive/neutral/negative)
   - Key moments (1-3 highlights)
   - How it ended (good_note/abrupt/conflict)

3. UNRESOLVED THREADS:
   - follow_up: Things to follow up on later
   - question: Questions asked but not answered
   - promise: Promises made by either party
   - topic: Interesting topics worth revisiting

4. NIKITA'S THOUGHTS (simulate her inner life):
   - thinking: What she's thinking about from this conversation
   - wants_to_share: Things she wants to bring up next time
   - question: Questions she has for him
   - feeling: Her emotional state

Be concise but thorough. Output as JSON."""

    async def process_conversation(
        self,
        conversation_id: UUID,
    ) -> PipelineResult:
        """Run the full post-processing pipeline for a conversation.

        Args:
            conversation_id: The conversation to process.

        Returns:
            PipelineResult with success status and extracted data.
        """
        result = PipelineResult(
            conversation_id=conversation_id,
            success=False,
            stage_reached="init",
        )

        try:
            # Stage 1: Ingestion
            result.stage_reached = "ingestion"
            conversation = await self._stage_ingestion(conversation_id)
            if conversation is None:
                result.error = "Conversation not found"
                return result

            # Stage 2-5: LLM Extraction (combined for efficiency)
            result.stage_reached = "extraction"
            extraction = await self._stage_extraction(conversation)

            # Stage 3: Store conversation analysis
            result.stage_reached = "analysis"
            result.summary = extraction.summary
            result.emotional_tone = extraction.emotional_tone
            result.extracted_entities = {
                "facts": extraction.facts,
                "entities": extraction.entities,
                "preferences": extraction.preferences,
                "key_moments": extraction.key_moments,
                "how_it_ended": extraction.how_it_ended,
            }

            # Stage 4: Create threads
            result.stage_reached = "threads"
            threads_created = await self._stage_create_threads(
                conversation=conversation,
                threads=extraction.threads,
                resolved_ids=extraction.resolved_threads,
            )
            result.threads_created = threads_created

            # Stage 5: Create thoughts
            result.stage_reached = "thoughts"
            thoughts_created = await self._stage_create_thoughts(
                conversation=conversation,
                thoughts=extraction.thoughts,
            )
            result.thoughts_created = thoughts_created

            # Stage 6: Graph updates
            result.stage_reached = "graph_updates"
            await self._stage_graph_updates(
                conversation=conversation,
                extraction=extraction,
            )

            # Stage 7: Summary rollups
            result.stage_reached = "summary_rollups"
            await self._stage_summary_rollups(
                conversation=conversation,
                extraction=extraction,
            )

            # Stage 8: Mark processed
            result.stage_reached = "finalization"
            await self._conversation_repo.mark_processed(
                conversation_id=conversation_id,
                summary=extraction.summary,
                emotional_tone=extraction.emotional_tone,
                extracted_entities=result.extracted_entities,
            )

            result.success = True
            result.stage_reached = "complete"
            logger.info(f"Successfully processed conversation {conversation_id}")

        except Exception as e:
            result.error = str(e)
            logger.error(
                f"Pipeline failed at stage {result.stage_reached} "
                f"for conversation {conversation_id}: {e}"
            )

            # Mark as failed
            try:
                await self._conversation_repo.mark_failed(conversation_id)
            except Exception:
                pass

        return result

    async def _stage_ingestion(
        self,
        conversation_id: UUID,
    ) -> Conversation | None:
        """Stage 1: Load conversation and validate.

        Args:
            conversation_id: The conversation UUID.

        Returns:
            Conversation if found, None otherwise.
        """
        conversation = await self._conversation_repo.get(conversation_id)
        if conversation is None:
            return None

        # Already marked as processing by session_detector
        # Just validate it has messages
        if not conversation.messages:
            logger.warning(f"Conversation {conversation_id} has no messages")
            return None

        return conversation

    async def _stage_extraction(
        self,
        conversation: Conversation,
    ) -> ExtractionResult:
        """Stages 2-5: Run LLM extraction via MetaPromptService.

        Uses meta-prompts for intelligent entity extraction instead
        of static f-string templates.

        Args:
            conversation: The conversation to analyze.

        Returns:
            ExtractionResult with all extracted data.
        """
        from nikita.meta_prompts import MetaPromptService

        # Format messages for LLM
        messages_text = self._format_messages(conversation.messages)

        # Use MetaPromptService for intelligent extraction
        meta_service = MetaPromptService(self._session)
        data = await meta_service.extract_entities(
            conversation=messages_text,
            user_id=conversation.user_id,
        )

        logger.info(
            "Extracted entities via meta-prompt",
            extra={"conversation_id": str(conversation.id)},
        )

        # Map to ExtractionResult
        # MetaPromptService returns: user_facts, threads, emotional_markers, nikita_thoughts, summary
        facts = [
            {"type": f.get("category", "fact"), "content": f.get("content", "")}
            for f in data.get("user_facts", [])
        ]

        threads = [
            {"type": t.get("thread_type", "topic"), "content": t.get("topic", t.get("hook", ""))}
            for t in data.get("threads", [])
        ]

        thoughts = [
            {"type": t.get("type", "thinking"), "content": t.get("content", "")}
            for t in data.get("nikita_thoughts", [])
        ]

        # Extract emotional tone from markers
        markers = data.get("emotional_markers", [])
        if markers:
            # Use the most intense emotional marker
            sorted_markers = sorted(markers, key=lambda m: m.get("intensity", 0), reverse=True)
            emotional_type = sorted_markers[0].get("emotion_type", "neutral")
            emotional_tone = {
                "connection": "positive",
                "excitement": "positive",
                "vulnerable_share": "positive",
                "conflict": "negative",
                "disappointment": "negative",
            }.get(emotional_type, "neutral")
        else:
            emotional_tone = "neutral"

        return ExtractionResult(
            facts=facts,
            entities=[],  # Entities handled separately in graph updates
            preferences=[],  # Preferences detected via vice_detection
            summary=data.get("summary", "Conversation occurred."),
            emotional_tone=emotional_tone,
            key_moments=[m.get("context", "") for m in markers[:3]],
            how_it_ended="good_note" if emotional_tone == "positive" else "neutral",
            threads=threads,
            resolved_threads=[],  # TODO: Detect resolved threads
            thoughts=thoughts,
        )

    def _format_messages(self, messages: list[dict[str, Any]]) -> str:
        """Format messages for LLM prompt."""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            speaker = "User" if role == "user" else "Nikita"
            lines.append(f"{speaker}: {content}")
        return "\n".join(lines)

    async def _stage_create_threads(
        self,
        conversation: Conversation,
        threads: list[dict[str, str]],
        resolved_ids: list[UUID],
    ) -> int:
        """Stage 4: Create conversation threads.

        Args:
            conversation: Source conversation.
            threads: Extracted thread data.
            resolved_ids: Thread IDs to mark resolved.

        Returns:
            Number of threads created.
        """
        # Resolve existing threads
        for thread_id in resolved_ids:
            try:
                await self._thread_repo.resolve_thread(thread_id)
            except ValueError:
                pass

        # Create new threads
        threads_data = [
            {"thread_type": t["type"], "content": t["content"]}
            for t in threads
            if "type" in t and "content" in t
        ]

        if threads_data:
            await self._thread_repo.bulk_create_threads(
                user_id=conversation.user_id,
                threads_data=threads_data,
                source_conversation_id=conversation.id,
            )

        return len(threads_data)

    async def _stage_create_thoughts(
        self,
        conversation: Conversation,
        thoughts: list[dict[str, str]],
    ) -> int:
        """Stage 5: Create Nikita's thoughts.

        Args:
            conversation: Source conversation.
            thoughts: Extracted thought data.

        Returns:
            Number of thoughts created.
        """
        thoughts_data = [
            {"thought_type": t["type"], "content": t["content"]}
            for t in thoughts
            if "type" in t and "content" in t
        ]

        if thoughts_data:
            await self._thought_repo.bulk_create_thoughts(
                user_id=conversation.user_id,
                thoughts_data=thoughts_data,
                source_conversation_id=conversation.id,
            )

        return len(thoughts_data)

    async def _stage_graph_updates(
        self,
        conversation: Conversation,
        extraction: ExtractionResult,
    ) -> None:
        """Stage 6: Update Neo4j knowledge graphs.

        Args:
            conversation: Source conversation.
            extraction: Extracted data.
        """
        # TODO: Implement Graphiti integration
        # This will update:
        # - user_graph_{user_id}: facts, preferences, patterns
        # - relationship_graph_{user_id}: episodes, milestones, inside jokes
        # - nikita_graph_{user_id}: her simulated life events
        logger.debug(
            f"Graph updates for conversation {conversation.id} "
            f"(facts: {len(extraction.facts)}, entities: {len(extraction.entities)})"
        )

    async def _stage_summary_rollups(
        self,
        conversation: Conversation,
        extraction: ExtractionResult,
    ) -> None:
        """Stage 7: Update daily summaries.

        Args:
            conversation: Source conversation.
            extraction: Extracted data.
        """
        today = date.today()

        # Get or create today's summary
        summary = await self._summary_repo.get_for_date(
            user_id=conversation.user_id,
            summary_date=today,
        )

        if summary is None:
            # Create new daily summary
            await self._summary_repo.create_summary(
                user_id=conversation.user_id,
                summary_date=today,
                summary_text=extraction.summary,
                key_moments=[{"source": str(conversation.id), "moments": extraction.key_moments}],
                emotional_tone=extraction.emotional_tone,
            )
        else:
            # Update existing summary
            # Append this conversation's summary to the day's summary
            existing_moments = summary.key_moments or []
            existing_moments.append({
                "source": str(conversation.id),
                "moments": extraction.key_moments,
            })

            await self._summary_repo.update_summary(
                summary_id=summary.id,
                summary_text=f"{summary.summary_text or ''}\n\n{extraction.summary}".strip(),
                key_moments=existing_moments,
            )


async def process_conversations(
    session: AsyncSession,
    conversation_ids: list[UUID],
) -> list[PipelineResult]:
    """Process multiple conversations.

    Args:
        session: Database session.
        conversation_ids: List of conversation UUIDs to process.

    Returns:
        List of PipelineResult for each conversation.
    """
    processor = PostProcessor(session)
    results = []

    for conv_id in conversation_ids:
        result = await processor.process_conversation(conv_id)
        results.append(result)

    return results
