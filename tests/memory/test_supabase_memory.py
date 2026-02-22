"""Tests for SupabaseMemory — pgVector-based memory replacement for Neo4j/Graphiti.

Spec 042 Phase 1: T1.1, T1.2, T1.3, T1.6
- T1.1: SupabaseMemory class (add_fact, search, get_recent, context_for_prompt)
- T1.2: Duplicate detection (find_similar, supersession)
- T1.3: Embedding generation (OpenAI text-embedding-3-small, retry, batch)
- T1.6: Comprehensive test suite (40 tests target)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

# Will be imported once implemented
# from nikita.memory.supabase_memory import SupabaseMemory, get_supabase_memory_client


# ── Fixtures ─────────────────────────────────────────────────────────────────

FAKE_EMBEDDING = [0.1] * 1536  # 1536-dim placeholder


@pytest.fixture
def mock_session():
    """Create a mock async SQLAlchemy session."""
    session = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_embedding_client():
    """Create a mock OpenAI embedding client.

    Returns a callable async mock that produces 1536-dim vectors.
    """
    client = AsyncMock()
    # Default: return a single embedding
    client.create.return_value = MagicMock(
        data=[MagicMock(embedding=FAKE_EMBEDDING)]
    )
    return client


@pytest.fixture
def user_id():
    """Fixed test user UUID."""
    return uuid4()


@pytest.fixture
def memory(mock_session, mock_embedding_client, user_id):
    """Create a SupabaseMemory instance with mocks."""
    from nikita.memory.supabase_memory import SupabaseMemory

    return SupabaseMemory(
        session=mock_session,
        user_id=user_id,
        openai_api_key="test-openai-key",
    )


# ── T1.1: SupabaseMemory Class ──────────────────────────────────────────────


class TestSupabaseMemoryInit:
    """AC-1.1.1: Constructor accepts session + openai_api_key."""

    def test_init_stores_session(self, mock_session):
        from nikita.memory.supabase_memory import SupabaseMemory

        user_id = uuid4()
        mem = SupabaseMemory(
            session=mock_session,
            user_id=user_id,
            openai_api_key="sk-test",
        )
        assert mem.user_id == user_id

    def test_init_stores_openai_key(self, mock_session):
        from nikita.memory.supabase_memory import SupabaseMemory

        mem = SupabaseMemory(
            session=mock_session,
            user_id=uuid4(),
            openai_api_key="sk-test-key-123",
        )
        assert mem._openai_api_key == "sk-test-key-123"

    def test_async_context_manager(self, mock_session):
        """SupabaseMemory supports async with statement."""
        from nikita.memory.supabase_memory import SupabaseMemory

        mem = SupabaseMemory(
            session=mock_session,
            user_id=uuid4(),
            openai_api_key="sk-test",
        )
        assert hasattr(mem, "__aenter__")
        assert hasattr(mem, "__aexit__")


class TestAddFact:
    """AC-1.1.2: add_fact generates embedding and inserts via repository."""

    @pytest.mark.asyncio
    async def test_add_fact_returns_memory_fact(self, memory):
        """add_fact returns the created MemoryFact."""
        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "find_similar", new_callable=AsyncMock, return_value=None):
                with patch.object(memory, "_repo") as mock_repo:
                    mock_fact = MagicMock()
                    mock_fact.id = uuid4()
                    mock_fact.fact = "User likes coffee"
                    mock_repo.add_fact = AsyncMock(return_value=mock_fact)

                    result = await memory.add_fact(
                        fact="User likes coffee",
                        graph_type="user",
                        source="conversation",
                        confidence=0.9,
                    )
                    assert result.fact == "User likes coffee"

    @pytest.mark.asyncio
    async def test_add_fact_generates_embedding(self, memory):
        """add_fact calls _generate_embedding internally."""
        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING) as mock_embed:
            with patch.object(memory, "find_similar", new_callable=AsyncMock, return_value=None):
                with patch.object(memory, "_repo") as mock_repo:
                    mock_repo.add_fact = AsyncMock(return_value=MagicMock())

                    await memory.add_fact(
                        fact="User likes tea",
                        graph_type="user",
                        source="conversation",
                        confidence=0.8,
                    )
                    mock_embed.assert_awaited_once_with("User likes tea")

    @pytest.mark.asyncio
    async def test_add_fact_passes_all_fields_to_repo(self, memory, user_id):
        """add_fact forwards all arguments to repository."""
        conv_id = uuid4()
        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "find_similar", new_callable=AsyncMock, return_value=None):
                with patch.object(memory, "_repo") as mock_repo:
                    mock_repo.add_fact = AsyncMock(return_value=MagicMock())

                    await memory.add_fact(
                        fact="User works at Google",
                        graph_type="user",
                        source="onboarding",
                        confidence=0.95,
                        metadata={"source_msg": "I work at Google"},
                        conversation_id=conv_id,
                    )

                    mock_repo.add_fact.assert_awaited_once()
                    call_kwargs = mock_repo.add_fact.call_args[1]
                    assert call_kwargs["user_id"] == user_id
                    assert call_kwargs["fact"] == "User works at Google"
                    assert call_kwargs["graph_type"] == "user"
                    assert call_kwargs["source"] == "onboarding"
                    assert call_kwargs["confidence"] == 0.95
                    assert call_kwargs["embedding"] == FAKE_EMBEDDING
                    assert call_kwargs["conversation_id"] == conv_id

    @pytest.mark.asyncio
    async def test_add_fact_with_metadata(self, memory):
        """add_fact passes metadata to repository."""
        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "find_similar", new_callable=AsyncMock, return_value=None):
                with patch.object(memory, "_repo") as mock_repo:
                    mock_repo.add_fact = AsyncMock(return_value=MagicMock())

                    await memory.add_fact(
                        fact="User likes cats",
                        graph_type="user",
                        source="conversation",
                        confidence=0.7,
                        metadata={"topic": "pets", "sentiment": "positive"},
                    )
                    call_kwargs = mock_repo.add_fact.call_args[1]
                    assert call_kwargs["metadata"] == {"topic": "pets", "sentiment": "positive"}


class TestSearch:
    """AC-1.1.3: search embeds query + performs pgVector cosine search.

    Spec 102 FR-002: search() now uses a single semantic_search_batch() call
    instead of N sequential semantic_search() calls.
    """

    @pytest.mark.asyncio
    async def test_search_returns_facts(self, memory):
        """search returns list of dicts with fact, graph_type, created_at."""
        mock_fact = MagicMock()
        mock_fact.fact = "User likes cats"
        mock_fact.graph_type = "user"
        mock_fact.created_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
        mock_fact.confidence = 0.9

        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "_repo") as mock_repo:
                mock_repo.semantic_search_batch = AsyncMock(return_value=[(mock_fact, 0.15)])

                results = await memory.search(
                    query="what does user like",
                    graph_types=["user"],
                    limit=5,
                )
                assert len(results) == 1
                assert results[0]["fact"] == "User likes cats"
                assert results[0]["graph_type"] == "user"

    @pytest.mark.asyncio
    async def test_search_generates_query_embedding(self, memory):
        """search calls _generate_embedding with the query text."""
        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING) as mock_embed:
            with patch.object(memory, "_repo") as mock_repo:
                mock_repo.semantic_search_batch = AsyncMock(return_value=[])

                await memory.search(query="coffee preferences")
                mock_embed.assert_awaited_once_with("coffee preferences")

    @pytest.mark.asyncio
    async def test_search_filters_by_graph_types(self, memory):
        """search filters by graph_types via batch call (single DB query)."""
        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "_repo") as mock_repo:
                mock_repo.semantic_search_batch = AsyncMock(return_value=[])

                await memory.search(
                    query="test",
                    graph_types=["user", "relationship"],
                )
                # Single batch call with graph_types list (not per-type calls)
                mock_repo.semantic_search_batch.assert_awaited_once()
                call_kwargs = mock_repo.semantic_search_batch.call_args[1]
                assert call_kwargs["graph_types"] == ["user", "relationship"]

    @pytest.mark.asyncio
    async def test_search_respects_limit(self, memory):
        """search passes limit to repository."""
        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "_repo") as mock_repo:
                mock_repo.semantic_search_batch = AsyncMock(return_value=[])

                await memory.search(query="test", limit=3)
                call_kwargs = mock_repo.semantic_search_batch.call_args[1]
                assert call_kwargs["limit"] == 3

    @pytest.mark.asyncio
    async def test_search_respects_min_confidence(self, memory):
        """search passes min_confidence to repository."""
        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "_repo") as mock_repo:
                mock_repo.semantic_search_batch = AsyncMock(return_value=[])

                await memory.search(query="test", min_confidence=0.5)
                call_kwargs = mock_repo.semantic_search_batch.call_args[1]
                assert call_kwargs["min_confidence"] == 0.5

    @pytest.mark.asyncio
    async def test_search_all_graphs_by_default(self, memory):
        """search queries all 3 graphs in a single batch call when graph_types is None."""
        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "_repo") as mock_repo:
                mock_repo.semantic_search_batch = AsyncMock(return_value=[])

                await memory.search(query="test")
                # Single batch call covering all 3 graph types
                mock_repo.semantic_search_batch.assert_awaited_once()
                call_kwargs = mock_repo.semantic_search_batch.call_args[1]
                assert set(call_kwargs["graph_types"]) == {"user", "relationship", "nikita"}

    @pytest.mark.asyncio
    async def test_search_returns_distance_scores(self, memory):
        """search results include distance score for ranking."""
        mock_fact = MagicMock()
        mock_fact.fact = "fact1"
        mock_fact.graph_type = "user"
        mock_fact.created_at = datetime.now(timezone.utc)
        mock_fact.confidence = 0.9

        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "_repo") as mock_repo:
                mock_repo.semantic_search_batch = AsyncMock(return_value=[(mock_fact, 0.12)])

                results = await memory.search(query="test")
                assert "distance" in results[0]
                assert results[0]["distance"] == 0.12


class TestGetRecent:
    """AC-1.1.4: get_recent temporal query."""

    @pytest.mark.asyncio
    async def test_get_recent_returns_facts(self, memory):
        """get_recent returns list of MemoryFact records."""
        mock_fact = MagicMock()
        mock_fact.fact = "Recent event"

        with patch.object(memory, "_repo") as mock_repo:
            mock_repo.get_recent = AsyncMock(return_value=[mock_fact])

            results = await memory.get_recent(limit=10)
            assert len(results) == 1
            assert results[0].fact == "Recent event"

    @pytest.mark.asyncio
    async def test_get_recent_filters_by_graph_type(self, memory):
        """get_recent passes graph_type filter."""
        with patch.object(memory, "_repo") as mock_repo:
            mock_repo.get_recent = AsyncMock(return_value=[])

            await memory.get_recent(graph_type="nikita", limit=5)
            call_kwargs = mock_repo.get_recent.call_args[1]
            assert call_kwargs["graph_type"] == "nikita"

    @pytest.mark.asyncio
    async def test_get_recent_respects_limit(self, memory):
        """get_recent passes limit."""
        with patch.object(memory, "_repo") as mock_repo:
            mock_repo.get_recent = AsyncMock(return_value=[])

            await memory.get_recent(limit=25)
            call_kwargs = mock_repo.get_recent.call_args[1]
            assert call_kwargs["limit"] == 25


class TestGetContextForPrompt:
    """get_context_for_prompt returns formatted string for LLM injection."""

    @pytest.mark.asyncio
    async def test_returns_formatted_context(self, memory):
        """Returns format: [date] (label) fact."""
        mock_results = [
            {
                "fact": "User works at Google",
                "graph_type": "user",
                "created_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
                "distance": 0.1,
            },
            {
                "fact": "We argued about pineapple pizza",
                "graph_type": "relationship",
                "created_at": datetime(2026, 1, 14, tzinfo=timezone.utc),
                "distance": 0.2,
            },
        ]

        with patch.object(memory, "search", new_callable=AsyncMock, return_value=mock_results):
            context = await memory.get_context_for_prompt("tell me about yourself")
            assert "[2026-01-15]" in context
            assert "(About them)" in context
            assert "User works at Google" in context
            assert "(Our history)" in context

    @pytest.mark.asyncio
    async def test_empty_results_returns_message(self, memory):
        """Returns default message when no memories found."""
        with patch.object(memory, "search", new_callable=AsyncMock, return_value=[]):
            context = await memory.get_context_for_prompt("hello")
            assert "No relevant memories found" in context

    @pytest.mark.asyncio
    async def test_graph_type_labels(self, memory):
        """Maps graph types to human-readable labels."""
        mock_results = [
            {
                "fact": "Nikita's life event",
                "graph_type": "nikita",
                "created_at": datetime(2026, 1, 10, tzinfo=timezone.utc),
                "distance": 0.1,
            },
        ]
        with patch.object(memory, "search", new_callable=AsyncMock, return_value=mock_results):
            context = await memory.get_context_for_prompt("what's up")
            assert "(My life)" in context


# ── T1.2: Duplicate Detection ────────────────────────────────────────────────


class TestFindSimilar:
    """AC-1.2.1: find_similar finds near-duplicate facts."""

    @pytest.mark.asyncio
    async def test_find_similar_returns_match(self, memory):
        """Returns existing fact if similarity > threshold."""
        mock_fact = MagicMock()
        mock_fact.fact = "User likes coffee"
        mock_fact.id = uuid4()

        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "_repo") as mock_repo:
                # Distance 0.03 → similarity 0.97 > 0.95 threshold
                mock_repo.semantic_search = AsyncMock(return_value=[(mock_fact, 0.03)])

                result = await memory.find_similar("User likes coffee", threshold=0.95)
                assert result is not None
                assert result.fact == "User likes coffee"

    @pytest.mark.asyncio
    async def test_find_similar_returns_none_below_threshold(self, memory):
        """Returns None if no facts are similar enough."""
        mock_fact = MagicMock()
        mock_fact.fact = "User likes dogs"

        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "_repo") as mock_repo:
                # Distance 0.3 → similarity 0.7 < 0.95 threshold
                mock_repo.semantic_search = AsyncMock(return_value=[(mock_fact, 0.3)])

                result = await memory.find_similar("User likes coffee", threshold=0.95)
                assert result is None

    @pytest.mark.asyncio
    async def test_find_similar_empty_results(self, memory):
        """Returns None when no results at all."""
        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "_repo") as mock_repo:
                mock_repo.semantic_search = AsyncMock(return_value=[])

                result = await memory.find_similar("something new")
                assert result is None


class TestDeduplication:
    """AC-1.2.2 + AC-1.2.3: add_fact supersedes duplicates."""

    @pytest.mark.asyncio
    async def test_add_fact_supersedes_duplicate(self, memory):
        """If similar fact exists, old fact is deactivated and new one points to it."""
        old_fact = MagicMock()
        old_fact.id = uuid4()
        old_fact.fact = "User likes coffee"

        new_fact = MagicMock()
        new_fact.id = uuid4()
        new_fact.fact = "User really loves coffee"

        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "find_similar", new_callable=AsyncMock, return_value=old_fact):
                with patch.object(memory, "_repo") as mock_repo:
                    mock_repo.add_fact = AsyncMock(return_value=new_fact)
                    mock_repo.deactivate = AsyncMock(return_value=True)

                    result = await memory.add_fact(
                        fact="User really loves coffee",
                        graph_type="user",
                        source="conversation",
                        confidence=0.9,
                    )

                    # Old fact should be deactivated with superseded_by
                    mock_repo.deactivate.assert_awaited_once_with(
                        old_fact.id,
                        superseded_by_id=new_fact.id,
                    )

    @pytest.mark.asyncio
    async def test_add_fact_no_dedup_when_no_similar(self, memory):
        """If no similar fact, just inserts normally (no deactivation)."""
        with patch.object(memory, "_generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING):
            with patch.object(memory, "find_similar", new_callable=AsyncMock, return_value=None):
                with patch.object(memory, "_repo") as mock_repo:
                    mock_repo.add_fact = AsyncMock(return_value=MagicMock())
                    mock_repo.deactivate = AsyncMock()

                    await memory.add_fact(
                        fact="User likes sushi",
                        graph_type="user",
                        source="conversation",
                        confidence=0.8,
                    )

                    mock_repo.deactivate.assert_not_awaited()


# ── T1.3: Embedding Generation ───────────────────────────────────────────────


class TestEmbeddingGeneration:
    """AC-1.3.1: Uses OpenAI text-embedding-3-small (1536 dims)."""

    @pytest.mark.asyncio
    async def test_generate_embedding_calls_openai(self, memory):
        """_generate_embedding calls OpenAI embeddings API."""
        with patch("nikita.memory.supabase_memory.openai.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            mock_client.embeddings.create = AsyncMock(
                return_value=MagicMock(data=[MagicMock(embedding=FAKE_EMBEDDING)])
            )
            MockClient.return_value = mock_client

            # Re-create memory to pick up mock
            from nikita.memory.supabase_memory import SupabaseMemory

            mem = SupabaseMemory(
                session=AsyncMock(),
                user_id=uuid4(),
                openai_api_key="sk-test",
            )
            result = await mem._generate_embedding("Hello world")
            assert len(result) == 1536

    @pytest.mark.asyncio
    async def test_generate_embedding_uses_correct_model(self, memory):
        """Uses text-embedding-3-small model."""
        with patch("nikita.memory.supabase_memory.openai.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            mock_client.embeddings.create = AsyncMock(
                return_value=MagicMock(data=[MagicMock(embedding=FAKE_EMBEDDING)])
            )
            MockClient.return_value = mock_client

            from nikita.memory.supabase_memory import SupabaseMemory

            mem = SupabaseMemory(
                session=AsyncMock(),
                user_id=uuid4(),
                openai_api_key="sk-test",
            )
            await mem._generate_embedding("test text")
            call_kwargs = mock_client.embeddings.create.call_args[1]
            assert call_kwargs["model"] == "text-embedding-3-small"


class TestBatchEmbedding:
    """AC-1.3.2: Batch embedding support."""

    @pytest.mark.asyncio
    async def test_batch_embed_multiple_texts(self, memory):
        """generate_embeddings_batch handles multiple texts."""
        batch_embeddings = [FAKE_EMBEDDING, FAKE_EMBEDDING, FAKE_EMBEDDING]
        with patch("nikita.memory.supabase_memory.openai.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            mock_client.embeddings.create = AsyncMock(
                return_value=MagicMock(
                    data=[
                        MagicMock(embedding=FAKE_EMBEDDING),
                        MagicMock(embedding=FAKE_EMBEDDING),
                        MagicMock(embedding=FAKE_EMBEDDING),
                    ]
                )
            )
            MockClient.return_value = mock_client

            from nikita.memory.supabase_memory import SupabaseMemory

            mem = SupabaseMemory(
                session=AsyncMock(),
                user_id=uuid4(),
                openai_api_key="sk-test",
            )
            results = await mem.generate_embeddings_batch(
                ["text1", "text2", "text3"]
            )
            assert len(results) == 3
            assert all(len(e) == 1536 for e in results)


class TestEmbeddingRetry:
    """AC-1.3.3: Retry 3x with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retries_on_api_error(self, memory):
        """Retries up to 3 times on OpenAI API failure."""
        with patch("nikita.memory.supabase_memory.openai.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            # Fail twice, succeed on third try
            mock_client.embeddings.create = AsyncMock(
                side_effect=[
                    Exception("rate limit"),
                    Exception("timeout"),
                    MagicMock(data=[MagicMock(embedding=FAKE_EMBEDDING)]),
                ]
            )
            MockClient.return_value = mock_client

            from nikita.memory.supabase_memory import SupabaseMemory

            mem = SupabaseMemory(
                session=AsyncMock(),
                user_id=uuid4(),
                openai_api_key="sk-test",
            )
            with patch("nikita.memory.supabase_memory.asyncio.sleep", new_callable=AsyncMock):
                result = await mem._generate_embedding("test")
                assert len(result) == 1536
                assert mock_client.embeddings.create.call_count == 3


class TestEmbeddingFailure:
    """AC-1.3.4: On persistent failure, raise with details."""

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """Raises EmbeddingError after 3 failed attempts."""
        with patch("nikita.memory.supabase_memory.openai.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            mock_client.embeddings.create = AsyncMock(
                side_effect=Exception("persistent failure")
            )
            MockClient.return_value = mock_client

            from nikita.memory.supabase_memory import SupabaseMemory, EmbeddingError

            mem = SupabaseMemory(
                session=AsyncMock(),
                user_id=uuid4(),
                openai_api_key="sk-test",
            )
            with patch("nikita.memory.supabase_memory.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(EmbeddingError):
                    await mem._generate_embedding("test")


# ── NikitaMemory Compatibility Methods ───────────────────────────────────────


class TestNikitaMemoryCompat:
    """SupabaseMemory provides NikitaMemory-compatible convenience methods."""

    @pytest.mark.asyncio
    async def test_add_user_fact(self, memory):
        """add_user_fact wraps add_fact with graph_type='user'."""
        with patch.object(memory, "add_fact", new_callable=AsyncMock, return_value=MagicMock()) as mock_add:
            await memory.add_user_fact("User likes coffee", confidence=0.9)
            mock_add.assert_awaited_once()
            call_kwargs = mock_add.call_args[1]
            assert call_kwargs["graph_type"] == "user"
            assert call_kwargs["confidence"] == 0.9
            assert "User likes coffee" in call_kwargs["fact"]

    @pytest.mark.asyncio
    async def test_get_user_facts(self, memory):
        """get_user_facts returns list of fact strings from user graph."""
        mock_fact1 = MagicMock()
        mock_fact1.fact = "Likes coffee"
        mock_fact2 = MagicMock()
        mock_fact2.fact = "Works at Google"

        with patch.object(memory, "_repo") as mock_repo:
            mock_repo.get_by_user = AsyncMock(return_value=[mock_fact1, mock_fact2])

            facts = await memory.get_user_facts(limit=50)
            assert facts == ["Likes coffee", "Works at Google"]

    @pytest.mark.asyncio
    async def test_add_relationship_episode(self, memory):
        """add_relationship_episode wraps add_fact with graph_type='relationship'."""
        with patch.object(memory, "add_fact", new_callable=AsyncMock, return_value=MagicMock()) as mock_add:
            await memory.add_relationship_episode("First date at the park")
            mock_add.assert_awaited_once()
            call_kwargs = mock_add.call_args[1]
            assert call_kwargs["graph_type"] == "relationship"

    @pytest.mark.asyncio
    async def test_get_relationship_episodes(self, memory):
        """get_relationship_episodes returns list of episode strings."""
        mock_fact = MagicMock()
        mock_fact.fact = "Went to the movies together"

        with patch.object(memory, "_repo") as mock_repo:
            mock_repo.get_by_user = AsyncMock(return_value=[mock_fact])

            episodes = await memory.get_relationship_episodes(limit=50)
            assert episodes == ["Went to the movies together"]

    @pytest.mark.asyncio
    async def test_add_nikita_event(self, memory):
        """add_nikita_event wraps add_fact with graph_type='nikita'."""
        with patch.object(memory, "add_fact", new_callable=AsyncMock, return_value=MagicMock()) as mock_add:
            await memory.add_nikita_event("Got promoted at work")
            mock_add.assert_awaited_once()
            call_kwargs = mock_add.call_args[1]
            assert call_kwargs["graph_type"] == "nikita"

    @pytest.mark.asyncio
    async def test_get_nikita_events(self, memory):
        """get_nikita_events returns list of event strings from nikita graph."""
        mock_fact = MagicMock()
        mock_fact.fact = "Started new project at work"

        with patch.object(memory, "_repo") as mock_repo:
            mock_repo.get_by_user = AsyncMock(return_value=[mock_fact])

            events = await memory.get_nikita_events(limit=50)
            assert events == ["Started new project at work"]

    @pytest.mark.asyncio
    async def test_search_memory_compat(self, memory):
        """search_memory wraps search for NikitaMemory compatibility."""
        mock_results = [
            {"fact": "Test fact", "graph_type": "user", "created_at": datetime.now(timezone.utc), "distance": 0.1},
        ]
        with patch.object(memory, "search", new_callable=AsyncMock, return_value=mock_results):
            results = await memory.search_memory("test query", limit=5)
            assert len(results) == 1
            assert results[0]["fact"] == "Test fact"


# ── Factory Function ─────────────────────────────────────────────────────────


class TestFactory:
    """get_supabase_memory_client factory function."""

    @pytest.mark.asyncio
    async def test_factory_creates_instance(self):
        """Factory returns initialized SupabaseMemory."""
        with patch("nikita.memory.supabase_memory.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="sk-test")
            mock_session = AsyncMock()
            with patch("nikita.db.database.get_session_maker") as mock_maker:
                mock_maker.return_value = MagicMock(return_value=mock_session)
                with patch("nikita.db.database.get_async_engine"):
                    from nikita.memory.supabase_memory import get_supabase_memory_client

                    client = await get_supabase_memory_client(uuid4())
                    assert client is not None
                    assert client._openai_api_key == "sk-test"
