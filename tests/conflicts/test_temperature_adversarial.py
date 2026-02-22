"""Adversarial tests for TemperatureEngine (Spec 057).

Targets boundary conditions, overflow/underflow, float precision,
and extreme inputs that may expose clamping, zone classification,
or arithmetic bugs.
"""

import math
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from nikita.conflicts.models import (
    ConflictDetails,
    TemperatureZone,
)
from nikita.conflicts.temperature import TemperatureEngine


# ---------------------------------------------------------------------------
# 1. Zone boundary classification
# ---------------------------------------------------------------------------


class TestTemperatureBoundaryAdversarial:
    """Exact boundary values: which zone do they fall into?

    Zone boundaries per ZONE_BOUNDARIES dict:
      CALM:     [0.0, 25.0)
      WARM:     [25.0, 50.0)
      HOT:      [50.0, 75.0)
      CRITICAL: [75.0, 100.0]
    Upper bound is exclusive EXCEPT for CRITICAL's 100.0.
    """

    def test_zero_is_calm(self):
        """0.0 is the lower bound of CALM."""
        assert TemperatureEngine.get_zone(0.0) == TemperatureZone.CALM

    def test_25_is_warm(self):
        """25.0 is the lower bound of WARM (upper bound of CALM is exclusive)."""
        assert TemperatureEngine.get_zone(25.0) == TemperatureZone.WARM

    def test_50_is_hot(self):
        """50.0 is the lower bound of HOT."""
        assert TemperatureEngine.get_zone(50.0) == TemperatureZone.HOT

    def test_75_is_critical(self):
        """75.0 is the lower bound of CRITICAL."""
        assert TemperatureEngine.get_zone(75.0) == TemperatureZone.CRITICAL

    def test_100_is_critical(self):
        """100.0 must be CRITICAL (the only zone that includes its upper bound)."""
        assert TemperatureEngine.get_zone(100.0) == TemperatureZone.CRITICAL

    def test_just_below_25(self):
        """24.999... should still be CALM."""
        assert TemperatureEngine.get_zone(24.999999999999) == TemperatureZone.CALM

    def test_just_below_50(self):
        """49.999... should still be WARM."""
        assert TemperatureEngine.get_zone(49.999999999999) == TemperatureZone.WARM

    def test_just_below_75(self):
        """74.999... should still be HOT."""
        assert TemperatureEngine.get_zone(74.999999999999) == TemperatureZone.HOT

    def test_negative_temperature_zone(self):
        """Negative temperature: get_zone doesn't clamp — should return CALM.
        NOTE: May fail if get_zone assumes valid 0-100 input."""
        assert TemperatureEngine.get_zone(-1.0) == TemperatureZone.CALM

    def test_temperature_above_100_zone(self):
        """Temperature >100: get_zone doesn't clamp — should return CRITICAL.
        NOTE: May fail if get_zone assumes valid 0-100 input."""
        assert TemperatureEngine.get_zone(150.0) == TemperatureZone.CRITICAL


# ---------------------------------------------------------------------------
# 2. Overflow / Underflow
# ---------------------------------------------------------------------------


