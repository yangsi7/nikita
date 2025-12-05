"""Tests for scoring service integration (spec 003).

TDD: Tests for ScoringService which integrates ScoreAnalyzer,
ScoreCalculator, and score history logging.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.config.enums import EngagementState
from nikita.engine.scoring.models import (
    ConversationContext,
    MetricDeltas,
    ResponseAnalysis,
    ScoreChangeEvent,
)
from nikita.engine.scoring.service import ScoringService


class TestScoringServiceCreation:
    """Test ScoringService initialization."""

    def test_create_service(self):
        """Test creating a ScoringService instance."""
        service = ScoringService()
        assert service is not None
        assert service.analyzer is not None
        assert service.calculator is not None


class TestScoringServiceScore:
    """Test ScoringService.score_interaction() method."""

    @pytest.fixture
    def service(self):
        """Create ScoringService instance."""
        return ScoringService()

    @pytest.fixture
    def mock_analysis(self):
        """Create mock ResponseAnalysis."""
        return ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("5"),
                passion=Decimal("3"),
                trust=Decimal("2"),
                secureness=Decimal("1"),
            ),
            explanation="Good interaction",
            behaviors_identified=["genuine_interest"],
            confidence=Decimal("0.85"),
        )

    @pytest.fixture
    def mock_context(self):
        """Create mock conversation context."""
        return ConversationContext(
            chapter=1,
            relationship_score=Decimal("50"),
            recent_messages=[],
            relationship_state="stable",
        )

    @pytest.fixture
    def current_metrics(self):
        """Create current metrics dict."""
        return {
            "intimacy": Decimal("50"),
            "passion": Decimal("50"),
            "trust": Decimal("50"),
            "secureness": Decimal("50"),
        }

    @pytest.mark.asyncio
    async def test_score_interaction_returns_result(
        self, service, mock_analysis, mock_context, current_metrics
    ):
        """Test that score_interaction returns a ScoreResult."""
        # Mock the analyzer
        with patch.object(service.analyzer, "analyze", return_value=mock_analysis):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="Hi!",
                nikita_response="Hello!",
                context=mock_context,
                current_metrics=current_metrics,
                engagement_state=EngagementState.IN_ZONE,
            )

        assert result is not None
        assert result.score_after > result.score_before

    @pytest.mark.asyncio
    async def test_score_interaction_with_history(
        self, service, mock_analysis, mock_context, current_metrics
    ):
        """Test that score_interaction logs to history."""
        user_id = uuid4()
        mock_session = AsyncMock()
        mock_repo = AsyncMock()

        with (
            patch.object(service.analyzer, "analyze", return_value=mock_analysis),
            patch.object(service, "_log_history", new_callable=AsyncMock) as mock_log,
        ):
            result = await service.score_interaction(
                user_id=user_id,
                user_message="Hi!",
                nikita_response="Hello!",
                context=mock_context,
                current_metrics=current_metrics,
                engagement_state=EngagementState.IN_ZONE,
                session=mock_session,
            )

            # Verify history logging was called
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_score_interaction_with_events(
        self, service, mock_context, current_metrics
    ):
        """Test that threshold events are detected and returned."""
        # Set up to cross boss threshold (55 for ch1)
        current_metrics["intimacy"] = Decimal("53")
        current_metrics["passion"] = Decimal("53")
        current_metrics["trust"] = Decimal("53")
        current_metrics["secureness"] = Decimal("53")

        analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("5"),
                passion=Decimal("5"),
                trust=Decimal("5"),
                secureness=Decimal("5"),
            ),
        )

        with patch.object(service.analyzer, "analyze", return_value=analysis):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="I love you",
                nikita_response="That's sweet",
                context=mock_context,
                current_metrics=current_metrics,
                engagement_state=EngagementState.IN_ZONE,
            )

        # Should have boss_threshold_reached event
        assert len(result.events) > 0
        assert any(e.event_type == "boss_threshold_reached" for e in result.events)


class TestScoringServiceAnalyzeOnly:
    """Test analyze-only mode (no score update)."""

    @pytest.fixture
    def service(self):
        """Create ScoringService instance."""
        return ScoringService()

    @pytest.fixture
    def mock_context(self):
        """Create mock conversation context."""
        return ConversationContext(
            chapter=2,
            relationship_score=Decimal("60"),
        )

    @pytest.mark.asyncio
    async def test_analyze_only(self, service, mock_context):
        """Test analyze_only returns analysis without calculating scores."""
        analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("3"),
                passion=Decimal("2"),
                trust=Decimal("1"),
                secureness=Decimal("0"),
            ),
            explanation="Positive interaction",
            behaviors_identified=["engaged"],
            confidence=Decimal("0.80"),
        )

        with patch.object(service.analyzer, "analyze", return_value=analysis):
            result = await service.analyze_only(
                user_message="Test",
                nikita_response="Test",
                context=mock_context,
            )

        assert isinstance(result, ResponseAnalysis)
        assert result.deltas.intimacy == Decimal("3")


class TestScoringServiceBatchScoring:
    """Test batch scoring for voice transcripts."""

    @pytest.fixture
    def service(self):
        """Create ScoringService instance."""
        return ScoringService()

    @pytest.fixture
    def mock_context(self):
        """Create mock conversation context."""
        return ConversationContext(
            chapter=3,
            relationship_score=Decimal("65"),
        )

    @pytest.fixture
    def current_metrics(self):
        """Create current metrics dict."""
        return {
            "intimacy": Decimal("60"),
            "passion": Decimal("60"),
            "trust": Decimal("60"),
            "secureness": Decimal("60"),
        }

    @pytest.mark.asyncio
    async def test_score_batch(self, service, mock_context, current_metrics):
        """Test scoring multiple exchanges at once."""
        exchanges = [
            ("How was your day?", "It was good!"),
            ("What did you do?", "I worked on a project."),
        ]

        batch_analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("6"),
                passion=Decimal("4"),
                trust=Decimal("5"),
                secureness=Decimal("3"),
            ),
            explanation="Overall positive conversation",
            behaviors_identified=["engaged", "interested"],
            confidence=Decimal("0.85"),
        )

        with patch.object(service.analyzer, "analyze_batch", return_value=batch_analysis):
            result = await service.score_batch(
                user_id=uuid4(),
                exchanges=exchanges,
                context=mock_context,
                current_metrics=current_metrics,
                engagement_state=EngagementState.IN_ZONE,
            )

        assert result is not None
        assert result.score_after > result.score_before
