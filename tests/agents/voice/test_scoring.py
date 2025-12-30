"""Test voice call scoring.

T019: Unit tests for VoiceCallScorer
Tests:
- AC-FR006-001: Given call ends, When transcript analyzed, Then single aggregate score
- AC-FR006-002: Given good call, When scored, Then positive metric deltas
- AC-FR006-003: Given score history, When logged, Then source = "voice_call"

These tests verify that voice conversations are scored and affect user metrics
the same way text conversations do.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.engine.scoring.models import (
    ConversationContext,
    MetricDeltas,
    ResponseAnalysis,
)


class TestVoiceCallScorer:
    """Test VoiceCallScorer scoring logic."""

    @pytest.fixture
    def user_id(self):
        return uuid4()

    @pytest.fixture
    def session_id(self):
        return "voice_session_123"

    @pytest.fixture
    def mock_transcript(self):
        """Sample voice transcript with multiple exchanges."""
        return [
            ("Hey Nikita, I missed you today", "Mmm, did you now? Tell me more..."),
            ("Work was stressful, needed to hear your voice", "I'm here. What happened?"),
            ("Boss was being unreasonable again", "[soft sigh] Some people..."),
        ]

    @pytest.fixture
    def mock_analysis_positive(self):
        """Analysis result for a positive conversation."""
        return ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("3"),
                passion=Decimal("2"),
                trust=Decimal("2"),
                secureness=Decimal("4"),
            ),
            explanation="User opened up about stress, Nikita was supportive",
            behaviors_identified=["vulnerability", "emotional_support", "active_listening"],
            confidence=Decimal("0.85"),
        )

    @pytest.fixture
    def mock_context(self):
        """Conversation context for scoring."""
        return ConversationContext(
            chapter=3,
            relationship_score=Decimal("65"),
            relationship_state="IN_ZONE",
            recent_messages=[],
        )

    @pytest.mark.asyncio
    async def test_score_call_returns_aggregate_score(
        self, user_id, session_id, mock_transcript, mock_analysis_positive, mock_context
    ):
        """AC-FR006-001: Given call ends, When transcript analyzed, Then single aggregate score."""
        from nikita.agents.voice.scoring import VoiceCallScorer

        scorer = VoiceCallScorer()

        # Mock the ScoreAnalyzer.analyze_batch() method
        with patch.object(
            scorer, "_analyzer"
        ) as mock_analyzer:
            mock_analyzer.analyze_batch = AsyncMock(return_value=mock_analysis_positive)

            result = await scorer.score_call(
                user_id=user_id,
                session_id=session_id,
                transcript=mock_transcript,
                context=mock_context,
            )

        # Should return a single CallScore with aggregated deltas
        assert result is not None
        assert result.session_id == session_id
        assert result.deltas is not None
        assert isinstance(result.deltas, MetricDeltas)
        # All exchanges analyzed together produce single aggregate
        mock_analyzer.analyze_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_score_call_positive_deltas(
        self, user_id, session_id, mock_transcript, mock_analysis_positive, mock_context
    ):
        """AC-FR006-002: Given good call, When scored, Then positive metric deltas."""
        from nikita.agents.voice.scoring import VoiceCallScorer

        scorer = VoiceCallScorer()

        with patch.object(scorer, "_analyzer") as mock_analyzer:
            mock_analyzer.analyze_batch = AsyncMock(return_value=mock_analysis_positive)

            result = await scorer.score_call(
                user_id=user_id,
                session_id=session_id,
                transcript=mock_transcript,
                context=mock_context,
            )

        # Positive conversation should have positive deltas
        assert result.deltas.intimacy > 0
        assert result.deltas.passion > 0
        assert result.deltas.trust > 0
        assert result.deltas.secureness > 0

    @pytest.mark.asyncio
    async def test_score_call_considers_duration(
        self, user_id, session_id, mock_transcript, mock_analysis_positive, mock_context
    ):
        """Call duration is included in the result for logging."""
        from nikita.agents.voice.scoring import VoiceCallScorer

        scorer = VoiceCallScorer()

        with patch.object(scorer, "_analyzer") as mock_analyzer:
            mock_analyzer.analyze_batch = AsyncMock(return_value=mock_analysis_positive)

            result = await scorer.score_call(
                user_id=user_id,
                session_id=session_id,
                transcript=mock_transcript,
                context=mock_context,
                duration_seconds=180,  # 3 minute call
            )

        assert result.duration_seconds == 180

    @pytest.mark.asyncio
    async def test_score_call_empty_transcript(
        self, user_id, session_id, mock_context
    ):
        """Empty transcript returns neutral score."""
        from nikita.agents.voice.scoring import VoiceCallScorer

        scorer = VoiceCallScorer()

        result = await scorer.score_call(
            user_id=user_id,
            session_id=session_id,
            transcript=[],
            context=mock_context,
        )

        # Empty transcript = neutral deltas
        assert result.deltas.intimacy == Decimal("0")
        assert result.deltas.passion == Decimal("0")
        assert result.deltas.trust == Decimal("0")
        assert result.deltas.secureness == Decimal("0")


class TestScoreApplication:
    """Test score application to user metrics."""

    @pytest.fixture
    def user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_call_score(self):
        """Call score to apply."""
        from nikita.agents.voice.scoring import CallScore

        return CallScore(
            session_id="voice_session_456",
            deltas=MetricDeltas(
                intimacy=Decimal("3"),
                passion=Decimal("2"),
                trust=Decimal("2"),
                secureness=Decimal("4"),
            ),
            explanation="Good conversation",
            duration_seconds=180,
        )

    @pytest.mark.asyncio
    async def test_apply_score_updates_metrics(self, user_id, mock_call_score):
        """AC-T021.1: apply_score updates user_metrics."""
        from nikita.agents.voice.scoring import VoiceCallScorer

        scorer = VoiceCallScorer()

        # Mock database session and repositories
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        # Mock user
        mock_user = MagicMock()
        mock_user.chapter = 3

        # Mock metrics
        mock_metrics = MagicMock()
        mock_metrics.calculate_composite_score = MagicMock(return_value=Decimal("52.5"))

        mock_updated_metrics = MagicMock()
        mock_updated_metrics.calculate_composite_score = MagicMock(return_value=Decimal("55.0"))

        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        mock_metrics_repo = MagicMock()
        mock_metrics_repo.get_by_user_id = AsyncMock(return_value=mock_metrics)
        mock_metrics_repo.update_metrics = AsyncMock(return_value=mock_updated_metrics)

        mock_history_repo = MagicMock()
        mock_history_repo.log_event = AsyncMock()

        with patch("nikita.db.database.get_session_maker") as mock_get_session:
            mock_session_maker = MagicMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_session_maker

            with patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo:
                MockUserRepo.return_value = mock_user_repo

                with patch(
                    "nikita.db.repositories.metrics_repository.UserMetricsRepository"
                ) as MockMetricsRepo:
                    MockMetricsRepo.return_value = mock_metrics_repo

                    with patch(
                        "nikita.db.repositories.score_history_repository.ScoreHistoryRepository"
                    ) as MockHistoryRepo:
                        MockHistoryRepo.return_value = mock_history_repo

                        await scorer.apply_score(user_id, mock_call_score)

        # Verify update was called with deltas
        mock_metrics_repo.update_metrics.assert_called_once_with(
            user_id,
            intimacy_delta=Decimal("3"),
            passion_delta=Decimal("2"),
            trust_delta=Decimal("2"),
            secureness_delta=Decimal("4"),
        )

    @pytest.mark.asyncio
    async def test_apply_score_logs_to_history(self, user_id, mock_call_score):
        """AC-FR006-003 + AC-T021.2: Score logged with source = "voice_call"."""
        from nikita.agents.voice.scoring import VoiceCallScorer

        scorer = VoiceCallScorer()

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        mock_user = MagicMock()
        mock_user.chapter = 3

        mock_metrics = MagicMock()
        mock_metrics.calculate_composite_score = MagicMock(return_value=Decimal("52.5"))

        mock_updated_metrics = MagicMock()
        mock_updated_metrics.calculate_composite_score = MagicMock(return_value=Decimal("55.0"))

        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        mock_metrics_repo = MagicMock()
        mock_metrics_repo.get_by_user_id = AsyncMock(return_value=mock_metrics)
        mock_metrics_repo.update_metrics = AsyncMock(return_value=mock_updated_metrics)

        mock_history_repo = MagicMock()
        mock_history_repo.log_event = AsyncMock()

        with patch("nikita.db.database.get_session_maker") as mock_get_session:
            mock_session_maker = MagicMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_session_maker

            with patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo:
                MockUserRepo.return_value = mock_user_repo

                with patch(
                    "nikita.db.repositories.metrics_repository.UserMetricsRepository"
                ) as MockMetricsRepo:
                    MockMetricsRepo.return_value = mock_metrics_repo

                    with patch(
                        "nikita.db.repositories.score_history_repository.ScoreHistoryRepository"
                    ) as MockHistoryRepo:
                        MockHistoryRepo.return_value = mock_history_repo

                        await scorer.apply_score(user_id, mock_call_score)

        # Verify score history was logged with voice_call source
        mock_history_repo.log_event.assert_called_once()
        call_kwargs = mock_history_repo.log_event.call_args[1]
        assert call_kwargs["event_type"] == "voice_call"

    @pytest.mark.asyncio
    async def test_apply_score_includes_session_id(self, user_id, mock_call_score):
        """AC-T021.3: Session ID included in event details."""
        from nikita.agents.voice.scoring import VoiceCallScorer

        scorer = VoiceCallScorer()

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        mock_user = MagicMock()
        mock_user.chapter = 3

        mock_metrics = MagicMock()
        mock_metrics.calculate_composite_score = MagicMock(return_value=Decimal("52.5"))

        mock_updated_metrics = MagicMock()
        mock_updated_metrics.calculate_composite_score = MagicMock(return_value=Decimal("55.0"))

        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        mock_metrics_repo = MagicMock()
        mock_metrics_repo.get_by_user_id = AsyncMock(return_value=mock_metrics)
        mock_metrics_repo.update_metrics = AsyncMock(return_value=mock_updated_metrics)

        mock_history_repo = MagicMock()
        mock_history_repo.log_event = AsyncMock()

        with patch("nikita.db.database.get_session_maker") as mock_get_session:
            mock_session_maker = MagicMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_session_maker

            with patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo:
                MockUserRepo.return_value = mock_user_repo

                with patch(
                    "nikita.db.repositories.metrics_repository.UserMetricsRepository"
                ) as MockMetricsRepo:
                    MockMetricsRepo.return_value = mock_metrics_repo

                    with patch(
                        "nikita.db.repositories.score_history_repository.ScoreHistoryRepository"
                    ) as MockHistoryRepo:
                        MockHistoryRepo.return_value = mock_history_repo

                        await scorer.apply_score(user_id, mock_call_score)

        # The session_id should be part of the logged data
        mock_history_repo.log_event.assert_called_once()
        call_kwargs = mock_history_repo.log_event.call_args[1]
        assert call_kwargs["event_details"]["session_id"] == "voice_session_456"


class TestCallScoreModel:
    """Test CallScore data model."""

    def test_call_score_model(self):
        """CallScore holds all scoring data."""
        from nikita.agents.voice.scoring import CallScore

        score = CallScore(
            session_id="voice_session_789",
            deltas=MetricDeltas(
                intimacy=Decimal("2"),
                passion=Decimal("1"),
                trust=Decimal("3"),
                secureness=Decimal("2"),
            ),
            explanation="Supportive conversation about work stress",
            duration_seconds=240,
        )

        assert score.session_id == "voice_session_789"
        assert score.deltas.intimacy == Decimal("2")
        assert score.duration_seconds == 240
        assert "work stress" in score.explanation

    def test_call_score_default_duration(self):
        """Duration defaults to 0 if not provided."""
        from nikita.agents.voice.scoring import CallScore

        score = CallScore(
            session_id="test_session",
            deltas=MetricDeltas(
                intimacy=Decimal("0"),
                passion=Decimal("0"),
                trust=Decimal("0"),
                secureness=Decimal("0"),
            ),
        )

        assert score.duration_seconds == 0
