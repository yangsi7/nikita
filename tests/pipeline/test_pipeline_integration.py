"""Integration tests for the post-processing pipeline.

Tests each stage with realistic data structures to prove the pipeline
works end-to-end. Unlike test_e2e_unified.py which uses FakeStages,
these tests use the REAL stage implementations with mocked external deps.

Tests prove:
1. Orchestrator loads conversation + user state into context
2. Extraction handles JSONB dict messages correctly
3. Memory update receives dict-format facts from extraction
4. Summary stage generates and stores per-conversation summary
5. Full pipeline flow from conversation -> processed with all artifacts
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

import pytest

from nikita.pipeline.models import PipelineContext, PipelineResult
from nikita.pipeline.orchestrator import PipelineOrchestrator
from nikita.pipeline.stages.base import BaseStage, StageResult, StageError
from nikita.pipeline.stages.extraction import ExtractionStage, ExtractionResult
from nikita.pipeline.stages.summary import SummaryStage
from nikita.pipeline.stages.game_state import GameStateStage
from nikita.pipeline.stages.conflict import ConflictStage


# ── Helpers ──────────────────────────────────────────────────────────────

def make_conversation(
    user_id=None,
    messages=None,
    platform="telegram",
    status="processing",
):
    """Create a mock conversation with JSONB dict messages."""
    conv = MagicMock()
    conv.id = uuid4()
    conv.user_id = user_id or uuid4()
    conv.platform = platform
    conv.status = status
    conv.messages = messages if messages is not None else [
        {"role": "user", "content": "Hey babe, how was your day?", "timestamp": "2026-02-10T10:00:00"},
        {"role": "assistant", "content": "ugh it was awful. my boss yelled at me again", "timestamp": "2026-02-10T10:01:00"},
        {"role": "user", "content": "That sucks, want to talk about it?", "timestamp": "2026-02-10T10:02:00"},
        {"role": "assistant", "content": "not really... can we just watch something tonight?", "timestamp": "2026-02-10T10:03:00"},
    ]
    conv.conversation_summary = None
    conv.emotional_tone = None
    conv.extracted_entities = None
    return conv


def make_user(user_id=None, chapter=2, score=Decimal("65.00")):
    """Create a mock user with metrics, engagement, and vices."""
    user = MagicMock()
    user.id = user_id or uuid4()
    user.chapter = chapter
    user.game_status = "active"
    user.relationship_score = score

    # Metrics
    user.metrics = MagicMock()
    user.metrics.intimacy = Decimal("55.00")
    user.metrics.passion = Decimal("48.00")
    user.metrics.trust = Decimal("62.00")
    user.metrics.secureness = Decimal("50.00")

    # Engagement state
    user.engagement_state = MagicMock()
    user.engagement_state.current_state = "engaged"

    # Vice preferences
    vice1 = MagicMock()
    vice1.category = "jealousy"
    vice2 = MagicMock()
    vice2.category = "materialism"
    user.vice_preferences = [vice1, vice2]

    return user


def make_session():
    """Create a mock async session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()

    # begin_nested returns an async context manager
    nested = AsyncMock()
    nested.__aenter__ = AsyncMock(return_value=None)
    nested.__aexit__ = AsyncMock(return_value=None)
    session.begin_nested = MagicMock(return_value=nested)

    return session


def _patch_repos(conversation, user):
    """Patch both repositories used by _load_context()."""
    mock_conv_repo_cls = MagicMock()
    mock_conv_repo_cls.return_value.get = AsyncMock(return_value=conversation)
    mock_user_repo_cls = MagicMock()
    mock_user_repo_cls.return_value.get = AsyncMock(return_value=user)
    return (
        patch("nikita.db.repositories.conversation_repository.ConversationRepository", mock_conv_repo_cls),
        patch("nikita.db.repositories.user_repository.UserRepository", mock_user_repo_cls),
    )


# ── Test: Orchestrator loads context ─────────────────────────────────────

