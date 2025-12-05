"""Tests for scoring engine models (spec 003).

TDD: These tests define the expected behavior for ResponseAnalysis
and ConversationContext models.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from nikita.engine.scoring.models import (
    ConversationContext,
    MetricDeltas,
    ResponseAnalysis,
    ScoreChangeEvent,
)


class TestMetricDeltas:
    """Test MetricDeltas model with delta bounds validation."""

    def test_valid_deltas(self):
        """Test that valid deltas within bounds are accepted."""
        deltas = MetricDeltas(
            intimacy=Decimal("5"),
            passion=Decimal("3"),
            trust=Decimal("-2"),
            secureness=Decimal("0"),
        )
        assert deltas.intimacy == Decimal("5")
        assert deltas.passion == Decimal("3")
        assert deltas.trust == Decimal("-2")
        assert deltas.secureness == Decimal("0")

    def test_max_positive_delta(self):
        """Test that +10 is accepted (max positive)."""
        deltas = MetricDeltas(
            intimacy=Decimal("10"),
            passion=Decimal("10"),
            trust=Decimal("10"),
            secureness=Decimal("10"),
        )
        assert deltas.intimacy == Decimal("10")

    def test_max_negative_delta(self):
        """Test that -10 is accepted (max negative)."""
        deltas = MetricDeltas(
            intimacy=Decimal("-10"),
            passion=Decimal("-10"),
            trust=Decimal("-10"),
            secureness=Decimal("-10"),
        )
        assert deltas.intimacy == Decimal("-10")

    def test_delta_exceeds_positive_bound(self):
        """Test that +11 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MetricDeltas(
                intimacy=Decimal("11"),
                passion=Decimal("0"),
                trust=Decimal("0"),
                secureness=Decimal("0"),
            )
        assert "intimacy" in str(exc_info.value)

    def test_delta_exceeds_negative_bound(self):
        """Test that -11 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MetricDeltas(
                intimacy=Decimal("0"),
                passion=Decimal("-11"),
                trust=Decimal("0"),
                secureness=Decimal("0"),
            )
        assert "passion" in str(exc_info.value)

    def test_decimal_precision(self):
        """Test that deltas can have decimal precision."""
        deltas = MetricDeltas(
            intimacy=Decimal("5.5"),
            passion=Decimal("-2.25"),
            trust=Decimal("0.1"),
            secureness=Decimal("9.999"),
        )
        assert deltas.intimacy == Decimal("5.5")
        assert deltas.passion == Decimal("-2.25")

    def test_total_property(self):
        """Test that total computes sum of all deltas."""
        deltas = MetricDeltas(
            intimacy=Decimal("5"),
            passion=Decimal("3"),
            trust=Decimal("-2"),
            secureness=Decimal("1"),
        )
        assert deltas.total == Decimal("7")

    def test_is_positive_property(self):
        """Test is_positive property."""
        positive = MetricDeltas(
            intimacy=Decimal("5"), passion=Decimal("3"), trust=Decimal("0"), secureness=Decimal("0")
        )
        assert positive.is_positive is True

        negative = MetricDeltas(
            intimacy=Decimal("-5"), passion=Decimal("-3"), trust=Decimal("0"), secureness=Decimal("0")
        )
        assert negative.is_positive is False

        neutral = MetricDeltas(
            intimacy=Decimal("0"), passion=Decimal("0"), trust=Decimal("0"), secureness=Decimal("0")
        )
        assert neutral.is_positive is False


class TestResponseAnalysis:
    """Test ResponseAnalysis model with full LLM analysis result."""

    def test_valid_analysis(self):
        """Test creating a valid ResponseAnalysis."""
        analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("5"),
                passion=Decimal("3"),
                trust=Decimal("2"),
                secureness=Decimal("1"),
            ),
            explanation="The user showed genuine interest and vulnerability.",
            behaviors_identified=["genuine_curiosity", "emotional_openness"],
            confidence=Decimal("0.85"),
        )
        assert analysis.deltas.intimacy == Decimal("5")
        assert analysis.explanation == "The user showed genuine interest and vulnerability."
        assert "genuine_curiosity" in analysis.behaviors_identified
        assert analysis.confidence == Decimal("0.85")

    def test_analysis_defaults(self):
        """Test ResponseAnalysis with minimal required fields."""
        analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("0"),
                passion=Decimal("0"),
                trust=Decimal("0"),
                secureness=Decimal("0"),
            ),
        )
        assert analysis.explanation == ""
        assert analysis.behaviors_identified == []
        assert analysis.confidence == Decimal("1.0")

    def test_confidence_bounds(self):
        """Test that confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            ResponseAnalysis(
                deltas=MetricDeltas(
                    intimacy=Decimal("0"),
                    passion=Decimal("0"),
                    trust=Decimal("0"),
                    secureness=Decimal("0"),
                ),
                confidence=Decimal("1.5"),
            )

        with pytest.raises(ValidationError):
            ResponseAnalysis(
                deltas=MetricDeltas(
                    intimacy=Decimal("0"),
                    passion=Decimal("0"),
                    trust=Decimal("0"),
                    secureness=Decimal("0"),
                ),
                confidence=Decimal("-0.1"),
            )

    def test_behaviors_list(self):
        """Test that behaviors_identified accepts list of strings."""
        analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("3"),
                passion=Decimal("0"),
                trust=Decimal("0"),
                secureness=Decimal("0"),
            ),
            behaviors_identified=[
                "genuine_interest",
                "thoughtful_response",
                "emotional_validation",
            ],
        )
        assert len(analysis.behaviors_identified) == 3


