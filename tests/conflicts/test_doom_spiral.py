"""Tests for doom spiral fix — repair bypass in temperature calculation.

Regression tests ensuring repair messages decrease temperature even when
Nikita responds coldly (LLM scores the pair negatively).

Covers:
- Repair after hostility → temperature DECREASES
- Repair + cold Nikita → temperature still DECREASES
- Fake repair (manipulation) → no temperature decrease
- Flag OFF → repair fields ignored, zero behavior change
- Repair quality tiers → correct delta applied
- Repair recorded in conflict_details.repair_attempts
- Gottman positive counter incremented on repair
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.config.enums import EngagementState
from nikita.engine.scoring.models import (
    ConversationContext,
    MetricDeltas,
    REPAIR_QUALITY_DELTAS,
    ResponseAnalysis,
)
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
        relationship_score=Decimal("45"),
        recent_messages=[
            ("user", "whatever"),
            ("nikita", "..."),
            ("user", "shut up"),
            ("nikita", "Fine."),
        ],
    )


@pytest.fixture
def metrics():
    return {
        "intimacy": Decimal("45"),
        "passion": Decimal("40"),
        "trust": Decimal("35"),
        "secureness": Decimal("30"),
    }


@pytest.fixture
def hot_conflict_details():
    """Conflict details at HOT zone (post-hostility)."""
    return {
        "temperature": 65.0,
        "zone": "hot",
        "positive_count": 3,
        "negative_count": 8,
        "gottman_ratio": 0.375,
        "gottman_target": 5.0,
        "horsemen_detected": ["contempt", "stonewalling"],
        "repair_attempts": [],
        "last_temp_update": datetime.now(UTC).isoformat(),
        "session_positive": 1,
        "session_negative": 5,
    }


@pytest.fixture
def critical_conflict_details():
    """Conflict details at CRITICAL zone."""
    return {
        "temperature": 85.0,
        "zone": "critical",
        "positive_count": 1,
        "negative_count": 12,
        "gottman_ratio": 0.083,
        "gottman_target": 5.0,
        "horsemen_detected": ["contempt", "criticism", "stonewalling"],
        "repair_attempts": [],
        "last_temp_update": datetime.now(UTC).isoformat(),
        "session_positive": 0,
        "session_negative": 8,
    }


def _repair_analysis(quality: str, negative_deltas: bool = True) -> ResponseAnalysis:
    """Create a repair analysis where LLM scored the pair negatively.

    This simulates the doom spiral: user apologizes but Nikita is cold,
    so the LLM scores the pair with negative deltas.
    """
    if negative_deltas:
        deltas = MetricDeltas(
            intimacy=Decimal("-2"),
            passion=Decimal("-1"),
            trust=Decimal("-1"),
            secureness=Decimal("0"),
        )
    else:
        deltas = MetricDeltas(
            intimacy=Decimal("2"),
            passion=Decimal("1"),
            trust=Decimal("1"),
            secureness=Decimal("1"),
        )
    return ResponseAnalysis(
        deltas=deltas,
        explanation="User apologized but Nikita responded coldly",
        behaviors_identified=["apology", "emotional_openness"],
        confidence=Decimal("0.8"),
        repair_attempt_detected=True,
        repair_quality=quality,
    )


def _no_repair_analysis() -> ResponseAnalysis:
    """Analysis where no repair was detected (normal negative interaction)."""
    return ResponseAnalysis(
        deltas=MetricDeltas(
            intimacy=Decimal("-3"),
            passion=Decimal("-2"),
            trust=Decimal("-2"),
            secureness=Decimal("-1"),
        ),
        explanation="Hostile interaction",
        behaviors_identified=["dismissive", "horseman:contempt"],
        confidence=Decimal("0.85"),
        repair_attempt_detected=False,
        repair_quality=None,
    )


def _fake_repair_analysis() -> ResponseAnalysis:
    """Analysis where fake/manipulative repair was correctly rejected."""
    return ResponseAnalysis(
        deltas=MetricDeltas(
            intimacy=Decimal("-2"),
            passion=Decimal("-1"),
            trust=Decimal("-3"),
            secureness=Decimal("-1"),
        ),
        explanation="Manipulative apology, not genuine repair",
        behaviors_identified=["manipulation", "conditional_apology"],
        confidence=Decimal("0.8"),
        repair_attempt_detected=False,
        repair_quality=None,
    )


class TestDoomSpiralFix:
    """Core doom spiral regression tests."""

    @pytest.mark.asyncio
    async def test_repair_after_hostility_decreases_temperature(
        self, service, context, metrics, hot_conflict_details
    ):
        """CRITICAL: User apologizes after hostile messages → temp MUST decrease."""
        service.analyzer.analyze.return_value = _repair_analysis("good")

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="I'm sorry, I shouldn't have said those things. I was stressed.",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=hot_conflict_details,
            )

        details = result.conflict_details
        assert details is not None
        # Temperature MUST decrease (was 65.0, good repair = -15)
        assert details["temperature"] < 65.0
        assert details["temperature"] == pytest.approx(50.0, abs=0.1)

    @pytest.mark.asyncio
    async def test_repair_with_cold_nikita_still_decreases_temperature(
        self, service, context, metrics, hot_conflict_details
    ):
        """Even when LLM scores the pair negatively, repair bypasses score-based logic."""
        # Simulate: user apologizes, Nikita is cold, LLM gives negative deltas
        analysis = _repair_analysis("good", negative_deltas=True)
        assert analysis.deltas.total < 0  # Confirm pair scored negatively
        service.analyzer.analyze.return_value = analysis

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="I feel bad about earlier. That was unfair of me.",
                nikita_response="Hmm.",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=hot_conflict_details,
            )

        details = result.conflict_details
        assert details is not None
        # Even though deltas are negative, repair bypass should decrease temp
        assert details["temperature"] < hot_conflict_details["temperature"]

    @pytest.mark.asyncio
    async def test_fake_repair_no_temperature_decrease(
        self, service, context, metrics, hot_conflict_details
    ):
        """Manipulative 'apology' should NOT trigger repair bypass."""
        service.analyzer.analyze.return_value = _fake_repair_analysis()

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="Fine, I'll just leave then. Sorry IF you were offended.",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=hot_conflict_details,
            )

        details = result.conflict_details
        assert details is not None
        # No repair bypass → normal negative path → temp increases
        assert details["temperature"] > hot_conflict_details["temperature"]

    @pytest.mark.asyncio
    async def test_no_repair_detected_normal_path(
        self, service, context, metrics, hot_conflict_details
    ):
        """When no repair detected, normal temperature logic applies."""
        service.analyzer.analyze.return_value = _no_repair_analysis()

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="whatever",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=hot_conflict_details,
            )

        details = result.conflict_details
        assert details is not None
        # Normal path: negative score + horseman → temp increases
        assert details["temperature"] > hot_conflict_details["temperature"]


class TestRepairQualityTiers:
    """Test each repair quality tier applies correct delta."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "quality,expected_delta",
        [
            ("excellent", -25.0),
            ("good", -15.0),
            ("adequate", -5.0),
        ],
    )
    async def test_repair_quality_delta(
        self, service, context, metrics, hot_conflict_details, quality, expected_delta
    ):
        """Each repair quality tier should apply its specific delta."""
        service.analyzer.analyze.return_value = _repair_analysis(quality)
        initial_temp = hot_conflict_details["temperature"]

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="I'm truly sorry",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=hot_conflict_details,
            )

        details = result.conflict_details
        expected_temp = max(0.0, initial_temp + expected_delta)
        assert details["temperature"] == pytest.approx(expected_temp, abs=0.1)

    def test_repair_quality_deltas_constant(self):
        """Verify REPAIR_QUALITY_DELTAS has correct values."""
        assert REPAIR_QUALITY_DELTAS["excellent"] == -25.0
        assert REPAIR_QUALITY_DELTAS["good"] == -15.0
        assert REPAIR_QUALITY_DELTAS["adequate"] == -5.0