class TestTemperatureOverflowUnderflow:
    """Test clamping behavior for extreme increase/decrease operations."""

    def test_increase_near_max(self):
        """increase(99.5, 10.0) must clamp to 100.0."""
        assert TemperatureEngine.increase(99.5, 10.0) == 100.0

    def test_decrease_near_min(self):
        """decrease(0.5, 10.0) must clamp to 0.0."""
        assert TemperatureEngine.decrease(0.5, 10.0) == 0.0

    def test_increase_with_inf_delta(self):
        """increase(50.0, float('inf')) should clamp to 100.0, not produce inf.
        NOTE: May fail if implementation doesn't handle infinity."""
        result = TemperatureEngine.increase(50.0, float("inf"))
        assert result == 100.0, f"Expected 100.0, got {result}"
        assert not math.isinf(result), "Result must not be infinity"

    def test_increase_with_huge_delta(self):
        """increase(50.0, 1e18) should clamp to 100.0."""
        result = TemperatureEngine.increase(50.0, 1e18)
        assert result == 100.0

    def test_decrease_with_inf_delta(self):
        """decrease(50.0, float('inf')) should clamp to 0.0, not produce -inf.
        NOTE: May fail if implementation doesn't handle infinity."""
        result = TemperatureEngine.decrease(50.0, float("inf"))
        assert result == 0.0, f"Expected 0.0, got {result}"
        assert not math.isinf(result), "Result must not be -infinity"

    def test_decrease_with_huge_delta(self):
        """decrease(50.0, 1e18) should clamp to 0.0."""
        result = TemperatureEngine.decrease(50.0, 1e18)
        assert result == 0.0

    def test_increase_already_at_max(self):
        """increase(100.0, 5.0) should stay at 100.0."""
        assert TemperatureEngine.increase(100.0, 5.0) == 100.0

    def test_decrease_already_at_min(self):
        """decrease(0.0, 5.0) should stay at 0.0."""
        assert TemperatureEngine.decrease(0.0, 5.0) == 0.0

    def test_increase_with_nan_delta(self):
        """increase(50.0, float('nan')) — NaN arithmetic is hazardous.
        NOTE: May fail — NaN propagates through min/max unpredictably."""
        result = TemperatureEngine.increase(50.0, float("nan"))
        # NaN should ideally not propagate; 50.0 or 100.0 would be safe
        assert not math.isnan(result), f"NaN leaked into result: {result}"

    def test_decrease_with_nan_delta(self):
        """decrease(50.0, float('nan')) — NaN should not propagate.
        NOTE: May fail — Python's max/min behavior with NaN is surprising."""
        result = TemperatureEngine.decrease(50.0, float("nan"))
        assert not math.isnan(result), f"NaN leaked into result: {result}"


# ---------------------------------------------------------------------------
# 3. Negative and huge deltas
# ---------------------------------------------------------------------------


class TestTemperatureNegativeHugeDeltas:
    """Test that negative deltas are abs'd and huge values clamp properly."""

    def test_increase_negative_delta(self):
        """increase uses abs(delta), so negative should behave like positive."""
        assert TemperatureEngine.increase(50.0, -10.0) == 60.0

    def test_decrease_negative_delta(self):
        """decrease uses abs(delta), so negative delta should still decrease."""
        assert TemperatureEngine.decrease(50.0, -10.0) == 40.0

    def test_increase_huge_positive(self):
        """Huge positive delta: result must be 100.0."""
        assert TemperatureEngine.increase(0.0, 1e12) == 100.0

    def test_decrease_huge_positive(self):
        """Huge positive delta on decrease: result must be 0.0."""
        assert TemperatureEngine.decrease(100.0, 1e12) == 0.0

    def test_increase_zero_delta(self):
        """Zero delta should leave temperature unchanged."""
        assert TemperatureEngine.increase(42.0, 0.0) == 42.0

    def test_decrease_zero_delta(self):
        """Zero delta should leave temperature unchanged."""
        assert TemperatureEngine.decrease(42.0, 0.0) == 42.0

    def test_increase_negative_current(self):
        """increase(-5.0, 3.0) — negative current is out-of-range but should clamp.
        NOTE: May fail if implementation assumes current is already valid."""
        result = TemperatureEngine.increase(-5.0, 3.0)
        assert 0.0 <= result <= 100.0, f"Result {result} outside valid range"

    def test_decrease_above_100_current(self):
        """decrease(120.0, 10.0) — current above range.
        NOTE: May fail if implementation assumes current is already valid."""
        result = TemperatureEngine.decrease(120.0, 10.0)
        assert 0.0 <= result <= 100.0, f"Result {result} outside valid range"


# ---------------------------------------------------------------------------
# 4. Float precision in zone classification
# ---------------------------------------------------------------------------


