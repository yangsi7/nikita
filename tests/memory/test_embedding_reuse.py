"""Tests for Spec 102 Story 1: Embedding Reuse in add_fact() and find_similar().

T1.3: 3 tests verifying:
- add_fact() calls _generate_embedding exactly ONCE (no double-call)
- find_similar() with pre-computed embedding skips generation
- find_similar() without embedding param still generates (backward compat)
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.memory.supabase_memory import SupabaseMemory

FAKE_EMBEDDING = [0.1] * 1536


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def memory(user_id):
    session = AsyncMock()
    mem = SupabaseMemory(
        session=session,
        user_id=user_id,
        openai_api_key="sk-test",
    )
    return mem


class TestEmbeddingReuse:
    """Spec 102 FR-001: Fix embedding double-call in add_fact()."""

    @pytest.mark.asyncio
    async def test_add_fact_calls_generate_embedding_exactly_once(self, memory):
        """AC: add_fact() calls _generate_embedding() exactly ONCE.

        Before fix, add_fact() called _generate_embedding once directly,
        then find_similar() called it again internally = 2 API calls.
        After fix, the pre-computed embedding is passed to find_similar().
        """
        with patch.object(
            memory,
            "_generate_embedding",
            new_callable=AsyncMock,
            return_value=FAKE_EMBEDDING,
        ) as mock_embed:
            with patch.object(memory, "_repo") as mock_repo:
                mock_repo.add_fact = AsyncMock(return_value=MagicMock(id=uuid4()))
                mock_repo.semantic_search = AsyncMock(return_value=[])

                await memory.add_fact(
                    fact="User likes coffee",
                    graph_type="user",
                    source="conversation",
                    confidence=0.9,
                )

                # Critical assertion: only ONE embedding API call
                mock_embed.assert_awaited_once_with("User likes coffee")

    @pytest.mark.asyncio
    async def test_find_similar_skips_generation_with_precomputed_embedding(
        self, memory
    ):
        """AC: find_similar(text, embedding=emb) uses provided embedding, skips generation."""
        with patch.object(
            memory,
            "_generate_embedding",
            new_callable=AsyncMock,
            return_value=FAKE_EMBEDDING,
        ) as mock_embed:
            with patch.object(memory, "_repo") as mock_repo:
                mock_repo.semantic_search = AsyncMock(return_value=[])

                await memory.find_similar(
                    "User likes coffee",
                    embedding=FAKE_EMBEDDING,
                )

                # Should NOT call _generate_embedding when embedding is provided
                mock_embed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_find_similar_generates_embedding_when_not_provided(self, memory):
        """AC: find_similar() without embedding param still generates (backward compat)."""
        with patch.object(
            memory,
            "_generate_embedding",
            new_callable=AsyncMock,
            return_value=FAKE_EMBEDDING,
        ) as mock_embed:
            with patch.object(memory, "_repo") as mock_repo:
                mock_repo.semantic_search = AsyncMock(return_value=[])

                await memory.find_similar("User likes coffee")

                # Should call _generate_embedding when no embedding provided
                mock_embed.assert_awaited_once_with("User likes coffee")