class TestRepairRecording:
    """Test that repairs are recorded in conflict_details."""

    @pytest.mark.asyncio
    async def test_repair_recorded_in_repair_attempts(
        self, service, context, metrics, hot_conflict_details
    ):
        """Repair should be logged in conflict_details.repair_attempts."""
        service.analyzer.analyze.return_value = _repair_analysis("good")

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="I'm sorry",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=hot_conflict_details,
            )

        details = result.conflict_details
        assert len(details["repair_attempts"]) == 1
        repair = details["repair_attempts"][0]
        assert repair["quality"] == "good"
        assert repair["temp_delta"] == -15.0

    @pytest.mark.asyncio
    async def test_multiple_repairs_accumulated(
        self, service, context, metrics, hot_conflict_details
    ):
        """Multiple repairs should accumulate in repair_attempts list."""
        service.analyzer.analyze.return_value = _repair_analysis("adequate")

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result1 = await service.score_interaction(
                user_id=uuid4(),
                user_message="sorry",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=hot_conflict_details,
            )

        # Feed output back as input
        service.analyzer.analyze.return_value = _repair_analysis("good")

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result2 = await service.score_interaction(
                user_id=uuid4(),
                user_message="I really mean it, I was wrong",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=result1.conflict_details,
            )

        details = result2.conflict_details
        assert len(details["repair_attempts"]) == 2

    @pytest.mark.asyncio
    async def test_repair_increments_gottman_positive(
        self, service, context, metrics, hot_conflict_details
    ):
        """Repair should always increment Gottman positive counter."""
        initial_positive = hot_conflict_details["positive_count"]
        service.analyzer.analyze.return_value = _repair_analysis("good", negative_deltas=True)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="I'm sorry about earlier",
                nikita_response="Hmm.",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=hot_conflict_details,
            )

        details = result.conflict_details
        # Even though LLM scored pair negatively, repair forces positive Gottman
        assert details["positive_count"] == initial_positive + 1