class TestTemperatureFloatPrecision:
    """Float precision near zone boundaries.

    IEEE 754 representation can cause 24.999999999 != 25.0 etc.
    """

    def test_just_under_warm_boundary(self):
        """24.999999999 should be CALM (just below 25.0)."""
        assert TemperatureEngine.get_zone(24.999999999) == TemperatureZone.CALM

    def test_just_over_warm_boundary(self):
        """25.0000000001 should be WARM (just above 25.0).
        NOTE: May fail if float representation rounds to exactly 25.0."""
        val = 25.0000000001
        zone = TemperatureEngine.get_zone(val)
        # It's either WARM (correct for >25.0) or CALM (if rounded to 25.0)
        # The value 25.0000000001 should be > 25.0 in IEEE 754
        assert zone == TemperatureZone.WARM, f"Expected WARM for {val}, got {zone}"

    def test_just_under_hot_boundary(self):
        """49.999999999 should be WARM."""
        assert TemperatureEngine.get_zone(49.999999999) == TemperatureZone.WARM

    def test_just_over_hot_boundary(self):
        """50.0000000001 should be HOT."""
        val = 50.0000000001
        zone = TemperatureEngine.get_zone(val)
        assert zone == TemperatureZone.HOT, f"Expected HOT for {val}, got {zone}"

    def test_just_under_critical_boundary(self):
        """74.999999999 should be HOT."""
        assert TemperatureEngine.get_zone(74.999999999) == TemperatureZone.HOT

    def test_just_over_critical_boundary(self):
        """75.0000000001 should be CRITICAL."""
        val = 75.0000000001
        zone = TemperatureEngine.get_zone(val)
        assert zone == TemperatureZone.CRITICAL, f"Expected CRITICAL for {val}, got {zone}"

    def test_float_subtraction_precision(self):
        """0.1 + 0.2 != 0.3 in IEEE 754. Verify zone for computed value near 25.0."""
        # 24.7 + 0.3 should be exactly 25.0 but may not due to float precision
        computed = 24.7 + 0.3
        if computed < 25.0:
            assert TemperatureEngine.get_zone(computed) == TemperatureZone.CALM
        else:
            assert TemperatureEngine.get_zone(computed) == TemperatureZone.WARM


# ---------------------------------------------------------------------------
# 5. Time decay adversarial
# ---------------------------------------------------------------------------


class TestTimeDecayAdversarial:
    """Edge cases for apply_time_decay: negative hours, huge hours, zero, negative rate."""

    def test_zero_hours_no_decay(self):
        """Zero hours elapsed = no decay."""
        result = TemperatureEngine.apply_time_decay(50.0, 0.0)
        assert result == 50.0

    def test_negative_hours_should_not_increase(self):
        """Negative hours elapsed — should not increase temperature.
        NOTE: May fail if implementation computes negative decay (= increase).
        The formula is `current - hours * rate`, so negative hours gives
        `current - (negative) = current + positive`, which INCREASES temp."""
        result = TemperatureEngine.apply_time_decay(50.0, -10.0)
        assert result <= 50.0, (
            f"Temperature increased from 50.0 to {result} with negative hours! "
            "Negative elapsed time should not raise temperature."
        )

    def test_huge_hours_clamps_to_zero(self):
        """1e6 hours elapsed should decay to 0.0."""
        result = TemperatureEngine.apply_time_decay(100.0, 1e6)
        assert result == 0.0

    def test_negative_rate(self):
        """Negative decay rate: should not increase temperature.
        NOTE: May fail — negative rate with positive hours = negative decay
        amount, which is subtracted, giving `current - (-X) = current + X`."""
        result = TemperatureEngine.apply_time_decay(50.0, 1.0, rate=-0.5)
        assert result <= 50.0, (
            f"Temperature increased from 50.0 to {result} with negative rate! "
            "Negative rate should not raise temperature."
        )

    def test_zero_rate_no_decay(self):
        """Rate of 0.0 should produce no decay."""
        result = TemperatureEngine.apply_time_decay(75.0, 100.0, rate=0.0)
        assert result == 75.0

    def test_inf_hours(self):
        """Infinite hours elapsed should decay to 0.0.
        NOTE: May fail — inf * 0.5 = inf, 50.0 - inf = -inf, max(0, -inf)=0."""
        result = TemperatureEngine.apply_time_decay(50.0, float("inf"))
        assert result == 0.0

    def test_inf_rate(self):
        """Infinite rate should decay to 0.0 for any positive hours."""
        result = TemperatureEngine.apply_time_decay(50.0, 1.0, rate=float("inf"))
        assert result == 0.0

    def test_nan_hours(self):
        """NaN hours should not produce NaN result.
        NOTE: May fail — NaN propagates through arithmetic."""
        result = TemperatureEngine.apply_time_decay(50.0, float("nan"))
        assert not math.isnan(result), f"NaN leaked: {result}"

    def test_decay_from_zero(self):
        """Decaying from 0.0 should stay at 0.0."""
        result = TemperatureEngine.apply_time_decay(0.0, 10.0)
        assert result == 0.0

    def test_exact_decay_to_zero(self):
        """Exact hours to reach 0.0: temp=10.0, rate=0.5, hours=20.0."""
        result = TemperatureEngine.apply_time_decay(10.0, 20.0, rate=0.5)
        assert result == 0.0


