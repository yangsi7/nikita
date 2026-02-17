"""Tests for temperature engine (Spec 057, T4).

Tests cover:
- Temperature increase/decrease with clamping
- Zone boundaries (CALM, WARM, HOT, CRITICAL)
- Time decay
- Injection probability interpolation
- Score delta to temperature mapping
- Horseman and trigger deltas
"""

import pytest
from datetime import UTC, datetime

from nikita.conflicts.models import (
    ConflictDetails,
    HorsemanType,
    TemperatureZone,
    TriggerType,
)
from nikita.conflicts.temperature import TemperatureEngine


class TestTemperatureIncrease:
    """Test temperature increase with clamping."""

    def test_normal_increase(self):
        assert TemperatureEngine.increase(50.0, 10.0) == 60.0

    def test_increase_clamped_at_100(self):
        assert TemperatureEngine.increase(95.0, 10.0) == 100.0

    def test_increase_from_zero(self):
        assert TemperatureEngine.increase(0.0, 5.0) == 5.0

    def test_increase_negative_delta_becomes_positive(self):
        # abs(delta) is used
        assert TemperatureEngine.increase(50.0, -10.0) == 60.0

    def test_increase_exact_boundary(self):
        assert TemperatureEngine.increase(75.0, 25.0) == 100.0


class TestTemperatureDecrease:
    """Test temperature decrease with clamping."""

    def test_normal_decrease(self):
        assert TemperatureEngine.decrease(50.0, 10.0) == 40.0

    def test_decrease_clamped_at_zero(self):
        assert TemperatureEngine.decrease(5.0, 10.0) == 0.0

    def test_decrease_from_100(self):
        assert TemperatureEngine.decrease(100.0, 25.0) == 75.0

    def test_decrease_negative_delta_becomes_positive(self):
        assert TemperatureEngine.decrease(50.0, -10.0) == 40.0


class TestGetZone:
    """Test zone computation from temperature value."""

    def test_calm_zone_zero(self):
        assert TemperatureEngine.get_zone(0.0) == TemperatureZone.CALM

    def test_calm_zone_upper_bound(self):
        assert TemperatureEngine.get_zone(24.9) == TemperatureZone.CALM

    def test_warm_zone_lower_bound(self):
        assert TemperatureEngine.get_zone(25.0) == TemperatureZone.WARM

    def test_warm_zone_upper_bound(self):
        assert TemperatureEngine.get_zone(49.9) == TemperatureZone.WARM

    def test_hot_zone_lower_bound(self):
        assert TemperatureEngine.get_zone(50.0) == TemperatureZone.HOT

    def test_hot_zone_upper_bound(self):
        assert TemperatureEngine.get_zone(74.9) == TemperatureZone.HOT

    def test_critical_zone_lower_bound(self):
        assert TemperatureEngine.get_zone(75.0) == TemperatureZone.CRITICAL

    def test_critical_zone_100(self):
        assert TemperatureEngine.get_zone(100.0) == TemperatureZone.CRITICAL


class TestTimeDecay:
    """Test passive time-based decay."""

    def test_one_hour_decay(self):
        result = TemperatureEngine.apply_time_decay(50.0, 1.0)
        assert result == pytest.approx(49.5)

    def test_24_hour_decay(self):
        result = TemperatureEngine.apply_time_decay(50.0, 24.0)
        assert result == pytest.approx(38.0)

    def test_decay_clamped_at_zero(self):
        result = TemperatureEngine.apply_time_decay(5.0, 100.0)
        assert result == 0.0

    def test_zero_hours_no_decay(self):
        result = TemperatureEngine.apply_time_decay(50.0, 0.0)
        assert result == 50.0

    def test_custom_rate(self):
        result = TemperatureEngine.apply_time_decay(50.0, 10.0, rate=1.0)
        assert result == pytest.approx(40.0)


class TestInjectionProbability:
    """Test injection probability per zone."""

    def test_calm_zero_probability(self):
        prob = TemperatureEngine.get_injection_probability(TemperatureZone.CALM)
        assert prob == (0.0, 0.0)

    def test_warm_probability(self):
        prob = TemperatureEngine.get_injection_probability(TemperatureZone.WARM)
        assert prob == (0.10, 0.25)

    def test_hot_probability(self):
        prob = TemperatureEngine.get_injection_probability(TemperatureZone.HOT)
        assert prob == (0.25, 0.60)

    def test_critical_probability(self):
        prob = TemperatureEngine.get_injection_probability(TemperatureZone.CRITICAL)
        assert prob == (0.60, 0.90)


