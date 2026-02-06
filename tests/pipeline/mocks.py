"""Mock classes for pipeline testing (TX.1).

Provides deterministic mock implementations that avoid real external calls:
- MockHaikuEnricher: No LLM calls for prompt enrichment
- MockEmbeddingClient: No OpenAI calls for embeddings
- MockExtractionAgent: No LLM calls for entity extraction
- MockReadyPromptRepo: In-memory prompt storage

AC-X.1.2: MockHaikuEnricher - deterministic enriched text
AC-X.1.3: MockEmbeddingClient - deterministic 1536-dim vectors
AC-X.1.4: MockExtractionAgent - deterministic facts/threads/thoughts
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import UUID


class MockHaikuEnricher:
    """Deterministic Haiku enrichment mock (no real LLM calls).

    Simulates narrative enrichment by prepending "[Enriched]" prefix
    and optionally truncating to simulate processing.

    Methods:
        enrich(raw_prompt, platform) -> enriched text
        enrich_section(section, context) -> enriched section
    """

    async def enrich(self, raw_prompt: str, platform: str = "text") -> str:
        """Return slightly modified prompt (simulating narrative enrichment).

        Args:
            raw_prompt: Raw system prompt to enrich
            platform: "text" or "voice"

        Returns:
            "[Enriched] {first 100 chars}..." to simulate processing
        """
        truncated = raw_prompt[:100] if len(raw_prompt) > 100 else raw_prompt
        suffix = "..." if len(raw_prompt) > 100 else ""
        return f"[Enriched] {truncated}{suffix}"

    async def enrich_section(self, section: str, context: dict[str, Any]) -> str:
        """Enrich a section with context.

        Args:
            section: Section of prompt to enrich
            context: Context dict (ignored in mock)

        Returns:
            "[Enriched section] {section}"
        """
        return f"[Enriched section] {section}"


class MockEmbeddingClient:
    """Deterministic embedding mock (no OpenAI calls).

    Generates 1536-dimensional vectors based on text hash.
    Same text always produces same vector.

    Methods:
        embed(text) -> 1536-dim vector
        embed_batch(texts) -> list of vectors
    """

    DIMENSION = 1536

    async def embed(self, text: str) -> list[float]:
        """Return deterministic 1536-dim vector based on text hash.

        Uses MD5 hash of text to generate reproducible vector.
        Each dimension is derived from a byte of the hash.

        Args:
            text: Text to embed

        Returns:
            List of 1536 floats in range [0.0, 1.0]
        """
        import hashlib

        # Generate hash from text
        h = int(hashlib.md5(text.encode()).hexdigest(), 16)

        # Create deterministic but unique vector
        # Use modulo and bit shifting for variation
        vector = []
        for i in range(self.DIMENSION):
            # Deterministic: same text -> same hash -> same vector
            byte_val = (h >> (i % 128)) & 0xFF
            normalized = byte_val / 255.0
            vector.append(normalized)

        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of 1536-dim vectors (one per text)
        """
        return [await self.embed(t) for t in texts]


class MockExtractionAgent:
    """Deterministic extraction mock (no real LLM calls).

    Returns fixed extraction results for testing without
    calling Claude or other LLM services.

    Methods:
        extract(messages, user_id) -> extraction dict
    """

    async def extract(
        self, messages: list[Any], user_id: UUID | None = None
    ) -> dict[str, Any]:
        """Extract facts, threads, thoughts from messages.

        Args:
            messages: List of message objects
            user_id: Optional user ID (ignored in mock)

        Returns:
            Dict with:
                - facts: list of fact dicts
                - threads: list of thread dicts
                - thoughts: list of thought dicts
                - summary: extraction summary string
                - emotional_tone: tone classification
        """
        return {
            "facts": [
                {
                    "content": "Mock fact extracted from conversation",
                    "type": "preference",
                }
            ],
            "threads": [{"topic": "mock conversation topic"}],
            "thoughts": [{"text": "mock internal thought"}],
            "summary": "Mock extraction summary",
            "emotional_tone": "neutral",
        }


class MockReadyPromptRepo:
    """In-memory ReadyPrompt repository mock (no database calls).

    Stores prompts in a dict keyed by (user_id, platform).
    Useful for testing prompt storage without database overhead.

    Methods:
        get_current(user_id, platform) -> prompt or None
        set_current(...) -> prompt object
    """

    def __init__(self):
        """Initialize empty in-memory storage."""
        self._prompts: dict[tuple[str, str], Any] = {}

    async def get_current(
        self, user_id: UUID, platform: str
    ) -> SimpleNamespace | None:
        """Get current prompt for user and platform.

        Args:
            user_id: User UUID
            platform: "text" or "voice"

        Returns:
            SimpleNamespace with prompt fields, or None if not found
        """
        return self._prompts.get((str(user_id), platform))

    async def set_current(
        self,
        user_id: UUID,
        platform: str,
        prompt_text: str,
        token_count: int,
        pipeline_version: str,
        generation_time_ms: float,
        context_snapshot: dict[str, Any] | None = None,
        conversation_id: UUID | None = None,
    ) -> SimpleNamespace:
        """Store current prompt for user and platform.

        Args:
            user_id: User UUID
            platform: "text" or "voice"
            prompt_text: Full prompt text
            token_count: Token count
            pipeline_version: Pipeline version (e.g., "v1", "v2")
            generation_time_ms: Generation time in milliseconds
            context_snapshot: Optional context snapshot dict
            conversation_id: Optional conversation UUID

        Returns:
            SimpleNamespace representing stored prompt
        """
        prompt = SimpleNamespace(
            user_id=user_id,
            platform=platform,
            prompt_text=prompt_text,
            token_count=token_count,
            pipeline_version=pipeline_version,
            generation_time_ms=generation_time_ms,
            is_current=True,
            context_snapshot=context_snapshot,
            conversation_id=conversation_id,
        )
        self._prompts[(str(user_id), platform)] = prompt
        return prompt

    async def get_history(
        self, user_id: UUID, platform: str, limit: int = 10
    ) -> list[SimpleNamespace]:
        """Get prompt history (mock returns empty list).

        Args:
            user_id: User UUID
            platform: "text" or "voice"
            limit: Max prompts to return

        Returns:
            Empty list (history not implemented in mock)
        """
        return []

    def clear(self) -> None:
        """Clear all stored prompts (useful for test cleanup)."""
        self._prompts.clear()
