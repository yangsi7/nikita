"""Supabase pgVector-based memory system.

Spec 042 Phase 1: T1.1, T1.2, T1.3
- T1.1: SupabaseMemory class (add_fact, search, get_recent, context_for_prompt)
- T1.2: Duplicate detection via cosine similarity
- T1.3: OpenAI text-embedding-3-small embedding generation with retry
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import openai
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.config.settings import get_settings
from nikita.db.repositories.memory_fact_repository import MemoryFactRepository

logger = logging.getLogger(__name__)

# Graph type labels for prompt formatting (matches NikitaMemory)
GRAPH_LABELS = {
    "nikita": "My life",
    "user": "About them",
    "relationship": "Our history",
}

ALL_GRAPH_TYPES = ["user", "relationship", "nikita"]

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1  # seconds


class EmbeddingError(Exception):
    """Raised when embedding generation fails after all retries."""

    pass


class SupabaseMemory:
    """pgVector-based memory system for semantic memory.

    Provides the memory interface backed by
    Supabase pgVector with <100ms search latency.

    Three graph types:
    - user: Facts about the player
    - relationship: Shared history and episodes
    - nikita: Her simulated life events

    Usage:
        async with SupabaseMemory(session, user_id, openai_api_key) as memory:
            await memory.add_user_fact("User likes coffee")
            results = await memory.search("coffee preferences")
    """

    def __init__(
        self,
        session: AsyncSession,
        user_id: UUID,
        openai_api_key: str,
    ) -> None:
        self.user_id = user_id
        self._openai_api_key = openai_api_key
        self._session = session
        self._repo = MemoryFactRepository(session)
        self._client = openai.AsyncOpenAI(api_key=openai_api_key)
        self._closed = False

    async def __aenter__(self) -> "SupabaseMemory":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        self._closed = True
        if exc_type is not None:
            logger.warning(
                "[MEMORY] Context manager exiting with exception: %s: %s",
                exc_type.__name__,
                exc_val,
            )
        return False

    async def close(self) -> None:
        self._closed = True

    # ── Embedding Generation (T1.3) ─────────────────────────────────────

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate 1536-dim embedding via OpenAI text-embedding-3-small.

        AC-1.3.1: Uses text-embedding-3-small (1536 dims).
        AC-1.3.3: Retries 3x with exponential backoff (1s, 2s, 4s).
        AC-1.3.4: Raises EmbeddingError on persistent failure.
        """
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await self._client.embeddings.create(
                    input=text,
                    model=EMBEDDING_MODEL,
                )
                return response.data[0].embedding
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF_BASE * (2**attempt)
                    logger.warning(
                        "[EMBEDDING] Attempt %d failed: %s. Retrying in %ds...",
                        attempt + 1,
                        str(e)[:100],
                        wait,
                    )
                    await asyncio.sleep(wait)

        raise EmbeddingError(
            f"Embedding generation failed after {MAX_RETRIES} attempts: {last_error}"
        )

    async def generate_embeddings_batch(
        self, texts: list[str]
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in a single API call.

        AC-1.3.2: Batch embedding support (up to 100 texts per call).
        """
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await self._client.embeddings.create(
                    input=texts,
                    model=EMBEDDING_MODEL,
                )
                return [d.embedding for d in response.data]
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF_BASE * (2**attempt)
                    await asyncio.sleep(wait)

        raise EmbeddingError(
            f"Batch embedding failed after {MAX_RETRIES} attempts: {last_error}"
        )

    # ── Core Operations (T1.1) ───────────────────────────────────────────

    async def add_fact(
        self,
        fact: str,
        graph_type: str,
        source: str,
        confidence: float,
        metadata: dict[str, Any] | None = None,
        conversation_id: UUID | None = None,
    ):
        """Add a fact with automatic embedding generation and dedup.

        AC-1.1.2: Generates embedding + inserts via repository.
        AC-1.2.2: If similar fact exists, supersedes old instead of duplicating.

        Spec 102 FR-001: Embedding generated ONCE and passed to find_similar()
        to avoid a double API call.
        """
        embedding = await self._generate_embedding(fact)

        # T1.2: Check for duplicates before inserting — pass pre-computed embedding
        existing = await self.find_similar(fact, threshold=0.95, embedding=embedding)

        new_fact = await self._repo.add_fact(
            user_id=self.user_id,
            fact=fact,
            graph_type=graph_type,
            embedding=embedding,
            source=source,
            confidence=confidence,
            metadata=metadata,
            conversation_id=conversation_id,
        )

        # AC-1.2.3: Deactivate old fact if duplicate found
        if existing is not None:
            await self._repo.deactivate(
                existing.id,
                superseded_by_id=new_fact.id,
            )

        return new_fact

    async def search(
        self,
        query: str,
        graph_types: list[str] | None = None,
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Semantic search across knowledge graphs.

        AC-1.1.3: Embeds query + pgVector cosine search.

        Spec 102 FR-002: Uses a single batch DB call via semantic_search_batch()
        instead of N sequential calls (one per graph type).
        """
        if graph_types is None:
            graph_types = ALL_GRAPH_TYPES

        query_embedding = await self._generate_embedding(query)

        rows = await self._repo.semantic_search_batch(
            user_id=self.user_id,
            query_embedding=query_embedding,
            graph_types=graph_types,
            limit=limit,
            min_confidence=min_confidence,
        )

        results = []
        for fact, distance in rows:
            results.append({
                "fact": fact.fact,
                "graph_type": fact.graph_type,
                "created_at": fact.created_at,
                "distance": distance,
                "confidence": fact.confidence,
            })

        # Results already ordered by distance from pgVector ORDER BY
        return results[:limit]

    async def get_recent(
        self,
        graph_type: str | None = None,
        limit: int = 20,
    ):
        """Get recent facts ordered by created_at DESC.

        AC-1.1.4: Temporal query.
        """
        return await self._repo.get_recent(
            user_id=self.user_id,
            graph_type=graph_type,
            limit=limit,
        )

    async def get_context_for_prompt(
        self,
        user_message: str,
        max_memories: int = 5,
    ) -> str:
        """Build context string for LLM prompt injection.

        Returns formatted memories matching NikitaMemory output format:
            [2026-01-14] (My life) Nikita's work event...
            [2026-01-13] (Our history) We argued about pizza...
        """
        memories = await self.search(query=user_message, limit=max_memories)

        if not memories:
            return "No relevant memories found."

        context_parts = []
        for memory in memories[:max_memories]:
            created = memory.get("created_at")
            date_str = created.strftime("%Y-%m-%d") if created else "Unknown"
            graph_label = GRAPH_LABELS.get(
                memory["graph_type"], memory["graph_type"]
            )
            context_parts.append(
                f"[{date_str}] ({graph_label}) {memory['fact']}"
            )

        return "\n".join(context_parts)

    # ── Duplicate Detection (T1.2) ───────────────────────────────────────

    async def find_similar(
        self,
        text: str,
        threshold: float = 0.95,
        embedding: list[float] | None = None,
    ):
        """Find near-duplicate fact by cosine similarity.

        AC-1.2.1: Returns existing fact if similarity > threshold.
        Cosine distance = 1 - similarity, so threshold 0.95 → max distance 0.05.

        Spec 102 FR-001: Accepts optional pre-computed embedding to avoid
        double API call when called from add_fact().

        Args:
            text: The fact text to compare.
            threshold: Similarity threshold (default 0.95).
            embedding: Optional pre-computed embedding; generated if not provided.
        """
        if embedding is None:
            embedding = await self._generate_embedding(text)

        results = await self._repo.semantic_search(
            user_id=self.user_id,
            query_embedding=embedding,
            limit=1,
        )

        if not results:
            return None

        fact, distance = results[0]
        # Cosine distance threshold: 1 - similarity
        max_distance = 1.0 - threshold
        if distance <= max_distance:
            return fact

        return None

    # ── NikitaMemory Compatibility Methods ───────────────────────────────

    async def add_user_fact(
        self,
        fact: str,
        confidence: float = 0.8,
        source_message: str | None = None,
    ) -> None:
        """Add a fact about the user (NikitaMemory compat)."""
        content = f"Learned about user: {fact}"
        if source_message:
            content += f" (from: '{source_message[:100]}...')"

        await self.add_fact(
            fact=content,
            graph_type="user",
            source="user_message",
            confidence=confidence,
            metadata={"source_message": source_message} if source_message else None,
        )

    async def get_user_facts(self, limit: int = 50) -> list[str]:
        """Get user facts as strings (NikitaMemory compat)."""
        facts = await self._repo.get_by_user(
            user_id=self.user_id,
            graph_type="user",
            active_only=True,
        )
        return [f.fact for f in facts[:limit]]

    async def add_relationship_episode(
        self,
        description: str,
        episode_type: str = "general",
    ) -> None:
        """Add relationship episode (NikitaMemory compat)."""
        await self.add_fact(
            fact=f"[{episode_type}] {description}",
            graph_type="relationship",
            source="system_event",
            confidence=0.8,
            metadata={"episode_type": episode_type},
        )

    async def get_relationship_episodes(self, limit: int = 50) -> list[str]:
        """Get relationship episodes as strings (NikitaMemory compat)."""
        facts = await self._repo.get_by_user(
            user_id=self.user_id,
            graph_type="relationship",
            active_only=True,
        )
        return [f.fact for f in facts[:limit]]

    async def add_nikita_event(
        self,
        description: str,
        event_type: str = "life_event",
    ) -> None:
        """Add Nikita life event (NikitaMemory compat)."""
        await self.add_fact(
            fact=f"[{event_type}] {description}",
            graph_type="nikita",
            source="system_event",
            confidence=0.8,
            metadata={"event_type": event_type},
        )

    async def get_nikita_events(self, limit: int = 50) -> list[str]:
        """Get Nikita events as strings (NikitaMemory compat)."""
        facts = await self._repo.get_by_user(
            user_id=self.user_id,
            graph_type="nikita",
            active_only=True,
        )
        return [f.fact for f in facts[:limit]]

    async def search_memory(
        self,
        query: str,
        graph_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search memory (NikitaMemory compat wrapper)."""
        return await self.search(
            query=query,
            graph_types=graph_types,
            limit=limit,
        )


async def get_supabase_memory_client(user_id: UUID) -> SupabaseMemory:
    """Factory function to create an initialized SupabaseMemory client.

    Reads OpenAI API key from settings and creates a fresh session.
    Caller is responsible for closing the session when done.
    """
    settings = get_settings()

    from nikita.db.database import get_session_maker

    session_maker = get_session_maker()
    session = session_maker()

    return SupabaseMemory(
        session=session,
        user_id=user_id,
        openai_api_key=settings.openai_api_key or "",
    )
