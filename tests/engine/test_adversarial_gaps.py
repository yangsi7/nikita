"""Adversarial/gap scenario tests for scoring engine and data integrity (GH #145).

Tests boundary conditions, edge cases, and invariants that were never
covered by existing test suites. All tests are fully mocked — no DB or
external services required.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from nikita.config.enums import EngagementState
from nikita.engine.scoring.calculator import ScoreCalculator
from nikita.engine.scoring.models import MetricDeltas, ResponseAnalysis


# ---------------------------------------------------------------------------
# Scoring boundary tests
# ---------------------------------------------------------------------------


class TestScoreMetricBounds:
    """Data integrity: score metrics must always be bounded [0, 100]."""

    @pytest.fixture
    def calculator(self):
        return ScoreCalculator()

    def test_all_zero_metrics_composite_is_zero(self, calculator):
        """Scoring with all-zero initial metrics produces composite = 0."""
        metrics = {
            "intimacy": Decimal("0"),
            "passion": Decimal("0"),
            "trust": Decimal("0"),
            "secureness": Decimal("0"),
        }
        composite = calculator.calculate_composite(metrics)
        assert composite == Decimal("0")

    def test_all_100_metrics_composite_is_100(self, calculator):
        """Scoring with all-100 metrics produces composite = 100."""
        metrics = {
            "intimacy": Decimal("100"),
            "passion": Decimal("100"),
            "trust": Decimal("100"),
            "secureness": Decimal("100"),
        }
        composite = calculator.calculate_composite(metrics)
        assert composite == Decimal("100")

    def test_update_metrics_never_exceeds_100(self, calculator):
        """Applying max positive deltas to 100 metrics stays at 100 (ceiling)."""
        metrics = {
            "intimacy": Decimal("100"),
            "passion": Decimal("100"),
            "trust": Decimal("100"),
            "secureness": Decimal("100"),
        }
        deltas = MetricDeltas(
            intimacy=Decimal("10"),
            passion=Decimal("10"),
            trust=Decimal("10"),
            secureness=Decimal("10"),
        )
        updated = calculator.update_metrics(metrics, deltas)
        for name, value in updated.items():
            assert value <= Decimal("100"), f"{name} exceeded 100: {value}"

    def test_update_metrics_never_goes_below_zero(self, calculator):
        """Applying max negative deltas to 0 metrics stays at 0 (floor)."""
        metrics = {
            "intimacy": Decimal("0"),
            "passion": Decimal("0"),
            "trust": Decimal("0"),
            "secureness": Decimal("0"),
        }
        deltas = MetricDeltas(
            intimacy=Decimal("-10"),
            passion=Decimal("-10"),
            trust=Decimal("-10"),
            secureness=Decimal("-10"),
        )
        updated = calculator.update_metrics(metrics, deltas)
        for name, value in updated.items():
            assert value >= Decimal("0"), f"{name} went negative: {value}"

    def test_composite_never_negative_with_zero_metrics(self, calculator):
        """Composite score with all-zero metrics is exactly 0, not negative."""
        metrics = {
            "intimacy": Decimal("0"),
            "passion": Decimal("0"),
            "trust": Decimal("0"),
            "secureness": Decimal("0"),
        }
        composite = calculator.calculate_composite(metrics)
        assert composite >= Decimal("0")

    def test_full_calculate_at_ceiling(self, calculator):
        """Full calculate() with all-100 metrics and max positive deltas stays bounded."""
        metrics = {
            "intimacy": Decimal("100"),
            "passion": Decimal("100"),
            "trust": Decimal("100"),
            "secureness": Decimal("100"),
        }
        analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("10"),
                passion=Decimal("10"),
                trust=Decimal("10"),
                secureness=Decimal("10"),
            ),
            explanation="Perfect interaction",
        )
        result = calculator.calculate(
            metrics, analysis, EngagementState.IN_ZONE, chapter=1,
        )
        assert result.score_after <= Decimal("100")
        for name, value in result.metrics_after.items():
            assert value <= Decimal("100"), f"{name} exceeded 100"

    def test_full_calculate_at_floor(self, calculator):
        """Full calculate() with all-zero metrics and max negative deltas stays bounded."""
        metrics = {
            "intimacy": Decimal("0"),
            "passion": Decimal("0"),
            "trust": Decimal("0"),
            "secureness": Decimal("0"),
        }
        analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("-10"),
                passion=Decimal("-10"),
                trust=Decimal("-10"),
                secureness=Decimal("-10"),
            ),
            explanation="Terrible interaction",
        )
        result = calculator.calculate(
            metrics, analysis, EngagementState.IN_ZONE, chapter=1,
        )
        assert result.score_after >= Decimal("0")
        for name, value in result.metrics_after.items():
            assert value >= Decimal("0"), f"{name} went negative"


class TestMetricDeltaBounds:
    """MetricDeltas model rejects out-of-range values."""

    def test_delta_exceeding_plus_10_rejected(self):
        """Delta > +10 raises ValidationError."""
        with pytest.raises(Exception):  # pydantic ValidationError
            MetricDeltas(intimacy=Decimal("11"))

    def test_delta_below_minus_10_rejected(self):
        """Delta < -10 raises ValidationError."""
        with pytest.raises(Exception):
            MetricDeltas(trust=Decimal("-11"))

    def test_delta_at_exact_bounds_accepted(self):
        """Deltas at exactly -10 and +10 are valid."""
        d = MetricDeltas(
            intimacy=Decimal("10"),
            passion=Decimal("-10"),
            trust=Decimal("10"),
            secureness=Decimal("-10"),
        )
        assert d.intimacy == Decimal("10")
        assert d.passion == Decimal("-10")


# ---------------------------------------------------------------------------
# Boss threshold event detection at exact boundary
# ---------------------------------------------------------------------------


class TestBossThresholdExact:
    """Boss encounter triggers at exactly the threshold score."""

    @pytest.fixture
    def calculator(self):
        return ScoreCalculator()

    def test_boss_event_fires_when_crossing_threshold(self, calculator):
        """Rising from below boss threshold to at-or-above fires event."""
        # Chapter 1 boss threshold is 55 from config
        events = calculator._detect_events(
            score_before=Decimal("54"),
            score_after=Decimal("55"),
            chapter=1,
        )
        event_types = [e.event_type for e in events]
        assert "boss_threshold_reached" in event_types

    def test_boss_event_does_not_fire_when_already_above(self, calculator):
        """No boss event if already above threshold."""
        events = calculator._detect_events(
            score_before=Decimal("56"),
            score_after=Decimal("60"),
            chapter=1,
        )
        event_types = [e.event_type for e in events]
        assert "boss_threshold_reached" not in event_types

    def test_game_over_event_at_zero(self, calculator):
        """Game over event fires when score drops to 0."""
        events = calculator._detect_events(
            score_before=Decimal("5"),
            score_after=Decimal("0"),
            chapter=1,
        )
        event_types = [e.event_type for e in events]
        assert "game_over" in event_types


# ---------------------------------------------------------------------------
# Decay never produces negative scores
# ---------------------------------------------------------------------------


class TestDecayNeverNegative:
    """Decay calculator must never produce negative score_after."""

    def test_decay_floors_at_zero(self):
        """Decay on a very low score stops at 0, never goes negative."""
        from nikita.engine.decay.calculator import DecayCalculator

        calc = DecayCalculator(max_decay_per_cycle=Decimal("20.0"))
        user_id = uuid4()

        # Create a user-like object with very low score and overdue interaction
        class FakeUser:
            id = user_id
            chapter = 1
            relationship_score = Decimal("2")
            last_interaction_at = datetime.now(UTC) - timedelta(hours=48)
            game_status = "active"

        result = calc.calculate_decay(FakeUser())
        assert result is not None
        assert result.score_after >= Decimal("0"), (
            f"Decay produced negative score: {result.score_after}"
        )
        assert result.score_after == Decimal("0")

    def test_decay_on_zero_score_is_zero_amount(self):
        """Decay on a user with score=0 produces decay_amount=0."""
        from nikita.engine.decay.calculator import DecayCalculator

        calc = DecayCalculator(max_decay_per_cycle=Decimal("20.0"))
        user_id = uuid4()

        class FakeUser:
            id = user_id
            chapter = 1
            relationship_score = Decimal("0")
            last_interaction_at = datetime.now(UTC) - timedelta(hours=48)
            game_status = "active"

        result = calc.calculate_decay(FakeUser())
        assert result is not None
        assert result.decay_amount == Decimal("0")
        assert result.score_after == Decimal("0")


# ---------------------------------------------------------------------------
# Chapter progression invariant: never backward
# ---------------------------------------------------------------------------


class TestChapterProgressionForward:
    """BossStateMachine.should_trigger_boss only allows forward progression."""

    def test_boss_does_not_trigger_when_game_over(self):
        """Boss cannot trigger if game_status is 'game_over'."""
        from nikita.engine.chapters.boss import BossStateMachine

        bsm = BossStateMachine()
        result = bsm.should_trigger_boss(
            relationship_score=Decimal("99"),
            chapter=1,
            game_status="game_over",
        )
        assert result is False

    def test_boss_does_not_trigger_when_won(self):
        """Boss cannot trigger if game_status is 'won'."""
        from nikita.engine.chapters.boss import BossStateMachine

        bsm = BossStateMachine()
        result = bsm.should_trigger_boss(
            relationship_score=Decimal("99"),
            chapter=5,
            game_status="won",
        )
        assert result is False

    def test_boss_does_not_trigger_during_boss_fight(self):
        """Boss cannot trigger if already in 'boss_fight' state."""
        from nikita.engine.chapters.boss import BossStateMachine

        bsm = BossStateMachine()
        result = bsm.should_trigger_boss(
            relationship_score=Decimal("99"),
            chapter=1,
            game_status="boss_fight",
        )
        assert result is False

    def test_boss_triggers_at_exactly_threshold(self):
        """Boss triggers when score == threshold and status is active."""
        from nikita.engine.chapters.boss import BossStateMachine

        bsm = BossStateMachine()
        result = bsm.should_trigger_boss(
            relationship_score=Decimal("55"),
            chapter=1,
            game_status="active",
        )
        assert result is True

    def test_boss_suppressed_during_cooldown(self):
        """Boss does not trigger when cool_down_until is in the future."""
        from nikita.engine.chapters.boss import BossStateMachine

        bsm = BossStateMachine()
        future = datetime.now(UTC) + timedelta(hours=12)
        result = bsm.should_trigger_boss(
            relationship_score=Decimal("99"),
            chapter=1,
            game_status="active",
            cool_down_until=future,
        )
        assert result is False