# ---------------------------------------------------------------------------
# 6. Interpolate probability adversarial
# ---------------------------------------------------------------------------


class TestInterpolateProbabilityAdversarial:
    """Edge cases for interpolate_probability."""

    def test_at_zero(self):
        """Temperature 0.0 = CALM zone, probability should be 0.0."""
        assert TemperatureEngine.interpolate_probability(0.0) == 0.0

    def test_at_100(self):
        """Temperature 100.0 = CRITICAL zone.
        CRITICAL zone: prob_min=0.60, prob_max=0.90
        zone_progress = (100 - 75) / (100 - 75) = 1.0
        Result = 0.60 + 0.30 * 1.0 = 0.90"""
        result = TemperatureEngine.interpolate_probability(100.0)
        assert result == pytest.approx(0.90, abs=1e-9)

    def test_at_calm_warm_boundary(self):
        """At 25.0: WARM zone, progress=0.0.
        Result = 0.10 + 0.15 * 0.0 = 0.10"""
        result = TemperatureEngine.interpolate_probability(25.0)
        assert result == pytest.approx(0.10, abs=1e-9)

    def test_at_warm_hot_boundary(self):
        """At 50.0: HOT zone, progress=0.0.
        Result = 0.25 + 0.35 * 0.0 = 0.25"""
        result = TemperatureEngine.interpolate_probability(50.0)
        assert result == pytest.approx(0.25, abs=1e-9)

    def test_at_hot_critical_boundary(self):
        """At 75.0: CRITICAL zone, progress=0.0.
        Result = 0.60 + 0.30 * 0.0 = 0.60"""
        result = TemperatureEngine.interpolate_probability(75.0)
        assert result == pytest.approx(0.60, abs=1e-9)

    def test_calm_midpoint(self):
        """At 12.5: CALM zone midpoint. CALM prob is 0.0 constant."""
        assert TemperatureEngine.interpolate_probability(12.5) == 0.0

    def test_warm_midpoint(self):
        """At 37.5: WARM zone midpoint.
        progress = (37.5 - 25) / (50 - 25) = 0.5
        Result = 0.10 + 0.15 * 0.5 = 0.175"""
        result = TemperatureEngine.interpolate_probability(37.5)
        assert result == pytest.approx(0.175, abs=1e-9)

    def test_hot_midpoint(self):
        """At 62.5: HOT zone midpoint.
        progress = (62.5 - 50) / (75 - 50) = 0.5
        Result = 0.25 + 0.35 * 0.5 = 0.425"""
        result = TemperatureEngine.interpolate_probability(62.5)
        assert result == pytest.approx(0.425, abs=1e-9)

    def test_critical_midpoint(self):
        """At 87.5: CRITICAL zone midpoint.
        progress = (87.5 - 75) / (100 - 75) = 0.5
        Result = 0.60 + 0.30 * 0.5 = 0.75"""
        result = TemperatureEngine.interpolate_probability(87.5)
        assert result == pytest.approx(0.75, abs=1e-9)

    def test_negative_temperature(self):
        """Negative temperature: zone=CALM, prob should be 0.0 or handle gracefully.
        NOTE: May fail — zone_progress could be negative."""
        result = TemperatureEngine.interpolate_probability(-10.0)
        assert result >= 0.0, f"Negative probability: {result}"

    def test_above_100_temperature(self):
        """Temperature >100: zone=CRITICAL, progress >1.0.
        NOTE: May fail — result could exceed 0.90."""
        result = TemperatureEngine.interpolate_probability(150.0)
        assert 0.0 <= result <= 1.0, f"Probability out of range: {result}"


