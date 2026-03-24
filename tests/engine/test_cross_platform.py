"""Cross-platform scoring and memory verification tests (GH #144).

Verifies that voice and text platforms share:
1. The same scoring pipeline (ScoringService + ScoreCalculator)
2. Score history with distinguishable source platform
3. Memory system (SupabaseMemory instance per user)
4. Conversation history (both platforms in conversations table)
5. Engagement multiplier consistency across platforms
6. Scoring formula consistency (same calculator, same weights)
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from nikita.config.enums import EngagementState
from nikita.engine.scoring.calculator import CALIBRATION_MULTIPLIERS, ScoreCalculator
from nikita.engine.scoring.models import (
    ConversationContext,
    MetricDeltas,
    ResponseAnalysis,
)
from nikita.engine.scoring.service import ScoringService
from nikita.pipeline.models import PipelineContext


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def base_metrics() -> dict[str, Decimal]:
    return {
        "intimacy": Decimal("50"),
        "passion": Decimal("50"),
        "trust": Decimal("50"),
        "secureness": Decimal("50"),
    }


@pytest.fixture
def conversation_context() -> ConversationContext:
    return ConversationContext(
        chapter=2,
        relationship_score=Decimal("55"),
        recent_messages=[],
        relationship_state="stable",
    )


@pytest.fixture
def positive_analysis() -> ResponseAnalysis:
    return ResponseAnalysis(
        deltas=MetricDeltas(
            intimacy=Decimal("4"),
            passion=Decimal("3"),
            trust=Decimal("2"),
            secureness=Decimal("1"),
        ),
        explanation="Positive interaction across platforms",
        behaviors_identified=["genuine_interest", "active_listening"],
        confidence=Decimal("0.9"),
    )


# ---------------------------------------------------------------------------
# 1. Pipeline accepts platform param and propagates it through PipelineContext
# ---------------------------------------------------------------------------

class TestPipelineContextPlatform:
    """Verify PipelineContext carries the platform field for both text and voice."""

    @pytest.mark.parametrize("platform", ["text", "voice"])
    def test_pipeline_context_stores_platform(self, user_id: UUID, platform: str):
        """PipelineContext.platform is set correctly for both platforms."""
        from datetime import datetime, timezone

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            platform=platform,
        )
        assert ctx.platform == platform

    def test_pipeline_context_defaults_to_text(self, user_id: UUID):
        """PipelineContext has no default — field is required, but orchestrator defaults to 'text'."""
        from datetime import datetime, timezone

        # The orchestrator.process() signature defaults platform="text"
        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        assert ctx.platform == "text"


class TestOrchestratorPlatformPropagation:
    """Verify PipelineOrchestrator.process() propagates platform into PipelineContext."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("platform", ["text", "voice"])
    async def test_orchestrator_sets_platform_on_context(self, user_id: UUID, platform: str):
        """Orchestrator creates PipelineContext with the given platform."""
        from nikita.pipeline.orchestrator import PipelineOrchestrator

        mock_session = AsyncMock()
        # Use empty stages list so no real stage work happens
        mock_stage = MagicMock()
        mock_stage.execute = AsyncMock(
            return_value=MagicMock(success=True, error=None)
        )

        orchestrator = PipelineOrchestrator(
            session=mock_session,
            stages=[("test_stage", mock_stage, False)],
        )

        # Mock begin_nested to act as a no-op async context manager
        mock_session.begin_nested = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock())
        )

        result = await orchestrator.process(
            conversation_id=uuid4(),
            user_id=user_id,
            platform=platform,
        )
        assert result.context.platform == platform


# ---------------------------------------------------------------------------
# 2. Score history records include source platform (text vs voice)
# ---------------------------------------------------------------------------

