"""Tests for temperature + Gottman integration in ScoringService (Spec 057).

T8: Gottman counter increment in ScoringService
T9: Temperature update in ScoringService

All tests use feature flag mocking — flag ON for temp tests, flag OFF for backward compat.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.config.enums import EngagementState
from nikita.engine.scoring.models import ConversationContext, MetricDeltas, ResponseAnalysis
from nikita.engine.scoring.service import ScoringService


@pytest.fixture
def service():
    """ScoringService with mocked analyzer."""
    svc = ScoringService()
    svc.analyzer = MagicMock()
    svc.analyzer.analyze = AsyncMock()
    return svc


@pytest.fixture
def context():
    return ConversationContext(
        chapter=3,
        relationship_score=Decimal("55"),
        recent_messages=[],
    )


@pytest.fixture
def metrics():
    return {
        "intimacy": Decimal("55"),
        "passion": Decimal("50"),
        "trust": Decimal("50"),
        "secureness": Decimal("45"),
    }


@pytest.fixture
def positive_analysis():
    return ResponseAnalysis(
        deltas=MetricDeltas(
            intimacy=Decimal("3"),
            passion=Decimal("2"),
            trust=Decimal("1"),
            secureness=Decimal("1"),
        ),
        explanation="Positive interaction",
        behaviors_identified=["engaging", "warm"],
        confidence=Decimal("0.9"),
    )


@pytest.fixture
def negative_analysis():
    return ResponseAnalysis(
        deltas=MetricDeltas(
            intimacy=Decimal("-3"),
            passion=Decimal("-2"),
            trust=Decimal("-4"),
            secureness=Decimal("-1"),
        ),
        explanation="Negative interaction",
        behaviors_identified=["dismissive", "horseman:contempt"],
        confidence=Decimal("0.8"),
    )


@pytest.fixture
def horsemen_analysis():
    return ResponseAnalysis(
        deltas=MetricDeltas(
            intimacy=Decimal("-2"),
            passion=Decimal("-1"),
            trust=Decimal("-3"),
            secureness=Decimal("-1"),
        ),
        explanation="Horsemen detected",
        behaviors_identified=[
            "horseman:criticism",
            "horseman:contempt",
            "horseman:stonewalling",
        ],
        confidence=Decimal("0.85"),
    )


@pytest.fixture
def empty_conflict_details():
    return {
        "temperature": 0.0,
        "zone": "calm",
        "positive_count": 0,
        "negative_count": 0,
        "gottman_ratio": 0.0,
        "gottman_target": 20.0,
        "horsemen_detected": [],
        "repair_attempts": [],
        "last_temp_update": None,
        "session_positive": 0,
        "session_negative": 0,
    }


class TestGottmanCounterInScoring:
    """T8: Gottman counter increment in ScoringService."""

    @pytest.mark.asyncio
    async def test_positive_interaction_increments_positive_counter(
        self, service, context, metrics, positive_analysis, empty_conflict_details
    ):
        """Positive interaction should increment positive_count."""
        service.analyzer.analyze.return_value = positive_analysis

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="I love spending time with you",
                nikita_response="Me too!",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=empty_conflict_details,
            )

        assert result.conflict_details is not None
        assert result.conflict_details["positive_count"] == 1
        assert result.conflict_details["negative_count"] == 0
        assert result.conflict_details["session_positive"] == 1

    @pytest.mark.asyncio
    async def test_negative_interaction_increments_negative_counter(
        self, service, context, metrics, negative_analysis, empty_conflict_details
    ):
        """Negative interaction should increment negative_count."""
        service.analyzer.analyze.return_value = negative_analysis

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="whatever",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=empty_conflict_details,
            )

        assert result.conflict_details is not None
        assert result.conflict_details["negative_count"] == 1
        assert result.conflict_details["session_negative"] == 1


class TestTemperatureUpdateInScoring:
    """T9: Temperature update in ScoringService."""

    @pytest.mark.asyncio
    async def test_negative_score_increases_temperature(
        self, service, context, metrics, negative_analysis, empty_conflict_details
    ):
        """Negative score delta should increase temperature."""
        service.analyzer.analyze.return_value = negative_analysis

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="k",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=empty_conflict_details,
            )

        assert result.conflict_details is not None
        assert result.conflict_details["temperature"] > 0.0

    @pytest.mark.asyncio
    async def test_horsemen_increase_temperature(
        self, service, context, metrics, horsemen_analysis, empty_conflict_details
    ):
        """Detected horsemen should add to temperature increase."""
        service.analyzer.analyze.return_value = horsemen_analysis

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="you're being ridiculous",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=empty_conflict_details,
            )

        details = result.conflict_details
        assert details is not None
        # criticism(4) + contempt(8) + stonewalling(5) = 17 from horsemen alone
        assert details["temperature"] > 15.0
        assert "criticism" in details["horsemen_detected"]
        assert "contempt" in details["horsemen_detected"]

    @pytest.mark.asyncio
    async def test_positive_score_decreases_temperature(
        self, service, context, metrics, positive_analysis
    ):
        """Positive score delta should decrease temperature when Gottman ratio is healthy."""
        # Use healthy Gottman ratio (above target) so both score AND ratio reduce temp
        warm_details = {
            "temperature": 40.0,
            "zone": "warm",
            "positive_count": 50,
            "negative_count": 1,
            "gottman_ratio": 50.0,
            "gottman_target": 20.0,
            "horsemen_detected": [],
            "repair_attempts": [],
            "last_temp_update": None,
            "session_positive": 0,
            "session_negative": 0,
        }
        service.analyzer.analyze.return_value = positive_analysis

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="I'm glad we talked",
                nikita_response="Me too",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=warm_details,
            )

        details = result.conflict_details
        assert details is not None
        # Temperature should decrease from positive score + above-target Gottman ratio
        assert details["temperature"] < 40.0

    @pytest.mark.asyncio
    async def test_none_conflict_details_returns_updated(
        self, service, context, metrics, positive_analysis
    ):
        """When conflict_details=None, service initializes and returns updated details."""
        service.analyzer.analyze.return_value = positive_analysis

        result = await service.score_interaction(
            user_id=uuid4(),
            user_message="hi",
            nikita_response="hello",
            context=context,
            current_metrics=metrics,
            engagement_state=EngagementState.IN_ZONE,
            conflict_details=None,
        )

        # Temperature update always runs now, even with None input (initializes defaults)
        assert result.conflict_details is not None

    @pytest.mark.asyncio
    async def test_none_conflict_details_initializes_empty(
        self, service, context, metrics, negative_analysis
    ):
        """When conflict_details is None and flag ON, should initialize empty."""
        service.analyzer.analyze.return_value = negative_analysis

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="go away",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=None,
            )

        assert result.conflict_details is not None
        assert result.conflict_details["temperature"] > 0.0

    @pytest.mark.asyncio
    async def test_zone_updates_correctly(
        self, service, context, metrics, horsemen_analysis
    ):
        """Zone should update based on new temperature value."""
        high_temp_details = {
            "temperature": 70.0,
            "zone": "hot",
            "positive_count": 2,
            "negative_count": 10,
            "gottman_ratio": 0.2,
            "gottman_target": 5.0,
            "horsemen_detected": [],
            "repair_attempts": [],
            "last_temp_update": None,
            "session_positive": 0,
            "session_negative": 0,
        }
        service.analyzer.analyze.return_value = horsemen_analysis

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="you never listen",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=high_temp_details,
            )

        details = result.conflict_details
        assert details is not None
        # From 70 + horsemen + negative score, should enter critical
        assert details["temperature"] > 75.0
        assert details["zone"] == "critical"