# ---------------------------------------------------------------------------
# 7. Score delta to temperature delta
# ---------------------------------------------------------------------------


class TestScoreDeltaAdversarial:
    """Edge cases for calculate_delta_from_score."""

    def test_zero_score_delta(self):
        """Zero score delta = zero temperature delta."""
        assert TemperatureEngine.calculate_delta_from_score(0.0) == 0.0

    def test_small_negative_below_threshold(self):
        """Small negative: -2.0 (below SCORE_DROP_THRESHOLD=3.0).
        Result = abs(-2.0) * 1.5 = 3.0 (no bonus)."""
        result = TemperatureEngine.calculate_delta_from_score(-2.0)
        assert result == pytest.approx(3.0)

    def test_exactly_at_threshold(self):
        """Score delta exactly at -SCORE_DROP_THRESHOLD = -3.0.
        abs(-3.0) = 3.0, NOT > 3.0, so no bonus.
        Result = 3.0 * 1.5 = 4.5."""
        result = TemperatureEngine.calculate_delta_from_score(-3.0)
        assert result == pytest.approx(4.5), (
            f"Expected 4.5 (no bonus at exactly threshold), got {result}"
        )

    def test_just_over_threshold(self):
        """Score delta just past threshold: -3.01.
        abs(-3.01) = 3.01 > 3.0, so bonus applies.
        Result = 3.01 * 1.5 + 5.0 = 4.515 + 5.0 = 9.515."""
        result = TemperatureEngine.calculate_delta_from_score(-3.01)
        assert result == pytest.approx(3.01 * 1.5 + 5.0, abs=1e-6)

    def test_huge_negative(self):
        """Huge negative score delta: -1000.
        Result = 1000 * 1.5 + 5.0 = 1505.0 (temp delta is unclamped)."""
        result = TemperatureEngine.calculate_delta_from_score(-1000.0)
        assert result == pytest.approx(1505.0)

    def test_huge_positive(self):
        """Huge positive score delta: 1000.
        Result = -(1000 * 0.5) = -500.0."""
        result = TemperatureEngine.calculate_delta_from_score(1000.0)
        assert result == pytest.approx(-500.0)

    def test_small_positive(self):
        """Small positive: 1.0.
        Result = -(1.0 * 0.5) = -0.5."""
        result = TemperatureEngine.calculate_delta_from_score(1.0)
        assert result == pytest.approx(-0.5)

    def test_negative_delta_is_always_positive_result(self):
        """Any negative score delta should produce positive temp delta."""
        for delta in [-0.01, -1.0, -5.0, -100.0]:
            result = TemperatureEngine.calculate_delta_from_score(delta)
            assert result > 0.0, f"delta={delta} produced non-positive temp_delta={result}"

    def test_positive_delta_is_always_negative_result(self):
        """Any positive score delta should produce negative temp delta."""
        for delta in [0.01, 1.0, 5.0, 100.0]:
            result = TemperatureEngine.calculate_delta_from_score(delta)
            assert result < 0.0, f"delta={delta} produced non-negative temp_delta={result}"


# ---------------------------------------------------------------------------
# 8. update_conflict_details adversarial
# ---------------------------------------------------------------------------


