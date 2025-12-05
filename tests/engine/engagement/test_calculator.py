"""Tests for Engagement Calculator Phase 3.

TDD tests for spec 014 - T3.1 through T3.3.
Tests written FIRST, implementation follows.
"""

from decimal import Decimal

import pytest


# ==============================================================================
# T3.1: OptimalFrequency Calculator Tests
# ==============================================================================


class TestOptimalFrequencyCalculatorClass:
    """Tests for OptimalFrequencyCalculator class structure (AC-3.1.1)."""

    def test_ac_3_1_1_class_exists_in_calculator_module(self):
        """AC-3.1.1: OptimalFrequencyCalculator class in calculator.py."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        assert OptimalFrequencyCalculator is not None

    def test_calculator_has_get_optimal_method(self):
        """OptimalFrequencyCalculator has get_optimal() method."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        assert hasattr(calculator, "get_optimal")
        assert callable(calculator.get_optimal)


class TestBaseOptimalFrequency:
    """Tests for base optimal frequency values (AC-3.1.2)."""

    def test_ac_3_1_2_base_optimal_chapter_1(self):
        """AC-3.1.2: Chapter 1 base optimal = 15 messages/day."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        # Monday (0) has modifier 0.9
        base = calculator.get_optimal(chapter=1, day_of_week=0)
        # Base is 15, Monday modifier 0.9 = 13.5, rounded
        assert base >= 13 and base <= 14

    def test_ac_3_1_2_base_optimal_chapter_2(self):
        """AC-3.1.2: Chapter 2 base optimal = 12 messages/day."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        base = calculator.get_optimal(chapter=2, day_of_week=0)
        # Base 12 * 0.9 = 10.8
        assert base >= 10 and base <= 11

    def test_ac_3_1_2_base_optimal_chapter_3(self):
        """AC-3.1.2: Chapter 3 base optimal = 10 messages/day."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        base = calculator.get_optimal(chapter=3, day_of_week=0)
        # Base 10 * 0.9 = 9
        assert base >= 9 and base <= 10

    def test_ac_3_1_2_base_optimal_chapter_4(self):
        """AC-3.1.2: Chapter 4 base optimal = 8 messages/day."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        base = calculator.get_optimal(chapter=4, day_of_week=0)
        assert base >= 7 and base <= 8

    def test_ac_3_1_2_base_optimal_chapter_5(self):
        """AC-3.1.2: Chapter 5 base optimal = 6 messages/day."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        base = calculator.get_optimal(chapter=5, day_of_week=0)
        assert base >= 5 and base <= 6


class TestDayModifier:
    """Tests for day-of-week modifiers (AC-3.1.3)."""

    def test_ac_3_1_3_day_modifier_monday(self):
        """AC-3.1.3: Monday modifier = 0.9."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        # Chapter 1 base = 15, Monday (0) modifier = 0.9
        optimal = calculator.get_optimal(chapter=1, day_of_week=0)
        # 15 * 0.9 = 13.5
        assert optimal >= 13 and optimal <= 14

    def test_ac_3_1_3_day_modifier_saturday(self):
        """AC-3.1.3: Saturday modifier = 1.2."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        # Chapter 1 base = 15, Saturday (5) modifier = 1.2
        optimal = calculator.get_optimal(chapter=1, day_of_week=5)
        # 15 * 1.2 = 18
        assert optimal >= 17 and optimal <= 18

    def test_ac_3_1_3_day_modifier_sunday(self):
        """AC-3.1.3: Sunday modifier = 1.1."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        optimal = calculator.get_optimal(chapter=1, day_of_week=6)
        # 15 * 1.1 = 16.5
        assert optimal >= 16 and optimal <= 17


