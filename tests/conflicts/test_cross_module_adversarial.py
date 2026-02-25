"""DA-04: Adversarial cross-module integration tests for conflict system.

Targets data flow across:
- nikita/conflicts/temperature.py (TemperatureEngine)
- nikita/conflicts/gottman.py (GottmanTracker)
- nikita/conflicts/generator.py (ConflictGenerator)
- nikita/conflicts/breakup.py (BreakupManager)
- nikita/conflicts/models.py (ConflictDetails, GottmanCounters)

Uses mocks and direct model construction (ConflictStore removed in Spec 057).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from nikita.conflicts.breakup import BreakupManager, BreakupRisk
from nikita.conflicts.generator import ConflictGenerator, GenerationContext
from nikita.conflicts.gottman import GottmanTracker
from nikita.conflicts.models import (
    ConflictDetails,
    ConflictTrigger,
    ConflictType,
    GottmanCounters,
    TemperatureZone,
    TriggerType,
)
from nikita.conflicts.temperature import TemperatureEngine


class TestStaleConflictDetails:
    """ConflictDetails with last_temp_update from 30 days ago.

    TemperatureEngine.update_conflict_details should still work —
    it does not reject stale timestamps.
    """

    def test_stale_30_day_old_update(self):
        """30-day-old last_temp_update should be accepted and overwritten."""
        old_timestamp = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        details = ConflictDetails(
            temperature=45.0,
            zone="warm",
            last_temp_update=old_timestamp,
        )

        now = datetime.now(UTC)
        updated = TemperatureEngine.update_conflict_details(details, temp_delta=10.0, now=now)

        assert updated.temperature == 55.0
        assert updated.zone == "hot"
        assert updated.last_temp_update == now.isoformat()

    def test_stale_365_day_old_update(self):
        """1-year-old last_temp_update should still work."""
        old_timestamp = (datetime.now(UTC) - timedelta(days=365)).isoformat()
        details = ConflictDetails(
            temperature=10.0,
            zone="calm",
            last_temp_update=old_timestamp,
        )

        updated = TemperatureEngine.update_conflict_details(details, temp_delta=20.0)
        assert updated.temperature == 30.0
        assert updated.zone == "warm"

    def test_null_last_temp_update(self):
        """None last_temp_update is valid — fresh state."""
        details = ConflictDetails(temperature=50.0, last_temp_update=None)
        updated = TemperatureEngine.update_conflict_details(details, temp_delta=-10.0)
        assert updated.temperature == 40.0
        assert updated.last_temp_update is not None

    def test_stale_details_preserve_all_fields(self):
        """All non-temperature fields should be preserved through update."""
        old_timestamp = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        details = ConflictDetails(
            temperature=30.0,
            zone="warm",
            positive_count=10,
            negative_count=3,
            gottman_ratio=3.33,
            gottman_target=5.0,
            horsemen_detected=["criticism"],
            repair_attempts=[{"at": "2025-01-01T00:00:00Z", "quality": "good", "temp_delta": -3.0}],
            last_temp_update=old_timestamp,
            session_positive=4,
            session_negative=2,
        )

        updated = TemperatureEngine.update_conflict_details(details, temp_delta=5.0)
        assert updated.positive_count == 10
        assert updated.negative_count == 3
        assert updated.gottman_ratio == 3.33
        assert updated.gottman_target == 5.0
        assert updated.horsemen_detected == ["criticism"]
        assert len(updated.repair_attempts) == 1
        assert updated.session_positive == 4
        assert updated.session_negative == 2


class TestHighNegativeZeroPositive:
    """GottmanCounters with negative_count=100, positive_count=0.

    Ratio = 0.0 (not inf). Should produce a positive temperature delta
    (bad ratio = temperature increase).
    """

    def test_ratio_zero_with_negatives(self):
        """0 positive, 100 negative -> ratio 0.0."""
        counters = GottmanCounters(positive_count=0, negative_count=100)
        ratio = GottmanTracker.get_ratio(counters)
        assert ratio == 0.0

    def test_below_target_with_zero_positives(self):
        """Zero positives, many negatives -> below target in conflict mode."""
        counters = GottmanCounters(positive_count=0, negative_count=100)
        assert GottmanTracker.is_below_target(counters, is_in_conflict=True)

    def test_below_target_with_zero_positives_normal(self):
        """Zero positives, many negatives -> below target in normal mode."""
        counters = GottmanCounters(positive_count=0, negative_count=100)
        assert GottmanTracker.is_below_target(counters, is_in_conflict=False)

    def test_temperature_delta_positive_with_bad_ratio(self):
        """Bad ratio should produce a positive temperature delta (increase)."""
        counters = GottmanCounters(positive_count=0, negative_count=100)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        assert delta > 0.0, "Bad ratio should increase temperature"

    def test_temperature_delta_max_with_zero_ratio(self):
        """Zero ratio is maximally below target -> delta should be at max."""
        counters = GottmanCounters(positive_count=0, negative_count=100)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        # shortfall = (target - 0) / target = 1.0 -> max delta
        expected = GottmanTracker.BELOW_TARGET_DELTA_MIN + (
            GottmanTracker.BELOW_TARGET_DELTA_MAX - GottmanTracker.BELOW_TARGET_DELTA_MIN
        ) * 1.0
        assert delta == pytest.approx(expected)

    def test_temperature_delta_normal_mode_worse(self):
        """Normal mode has higher target (20:1), so delta should be same max."""
        counters = GottmanCounters(positive_count=0, negative_count=100)
        delta_conflict = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        delta_normal = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=False)
        # Both should be at max delta since ratio=0 is maximally below either target
        assert delta_conflict == pytest.approx(delta_normal)

    def test_single_negative_zero_positive(self):
        """Even 1 negative with 0 positive -> ratio 0.0, below target."""
        counters = GottmanCounters(positive_count=0, negative_count=1)
        assert GottmanTracker.get_ratio(counters) == 0.0
        assert GottmanTracker.is_below_target(counters, is_in_conflict=True)


class TestConflictDetailsAcrossModules:
    """Create ConflictDetails, update via TemperatureEngine, then via GottmanTracker.

    Verify all fields preserved correctly through multi-module flow.
    """

    def test_temperature_then_gottman_flow(self):
        """Update temperature, then record a Gottman interaction — fields preserved."""
        # Start with custom state
        details = ConflictDetails(
            temperature=40.0,
            zone="warm",
            positive_count=5,
            negative_count=1,
            gottman_ratio=5.0,
            gottman_target=5.0,
            horsemen_detected=["contempt"],
            session_positive=2,
            session_negative=0,
        )

        # Step 1: Temperature increase via TemperatureEngine
        after_temp = TemperatureEngine.update_conflict_details(details, temp_delta=20.0)
        assert after_temp.temperature == 60.0
        assert after_temp.zone == "hot"
        # Gottman fields preserved
        assert after_temp.positive_count == 5
        assert after_temp.negative_count == 1
        assert after_temp.horsemen_detected == ["contempt"]
        assert after_temp.session_positive == 2

        # Step 2: Gottman negative interaction
        after_gottman = GottmanTracker.update_conflict_details(
            after_temp, is_positive=False, is_in_conflict=True
        )
        assert after_gottman.negative_count == 2
        assert after_gottman.session_negative == 1
        # Temperature fields preserved
        assert after_gottman.temperature == 60.0
        assert after_gottman.zone == "hot"
        assert after_gottman.horsemen_detected == ["contempt"]
        # Ratio recalculated
        assert after_gottman.gottman_ratio == pytest.approx(5.0 / 2.0)

    def test_multiple_gottman_then_temperature(self):
        """Multiple Gottman interactions, then temperature update."""
        details = ConflictDetails(temperature=10.0, zone="calm")

        # 5 negative interactions
        for _ in range(5):
            details = GottmanTracker.update_conflict_details(
                details, is_positive=False, is_in_conflict=False
            )

        assert details.negative_count == 5
        assert details.positive_count == 0
        assert details.session_negative == 5

        # Temperature update should preserve Gottman state
        details = TemperatureEngine.update_conflict_details(details, temp_delta=50.0)
        assert details.temperature == 60.0
        assert details.negative_count == 5
        assert details.session_negative == 5

    def test_gottman_infinity_ratio_stored_as_999(self):
        """Infinity ratio gets stored as 999.0 in ConflictDetails.gottman_ratio."""
        details = ConflictDetails(temperature=20.0)

        # Positive interaction with 0 negatives -> inf ratio
        updated = GottmanTracker.update_conflict_details(
            details, is_positive=True, is_in_conflict=False
        )
        # GottmanTracker caps inf -> 999.0
        assert updated.gottman_ratio == 999.0
        assert updated.positive_count == 1
        assert updated.negative_count == 0

    def test_temperature_clamping_in_flow(self):
        """Temperature should clamp to 0-100 through the flow."""
        details = ConflictDetails(temperature=95.0, zone="critical")

        # Try to push above 100
        updated = TemperatureEngine.update_conflict_details(details, temp_delta=50.0)
        assert updated.temperature == 100.0

        # Try to push below 0
        updated2 = TemperatureEngine.update_conflict_details(
            ConflictDetails(temperature=5.0), temp_delta=-50.0
        )
        assert updated2.temperature == 0.0


class TestGeneratorWithExtremeTemperature:
    """ConflictGenerator._generate_with_temperature with extreme values.

    Tests temperature-based thresholds (flag removed, always active).
    """

    def _make_trigger(self, severity: float = 0.5) -> ConflictTrigger:
        """Create a test trigger."""
        return ConflictTrigger(
            trigger_id="test-trigger-1",
            trigger_type=TriggerType.JEALOUSY,
            severity=severity,
        )

    def _make_context(self, user_id: str = "user-1") -> GenerationContext:
        """Create a test generation context."""
        return GenerationContext(
            user_id=user_id,
            chapter=3,
            relationship_score=40,
        )

    def test_critical_zone_caps_severity(self):
        """Temperature=100 (CRITICAL) — severity should be capped at 1.0."""
        generator = ConflictGenerator()
        context = self._make_context()
        triggers = [self._make_trigger(severity=0.9)]
        conflict_details = {"temperature": 100.0, "zone": "critical"}

        with patch("nikita.conflicts.generator.random.random", return_value=0.0):
            result = generator._generate_with_temperature(
                triggers, context, conflict_details
            )

        if result.generated:
            assert result.conflict is not None
            assert result.conflict.severity <= 1.0

    def test_calm_zone_blocks_generation(self):
        """Temperature=0 (CALM) — no conflict should be generated."""
        generator = ConflictGenerator()
        context = self._make_context()
        triggers = [self._make_trigger(severity=1.0)]
        conflict_details = {"temperature": 0.0, "zone": "calm"}

        result = generator._generate_with_temperature(
            triggers, context, conflict_details
        )

        assert result.generated is False
        assert "CALM" in result.reason

    def test_warm_zone_severity_cap(self):
        """Temperature=30 (WARM) — severity capped at 0.4."""
        generator = ConflictGenerator()
        context = self._make_context()
        triggers = [self._make_trigger(severity=0.9)]
        conflict_details = {"temperature": 30.0, "zone": "warm"}

        with patch("nikita.conflicts.generator.random.random", return_value=0.0):
            result = generator._generate_with_temperature(
                triggers, context, conflict_details
            )

        if result.generated:
            assert result.conflict.severity <= 0.4

    def test_hot_zone_severity_cap(self):
        """Temperature=60 (HOT) — severity capped at 0.7."""
        generator = ConflictGenerator()
        context = self._make_context()
        triggers = [self._make_trigger(severity=1.0)]
        conflict_details = {"temperature": 60.0, "zone": "hot"}

        with patch("nikita.conflicts.generator.random.random", return_value=0.0):
            result = generator._generate_with_temperature(
                triggers, context, conflict_details
            )

        if result.generated:
            assert result.conflict.severity <= 0.7

    def test_no_triggers_no_injection(self):
        """CRITICAL zone but no triggers — should skip generation."""
        generator = ConflictGenerator()
        context = self._make_context()
        conflict_details = {"temperature": 90.0, "zone": "critical"}

        result = generator._generate_with_temperature(
            triggers=[], context=context, conflict_details=conflict_details
        )

        assert result.generated is False
        assert "No triggers" in result.reason

    def test_injection_roll_failure(self):
        """Injection probability roll fails — no conflict generated."""
        generator = ConflictGenerator()
        context = self._make_context()
        triggers = [self._make_trigger(severity=0.9)]
        # WARM zone: max probability = 0.25
        conflict_details = {"temperature": 30.0, "zone": "warm"}

        # random.random() returns 0.99 -> >= injection_probability -> skip
        with patch("nikita.conflicts.generator.random.random", return_value=0.99):
            result = generator._generate_with_temperature(
                triggers, context, conflict_details
            )

        assert result.generated is False
        assert "injection roll failed" in result.reason


class TestBreakupWithConflictDetails:
    """BreakupManager._check_temperature_threshold with various conflict_details.

    Requires store mock and feature flag mock.
    """

    def _make_store(self, consecutive_crises: int = 0) -> MagicMock:
        """Create a mock store (spec removed — ConflictStore deleted in Spec 057)."""
        store = MagicMock()
        store.count_consecutive_unresolved_crises.return_value = consecutive_crises
        store.get_active_conflict.return_value = None
        store.get_conflict_summary.return_value = MagicMock(
            total_conflicts=0, resolved_conflicts=0, current_conflict=None
        )
        return store

    def test_critical_zone_over_48h_triggers_breakup(self):
        """Temperature >90 in CRITICAL zone for >48h should trigger breakup."""
        manager = BreakupManager()

        conflict_details = {"temperature": 95.0, "zone": "critical"}
        last_conflict_at = datetime.now(UTC) - timedelta(hours=49)

        result = manager._check_temperature_threshold(
            user_id="user-1",
            relationship_score=30,
            conflict_details=conflict_details,
            last_conflict_at=last_conflict_at,
            consecutive_crises=0,
        )

        assert result is not None
        assert result.should_breakup is True
        assert result.risk_level == BreakupRisk.TRIGGERED

    def test_critical_zone_over_24h_warns(self):
        """CRITICAL zone for >24h but <48h or temp<=90 should warn."""
        manager = BreakupManager()

        conflict_details = {"temperature": 80.0, "zone": "critical"}
        last_conflict_at = datetime.now(UTC) - timedelta(hours=25)

        result = manager._check_temperature_threshold(
            user_id="user-1",
            relationship_score=30,
            conflict_details=conflict_details,
            last_conflict_at=last_conflict_at,
            consecutive_crises=0,
        )

        assert result is not None
        assert result.should_warn is True
        assert result.risk_level == BreakupRisk.CRITICAL
        assert result.should_breakup is False

    def test_critical_zone_under_24h_no_action(self):
        """CRITICAL zone for <24h should return None (no temperature-based action)."""
        manager = BreakupManager()

        conflict_details = {"temperature": 80.0, "zone": "critical"}
        last_conflict_at = datetime.now(UTC) - timedelta(hours=12)

        result = manager._check_temperature_threshold(
            user_id="user-1",
            relationship_score=30,
            conflict_details=conflict_details,
            last_conflict_at=last_conflict_at,
            consecutive_crises=0,
        )

        assert result is None

    def test_non_critical_zone_returns_none(self):
        """HOT zone (not CRITICAL) should return None."""
        manager = BreakupManager()

        conflict_details = {"temperature": 60.0, "zone": "hot"}
        last_conflict_at = datetime.now(UTC) - timedelta(hours=100)

        result = manager._check_temperature_threshold(
            user_id="user-1",
            relationship_score=30,
            conflict_details=conflict_details,
            last_conflict_at=last_conflict_at,
            consecutive_crises=0,
        )

        assert result is None

    def test_critical_zone_no_timestamp_returns_none(self):
        """CRITICAL zone but no last_conflict_at -> None (cannot check duration)."""
        manager = BreakupManager()

        conflict_details = {"temperature": 95.0, "zone": "critical"}

        result = manager._check_temperature_threshold(
            user_id="user-1",
            relationship_score=30,
            conflict_details=conflict_details,
            last_conflict_at=None,
            consecutive_crises=0,
        )

        assert result is None

    def test_exactly_90_temperature_no_breakup(self):
        """Temperature exactly 90.0 — threshold is >90, so no breakup."""
        manager = BreakupManager()

        conflict_details = {"temperature": 90.0, "zone": "critical"}
        last_conflict_at = datetime.now(UTC) - timedelta(hours=49)

        result = manager._check_temperature_threshold(
            user_id="user-1",
            relationship_score=30,
            conflict_details=conflict_details,
            last_conflict_at=last_conflict_at,
            consecutive_crises=0,
        )

        # temp is exactly 90.0, threshold is >90.0, so breakup NOT triggered
        # But >24h in CRITICAL, so warning should fire
        assert result is not None
        assert result.should_breakup is False
        assert result.should_warn is True

    def test_breakup_with_full_flag_integration(self):
        """Full check_threshold with temperature breakup (flag removed, always active)."""
        manager = BreakupManager()

        conflict_details = {"temperature": 95.0, "zone": "critical"}
        last_conflict_at = datetime.now(UTC) - timedelta(hours=50)

        result = manager.check_threshold(
            user_id="user-1",
            relationship_score=50,  # Above normal breakup threshold
            conflict_details=conflict_details,
            last_conflict_at=last_conflict_at,
        )

        assert result.should_breakup is True
        assert "Temperature" in result.reason

    def test_no_conflict_details_skips_temperature_check(self):
        """No conflict_details provided — temperature checks skipped, only score-based.

        Replaces test_flag_disabled_skips_temperature_check: flag removed,
        temperature path is now gated on conflict_details presence.
        """
        manager = BreakupManager()

        # No conflict_details → score-based only
        result = manager.check_threshold(
            user_id="user-1",
            relationship_score=50,  # Above normal breakup threshold
            conflict_details=None,
            last_conflict_at=None,
        )

        # Score is 50 (above threshold 10), so no breakup
        assert result.should_breakup is False
        assert result.risk_level == BreakupRisk.NONE

    def test_calm_zone_from_jsonb_pass_through(self):
        """CALM zone conflict_details passed to _check_temperature_threshold -> None."""
        manager = BreakupManager()

        conflict_details = {"temperature": 10.0, "zone": "calm"}
        last_conflict_at = datetime.now(UTC) - timedelta(hours=100)

        result = manager._check_temperature_threshold(
            user_id="user-1",
            relationship_score=50,
            conflict_details=conflict_details,
            last_conflict_at=last_conflict_at,
            consecutive_crises=0,
        )

        assert result is None
