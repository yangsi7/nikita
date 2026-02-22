"""Shared pytest fixtures for pipeline tests (TX.1).

Provides factory fixtures for creating test contexts, mock sessions,
and fully-populated contexts for different testing scenarios.

AC-X.1.1: Async session fixtures, PipelineContext factory, stage isolation
AC-X.1.2-X.1.4: Mock fixtures for Haiku, embeddings, extraction (in mocks.py)
AC-X.1.5: Function-scoped sessions with clean DB state per test
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.pipeline.models import PipelineContext


@pytest.fixture
def make_context():
    """Factory function for creating PipelineContext instances.

    Usage:
        def test_something(make_context):
            ctx = make_context(chapter=3, platform="voice")
            # test with ctx

    Default values:
        - conversation_id: random UUID
        - user_id: random UUID
        - started_at: current UTC time
        - platform: "text"
        - chapter: 2
        - relationship_score: Decimal("65")
        - game_status: "active"
        - vices: ["dark_humor", "risk_taking"]
        - engagement_state: "engaged"
        - metrics: {intimacy: 55, passion: 60, trust: 50, secureness: 45}
    """
    def _factory(**overrides) -> PipelineContext:
        defaults = dict(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
            chapter=2,
            relationship_score=Decimal("65"),
            game_status="active",
            vices=["dark_humor", "risk_taking"],
            engagement_state="engaged",
            metrics={
                "intimacy": Decimal("55"),
                "passion": Decimal("60"),
                "trust": Decimal("50"),
                "secureness": Decimal("45"),
            },
        )
        defaults.update(overrides)
        return PipelineContext(**defaults)
    return _factory


@pytest.fixture
def mock_session():
    """Mock async SQLAlchemy session for stage isolation.

    Provides mocked methods for all common async session operations:
    - execute, flush, refresh, commit, rollback
    - All return AsyncMock() for awaitable behavior

    Usage:
        async def test_stage(mock_session):
            stage = ExtractionStage(session=mock_session)
            await stage.execute(ctx)
            assert mock_session.commit.called
    """
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def rich_context(make_context):
    """Pre-populated context with all stages filled (for prompt builder tests).

    This fixture simulates a context that has passed through all 8 pipeline
    stages (before PromptBuilderStage), with realistic data for each stage.

    Populated fields:
    - Extraction: 3 facts, 2 threads, 2 thoughts, summary, emotional_tone
    - Memory: facts_stored=3, facts_deduplicated=1
    - Life sim: 2 life events
    - Emotional: 4D emotional state
    - Game state: score_delta, chapter_changed, score_events
    - Conflict: active_conflict=False
    - Touchpoint: touchpoint_scheduled=False
    - Summary: daily_summary_updated=True

    Usage:
        def test_prompt_generation(rich_context):
            # Context already has all stage data populated
            assert len(rich_context.extracted_facts) == 3
            assert rich_context.emotional_state["arousal"] == 0.6
    """
    return make_context(
        # Extraction stage results
        extracted_facts=[
            {"content": "User loves cats", "type": "preference"},
            {"content": "Works in tech", "type": "fact"},
            {"content": "Lives in NYC", "type": "location"},
        ],
        extracted_threads=[
            {"topic": "weekend plans"},
            {"topic": "work stress"},
        ],
        extracted_thoughts=[
            {"text": "He seems genuine"},
            {"text": "I want to know more"},
        ],
        extraction_summary="Discussed work and pet preferences",
        emotional_tone="warm",

        # Memory update stage results
        facts_stored=3,
        facts_deduplicated=1,

        # Life sim stage results
        life_events=[
            {"type": "coffee", "description": "Had coffee with Lena"},
            {"type": "work", "description": "Found a new bug bounty"},
        ],

        # Emotional stage results
        emotional_state={
            "arousal": 0.6,
            "valence": 0.7,
            "dominance": 0.5,
            "intimacy": 0.4,
        },

        # Game state stage results
        score_delta=Decimal("2.5"),
        chapter_changed=False,
        decay_applied=False,
        score_events=["positive_response"],

        # Conflict stage results
        active_conflict=False,
        conflict_type=None,

        # Touchpoint stage results
        touchpoint_scheduled=False,

        # Summary stage results
        daily_summary_updated=True,
    )


@pytest.fixture
def mock_conversation():
    """Mock conversation object with messages.

    Provides a minimal conversation structure with:
    - id: UUID
    - user_id: UUID
    - messages: list of message objects with content

    Usage:
        def test_extraction(mock_conversation, make_context):
            ctx = make_context()
            ctx.conversation = mock_conversation
            # test extraction stage
    """
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        messages=[
            SimpleNamespace(
                id=uuid4(),
                content="I love cats",
                role="user",
                created_at=datetime.now(timezone.utc),
            ),
            SimpleNamespace(
                id=uuid4(),
                content="That's sweet! Tell me more.",
                role="assistant",
                created_at=datetime.now(timezone.utc),
            ),
        ],
    )


@pytest.fixture
def mock_user():
    """Mock user object with metrics and game state.

    Provides a user structure with:
    - id: UUID
    - chapter: 2
    - game_status: "active"
    - relationship_score: Decimal("65")
    - metrics: UserMetrics object
    - vices: list of UserVicePreference objects

    Usage:
        def test_game_state(mock_user, make_context):
            ctx = make_context()
            ctx.user = mock_user
            # test game state stage
    """
    return SimpleNamespace(
        id=uuid4(),
        chapter=2,
        game_status="active",
        relationship_score=Decimal("65"),
        metrics=SimpleNamespace(
            intimacy=Decimal("55"),
            passion=Decimal("60"),
            trust=Decimal("50"),
            secureness=Decimal("45"),
        ),
        vices=[
            SimpleNamespace(category="dark_humor", intensity_level=3, engagement_score=Decimal("0.7")),
            SimpleNamespace(category="risk_taking", intensity_level=2, engagement_score=Decimal("0.6")),
        ],
        engagement_state="engaged",
    )


# Import mock classes for convenience
from tests.pipeline.mocks import (
    MockHaikuEnricher,
    MockEmbeddingClient,
    MockExtractionAgent,
    MockReadyPromptRepo,
)


@pytest.fixture
def mock_haiku():
    """Mock Haiku enrichment service (no real LLM calls).

    Returns deterministic enriched text with "[Enriched]" prefix.

    Usage:
        async def test_prompt_enrichment(mock_haiku):
            enriched = await mock_haiku.enrich("System prompt")
            assert enriched.startswith("[Enriched]")
    """
    return MockHaikuEnricher()


@pytest.fixture
def mock_embeddings():
    """Mock embedding client (no OpenAI calls).

    Returns deterministic 1536-dim vectors based on text hash.

    Usage:
        async def test_memory_embedding(mock_embeddings):
            vec = await mock_embeddings.embed("User loves cats")
            assert len(vec) == 1536
    """
    return MockEmbeddingClient()


@pytest.fixture
def mock_extraction():
    """Mock extraction agent (no real LLM calls).

    Returns deterministic facts, threads, thoughts, and summary.

    Usage:
        async def test_extraction(mock_extraction):
            result = await mock_extraction.extract(messages)
            assert "facts" in result
    """
    return MockExtractionAgent()


@pytest.fixture
def mock_prompt_repo():
    """Mock in-memory ReadyPrompt repository.

    Stores prompts in memory, no database calls.

    Usage:
        async def test_prompt_storage(mock_prompt_repo):
            await mock_prompt_repo.set_current(
                user_id, "text", "prompt", 100, "v1", 150
            )
            prompt = await mock_prompt_repo.get_current(user_id, "text")
            assert prompt.prompt_text == "prompt"
    """
    return MockReadyPromptRepo()