class TestGetOptimalMethod:
    """Tests for get_optimal() method (AC-3.1.4)."""

    def test_ac_3_1_4_returns_messages_per_day(self):
        """AC-3.1.4: get_optimal(chapter, day_of_week) returns messages/day."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        result = calculator.get_optimal(chapter=1, day_of_week=0)

        assert isinstance(result, int)
        assert result > 0


class TestToleranceBand:
    """Tests for tolerance band (AC-3.1.5)."""

    def test_ac_3_1_5_tolerance_chapter_1(self):
        """AC-3.1.5: Chapter 1 tolerance = ±10%."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        tolerance = calculator.get_tolerance_band(chapter=1)

        assert tolerance == Decimal("0.10")

    def test_ac_3_1_5_tolerance_chapter_2(self):
        """AC-3.1.5: Chapter 2 tolerance = ±15%."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        tolerance = calculator.get_tolerance_band(chapter=2)

        assert tolerance == Decimal("0.15")

    def test_ac_3_1_5_tolerance_chapter_3(self):
        """AC-3.1.5: Chapter 3 tolerance = ±20%."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        tolerance = calculator.get_tolerance_band(chapter=3)

        assert tolerance == Decimal("0.20")

    def test_ac_3_1_5_tolerance_chapter_4(self):
        """AC-3.1.5: Chapter 4 tolerance = ±25%."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        tolerance = calculator.get_tolerance_band(chapter=4)

        assert tolerance == Decimal("0.25")

    def test_ac_3_1_5_tolerance_chapter_5(self):
        """AC-3.1.5: Chapter 5 tolerance = ±30%."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        tolerance = calculator.get_tolerance_band(chapter=5)

        assert tolerance == Decimal("0.30")


class TestGetBounds:
    """Tests for get_bounds() method (AC-3.1.6)."""

    def test_ac_3_1_6_returns_lower_upper_tuple(self):
        """AC-3.1.6: get_bounds(chapter, day_of_week) returns (lower, upper)."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        lower, upper = calculator.get_bounds(chapter=1, day_of_week=0)

        assert isinstance(lower, int)
        assert isinstance(upper, int)
        assert lower < upper

    def test_bounds_reflect_tolerance(self):
        """Bounds reflect tolerance percentage."""
        from nikita.engine.engagement.calculator import OptimalFrequencyCalculator

        calculator = OptimalFrequencyCalculator()
        optimal = calculator.get_optimal(chapter=1, day_of_week=0)
        lower, upper = calculator.get_bounds(chapter=1, day_of_week=0)

        # Chapter 1 = ±10%
        expected_lower = int(optimal * 0.90)
        expected_upper = int(optimal * 1.10)

        assert lower == expected_lower or lower == expected_lower + 1
        assert upper == expected_upper or upper == expected_upper - 1


# ==============================================================================
# T3.2: CalibrationCalculator Tests
# ==============================================================================


class TestCalibrationCalculatorClass:
    """Tests for CalibrationCalculator class structure (AC-3.2.1)."""

    def test_ac_3_2_1_class_exists_in_calculator_module(self):
        """AC-3.2.1: CalibrationCalculator class in calculator.py."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        assert CalibrationCalculator is not None

    def test_calculator_has_compute_method(self):
        """CalibrationCalculator has compute() method."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        assert hasattr(calculator, "compute")
        assert callable(calculator.compute)


class TestFrequencyComponent:
    """Tests for frequency component (AC-3.2.2)."""

    def test_ac_3_2_2_frequency_component_method_exists(self):
        """AC-3.2.2: _frequency_component() method exists."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        assert hasattr(calculator, "_frequency_component")

    def test_frequency_component_perfect_match(self):
        """Perfect frequency match returns 1.0."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        # Actual = optimal
        result = calculator._frequency_component(
            actual_messages=15,
            optimal_messages=15,
        )
        assert result == Decimal("1")

    def test_frequency_component_half_optimal(self):
        """Half of optimal returns 0.5."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        # Actual = 50% of optimal
        result = calculator._frequency_component(
            actual_messages=8,
            optimal_messages=16,
        )
        assert result == Decimal("0.5")

    def test_frequency_component_double_optimal(self):
        """Double optimal returns 0.0 (capped deviation)."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        # Actual = 2x optimal → deviation = 1 → score = 0
        result = calculator._frequency_component(
            actual_messages=30,
            optimal_messages=15,
        )
        assert result == Decimal("0")


class TestTimingComponent:
    """Tests for timing component (AC-3.2.3)."""

    def test_ac_3_2_3_timing_component_method_exists(self):
        """AC-3.2.3: _timing_component() method exists."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        assert hasattr(calculator, "_timing_component")

    def test_timing_component_good_timing(self):
        """Good response timing returns high score."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        # 5 minutes avg response time = good
        result = calculator._timing_component(
            avg_response_seconds=300,  # 5 minutes
        )
        assert result >= Decimal("0.7")

    def test_timing_component_too_fast(self):
        """Too-fast timing returns medium score (slightly clingy)."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        # 10 seconds = too eager
        result = calculator._timing_component(
            avg_response_seconds=10,
        )
        assert result >= Decimal("0.5") and result <= Decimal("0.8")

    def test_timing_component_too_slow(self):
        """Too-slow timing returns low score (neglecting)."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        # 6 hours = too slow
        result = calculator._timing_component(
            avg_response_seconds=6 * 3600,
        )
        assert result <= Decimal("0.3")


class TestContentComponent:
    """Tests for content component (AC-3.2.4)."""

    def test_ac_3_2_4_content_component_method_exists(self):
        """AC-3.2.4: _content_component() method exists."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        assert hasattr(calculator, "_content_component")

    def test_content_component_good_quality(self):
        """Good conversation quality returns high score."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        # Good length, low needy/distracted scores
        result = calculator._content_component(
            avg_message_length=80,
            needy_score=Decimal("0.1"),
            distracted_score=Decimal("0.1"),
        )
        assert result >= Decimal("0.7")

    def test_content_component_poor_quality(self):
        """Poor conversation quality returns low score."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        # Short messages, high needy score
        result = calculator._content_component(
            avg_message_length=10,
            needy_score=Decimal("0.8"),
            distracted_score=Decimal("0.5"),
        )
        assert result <= Decimal("0.4")


