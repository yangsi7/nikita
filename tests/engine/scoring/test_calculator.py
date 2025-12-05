"""Tests for scoring engine calculator (spec 003).

TDD: These tests define the expected behavior for ScoreCalculator
which applies deltas with engagement multipliers and calculates composite scores.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nikita.config.enums import EngagementState
from nikita.engine.scoring.calculator import ScoreCalculator, ScoreResult
from nikita.engine.scoring.models import MetricDeltas, ResponseAnalysis, ScoreChangeEvent


class TestScoreCalculatorCreation:
    """Test ScoreCalculator initialization."""

    def test_create_calculator(self):
        """Test creating a ScoreCalculator instance."""
        calculator = ScoreCalculator()
        assert calculator is not None

    def test_calculator_has_weights(self):
        """Test that calculator has metric weights configured."""
        calculator = ScoreCalculator()
        assert calculator.weights["intimacy"] == Decimal("0.30")
        assert calculator.weights["passion"] == Decimal("0.25")
        assert calculator.weights["trust"] == Decimal("0.25")
        assert calculator.weights["secureness"] == Decimal("0.20")


class TestCalibrationMultipliers:
    """Test engagement calibration multiplier integration (FR-011)."""

    @pytest.fixture
    def calculator(self):
        """Create ScoreCalculator instance."""
        return ScoreCalculator()

    @pytest.fixture
    def positive_deltas(self):
        """Create positive deltas for testing."""
        return MetricDeltas(
            intimacy=Decimal("5"),
            passion=Decimal("4"),
            trust=Decimal("3"),
            secureness=Decimal("2"),
        )

    @pytest.fixture
    def negative_deltas(self):
        """Create negative deltas for testing."""
        return MetricDeltas(
            intimacy=Decimal("-5"),
            passion=Decimal("-4"),
            trust=Decimal("-3"),
            secureness=Decimal("-2"),
        )

    def test_in_zone_multiplier(self, calculator, positive_deltas):
        """Test IN_ZONE state gives 1.0x multiplier (full credit)."""
        adjusted = calculator.apply_multiplier(positive_deltas, EngagementState.IN_ZONE)

        # IN_ZONE = 1.0x, so deltas unchanged
        assert adjusted.intimacy == Decimal("5")
        assert adjusted.passion == Decimal("4")
        assert adjusted.trust == Decimal("3")
        assert adjusted.secureness == Decimal("2")

    def test_calibrating_multiplier(self, calculator, positive_deltas):
        """Test CALIBRATING state gives 0.9x multiplier."""
        adjusted = calculator.apply_multiplier(positive_deltas, EngagementState.CALIBRATING)

        # CALIBRATING = 0.9x
        assert adjusted.intimacy == Decimal("4.5")
        assert adjusted.passion == Decimal("3.6")
        assert adjusted.trust == Decimal("2.7")
        assert adjusted.secureness == Decimal("1.8")

    def test_clingy_multiplier(self, calculator, positive_deltas):
        """Test CLINGY state gives 0.5x multiplier (harsh penalty)."""
        adjusted = calculator.apply_multiplier(positive_deltas, EngagementState.CLINGY)

        # CLINGY = 0.5x
        assert adjusted.intimacy == Decimal("2.5")
        assert adjusted.passion == Decimal("2")
        assert adjusted.trust == Decimal("1.5")
        assert adjusted.secureness == Decimal("1")

    def test_distant_multiplier(self, calculator, positive_deltas):
        """Test DISTANT state gives 0.6x multiplier."""
        adjusted = calculator.apply_multiplier(positive_deltas, EngagementState.DISTANT)

        # DISTANT = 0.6x
        assert adjusted.intimacy == Decimal("3")
        assert adjusted.passion == Decimal("2.4")
        assert adjusted.trust == Decimal("1.8")
        assert adjusted.secureness == Decimal("1.2")

    def test_out_of_zone_multiplier(self, calculator, positive_deltas):
        """Test OUT_OF_ZONE state gives 0.2x multiplier (danger zone)."""
        adjusted = calculator.apply_multiplier(positive_deltas, EngagementState.OUT_OF_ZONE)

        # OUT_OF_ZONE = 0.2x
        assert adjusted.intimacy == Decimal("1")
        assert adjusted.passion == Decimal("0.8")
        assert adjusted.trust == Decimal("0.6")
        assert adjusted.secureness == Decimal("0.4")

    def test_negative_deltas_not_reduced(self, calculator, negative_deltas):
        """Test that penalties (negative deltas) are NOT reduced by multiplier."""
        # Even with CLINGY (0.5x), negative deltas stay full
        adjusted = calculator.apply_multiplier(negative_deltas, EngagementState.CLINGY)

        # Negative deltas should NOT be reduced
        assert adjusted.intimacy == Decimal("-5")
        assert adjusted.passion == Decimal("-4")
        assert adjusted.trust == Decimal("-3")
        assert adjusted.secureness == Decimal("-2")

    def test_mixed_deltas(self, calculator):
        """Test mixed positive/negative deltas."""
        mixed = MetricDeltas(
            intimacy=Decimal("5"),   # Positive - should be reduced
            passion=Decimal("-3"),   # Negative - stays full
            trust=Decimal("2"),      # Positive - should be reduced
            secureness=Decimal("-1"), # Negative - stays full
        )

        adjusted = calculator.apply_multiplier(mixed, EngagementState.CLINGY)  # 0.5x

        assert adjusted.intimacy == Decimal("2.5")  # Reduced
        assert adjusted.passion == Decimal("-3")    # Not reduced
        assert adjusted.trust == Decimal("1")       # Reduced
        assert adjusted.secureness == Decimal("-1") # Not reduced


class TestCompositeScoreCalculation:
    """Test composite score calculation (FR-003)."""

    @pytest.fixture
    def calculator(self):
        """Create ScoreCalculator instance."""
        return ScoreCalculator()

    def test_calculate_composite_all_50(self, calculator):
        """Test composite with all metrics at 50."""
        metrics = {
            "intimacy": Decimal("50"),
            "passion": Decimal("50"),
            "trust": Decimal("50"),
            "secureness": Decimal("50"),
        }
        composite = calculator.calculate_composite(metrics)

        # 50*0.30 + 50*0.25 + 50*0.25 + 50*0.20 = 50
        assert composite == Decimal("50")

    def test_calculate_composite_weighted(self, calculator):
        """Test that weights are applied correctly."""
        metrics = {
            "intimacy": Decimal("100"),    # 100 * 0.30 = 30
            "passion": Decimal("0"),       # 0 * 0.25 = 0
            "trust": Decimal("0"),         # 0 * 0.25 = 0
            "secureness": Decimal("0"),    # 0 * 0.20 = 0
        }
        composite = calculator.calculate_composite(metrics)
        assert composite == Decimal("30")

        metrics2 = {
            "intimacy": Decimal("0"),
            "passion": Decimal("100"),     # 100 * 0.25 = 25
            "trust": Decimal("0"),
            "secureness": Decimal("0"),
        }
        composite2 = calculator.calculate_composite(metrics2)
        assert composite2 == Decimal("25")

    def test_calculate_composite_all_max(self, calculator):
        """Test composite with all metrics at 100."""
        metrics = {
            "intimacy": Decimal("100"),
            "passion": Decimal("100"),
            "trust": Decimal("100"),
            "secureness": Decimal("100"),
        }
        composite = calculator.calculate_composite(metrics)
        assert composite == Decimal("100")

    def test_calculate_composite_all_zero(self, calculator):
        """Test composite with all metrics at 0."""
        metrics = {
            "intimacy": Decimal("0"),
            "passion": Decimal("0"),
            "trust": Decimal("0"),
            "secureness": Decimal("0"),
        }
        composite = calculator.calculate_composite(metrics)
        assert composite == Decimal("0")


class TestMetricUpdate:
    """Test metric update with bounds enforcement (FR-004)."""

    @pytest.fixture
    def calculator(self):
        """Create ScoreCalculator instance."""
        return ScoreCalculator()

    def test_update_metrics_basic(self, calculator):
        """Test basic metric update."""
        current = {
            "intimacy": Decimal("50"),
            "passion": Decimal("50"),
            "trust": Decimal("50"),
            "secureness": Decimal("50"),
        }
        deltas = MetricDeltas(
            intimacy=Decimal("5"),
            passion=Decimal("3"),
            trust=Decimal("-2"),
            secureness=Decimal("1"),
        )

        updated = calculator.update_metrics(current, deltas)

        assert updated["intimacy"] == Decimal("55")
        assert updated["passion"] == Decimal("53")
        assert updated["trust"] == Decimal("48")
        assert updated["secureness"] == Decimal("51")

    def test_update_metrics_floor_at_zero(self, calculator):
        """Test that metrics cannot go below 0."""
        current = {
            "intimacy": Decimal("5"),
            "passion": Decimal("5"),
            "trust": Decimal("5"),
            "secureness": Decimal("5"),
        }
        deltas = MetricDeltas(
            intimacy=Decimal("-10"),
            passion=Decimal("-10"),
            trust=Decimal("-10"),
            secureness=Decimal("-10"),
        )

        updated = calculator.update_metrics(current, deltas)

        # All should floor at 0
        assert updated["intimacy"] == Decimal("0")
        assert updated["passion"] == Decimal("0")
        assert updated["trust"] == Decimal("0")
        assert updated["secureness"] == Decimal("0")

    def test_update_metrics_ceiling_at_100(self, calculator):
        """Test that metrics cannot exceed 100."""
        current = {
            "intimacy": Decimal("95"),
            "passion": Decimal("95"),
            "trust": Decimal("95"),
            "secureness": Decimal("95"),
        }
        deltas = MetricDeltas(
            intimacy=Decimal("10"),
            passion=Decimal("10"),
            trust=Decimal("10"),
            secureness=Decimal("10"),
        )

        updated = calculator.update_metrics(current, deltas)

        # All should ceiling at 100
        assert updated["intimacy"] == Decimal("100")
        assert updated["passion"] == Decimal("100")
        assert updated["trust"] == Decimal("100")
        assert updated["secureness"] == Decimal("100")


class TestScoreResult:
    """Test ScoreResult model."""

    def test_score_result_creation(self):
        """Test creating a ScoreResult."""
        result = ScoreResult(
            score_before=Decimal("50"),
            score_after=Decimal("55"),
            metrics_before={
                "intimacy": Decimal("50"),
                "passion": Decimal("50"),
                "trust": Decimal("50"),
                "secureness": Decimal("50"),
            },
            metrics_after={
                "intimacy": Decimal("55"),
                "passion": Decimal("53"),
                "trust": Decimal("52"),
                "secureness": Decimal("51"),
            },
            deltas_applied=MetricDeltas(
                intimacy=Decimal("5"),
                passion=Decimal("3"),
                trust=Decimal("2"),
                secureness=Decimal("1"),
            ),
            multiplier_applied=Decimal("1.0"),
            engagement_state=EngagementState.IN_ZONE,
            events=[],
        )

        assert result.score_before == Decimal("50")
        assert result.score_after == Decimal("55")
        assert result.delta == Decimal("5")

    def test_score_result_with_events(self):
        """Test ScoreResult with threshold events."""
        event = ScoreChangeEvent(
            event_type="boss_threshold_reached",
            chapter=1,
            score_before=Decimal("53"),
            score_after=Decimal("56"),
            threshold=Decimal("55"),
        )

        result = ScoreResult(
            score_before=Decimal("53"),
            score_after=Decimal("56"),
            metrics_before={
                "intimacy": Decimal("50"),
                "passion": Decimal("50"),
                "trust": Decimal("50"),
                "secureness": Decimal("50"),
            },
            metrics_after={
                "intimacy": Decimal("55"),
                "passion": Decimal("55"),
                "trust": Decimal("55"),
                "secureness": Decimal("55"),
            },
            deltas_applied=MetricDeltas(
                intimacy=Decimal("5"),
                passion=Decimal("5"),
                trust=Decimal("5"),
                secureness=Decimal("5"),
            ),
            multiplier_applied=Decimal("1.0"),
            engagement_state=EngagementState.IN_ZONE,
            events=[event],
        )

        assert len(result.events) == 1
        assert result.events[0].event_type == "boss_threshold_reached"


class TestFullCalculation:
    """Test full score calculation flow."""

    @pytest.fixture
    def calculator(self):
        """Create ScoreCalculator instance."""
        return ScoreCalculator()

    def test_calculate_full_flow(self, calculator):
        """Test the full calculation flow."""
        current_metrics = {
            "intimacy": Decimal("50"),
            "passion": Decimal("50"),
            "trust": Decimal("50"),
            "secureness": Decimal("50"),
        }

        analysis = ResponseAnalysis(
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

        result = calculator.calculate(
            current_metrics=current_metrics,
            analysis=analysis,
            engagement_state=EngagementState.IN_ZONE,
            chapter=1,
        )

        assert isinstance(result, ScoreResult)
        assert result.score_after > result.score_before
        assert result.multiplier_applied == Decimal("1.0")

    def test_calculate_with_clingy_state(self, calculator):
        """Test calculation with CLINGY engagement state."""
        current_metrics = {
            "intimacy": Decimal("50"),
            "passion": Decimal("50"),
            "trust": Decimal("50"),
            "secureness": Decimal("50"),
        }

        analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("10"),  # Would be +10, but reduced to +5
                passion=Decimal("10"),
                trust=Decimal("10"),
                secureness=Decimal("10"),
            ),
        )

        result = calculator.calculate(
            current_metrics=current_metrics,
            analysis=analysis,
            engagement_state=EngagementState.CLINGY,
            chapter=1,
        )

        # Deltas should be halved due to CLINGY multiplier (0.5x)
        assert result.multiplier_applied == Decimal("0.5")
        # Score increase should be less than with IN_ZONE
        assert result.delta < Decimal("10")
