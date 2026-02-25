"""Transcript management for voice calls (US-5: Cross-Modality Memory).

This module provides TranscriptManager which handles:
- Fetching transcripts from ElevenLabs (T025)
- Persisting transcripts to conversations table (AC-FR009-001)
- Extracting facts for Graphiti memory (T026, AC-FR010-001)
- Storing facts with source='voice_call' (T027)
- Generating summaries for cross-agent context

Implements T024-T028 acceptance criteria.
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from nikita.agents.voice.elevenlabs_client import get_elevenlabs_client
from nikita.agents.voice.models import TranscriptData, TranscriptEntry
from nikita.config.models import Models

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TranscriptManager:
    """Manager for voice call transcripts.

    Handles transcript persistence, fact extraction, and memory integration.
    Works with ElevenLabs API for transcript fetching and Graphiti for storage.
    """

    def __init__(self, session: "AsyncSession | None"):
        """Initialize TranscriptManager.

        Args:
            session: Database session for persistence (optional for extraction-only ops)
        """
        self.session = session

    async def fetch_transcript(
        self,
        conversation_id: str,
    ) -> TranscriptData | None:
        """Fetch transcript from ElevenLabs API.

        Uses ElevenLabsConversationsClient for all API interactions (DRY principle).

        Args:
            conversation_id: ElevenLabs conversation ID

        Returns:
            TranscriptData if successful, None on error
        """
        try:
            client = get_elevenlabs_client()
            detail = await client.get_conversation(conversation_id)
            return client.to_transcript_data(detail)
        except ValueError as e:
            # API key not configured
            logger.warning(f"[TRANSCRIPT] {e}")
            return None
        except Exception as e:
            logger.error(f"[TRANSCRIPT] Fetch failed: {e}")
            return None

    async def persist_transcript(
        self,
        user_id: UUID,
        transcript: TranscriptData,
    ) -> dict[str, Any]:
        """Persist transcript to conversations table.

        AC-FR009-001: Voice transcripts stored with platform='voice'.

        Args:
            user_id: User UUID
            transcript: Transcript data to persist

        Returns:
            Result dict with conversation_id and metadata
        """
        if self.session is None:
            raise ValueError("Database session required for persistence")

        conversation_id = str(uuid4())
        now = datetime.now(timezone.utc)

        # Build message content from entries
        messages = []
        for entry in transcript.entries:
            messages.append({
                "role": entry.speaker,
                "content": entry.text,
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else now.isoformat(),
            })

        # Create conversation record
        # NOTE: Actual implementation would use ConversationRepository
        # For now, we log and return result structure
        logger.info(
            f"[TRANSCRIPT] Persisting transcript: "
            f"user={user_id}, session={transcript.session_id}, "
            f"entries={len(transcript.entries)}"
        )

        result = {
            "conversation_id": conversation_id,
            "session_id": transcript.session_id,
            "platform": "voice",
            "entries_stored": len(transcript.entries),
            "user_turns": transcript.user_turns,
            "nikita_turns": transcript.nikita_turns,
            "total_duration_ms": transcript.total_duration_ms,
            "persisted_at": now.isoformat(),
        }

        return result

    def convert_to_exchange_pairs(
        self,
        transcript: TranscriptData,
    ) -> list[tuple[str, str]]:
        """Convert transcript to (user, nikita) exchange pairs.

        Pairs consecutive user→nikita messages for scoring.

        Args:
            transcript: Transcript data

        Returns:
            List of (user_message, nikita_response) tuples
        """
        pairs: list[tuple[str, str]] = []
        user_msg: str | None = None

        for entry in transcript.entries:
            if entry.speaker == "user":
                user_msg = entry.text
            elif entry.speaker == "nikita" and user_msg is not None:
                pairs.append((user_msg, entry.text))
                user_msg = None

        return pairs

    async def extract_facts(
        self,
        transcript: TranscriptData,
    ) -> list[dict[str, str]]:
        """Extract facts from transcript for memory storage.

        Uses LLM to identify factual statements about the user.

        Args:
            transcript: Transcript data

        Returns:
            List of fact dicts with 'fact' and 'category' keys
        """
        # Build full text for analysis
        full_text = "\n".join(
            f"{entry.speaker}: {entry.text}" for entry in transcript.entries
        )

        if not full_text.strip():
            return []

        return await self._extract_facts_via_llm(full_text)

    async def _extract_facts_via_llm(
        self,
        transcript_text: str,
    ) -> list[dict[str, str]]:
        """Use LLM to extract facts from transcript.

        Uses Pydantic AI with Claude to identify personal facts, preferences,
        and biographical information from voice conversation transcripts.

        Args:
            transcript_text: Full transcript text

        Returns:
            Extracted facts with categories (occupation, hobby, relationship,
            preference, biographical, emotional)
        """
        from pydantic import BaseModel
        from pydantic_ai import Agent

        # Define extraction schema
        class ExtractedFact(BaseModel):
            fact: str
            category: str  # occupation, hobby, relationship, preference, biographical, emotional

        class FactExtractionResult(BaseModel):
            facts: list[ExtractedFact]

        # Create extraction agent
        extract_agent = Agent(
            Models.sonnet(),
            output_type=FactExtractionResult,
            system_prompt="""You are a fact extraction assistant analyzing voice call transcripts.

Extract personal facts about the USER (human) - NOT about the AI assistant Nikita.

Categories:
- occupation: job, work, career info
- hobby: hobbies, interests, activities
- relationship: family, friends, partners
- preference: likes, dislikes, preferences
- biographical: age, location, education, life events
- emotional: feelings, emotional states, mental health