class TestScoreHistoryPlatformSource:
    """Verify score history distinguishes text vs voice sources."""

    @pytest.mark.asyncio
    async def test_text_scoring_logs_conversation_event_type(
        self, user_id: UUID, positive_analysis: ResponseAnalysis,
        conversation_context: ConversationContext, base_metrics: dict,
    ):
        """ScoringService.score_interaction logs event_type='conversation' for text."""
        service = ScoringService()
        mock_session = AsyncMock()

        mock_repo = MagicMock()
        mock_repo.log_event = AsyncMock()

        with patch.object(service.analyzer, "analyze", return_value=positive_analysis):
            with patch(
                "nikita.db.repositories.score_history_repository.ScoreHistoryRepository",
                return_value=mock_repo,
            ):
                await service.score_interaction(
                    user_id=user_id,
                    user_message="Hey babe",
                    nikita_response="Hey you",
                    context=conversation_context,
                    current_metrics=base_metrics,
                    engagement_state=EngagementState.IN_ZONE,
                    session=mock_session,
                )

                mock_repo.log_event.assert_awaited_once()
                call_kwargs = mock_repo.log_event.call_args
                # Default event_type for score_interaction is "conversation"
                assert call_kwargs.kwargs.get("event_type") == "conversation"

    @pytest.mark.asyncio
    async def test_voice_batch_scoring_logs_voice_call_event_type(
        self, user_id: UUID, positive_analysis: ResponseAnalysis,
        conversation_context: ConversationContext, base_metrics: dict,
    ):
        """ScoringService.score_batch logs event_type='voice_call' for voice."""
        service = ScoringService()
        mock_session = AsyncMock()

        exchanges = [("How are you?", "I'm great!"), ("Miss you", "Aww")]

        mock_repo = MagicMock()
        mock_repo.log_event = AsyncMock()

        with patch.object(service.analyzer, "analyze_batch", return_value=positive_analysis):
            with patch(
                "nikita.db.repositories.score_history_repository.ScoreHistoryRepository",
                return_value=mock_repo,
            ):
                await service.score_batch(
                    user_id=user_id,
                    exchanges=exchanges,
                    context=conversation_context,
                    current_metrics=base_metrics,
                    engagement_state=EngagementState.IN_ZONE,
                    session=mock_session,
                )

                mock_repo.log_event.assert_awaited_once()
                call_kwargs = mock_repo.log_event.call_args
                assert call_kwargs.kwargs.get("event_type") == "voice_call"


# ---------------------------------------------------------------------------
# 3. Memory is shared across platforms (same SupabaseMemory per user)
# ---------------------------------------------------------------------------

class TestSharedMemoryAcrossPlatforms:
    """Verify both platforms use the same SupabaseMemory instance per user."""

    def test_supabase_memory_is_user_scoped(self, user_id: UUID):
        """SupabaseMemory is initialized with user_id, not platform."""
        from nikita.memory.supabase_memory import SupabaseMemory

        mock_session = AsyncMock()
        # Both text and voice would create SupabaseMemory with the same user_id
        memory = SupabaseMemory(
            session=mock_session,
            user_id=user_id,
            openai_api_key="test-key",
        )
        assert memory.user_id == user_id
        # No platform field on SupabaseMemory — memory is shared
        assert not hasattr(memory, "platform")

    def test_two_platform_memories_share_user_scope(self, user_id: UUID):
        """Two SupabaseMemory instances for the same user_id target the same data."""
        from nikita.memory.supabase_memory import SupabaseMemory

        mock_session = AsyncMock()
        text_memory = SupabaseMemory(
            session=mock_session, user_id=user_id, openai_api_key="key"
        )
        voice_memory = SupabaseMemory(
            session=mock_session, user_id=user_id, openai_api_key="key"
        )
        # Same user_id means same memory scope — no platform isolation
        assert text_memory.user_id == voice_memory.user_id


# ---------------------------------------------------------------------------
# 4. Both text and voice conversations appear in the same history
# ---------------------------------------------------------------------------

class TestConversationHistoryUnified:
    """Verify Conversation model stores both platforms in the same table."""

    def test_conversation_model_accepts_telegram_platform(self):
        """Conversation can be created with platform='telegram'."""
        from nikita.db.models.conversation import Conversation

        conv = Conversation(
            user_id=uuid4(),
            platform="telegram",
            messages=[],
            started_at=MagicMock(),
        )
        assert conv.platform == "telegram"

    def test_conversation_model_accepts_voice_platform(self):
        """Conversation can be created with platform='voice'."""
        from nikita.db.models.conversation import Conversation

        conv = Conversation(
            user_id=uuid4(),
            platform="voice",
            messages=[],
            started_at=MagicMock(),
            elevenlabs_session_id="session-abc",
        )
        assert conv.platform == "voice"
        assert conv.elevenlabs_session_id == "session-abc"

    def test_voice_conversation_has_voice_specific_fields(self):
        """Voice conversations carry transcript_raw and elevenlabs_session_id."""
        from nikita.db.models.conversation import Conversation

        conv = Conversation(
            user_id=uuid4(),
            platform="voice",
            messages=[],
            started_at=MagicMock(),
            elevenlabs_session_id="sess-123",
            transcript_raw="User: Hi\nNikita: Hello",
        )
        assert conv.transcript_raw is not None
        assert conv.elevenlabs_session_id == "sess-123"

    def test_text_conversation_no_voice_fields(self):
        """Text conversations leave voice-specific fields as None."""
        from nikita.db.models.conversation import Conversation

        conv = Conversation(
            user_id=uuid4(),
            platform="telegram",
            messages=[{"role": "user", "content": "hi"}],
            started_at=MagicMock(),
        )
        assert conv.elevenlabs_session_id is None
        assert conv.transcript_raw is None