class TestUpdateConflictDetailsAdversarial:
    """Edge cases for update_conflict_details."""

    def _make_details(self, temp: float = 50.0) -> ConflictDetails:
        """Helper: create ConflictDetails with given temperature."""
        return ConflictDetails(
            temperature=temp,
            zone="warm",
            positive_count=5,
            negative_count=2,
            gottman_ratio=2.5,
            gottman_target=5.0,
        )

    def test_nan_delta(self):
        """NaN temp_delta should not produce NaN temperature.
        NOTE: May fail — NaN + 50.0 = NaN, then max(0, min(100, NaN)) is NaN."""
        details = self._make_details(50.0)
        result = TemperatureEngine.update_conflict_details(details, float("nan"))
        assert not math.isnan(result.temperature), (
            f"NaN leaked into temperature: {result.temperature}"
        )

    def test_inf_delta(self):
        """Infinite delta should clamp to 100.0."""
        details = self._make_details(50.0)
        result = TemperatureEngine.update_conflict_details(details, float("inf"))
        assert result.temperature == 100.0

    def test_neg_inf_delta(self):
        """Negative infinite delta should clamp to 0.0."""
        details = self._make_details(50.0)
        result = TemperatureEngine.update_conflict_details(details, float("-inf"))
        assert result.temperature == 0.0

    def test_huge_positive_delta(self):
        """Huge positive delta should clamp to 100.0."""
        details = self._make_details(50.0)
        result = TemperatureEngine.update_conflict_details(details, 1e18)
        assert result.temperature == 100.0

    def test_huge_negative_delta(self):
        """Huge negative delta should clamp to 0.0."""
        details = self._make_details(50.0)
        result = TemperatureEngine.update_conflict_details(details, -1e18)
        assert result.temperature == 0.0

    def test_zero_delta(self):
        """Zero delta should preserve temperature exactly."""
        details = self._make_details(42.0)
        result = TemperatureEngine.update_conflict_details(details, 0.0)
        assert result.temperature == 42.0

    def test_zone_updates_after_increase(self):
        """After increasing from 50 to 80, zone should be CRITICAL."""
        details = self._make_details(50.0)
        result = TemperatureEngine.update_conflict_details(details, 30.0)
        assert result.temperature == 80.0
        assert result.zone == TemperatureZone.CRITICAL.value

    def test_zone_updates_after_decrease(self):
        """After decreasing from 50 to 10, zone should be calm."""
        details = self._make_details(50.0)
        result = TemperatureEngine.update_conflict_details(details, -40.0)
        assert result.temperature == 10.0
        assert result.zone == TemperatureZone.CALM.value

    def test_preserves_gottman_counters(self):
        """update_conflict_details must not mutate Gottman counters."""
        details = self._make_details(50.0)
        result = TemperatureEngine.update_conflict_details(details, 10.0)
        assert result.positive_count == details.positive_count
        assert result.negative_count == details.negative_count
        assert result.gottman_ratio == details.gottman_ratio

    def test_details_at_max_temp_with_positive_delta(self):
        """Details already at 100.0, applying +10 should stay 100.0."""
        details = self._make_details(100.0)
        result = TemperatureEngine.update_conflict_details(details, 10.0)
        assert result.temperature == 100.0

    def test_details_at_min_temp_with_negative_delta(self):
        """Details at 0.0, applying -10 should stay 0.0."""
        details = self._make_details(0.0)
        result = TemperatureEngine.update_conflict_details(details, -10.0)
        assert result.temperature == 0.0

    def test_timestamp_is_set(self):
        """update_conflict_details should set last_temp_update."""
        details = self._make_details(50.0)
        now = datetime(2025, 1, 1, tzinfo=UTC)
        result = TemperatureEngine.update_conflict_details(details, 5.0, now=now)
        assert result.last_temp_update == now.isoformat()

    def test_pydantic_validation_blocks_invalid_temp(self):
        """ConflictDetails has ge=0, le=100 validator. Verify it catches out-of-range.
        NOTE: May fail if update_conflict_details does the clamping BEFORE
        passing to Pydantic, in which case this always succeeds.
        If NOT clamped, Pydantic should raise ValidationError."""
        details = self._make_details(50.0)
        # This should NOT raise even if delta pushes temp out of range,
        # because update_conflict_details clamps before constructing.
        result = TemperatureEngine.update_conflict_details(details, 1000.0)
        assert 0.0 <= result.temperature <= 100.0
