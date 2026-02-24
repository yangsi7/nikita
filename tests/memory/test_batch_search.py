"""Tests for Spec 102 Story 2: Batch Memory Search.

T2.3: 3 tests verifying:
- search() with 3 types makes 1 DB call via semantic_search_batch
- Results sorted by distance across all types
- Empty results handled gracefully
"""

from datetime import datetime, timezone
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


def _make_fact(fact_text: str, graph_type: str, distance: float):
    """Helper to create a (MemoryFact mock, distance) tuple."""
    fact = MagicMock()
    fact.fact = fact_text
    fact.graph_type = graph_type
    fact.created_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
    fact.confidence = 0.9
    return (fact, distance)


class TestBatchSearch:
    """Spec 102 FR-002: Batch memory search via single DB call."""

    @pytest.mark.asyncio
    async def test_search_multi_type_uses_single_batch_call(self, memory, user_id):
        """AC: search(graph_types=["user", "relationship", "nikita"]) makes 1 DB call."""
        with patch.object(
            memory,
            "_generate_embedding",
            new_callable=AsyncMock,
            return_value=FAKE_EMBEDDING,
        ):
            with patch.object(memory, "_repo") as mock_repo:
                mock_repo.semantic_search_batch = AsyncMock(return_value=[
                    _make_fact("User likes coffee", "user", 0.1),
                    _make_fact("We talked about pets", "relationship", 0.2),
                ])

                results = await memory.search(
                    query="coffee",
                    graph_types=["user", "relationship", "nikita"],
                )

                # Single batch call — NOT 3 sequential calls
                mock_repo.semantic_search_batch.assert_awaited_once()
                call_kwargs = mock_repo.semantic_search_batch.call_args[1]
                assert call_kwargs["user_id"] == user_id
                assert call_kwargs["graph_types"] == ["user", "relationship", "nikita"]

                assert len(results) == 2
                assert results[0]["fact"] == "User likes coffee"

    @pytest.mark.asyncio
    async def test_search_results_sorted_by_distance(self, memory):
        """AC: Results sorted by distance across all graph types."""
        with patch.object(
            memory,
            "_generate_embedding",
            new_callable=AsyncMock,
            return_value=FAKE_EMBEDDING,
        ):
            with patch.object(memory, "_repo") as mock_repo:
                # DB returns pre-sorted by distance (pgVector ORDER BY)
                mock_repo.semantic_search_batch = AsyncMock(return_value=[
                    _make_fact("Closest fact", "user", 0.05),
                    _make_fact("Middle fact", "relationship", 0.15),
                    _make_fact("Farthest fact", "nikita", 0.30),
                ])

                results = await memory.search(query="test")

                assert results[0]["distance"] == 0.05
                assert results[1]["distance"] == 0.15
                assert results[2]["distance"] == 0.30

    @pytest.mark.asyncio
    async def test_search_empty_results(self, memory):
        """AC: Empty results handled gracefully."""
        with patch.object(
            memory,
            "_generate_embedding",
            new_callable=AsyncMock,
            return_value=FAKE_EMBEDDING,
        ):
            with patch.object(memory, "_repo") as mock_repo:
                mock_repo.semantic_search_batch = AsyncMock(return_value=[])

                results = await memory.search(query="nonexistent topic")

                assert results == []