class TestComputeMethod:
    """Tests for compute() method (AC-3.2.5, AC-3.2.6)."""

    def test_ac_3_2_5_compute_returns_calibration_result(self):
        """AC-3.2.5: compute(player_metrics) returns CalibrationResult."""
        from nikita.engine.engagement.calculator import CalibrationCalculator
        from nikita.engine.engagement.models import CalibrationResult

        calculator = CalibrationCalculator()
        result = calculator.compute(
            actual_messages=15,
            optimal_messages=15,
            avg_response_seconds=300,
            avg_message_length=80,
            needy_score=Decimal("0.1"),
            distracted_score=Decimal("0.1"),
        )

        assert isinstance(result, CalibrationResult)
        assert hasattr(result, "score")
        assert hasattr(result, "frequency_component")
        assert hasattr(result, "timing_component")
        assert hasattr(result, "content_component")
        assert hasattr(result, "suggested_state")

    def test_ac_3_2_6_score_clamped_0_to_1(self):
        """AC-3.2.6: Score clamped to [0, 1] range."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        # Perfect metrics
        result = calculator.compute(
            actual_messages=15,
            optimal_messages=15,
            avg_response_seconds=300,
            avg_message_length=80,
            needy_score=Decimal("0"),
            distracted_score=Decimal("0"),
        )

        assert Decimal("0") <= result.score <= Decimal("1")

        # Terrible metrics
        result_bad = calculator.compute(
            actual_messages=50,
            optimal_messages=10,
            avg_response_seconds=10,
            avg_message_length=5,
            needy_score=Decimal("1"),
            distracted_score=Decimal("1"),
        )

        assert Decimal("0") <= result_bad.score <= Decimal("1")


class TestComponentWeights:
    """Tests for component weights."""

    def test_weights_sum_to_1(self):
        """Component weights: 40% frequency + 30% timing + 30% content = 100%."""
        from nikita.engine.engagement.calculator import CALIBRATION_WEIGHTS

        total = (
            CALIBRATION_WEIGHTS["frequency"] +
            CALIBRATION_WEIGHTS["timing"] +
            CALIBRATION_WEIGHTS["content"]
        )
        assert total == Decimal("1")


# ==============================================================================
# T3.3: State Mapping Tests
# ==============================================================================


class TestStateMapping:
    """Tests for state mapping function (AC-3.3.1 through AC-3.3.6)."""

    def test_ac_3_3_1_map_score_to_state_exists(self):
        """AC-3.3.1: map_score_to_state() function defined."""
        from nikita.engine.engagement.calculator import map_score_to_state

        assert map_score_to_state is not None
        assert callable(map_score_to_state)

    def test_ac_3_3_2_high_score_in_zone(self):
        """AC-3.3.2: Score >= 0.8 → IN_ZONE candidate."""
        from nikita.config.enums import EngagementState
        from nikita.engine.engagement.calculator import map_score_to_state

        result = map_score_to_state(
            score=Decimal("0.85"),
            is_clingy=False,
            is_neglecting=False,
        )
        assert result == EngagementState.IN_ZONE

    def test_ac_3_3_3_medium_score_drifting(self):
        """AC-3.3.3: Score 0.5-0.8 → DRIFTING candidate."""
        from nikita.config.enums import EngagementState
        from nikita.engine.engagement.calculator import map_score_to_state

        result = map_score_to_state(
            score=Decimal("0.65"),
            is_clingy=False,
            is_neglecting=False,
        )
        assert result == EngagementState.DRIFTING

    def test_ac_3_3_4_low_score_clingy(self):
        """AC-3.3.4: Score 0.3-0.5 with clingy → CLINGY."""
        from nikita.config.enums import EngagementState
        from nikita.engine.engagement.calculator import map_score_to_state

        result = map_score_to_state(
            score=Decimal("0.4"),
            is_clingy=True,
            is_neglecting=False,
        )
        assert result == EngagementState.CLINGY

    def test_ac_3_3_4_low_score_distant(self):
        """AC-3.3.4: Score 0.3-0.5 with neglecting → DISTANT."""
        from nikita.config.enums import EngagementState
        from nikita.engine.engagement.calculator import map_score_to_state

        result = map_score_to_state(
            score=Decimal("0.4"),
            is_clingy=False,
            is_neglecting=True,
        )
        assert result == EngagementState.DISTANT

    def test_ac_3_3_5_very_low_score_out_of_zone(self):
        """AC-3.3.5: Score < 0.3 → OUT_OF_ZONE candidate."""
        from nikita.config.enums import EngagementState
        from nikita.engine.engagement.calculator import map_score_to_state

        result = map_score_to_state(
            score=Decimal("0.2"),
            is_clingy=False,
            is_neglecting=False,
        )
        assert result == EngagementState.OUT_OF_ZONE

    def test_neutral_low_score_drifting(self):
        """Low score without clinginess or neglect → DRIFTING."""
        from nikita.config.enums import EngagementState
        from nikita.engine.engagement.calculator import map_score_to_state

        result = map_score_to_state(
            score=Decimal("0.45"),
            is_clingy=False,
            is_neglecting=False,
        )
        # Without clingy/neglect flags, mid-low score = DRIFTING
        assert result == EngagementState.DRIFTING


class TestCalibrationResultSuggestedState:
    """Tests for CalibrationResult.suggested_state integration."""

    def test_calibration_result_includes_suggested_state(self):
        """CalibrationResult includes correct suggested_state."""
        from nikita.config.enums import EngagementState
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        # Perfect metrics should suggest IN_ZONE
        result = calculator.compute(
            actual_messages=15,
            optimal_messages=15,
            avg_response_seconds=300,
            avg_message_length=80,
            needy_score=Decimal("0"),
            distracted_score=Decimal("0"),
        )

        assert result.suggested_state == EngagementState.IN_ZONE

    def test_poor_metrics_suggest_out_of_zone(self):
        """Poor metrics should suggest OUT_OF_ZONE."""
        from nikita.config.enums import EngagementState
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()
        # Very poor metrics
        result = calculator.compute(
            actual_messages=1,
            optimal_messages=15,
            avg_response_seconds=24 * 3600,  # 24 hours!
            avg_message_length=5,
            needy_score=Decimal("0.1"),
            distracted_score=Decimal("0.9"),
        )

        assert result.suggested_state in (
            EngagementState.OUT_OF_ZONE,
            EngagementState.DISTANT,
        )