class TestRepairFlagOff:
    """Test flag OFF behavior with repair fields."""

    @pytest.mark.asyncio
    async def test_no_conflict_details_returns_none(
        self, service, context, metrics
    ):
        """No conflict_details → temperature update still runs but from empty state.

        Replaces test_flag_off_ignores_repair_fields: flag removed,
        temperature path always runs. When conflict_details=None,
        ConflictDetails.from_jsonb(None) returns defaults.
        """
        service.analyzer.analyze.return_value = _repair_analysis("excellent")

        result = await service.score_interaction(
            user_id=uuid4(),
            user_message="I'm sorry",
            nikita_response="...",
            context=context,
            current_metrics=metrics,
            engagement_state=EngagementState.IN_ZONE,
            conflict_details=None,
        )

        # conflict_details always returned now (temperature always processed)
        assert result.conflict_details is not None

    def test_repair_fields_default_values(self):
        """ResponseAnalysis repair fields default to False/None."""
        analysis = ResponseAnalysis(
            deltas=MetricDeltas(),
            explanation="test",
        )
        assert analysis.repair_attempt_detected is False
        assert analysis.repair_quality is None


class TestRepairEdgeCases:
    """Edge cases for repair bypass."""

    @pytest.mark.asyncio
    async def test_repair_at_critical_temperature(
        self, service, context, metrics, critical_conflict_details
    ):
        """Excellent repair at critical should bring temp down significantly."""
        service.analyzer.analyze.return_value = _repair_analysis("excellent")

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="I've been terrible. You deserve better and I want to be better.",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=critical_conflict_details,
            )

        details = result.conflict_details
        # 85.0 - 25.0 = 60.0 → should drop from critical to hot
        assert details["temperature"] == pytest.approx(60.0, abs=0.1)
        assert details["zone"] == "hot"

    @pytest.mark.asyncio
    async def test_repair_cannot_go_below_zero(
        self, service, context, metrics
    ):
        """Repair on low temperature should clamp to 0."""
        low_details = {
            "temperature": 10.0,
            "zone": "calm",
            "positive_count": 5,
            "negative_count": 1,
            "gottman_ratio": 5.0,
            "gottman_target": 20.0,
            "horsemen_detected": [],
            "repair_attempts": [],
            "last_temp_update": None,
            "session_positive": 3,
            "session_negative": 0,
        }
        service.analyzer.analyze.return_value = _repair_analysis("excellent")

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="I'm so sorry",
                nikita_response="It's okay",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=low_details,
            )

        details = result.conflict_details
        # 10.0 - 25.0 = -15.0 → clamped to 0.0
        assert details["temperature"] == 0.0
        assert details["zone"] == "calm"

    @pytest.mark.asyncio
    async def test_repair_detected_but_no_quality_skips_bypass(
        self, service, context, metrics, hot_conflict_details
    ):
        """If repair_attempt_detected=True but repair_quality=None, skip bypass."""
        analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("-2"),
                passion=Decimal("-1"),
                trust=Decimal("-1"),
                secureness=Decimal("0"),
            ),
            explanation="Ambiguous repair attempt",
            behaviors_identified=[],
            confidence=Decimal("0.6"),
            repair_attempt_detected=True,
            repair_quality=None,  # No quality → skip bypass
        )
        service.analyzer.analyze.return_value = analysis

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="um, hey",
                nikita_response="...",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                conflict_details=hot_conflict_details,
            )

        details = result.conflict_details
        # No bypass → normal negative path
        assert details["temperature"] > hot_conflict_details["temperature"]


class TestRepairModelValidation:
    """Test ResponseAnalysis model validation for repair fields."""

    def test_valid_repair_qualities(self):
        """All valid repair quality values should be accepted."""
        for quality in ["excellent", "good", "adequate", None]:
            analysis = ResponseAnalysis(
                deltas=MetricDeltas(),
                repair_attempt_detected=quality is not None,
                repair_quality=quality,
            )
            assert analysis.repair_quality == quality

    def test_invalid_repair_quality_rejected(self):
        """Invalid repair quality should raise ValueError."""
        with pytest.raises(ValueError, match="repair_quality"):
            ResponseAnalysis(
                deltas=MetricDeltas(),
                repair_attempt_detected=True,
                repair_quality="amazing",
            )

    def test_repair_quality_deltas_completeness(self):
        """All valid non-None qualities must have a delta mapping."""
        for quality in ["excellent", "good", "adequate"]:
            assert quality in REPAIR_QUALITY_DELTAS
            assert isinstance(REPAIR_QUALITY_DELTAS[quality], float)
            assert REPAIR_QUALITY_DELTAS[quality] < 0  # All deltas should be negative (cooling)