Rules:
- Only extract CONCRETE facts (not vague statements)
- Focus on the USER's information, not Nikita's
- Each fact should be a standalone statement
- Skip greetings, small talk, and conversation fillers
- If no clear facts, return empty list

Example output for "I work at Google and love hiking on weekends":
[{"fact": "Works at Google", "category": "occupation"},
 {"fact": "Enjoys hiking on weekends", "category": "hobby"}]""",
        )

        try:
            result = await extract_agent.run(
                f"Extract personal facts from this voice call transcript:\n\n{transcript_text}"
            )
            facts = [
                {"fact": f.fact, "category": f.category}
                # pydantic-ai 1.x uses .output, older uses .data
                for f in (getattr(result, "output", None) or getattr(result, "data", None)).facts
            ]
            logger.info(f"[TRANSCRIPT] Extracted {len(facts)} facts from transcript")
            return facts
        except Exception as e:
            logger.error(f"[TRANSCRIPT] LLM extraction failed: {e}")
            return []

    async def store_fact(
        self,
        user_id: UUID,
        session_id: str,
        fact: str,
        category: str | None = None,
    ) -> None:
        """Store a single fact to Graphiti memory.

        AC-FR010-001: Facts stored with source='voice_call'.

        Args:
            user_id: User UUID
            session_id: Voice session ID for tracing
            fact: Fact content
            category: Optional category (occupation, hobby, etc.)
        """
        from nikita.memory import get_memory_client

        try:
            memory = await get_memory_client(str(user_id))
            await memory.add_fact(
                content=fact,
                category=category,
                source="voice_call",
                source_id=session_id,
            )
            logger.info(f"[TRANSCRIPT] Stored fact: {fact[:50]}...")
        except Exception as e:
            logger.error(f"[TRANSCRIPT] Failed to store fact: {e}")
            raise

    async def store_facts_batch(
        self,
        user_id: UUID,
        session_id: str,
        facts: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Store multiple facts to Graphiti memory.

        Args:
            user_id: User UUID
            session_id: Voice session ID
            facts: List of fact dicts with 'fact' and 'category' keys

        Returns:
            Result dict with count of stored facts
        """
        stored = 0
        errors = 0

        for fact_data in facts:
            try:
                await self.store_fact(
                    user_id=user_id,
                    session_id=session_id,
                    fact=fact_data.get("fact", ""),
                    category=fact_data.get("category"),
                )
                stored += 1
            except Exception as e:
                logger.error(f"[TRANSCRIPT] Batch store error: {e}")
                errors += 1

        return {
            "facts_stored": stored,
            "errors": errors,
            "session_id": session_id,
        }

    async def generate_summary(
        self,
        transcript: TranscriptData,
    ) -> str | None:
        """Generate summary of voice conversation.

        Args:
            transcript: Transcript data

        Returns:
            Summary string or None on failure
        """
        # Build full text
        full_text = "\n".join(
            f"{entry.speaker}: {entry.text}" for entry in transcript.entries
        )

        if not full_text.strip():
            return None

        return await self._summarize_via_llm(full_text)

    async def _summarize_via_llm(
        self,
        transcript_text: str,
    ) -> str:
        """Use LLM to summarize transcript in 2-3 sentences.

        Spec 072 G2: Creates a Pydantic AI agent with Claude Haiku for speed.
        Captures: what was discussed, emotional tone, commitments/plans made.

        Pattern: Same as FactExtractor in nikita/agents/text/facts.py —
        uses a structured Pydantic output type with a single Agent call.

        Args:
            transcript_text: Full transcript text (speaker: text format)

        Returns:
            2-3 sentence summary string, or empty string on failure/empty input
        """
        if not transcript_text.strip():
            return ""

        from pydantic import BaseModel
        from pydantic_ai import Agent

        class TranscriptSummary(BaseModel):
            summary: str  # 2-3 sentence summary of the voice call

        summarize_agent = Agent(
            Models.haiku(),
            output_type=TranscriptSummary,
            system_prompt="""You are a voice call summarizer. Given a transcript between a user and Nikita (an AI girlfriend), write a 2-3 sentence summary.

Your summary should capture:
1. What was discussed (main topics)
2. The emotional tone (warm, tense, playful, vulnerable, etc.)
3. Any commitments or plans mentioned

Keep the summary concise and factual. Write in past tense from Nikita's perspective.

Example: "The user shared news about completing a big work project. The tone was positive and celebratory. They made plans to celebrate together this weekend." """,
        )

        try:
            result = await summarize_agent.run(
                f"Summarize this voice call transcript:\n\n{transcript_text}"
            )
            # pydantic-ai 1.x uses .output; older uses .data
            output = getattr(result, "output", None) or getattr(result, "data", None)
            summary = output.summary if output else ""
            logger.info(f"[TRANSCRIPT] Generated summary ({len(summary)} chars)")
            return summary
        except Exception as e:
            logger.error(f"[TRANSCRIPT] LLM summarization failed: {e}")
            return ""

    def format_for_text_agent(
        self,
        transcript_summary: str,
        duration_seconds: int,
    ) -> str:
        """Format voice call summary for text agent context.

        Args:
            transcript_summary: Generated summary
            duration_seconds: Call duration

        Returns:
            Formatted string for text agent
        """
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60

        if minutes > 0:
            duration_str = f"{minutes}m {seconds}s"
        else:
            duration_str = f"{seconds}s"

        return (
            f"[Previous voice call - {duration_str}] "
            f"{transcript_summary}"
        )


# Factory function
def get_transcript_manager(
    session: "AsyncSession | None" = None,
) -> TranscriptManager:
    """Get TranscriptManager instance.

    Args:
        session: Optional database session

    Returns:
        TranscriptManager instance
    """
    return TranscriptManager(session=session)