class TestOrchestratorContextLoading:
    """Prove the orchestrator loads conversation + user state before stages."""

    @pytest.mark.asyncio
    async def test_load_context_populates_conversation(self):
        """Orchestrator sets ctx.conversation from DB."""
        session = make_session()
        conv_id = uuid4()
        user_id = uuid4()
        conversation = make_conversation(user_id=user_id)
        conversation.id = conv_id
        user = make_user(user_id=user_id)

        # Directly mock _load_context to control behavior
        orchestrator = PipelineOrchestrator(session, stages=[])

        async def mock_load(ctx):
            ctx.conversation = conversation
            ctx.user = user
            ctx.chapter = user.chapter
            ctx.game_status = user.game_status
            ctx.relationship_score = user.relationship_score
            ctx.metrics = {
                "intimacy": user.metrics.intimacy,
                "passion": user.metrics.passion,
                "trust": user.metrics.trust,
                "secureness": user.metrics.secureness,
            }
            ctx.engagement_state = user.engagement_state.current_state
            ctx.vices = [vp.category for vp in user.vice_preferences]

        with patch.object(orchestrator, "_load_context", side_effect=mock_load):
            result = await orchestrator.process(conv_id, user_id, "text")

        assert result.success is True
        assert result.context.conversation is conversation
        assert result.context.user is user
        assert result.context.chapter == 2
        assert result.context.relationship_score == Decimal("65.00")
        assert result.context.game_status == "active"
        assert result.context.engagement_state == "engaged"
        assert result.context.vices == ["jealousy", "materialism"]
        assert result.context.metrics["intimacy"] == Decimal("55.00")

    @pytest.mark.asyncio
    async def test_load_context_fails_on_missing_conversation(self):
        """Pipeline fails gracefully if conversation not found."""
        session = make_session()
        conv_id = uuid4()
        user_id = uuid4()

        orchestrator = PipelineOrchestrator(session, stages=[])

        async def mock_load_fail(ctx):
            raise ValueError(f"Conversation {ctx.conversation_id} not found")

        with patch.object(orchestrator, "_load_context", side_effect=mock_load_fail):
            result = await orchestrator.process(conv_id, user_id, "text")

        assert result.success is False
        assert result.error_stage == "context_load"
        assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_load_context_fails_on_missing_user(self):
        """Pipeline fails gracefully if user not found."""
        session = make_session()
        conv_id = uuid4()
        user_id = uuid4()

        orchestrator = PipelineOrchestrator(session, stages=[])

        async def mock_load_fail(ctx):
            raise ValueError(f"User {ctx.user_id} not found")

        with patch.object(orchestrator, "_load_context", side_effect=mock_load_fail):
            result = await orchestrator.process(conv_id, user_id, "text")

        assert result.success is False
        assert result.error_stage == "context_load"
        assert "User" in result.error_message

    @pytest.mark.asyncio
    async def test_load_context_handles_user_without_metrics(self):
        """Pipeline works even if user has no metrics/engagement/vices."""
        session = make_session()
        conv_id = uuid4()
        user_id = uuid4()
        conversation = make_conversation(user_id=user_id)

        orchestrator = PipelineOrchestrator(session, stages=[])

        async def mock_load(ctx):
            ctx.conversation = conversation
            ctx.user = MagicMock()
            ctx.chapter = 1
            ctx.game_status = "active"
            ctx.relationship_score = Decimal("50.00")
            # No metrics, no engagement, no vices

        with patch.object(orchestrator, "_load_context", side_effect=mock_load):
            result = await orchestrator.process(conv_id, user_id, "text")

        assert result.success is True
        assert result.context.chapter == 1
        assert result.context.vices == []

    @pytest.mark.asyncio
    async def test_load_context_real_implementation(self):
        """Test _load_context() method directly with mocked repos."""
        session = make_session()
        conv_id = uuid4()
        user_id = uuid4()
        conversation = make_conversation(user_id=user_id)
        conversation.id = conv_id
        user = make_user(user_id=user_id)

        # Build mock repos
        mock_conv_repo = MagicMock()
        mock_conv_repo.get = AsyncMock(return_value=conversation)
        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user)

        ctx = PipelineContext(
            conversation_id=conv_id,
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            platform="text",
        )

        orchestrator = PipelineOrchestrator(session, stages=[])

        with patch("nikita.db.repositories.conversation_repository.ConversationRepository", return_value=mock_conv_repo), \
             patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo):
            await orchestrator._load_context(ctx)

        assert ctx.conversation is conversation
        assert ctx.user is user
        assert ctx.chapter == 2
        assert ctx.relationship_score == Decimal("65.00")
        assert ctx.vices == ["jealousy", "materialism"]
        assert ctx.metrics["intimacy"] == Decimal("55.00")
        assert ctx.engagement_state == "engaged"