class TestConversationContext:
    """Test ConversationContext model for analysis context."""

    def test_valid_context(self):
        """Test creating valid conversation context."""
        context = ConversationContext(
            chapter=2,
            relationship_score=Decimal("65.5"),
            recent_messages=[
                ("user", "Hey, how was your day?"),
                ("nikita", "It was good! I went to yoga."),
            ],
            relationship_state="stable",
        )
        assert context.chapter == 2
        assert context.relationship_score == Decimal("65.5")
        assert len(context.recent_messages) == 2

    def test_chapter_bounds(self):
        """Test that chapter must be 1-5."""
        with pytest.raises(ValidationError):
            ConversationContext(
                chapter=0,
                relationship_score=Decimal("50"),
            )

        with pytest.raises(ValidationError):
            ConversationContext(
                chapter=6,
                relationship_score=Decimal("50"),
            )

    def test_relationship_score_bounds(self):
        """Test that relationship_score must be 0-100."""
        with pytest.raises(ValidationError):
            ConversationContext(
                chapter=1,
                relationship_score=Decimal("-1"),
            )

        with pytest.raises(ValidationError):
            ConversationContext(
                chapter=1,
                relationship_score=Decimal("101"),
            )

    def test_context_defaults(self):
        """Test context with minimal required fields."""
        context = ConversationContext(
            chapter=1,
            relationship_score=Decimal("50"),
        )
        assert context.recent_messages == []
        assert context.relationship_state == "stable"
        assert context.engagement_state is None
        assert context.last_message_hours_ago is None


class TestScoreChangeEvent:
    """Test ScoreChangeEvent for threshold events."""

    def test_boss_threshold_event(self):
        """Test creating boss threshold event."""
        event = ScoreChangeEvent(
            event_type="boss_threshold_reached",
            chapter=1,
            score_before=Decimal("53"),
            score_after=Decimal("56"),
            threshold=Decimal("55"),
            details={"threshold_name": "Chapter 1 Boss"},
        )
        assert event.event_type == "boss_threshold_reached"
        assert event.threshold == Decimal("55")

    def test_game_over_event(self):
        """Test creating game over event."""
        event = ScoreChangeEvent(
            event_type="game_over",
            chapter=3,
            score_before=Decimal("2"),
            score_after=Decimal("0"),
            details={"reason": "Score reached 0"},
        )
        assert event.event_type == "game_over"
        assert event.threshold is None

    def test_critical_low_event(self):
        """Test creating critical low event."""
        event = ScoreChangeEvent(
            event_type="critical_low",
            chapter=2,
            score_before=Decimal("22"),
            score_after=Decimal("18"),
            threshold=Decimal("20"),
        )
        assert event.event_type == "critical_low"

    def test_event_types(self):
        """Test that only valid event types are accepted."""
        valid_types = [
            "boss_threshold_reached",
            "critical_low",
            "recovery_from_critical",
            "game_over",
        ]
        for event_type in valid_types:
            event = ScoreChangeEvent(
                event_type=event_type,
                chapter=1,
                score_before=Decimal("50"),
                score_after=Decimal("55"),
            )
            assert event.event_type == event_type