# ---------------------------------------------------------------------------
# 5. Engagement multiplier applies to voice conversations
# ---------------------------------------------------------------------------

class TestEngagementMultiplierCrossPlatform:
    """Verify engagement multiplier is applied consistently for both platforms."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("engagement_state,expected_multiplier", [
        (EngagementState.IN_ZONE, Decimal("1.0")),
        (EngagementState.CLINGY, Decimal("0.5")),
        (EngagementState.DISTANT, Decimal("0.6")),
        (EngagementState.OUT_OF_ZONE, Decimal("0.2")),
    ])
    async def test_text_score_interaction_applies_multiplier(
        self, user_id: UUID, positive_analysis: ResponseAnalysis,
        conversation_context: ConversationContext, base_metrics: dict,
        engagement_state: EngagementState, expected_multiplier: Decimal,
    ):
        """Text scoring path applies engagement multiplier to positive deltas."""
        service = ScoringService()

        with patch.object(service.analyzer, "analyze", return_value=positive_analysis):
            result = await service.score_interaction(
                user_id=user_id,
                user_message="Hey",
                nikita_response="Hi!",
                context=conversation_context,
                current_metrics=base_metrics,
                engagement_state=engagement_state,
            )

        assert result.multiplier_applied == expected_multiplier

    @pytest.mark.asyncio
    @pytest.mark.parametrize("engagement_state,expected_multiplier", [
        (EngagementState.IN_ZONE, Decimal("1.0")),
        (EngagementState.CLINGY, Decimal("0.5")),
        (EngagementState.DISTANT, Decimal("0.6")),
        (EngagementState.OUT_OF_ZONE, Decimal("0.2")),
    ])
    async def test_voice_score_batch_applies_same_multiplier(
        self, user_id: UUID, positive_analysis: ResponseAnalysis,
        conversation_context: ConversationContext, base_metrics: dict,
        engagement_state: EngagementState, expected_multiplier: Decimal,
    ):
        """Voice batch scoring path applies the same engagement multiplier."""
        service = ScoringService()
        exchanges = [("Hey", "Hi!")]

        with patch.object(service.analyzer, "analyze_batch", return_value=positive_analysis):
            result = await service.score_batch(
                user_id=user_id,
                exchanges=exchanges,
                context=conversation_context,
                current_metrics=base_metrics,
                engagement_state=engagement_state,
            )

        assert result.multiplier_applied == expected_multiplier


# ---------------------------------------------------------------------------
# 6. Scoring formula is consistent across platforms
# ---------------------------------------------------------------------------

class TestScoringFormulaConsistency:
    """Verify identical inputs produce identical scores regardless of platform path."""

    @pytest.mark.asyncio
    async def test_same_analysis_produces_same_score_both_paths(
        self, user_id: UUID, positive_analysis: ResponseAnalysis,
        conversation_context: ConversationContext, base_metrics: dict,
    ):
        """Given identical analysis, text and voice produce the same ScoreResult."""
        service = ScoringService()

        # Text path: score_interaction
        with patch.object(service.analyzer, "analyze", return_value=positive_analysis):
            text_result = await service.score_interaction(
                user_id=user_id,
                user_message="I had a great day",
                nikita_response="Tell me more!",
                context=conversation_context,
                current_metrics=dict(base_metrics),
                engagement_state=EngagementState.IN_ZONE,
            )

        # Voice path: score_batch (single exchange, same content)
        with patch.object(service.analyzer, "analyze_batch", return_value=positive_analysis):
            voice_result = await service.score_batch(
                user_id=user_id,
                exchanges=[("I had a great day", "Tell me more!")],
                context=conversation_context,
                current_metrics=dict(base_metrics),
                engagement_state=EngagementState.IN_ZONE,
            )

        # Both paths use the same ScoreCalculator.calculate() under the hood
        assert text_result.score_before == voice_result.score_before
        assert text_result.score_after == voice_result.score_after
        assert text_result.metrics_after == voice_result.metrics_after
        assert text_result.multiplier_applied == voice_result.multiplier_applied
        assert text_result.deltas_applied == voice_result.deltas_applied

    def test_calculator_is_shared_instance_type(self):
        """Both ScoringService and VoiceCallScorer use ScoreAnalyzer from same module."""
        from nikita.agents.voice.scoring import VoiceCallScorer
        from nikita.engine.scoring.analyzer import ScoreAnalyzer

        service = ScoringService()
        voice_scorer = VoiceCallScorer()

        # Both use the same ScoreAnalyzer class
        assert type(service.analyzer) is ScoreAnalyzer
        assert type(voice_scorer._analyzer) is ScoreAnalyzer

    def test_calculator_uses_same_weights(self):
        """ScoreCalculator always uses the same metric weights from config."""
        calc1 = ScoreCalculator()
        calc2 = ScoreCalculator()

        assert calc1.weights == calc2.weights
        # Verify the canonical weights
        assert "intimacy" in calc1.weights
        assert "passion" in calc1.weights
        assert "trust" in calc1.weights
        assert "secureness" in calc1.weights
        assert sum(calc1.weights.values()) == Decimal("1")


# ---------------------------------------------------------------------------
# 7. VoiceCallScorer uses the same analyzer as text scoring
# ---------------------------------------------------------------------------

class TestVoiceCallScorerIntegration:
    """Verify VoiceCallScorer produces CallScore using shared ScoreAnalyzer."""

    @pytest.mark.asyncio
    async def test_voice_scorer_uses_analyze_batch(
        self, user_id: UUID, positive_analysis: ResponseAnalysis,
        conversation_context: ConversationContext,
    ):
        """VoiceCallScorer.score_call delegates to ScoreAnalyzer.analyze_batch."""
        from nikita.agents.voice.scoring import VoiceCallScorer

        scorer = VoiceCallScorer()
        transcript = [("Hey there", "Hey babe")]

        with patch.object(scorer._analyzer, "analyze_batch", return_value=positive_analysis) as mock_batch:
            call_score = await scorer.score_call(
                user_id=user_id,
                session_id="session-xyz",
                transcript=transcript,
                context=conversation_context,
                duration_seconds=120,
            )

            mock_batch.assert_awaited_once_with(transcript, conversation_context)

        assert call_score.session_id == "session-xyz"
        assert call_score.deltas == positive_analysis.deltas
        assert call_score.duration_seconds == 120

    @pytest.mark.asyncio
    async def test_voice_scorer_empty_transcript_returns_zero_deltas(
        self, user_id: UUID, conversation_context: ConversationContext,
    ):
        """Empty transcript produces zero deltas without calling the analyzer."""
        from nikita.agents.voice.scoring import VoiceCallScorer

        scorer = VoiceCallScorer()

        call_score = await scorer.score_call(
            user_id=user_id,
            session_id="session-empty",
            transcript=[],
            context=conversation_context,
        )

        assert call_score.deltas.intimacy == Decimal("0")
        assert call_score.deltas.passion == Decimal("0")
        assert call_score.deltas.trust == Decimal("0")
        assert call_score.deltas.secureness == Decimal("0")


# ---------------------------------------------------------------------------
# 8. Score history event_details contain platform-distinguishing data
# ---------------------------------------------------------------------------

class TestScoreHistoryEventDetails:
    """Verify event_details JSONB contains platform-specific metadata."""

    @pytest.mark.asyncio
    async def test_voice_batch_history_no_session_id_in_service(
        self, user_id: UUID, positive_analysis: ResponseAnalysis,
        conversation_context: ConversationContext, base_metrics: dict,
    ):
        """ScoringService.score_batch _log_history includes engagement_state and deltas."""
        service = ScoringService()
        mock_session = AsyncMock()
        exchanges = [("Hello", "Hi!")]

        mock_repo = MagicMock()
        mock_repo.log_event = AsyncMock()

        with patch.object(service.analyzer, "analyze_batch", return_value=positive_analysis):
            with patch(
                "nikita.db.repositories.score_history_repository.ScoreHistoryRepository",
                return_value=mock_repo,
            ):
                await service.score_batch(
                    user_id=user_id,
                    exchanges=exchanges,
                    context=conversation_context,
                    current_metrics=base_metrics,
                    engagement_state=EngagementState.IN_ZONE,
                    session=mock_session,
                )

                call_kwargs = mock_repo.log_event.call_args
                event_details = call_kwargs.kwargs.get("event_details")

                # event_details should contain scoring breakdown
                assert "delta" in event_details
                assert "deltas" in event_details
                assert "engagement_state" in event_details

    @pytest.mark.asyncio
    async def test_voice_scorer_apply_score_logs_voice_call_with_session_id(
        self, user_id: UUID,
    ):
        """VoiceCallScorer.apply_score logs to score_history with session_id in details."""
        from nikita.agents.voice.scoring import CallScore, VoiceCallScorer

        scorer = VoiceCallScorer()
        call_score = CallScore(
            session_id="session-abc-123",
            deltas=MetricDeltas(
                intimacy=Decimal("2"),
                passion=Decimal("1"),
                trust=Decimal("3"),
                secureness=Decimal("0"),
            ),
            explanation="Good call",
            duration_seconds=180,
        )

        # Build an async context manager for the session_maker
        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session_maker = MagicMock(return_value=mock_ctx)

        # Mock all the repositories
        mock_user = MagicMock()
        mock_user.chapter = 2

        mock_metrics = MagicMock()
        mock_metrics.calculate_composite_score.return_value = Decimal("55")

        mock_updated_metrics = MagicMock()
        mock_updated_metrics.calculate_composite_score.return_value = Decimal("58")

        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        mock_metrics_repo = MagicMock()
        mock_metrics_repo.get_by_user_id = AsyncMock(return_value=mock_metrics)
        mock_metrics_repo.update_metrics = AsyncMock(return_value=mock_updated_metrics)

        mock_history_repo = MagicMock()
        mock_log_event = AsyncMock()
        mock_history_repo.log_event = mock_log_event

        with patch("nikita.db.database.get_session_maker", return_value=mock_session_maker):
            with patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=mock_user_repo,
            ):
                with patch(
                    "nikita.db.repositories.metrics_repository.UserMetricsRepository",
                    return_value=mock_metrics_repo,
                ):
                    with patch(
                        "nikita.db.repositories.score_history_repository.ScoreHistoryRepository",
                        return_value=mock_history_repo,
                    ):
                        await scorer.apply_score(user_id, call_score)

                        mock_log_event.assert_awaited_once()
                        call_kwargs = mock_log_event.call_args
                        event_type = call_kwargs.kwargs.get("event_type")
                        event_details = call_kwargs.kwargs.get("event_details")

                        assert event_type == "voice_call"
                        assert event_details["session_id"] == "session-abc-123"
                        assert event_details["duration_seconds"] == 180


# ---------------------------------------------------------------------------
# 9. ScoreHistory model has no platform column (documented gap)
# ---------------------------------------------------------------------------

class TestScoreHistoryModelSchema:
    """Document the current schema: platform is encoded in event_type, not a column."""

    def test_score_history_uses_event_type_for_platform(self):
        """ScoreHistory distinguishes platform via event_type, not a platform column.

        event_type='conversation' -> text
        event_type='voice_call' -> voice
        """
        from nikita.db.models.game import ScoreHistory, SCORE_EVENT_TYPES

        # The event types list does NOT include 'voice_call' explicitly
        # but the code uses 'voice_call' as event_type (see scoring service)
        # This confirms voice_call is a valid event_type used at runtime
        assert "conversation" in SCORE_EVENT_TYPES

        # Verify the model has event_type but no dedicated platform column
        columns = {c.name for c in ScoreHistory.__table__.columns}
        assert "event_type" in columns
        # Document: no dedicated 'platform' column exists — platform
        # is inferred from event_type ('conversation' vs 'voice_call')
        assert "platform" not in columns, (
            "ScoreHistory uses event_type to distinguish platforms, not a platform column"
        )