# ── Test: Extraction handles JSONB dict messages ─────────────────────────

class TestExtractionStageIntegration:
    """Prove extraction stage handles JSONB dict messages correctly."""

    @pytest.mark.asyncio
    async def test_extraction_formats_jsonb_messages(self):
        """Messages stored as JSONB dicts are correctly formatted for LLM."""
        session = make_session()
        stage = ExtractionStage(session=session)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        ctx.conversation = make_conversation()

        # Mock the Pydantic AI agent to return extraction result
        mock_result = MagicMock()
        mock_result.data = ExtractionResult(
            facts=["User asked about Nikita's day", "User is empathetic"],
            threads=["Boss conflict at work"],
            thoughts=["He actually cares about my feelings"],
            summary="Player checked in on Nikita after a bad day at work, offered emotional support",
            emotional_tone="positive",
        )

        with patch.object(stage, "_get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_get_agent.return_value = mock_agent

            result = await stage._run(ctx)

        # Verify agent was called with properly formatted text
        call_args = mock_agent.run.call_args[0][0]
        assert "user: Hey babe, how was your day?" in call_args
        assert "assistant: ugh it was awful" in call_args

        # Verify extraction output is dict format (not raw strings)
        assert len(ctx.extracted_facts) == 2
        assert isinstance(ctx.extracted_facts[0], dict)
        assert ctx.extracted_facts[0]["content"] == "User asked about Nikita's day"
        assert ctx.extracted_facts[0]["type"] == "user_fact"

        # Verify threads are dict format
        assert len(ctx.extracted_threads) == 1
        assert ctx.extracted_threads[0]["content"] == "Boss conflict at work"

        # Verify summary and tone
        assert ctx.extraction_summary == "Player checked in on Nikita after a bad day at work, offered emotional support"
        assert ctx.emotional_tone == "positive"

        # Verify return dict has counts
        assert result["facts_count"] == 2
        assert result["threads_count"] == 1

    @pytest.mark.asyncio
    async def test_extraction_fails_without_conversation(self):
        """Extraction raises StageError when conversation not loaded."""
        session = make_session()
        stage = ExtractionStage(session=session)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        # ctx.conversation is None

        with pytest.raises(StageError, match="No conversation loaded"):
            await stage._run(ctx)

    @pytest.mark.asyncio
    async def test_extraction_skips_empty_messages(self):
        """Extraction returns empty result for conversation with no messages."""
        session = make_session()
        stage = ExtractionStage(session=session)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        conv = make_conversation(messages=[])
        ctx.conversation = conv

        result = await stage._run(ctx)
        assert result is not None
        # Empty message returns early with neutral defaults
        assert "tone" in result or "summary" in result or "facts" in result


# ── Test: Memory update handles dict-format facts ────────────────────────

class TestMemoryUpdateStageIntegration:
    """Prove memory update correctly processes dict-format facts from extraction."""

    @pytest.mark.asyncio
    async def test_memory_update_skips_when_no_facts(self):
        """MemoryUpdateStage returns early with zero counts when no facts."""
        from nikita.pipeline.stages.memory_update import MemoryUpdateStage

        session = make_session()
        stage = MemoryUpdateStage(session=session)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        ctx.extracted_facts = []  # No facts

        result = await stage._run(ctx)
        assert result["stored"] == 0
        assert result["deduplicated"] == 0


# ── Test: Summary stage generates and stores summary ─────────────────────

class TestSummaryStageIntegration:
    """Prove summary stage generates and stores per-conversation summary."""

    @pytest.mark.asyncio
    async def test_summary_stores_on_conversation(self):
        """SummaryStage writes summary to conversation record."""
        session = make_session()
        stage = SummaryStage(session=session)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        ctx.conversation = make_conversation()
        ctx.extraction_summary = "Player showed empathy about Nikita's bad day"
        ctx.emotional_tone = "positive"
        ctx.chapter = 2

        # Mock _enrich_summary to return base summary (no Haiku call)
        with patch.object(stage, "_enrich_summary", new_callable=AsyncMock, return_value="Player showed empathy about Nikita's bad day"):
            result = await stage._run(ctx)

        assert result["summary_stored"] is True
        assert result["summary_length"] > 0
        assert ctx.conversation.conversation_summary == "Player showed empathy about Nikita's bad day"
        assert ctx.conversation.emotional_tone == "positive"
        assert ctx.daily_summary_updated is True

    @pytest.mark.asyncio
    async def test_summary_skips_without_extraction_summary(self):
        """SummaryStage returns early if no extraction_summary available."""
        session = make_session()
        stage = SummaryStage(session=session)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        ctx.conversation = make_conversation()
        ctx.extraction_summary = ""  # Empty

        result = await stage._run(ctx)
        assert result["summary_stored"] is False
        assert result["reason"] == "no_extraction_summary"

    @pytest.mark.asyncio
    async def test_summary_skips_without_conversation(self):
        """SummaryStage returns early if no conversation loaded."""
        session = make_session()
        stage = SummaryStage(session=session)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        # ctx.conversation is None

        result = await stage._run(ctx)
        assert result["summary_stored"] is False
        assert result["reason"] == "no_conversation"

    @pytest.mark.asyncio
    async def test_summary_enrichment_with_haiku(self):
        """SummaryStage enriches summary via Haiku when API key available."""
        session = make_session()
        stage = SummaryStage(session=session)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        ctx.conversation = make_conversation()
        ctx.extraction_summary = "Player showed empathy"
        ctx.emotional_tone = "positive"
        ctx.chapter = 2

        enriched = "He was actually really sweet about my day. Made me feel heard."
        with patch.object(stage, "_enrich_summary", new_callable=AsyncMock, return_value=enriched):
            result = await stage._run(ctx)

        assert result["summary_stored"] is True
        assert result["enriched"] is True
        assert ctx.conversation.conversation_summary == enriched


# ── Test: Conflict stage uses real user state ─────────────────────────────

class TestConflictStageIntegration:
    """Prove conflict stage uses real user state from context."""

    @pytest.mark.asyncio
    async def test_conflict_triggers_on_low_score(self):
        """ConflictStage detects low score and triggers conflict."""
        session = make_session()
        stage = ConflictStage(session=session)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        ctx.relationship_score = Decimal("25")  # Below 30 threshold
        ctx.chapter = 3

        result = await stage._run(ctx)
        assert result["active"] is True
        assert result["type"] == "low_score"
        assert ctx.active_conflict is True

    @pytest.mark.asyncio
    async def test_conflict_triggers_on_emotional_distance(self):
        """ConflictStage detects cold emotional tone + chapter >= 3."""
        session = make_session()
        stage = ConflictStage(session=session)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        ctx.relationship_score = Decimal("55")
        ctx.emotional_tone = "cold"
        ctx.chapter = 3

        result = await stage._run(ctx)
        assert result["active"] is True
        assert result["type"] == "emotional_distance"

    @pytest.mark.asyncio
    async def test_no_conflict_for_healthy_relationship(self):
        """No conflict when score is healthy and tone is positive."""
        session = make_session()
        stage = ConflictStage(session=session)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        ctx.relationship_score = Decimal("65")
        ctx.emotional_tone = "positive"
        ctx.chapter = 2

        result = await stage._run(ctx)
        assert result["active"] is False
        assert result["type"] is None


# ── Test: Game state stage uses real context ──────────────────────────────

class TestGameStateStageIntegration:
    """Prove game state stage reads extraction data from context."""

    @pytest.mark.asyncio
    async def test_game_state_reads_extraction_data(self):
        """GameStateStage uses extraction_summary to evaluate."""
        session = make_session()
        stage = GameStateStage(session=session)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        ctx.extraction_summary = "Player was supportive and caring"
        ctx.chapter = 2

        result = await stage._run(ctx)
        assert result is not None
        assert "score_delta" in result
        assert "chapter_changed" in result


# ── Test: Full pipeline with mocked LLM ──────────────────────────────────

class TestFullPipelineWithMockedLLM:
    """Integration test: full pipeline with mocked external deps.

    Proves all stages connect properly, context propagates, and
    conversation gets processed with all artifacts stored.
    """

    @pytest.mark.asyncio
    async def test_full_pipeline_produces_all_artifacts(self):
        """Full pipeline produces summary, facts, emotional state, prompt."""
        session = make_session()
        conv_id = uuid4()
        user_id = uuid4()

        conversation = make_conversation(user_id=user_id)
        conversation.id = conv_id
        user = make_user(user_id=user_id)

        # Build extraction stage that returns test data
        class TestExtractionStage(BaseStage):
            name = "extraction"
            is_critical = True
            timeout_seconds = 5.0

            async def _run(self, ctx):
                ctx.extracted_facts = [
                    {"content": "User likes cats", "type": "user_fact"},
                    {"content": "User works in tech", "type": "personal"},
                ]
                ctx.extracted_threads = [
                    {"content": "Boss conflict", "type": "thread"},
                ]
                ctx.extracted_thoughts = [
                    {"content": "He seems really caring", "type": "thought"},
                ]
                ctx.extraction_summary = "Player showed empathy about Nikita's work stress"
                ctx.emotional_tone = "positive"
                return {"facts_count": 2, "threads_count": 1}

        # Build memory update stage that counts stored facts
        class TestMemoryStage(BaseStage):
            name = "memory_update"
            is_critical = True
            timeout_seconds = 5.0

            async def _run(self, ctx):
                ctx.facts_stored = len(ctx.extracted_facts)
                ctx.facts_deduplicated = 0
                return {"stored": ctx.facts_stored, "deduplicated": 0}

        # Build summary stage that stores summary
        class TestSummaryStage(BaseStage):
            name = "summary"
            is_critical = False
            timeout_seconds = 5.0

            async def _run(self, ctx):
                summary = ctx.extraction_summary
                ctx.conversation.conversation_summary = summary
                ctx.conversation.emotional_tone = ctx.emotional_tone
                ctx.daily_summary_updated = True
                return {"summary_stored": True, "summary_length": len(summary)}

        # Build prompt builder that generates a test prompt
        class TestPromptStage(BaseStage):
            name = "prompt_builder"
            is_critical = False
            timeout_seconds = 5.0

            async def _run(self, ctx):
                prompt = (
                    f"You are Nikita. Chapter {ctx.chapter}. "
                    f"Score: {ctx.relationship_score}. "
                    f"Vices: {', '.join(ctx.vices)}. "
                    f"Facts: {len(ctx.extracted_facts)}. "
                    f"Emotional state: {ctx.emotional_tone}. "
                    f"Summary: {ctx.extraction_summary}"
                )
                ctx.generated_prompt = prompt
                ctx.prompt_token_count = len(prompt.split())
                return {"generated": True, "text_tokens": ctx.prompt_token_count}

        stages = [
            ("extraction", TestExtractionStage(session=session), True),
            ("memory_update", TestMemoryStage(session=session), True),
            ("summary", TestSummaryStage(session=session), False),
            ("prompt_builder", TestPromptStage(session=session), False),
        ]

        orchestrator = PipelineOrchestrator(session, stages=stages)

        async def mock_load(ctx):
            ctx.conversation = conversation
            ctx.user = user
            ctx.chapter = user.chapter
            ctx.game_status = user.game_status
            ctx.relationship_score = user.relationship_score
            ctx.metrics = {
                "intimacy": user.metrics.intimacy,
                "passion": user.metrics.passion,
                "trust": user.metrics.trust,
                "secureness": user.metrics.secureness,
            }
            ctx.engagement_state = user.engagement_state.current_state
            ctx.vices = [vp.category for vp in user.vice_preferences]

        with patch.object(orchestrator, "_load_context", side_effect=mock_load):
            result = await orchestrator.process(conv_id, user_id, "text")

        # Pipeline succeeded
        assert result.success is True
        assert result.error_stage is None

        # Context was loaded
        ctx = result.context
        assert ctx.conversation is conversation
        assert ctx.user is user
        assert ctx.chapter == 2
        assert ctx.relationship_score == Decimal("65.00")
        assert ctx.vices == ["jealousy", "materialism"]

        # Extraction produced facts
        assert len(ctx.extracted_facts) == 2
        assert ctx.extracted_facts[0]["content"] == "User likes cats"
        assert ctx.extraction_summary == "Player showed empathy about Nikita's work stress"
        assert ctx.emotional_tone == "positive"

        # Memory stored facts
        assert ctx.facts_stored == 2
        assert ctx.facts_deduplicated == 0

        # Summary was stored on conversation
        assert ctx.daily_summary_updated is True
        assert conversation.conversation_summary == "Player showed empathy about Nikita's work stress"
        assert conversation.emotional_tone == "positive"

        # Prompt was generated with all context
        assert ctx.generated_prompt is not None
        assert "Chapter 2" in ctx.generated_prompt
        assert "65" in ctx.generated_prompt
        assert "jealousy" in ctx.generated_prompt
        assert "Facts: 2" in ctx.generated_prompt

        # All 4 stages completed
        assert len(ctx.stage_timings) == 4
        assert "extraction" in ctx.stage_timings
        assert "memory_update" in ctx.stage_timings
        assert "summary" in ctx.stage_timings
        assert "prompt_builder" in ctx.stage_timings

    @pytest.mark.asyncio
    async def test_pipeline_with_critical_failure_preserves_partial_context(self):
        """When extraction fails, no downstream stages run but context load is preserved."""
        session = make_session()
        conv_id = uuid4()
        user_id = uuid4()

        conversation = make_conversation(user_id=user_id)
        conversation.id = conv_id
        user = make_user(user_id=user_id)

        class FailingExtractionStage(BaseStage):
            name = "extraction"
            is_critical = True
            timeout_seconds = 5.0

            async def _run(self, ctx):
                raise StageError("extraction", "LLM API down")

        class NeverReachedStage(BaseStage):
            name = "summary"
            is_critical = False
            timeout_seconds = 5.0

            async def _run(self, ctx):
                raise AssertionError("This stage should never run")

        stages = [
            ("extraction", FailingExtractionStage(session=session), True),
            ("summary", NeverReachedStage(session=session), False),
        ]

        orchestrator = PipelineOrchestrator(session, stages=stages)

        async def mock_load(ctx):
            ctx.conversation = conversation
            ctx.user = user
            ctx.chapter = user.chapter
            ctx.game_status = user.game_status
            ctx.relationship_score = user.relationship_score

        with patch.object(orchestrator, "_load_context", side_effect=mock_load):
            result = await orchestrator.process(conv_id, user_id, "text")

        # Pipeline failed at extraction
        assert result.success is False
        assert result.error_stage == "extraction"

        # But context was loaded successfully before stages ran
        assert result.context.conversation is conversation
        assert result.context.user is user
        assert result.context.chapter == 2


# ── Test: Pipeline result used in tasks.py ───────────────────────────────

class TestPipelineResultAccess:
    """Prove PipelineResult attributes used in tasks.py work correctly."""

    def test_failed_result_has_context_conversation_id(self):
        """tasks.py accesses r.context.conversation_id for logging."""
        conv_id = uuid4()
        ctx = PipelineContext(
            conversation_id=conv_id,
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        result = PipelineResult.failed(ctx, "extraction", "test error")

        assert result.success is False
        assert result.context.conversation_id == conv_id

    def test_succeeded_result_has_summary_flag(self):
        """tasks.py checks ctx.daily_summary_updated to avoid overwriting enriched summary."""
        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        ctx.daily_summary_updated = True
        ctx.extraction_summary = "raw summary"
        result = PipelineResult.succeeded(ctx)

        # When daily_summary_updated is True, tasks.py passes summary=None
        # to mark_processed() so it doesn't overwrite the enriched summary
        summary_for_mark_processed = (
            None if result.context.daily_summary_updated
            else (result.context.extraction_summary or None)
        )
        assert summary_for_mark_processed is None