class TestMaxSeverity:
    """Test max severity per zone."""

    def test_calm_no_severity(self):
        assert TemperatureEngine.get_max_severity(TemperatureZone.CALM) == 0.0

    def test_warm_capped(self):
        assert TemperatureEngine.get_max_severity(TemperatureZone.WARM) == 0.4

    def test_hot_capped(self):
        assert TemperatureEngine.get_max_severity(TemperatureZone.HOT) == 0.7

    def test_critical_full(self):
        assert TemperatureEngine.get_max_severity(TemperatureZone.CRITICAL) == 1.0


class TestScoreDelta:
    """Test score delta to temperature mapping."""

    def test_negative_score_increases_temp(self):
        delta = TemperatureEngine.calculate_delta_from_score(-5.0)
        assert delta > 0

    def test_positive_score_decreases_temp(self):
        delta = TemperatureEngine.calculate_delta_from_score(5.0)
        assert delta < 0

    def test_zero_score_no_change(self):
        delta = TemperatureEngine.calculate_delta_from_score(0.0)
        assert delta == 0.0

    def test_large_drop_bonus(self):
        small_drop = TemperatureEngine.calculate_delta_from_score(-2.0)
        large_drop = TemperatureEngine.calculate_delta_from_score(-5.0)
        # Large drop gets bonus
        assert large_drop > small_drop + 3.0  # At least 5pt bonus

    def test_positive_slower_than_negative(self):
        pos = abs(TemperatureEngine.calculate_delta_from_score(5.0))
        neg = abs(TemperatureEngine.calculate_delta_from_score(-5.0))
        assert pos < neg


class TestHorsemanDelta:
    """Test horseman detection temperature deltas."""

    def test_criticism_delta(self):
        assert TemperatureEngine.calculate_delta_from_horseman(HorsemanType.CRITICISM) == 4.0

    def test_contempt_highest_delta(self):
        assert TemperatureEngine.calculate_delta_from_horseman(HorsemanType.CONTEMPT) == 8.0

    def test_defensiveness_delta(self):
        assert TemperatureEngine.calculate_delta_from_horseman(HorsemanType.DEFENSIVENESS) == 3.0

    def test_stonewalling_delta(self):
        assert TemperatureEngine.calculate_delta_from_horseman(HorsemanType.STONEWALLING) == 5.0


class TestTriggerDelta:
    """Test trigger type temperature deltas."""

    def test_boundary_highest(self):
        assert TemperatureEngine.calculate_delta_from_trigger(TriggerType.BOUNDARY) == 8.0

    def test_trust_high(self):
        assert TemperatureEngine.calculate_delta_from_trigger(TriggerType.TRUST) == 6.0

    def test_dismissive_low(self):
        assert TemperatureEngine.calculate_delta_from_trigger(TriggerType.DISMISSIVE) == 3.0


class TestInterpolateProbability:
    """Test linear interpolation of injection probability."""

    def test_calm_zone_zero(self):
        assert TemperatureEngine.interpolate_probability(10.0) == 0.0

    def test_warm_zone_midpoint(self):
        prob = TemperatureEngine.interpolate_probability(37.5)
        assert 0.10 < prob < 0.25

    def test_critical_zone_high(self):
        prob = TemperatureEngine.interpolate_probability(90.0)
        assert 0.60 < prob < 0.90


class TestUpdateConflictDetails:
    """Test updating conflict details with temperature delta."""

    def test_increase_temperature(self):
        details = ConflictDetails(temperature=30.0, zone="warm")
        updated = TemperatureEngine.update_conflict_details(details, 10.0)
        assert updated.temperature == 40.0
        assert updated.zone == "warm"

    def test_zone_transition_on_update(self):
        details = ConflictDetails(temperature=48.0, zone="warm")
        updated = TemperatureEngine.update_conflict_details(details, 5.0)
        assert updated.temperature == 53.0
        assert updated.zone == "hot"

    def test_clamp_at_100(self):
        details = ConflictDetails(temperature=95.0, zone="critical")
        updated = TemperatureEngine.update_conflict_details(details, 20.0)
        assert updated.temperature == 100.0

    def test_clamp_at_0(self):
        details = ConflictDetails(temperature=3.0, zone="calm")
        updated = TemperatureEngine.update_conflict_details(details, -10.0)
        assert updated.temperature == 0.0

    def test_preserves_gottman_counters(self):
        details = ConflictDetails(
            temperature=50.0, zone="hot",
            positive_count=10, negative_count=2,
        )
        updated = TemperatureEngine.update_conflict_details(details, 5.0)
        assert updated.positive_count == 10
        assert updated.negative_count == 2

    def test_updates_timestamp(self):
        details = ConflictDetails(temperature=50.0, zone="hot", last_temp_update=None)
        updated = TemperatureEngine.update_conflict_details(details, 5.0)
        assert updated.last_temp_update is not None
