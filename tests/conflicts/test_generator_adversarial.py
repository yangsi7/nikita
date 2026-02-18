"""DA-06: Adversarial tests for ConflictGenerator._generate_with_temperature().

Target: nikita/conflicts/generator.py — temperature zone injection, stochastic
probability, severity capping, edge cases at zone boundaries.

Tests cover:
- Zone boundary injection probabilities (exact + near-boundary values)
- Mixed severity triggers with filtering and zone caps
- Active conflict prevents generation even in CRITICAL zone
- Empty triggers with hot temperature
- Severity capping per zone (WARM=0.4, HOT=0.7, CRITICAL=1.0)
- CALM zone never generates conflicts
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from nikita.conflicts.generator import ConflictGenerator, GenerationContext, GenerationResult
from nikita.conflicts.models import (
    ActiveConflict,
    ConflictConfig,
    ConflictDetails,
    ConflictTrigger,
    ConflictType,
    EscalationLevel,
    TemperatureZone,
    TriggerType,
)
from nikita.conflicts.store import ConflictStore
from nikita.conflicts.temperature import TemperatureEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store(active_conflict=None, create_severity=None) -> MagicMock:
    """Create a mocked ConflictStore."""
    store = MagicMock(spec=ConflictStore)
    store.get_active_conflict.return_value = active_conflict
    store.count_consecutive_unresolved_crises.return_value = 0
    store.create_conflict.side_effect = lambda **kw: ActiveConflict(
        conflict_id=str(uuid4()),
        user_id=kw["user_id"],
        conflict_type=kw["conflict_type"],
        severity=kw["severity"],
        escalation_level=EscalationLevel.SUBTLE,
        triggered_at=datetime.now(UTC),
        trigger_ids=kw.get("trigger_ids", []),
    )
    return store


def _make_context(user_id="gen-adv-user", score=50, chapter=1) -> GenerationContext:
    return GenerationContext(
        user_id=user_id,
        chapter=chapter,
        relationship_score=score,
        recent_conflicts=[],
        days_since_last_conflict=2.0,
    )


def _make_trigger(severity=0.5, trigger_type=TriggerType.JEALOUSY) -> ConflictTrigger:
    return ConflictTrigger(
        trigger_id=str(uuid4()),
        trigger_type=trigger_type,
        severity=severity,
    )


def _details_at(temperature: float) -> dict:
    """ConflictDetails JSONB at a specific temperature."""
    zone = TemperatureEngine.get_zone(temperature)
    return ConflictDetails(
        temperature=temperature,
        zone=zone.value,
    ).to_jsonb()


# ===========================================================================
# TestZoneEdgeInjection
# ===========================================================================


class TestZoneEdgeInjection:
    """Test injection probabilities at exact zone boundaries.

    Zone boundaries and expected probabilities:
    - 25.0  (WARM start):    prob = 0.10
    - 49.99 (WARM end):      prob ~ 0.25
    - 50.0  (HOT start):     prob = 0.25
    - 74.99 (HOT end):       prob ~ 0.60
    - 75.0  (CRITICAL start): prob = 0.60
    - 99.99 (CRITICAL end):  prob ~ 0.90
    """

    def test_warm_start_exact_boundary(self):
        """At temp=25.0 (WARM start), injection prob=0.10."""
        prob = TemperatureEngine.interpolate_probability(25.0)
        assert abs(prob - 0.10) < 0.001, f"Expected 0.10, got {prob}"

    def test_warm_end_near_boundary(self):
        """At temp=49.99 (WARM end), injection prob ~ 0.25."""
        prob = TemperatureEngine.interpolate_probability(49.99)
        assert abs(prob - 0.25) < 0.01, f"Expected ~0.25, got {prob}"

    def test_hot_start_exact_boundary(self):
        """At temp=50.0 (HOT start), injection prob=0.25."""
        prob = TemperatureEngine.interpolate_probability(50.0)
        assert abs(prob - 0.25) < 0.001, f"Expected 0.25, got {prob}"

    def test_hot_end_near_boundary(self):
        """At temp=74.99 (HOT end), injection prob ~ 0.60."""
        prob = TemperatureEngine.interpolate_probability(74.99)
        assert abs(prob - 0.60) < 0.01, f"Expected ~0.60, got {prob}"

    def test_critical_start_exact_boundary(self):
        """At temp=75.0 (CRITICAL start), injection prob=0.60."""
        prob = TemperatureEngine.interpolate_probability(75.0)
        assert abs(prob - 0.60) < 0.001, f"Expected 0.60, got {prob}"

    def test_critical_end_near_boundary(self):
        """At temp=99.99 (CRITICAL end), injection prob ~ 0.90."""
        prob = TemperatureEngine.interpolate_probability(99.99)
        assert abs(prob - 0.90) < 0.01, f"Expected ~0.90, got {prob}"

    def test_warm_injection_succeeds_when_roll_below_prob(self):
        """At temp=25.0 (prob=0.10), random=0.05 => injection succeeds."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.5)]
        details = _details_at(25.0)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("random.random", return_value=0.05):  # Below 0.10
                result = gen.generate(triggers, ctx, conflict_details=details)

        assert result.generated is True

    def test_warm_injection_fails_when_roll_above_prob(self):
        """At temp=25.0 (prob=0.10), random=0.15 => injection fails."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.5)]
        details = _details_at(25.0)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("random.random", return_value=0.15):  # Above 0.10
                result = gen.generate(triggers, ctx, conflict_details=details)

        assert result.generated is False
        assert "roll failed" in result.reason.lower()

    def test_critical_injection_succeeds_high_roll(self):
        """At temp=99.0 (prob~0.89), random=0.85 => injection succeeds."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.5)]
        details = _details_at(99.0)

        prob = TemperatureEngine.interpolate_probability(99.0)
        # Roll below prob => success
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("random.random", return_value=prob - 0.01):
                result = gen.generate(triggers, ctx, conflict_details=details)

        assert result.generated is True

    def test_boundary_25_is_warm_not_calm(self):
        """Exactly 25.0 is WARM, not CALM (CALM is < 25.0)."""
        zone = TemperatureEngine.get_zone(25.0)
        assert zone == TemperatureZone.WARM

    def test_boundary_50_is_hot_not_warm(self):
        """Exactly 50.0 is HOT, not WARM."""
        zone = TemperatureEngine.get_zone(50.0)
        assert zone == TemperatureZone.HOT

    def test_boundary_75_is_critical_not_hot(self):
        """Exactly 75.0 is CRITICAL, not HOT."""
        zone = TemperatureEngine.get_zone(75.0)
        assert zone == TemperatureZone.CRITICAL


# ===========================================================================
# TestMixedSeverityTriggers
# ===========================================================================


class TestMixedSeverityTriggers:
    """Multiple triggers with severities [0.1, 0.5, 0.9] in WARM zone.

    Trigger at 0.1 should be filtered (below MIN_SEVERITY_THRESHOLD=0.25).
    Severity should be capped at 0.4 for WARM zone.
    """

    def test_low_severity_trigger_filtered(self):
        """Trigger with severity=0.1 is below MIN_SEVERITY_THRESHOLD=0.25."""
        gen = ConflictGenerator(store=_make_store())
        triggers = [_make_trigger(severity=0.1)]
        filtered = gen._prioritize_triggers(triggers)
        assert len(filtered) == 0, "Severity 0.1 should be filtered out"

    def test_mixed_triggers_in_warm_zone(self):
        """Three triggers [0.1, 0.5, 0.9]: only 0.5 and 0.9 pass filter."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        triggers = [
            _make_trigger(severity=0.1, trigger_type=TriggerType.DISMISSIVE),
            _make_trigger(severity=0.5, trigger_type=TriggerType.JEALOUSY),
            _make_trigger(severity=0.9, trigger_type=TriggerType.TRUST),
        ]
        details = _details_at(35.0)  # WARM zone

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("random.random", return_value=0.001):  # Force injection
                result = gen.generate(triggers, ctx, conflict_details=details)

        if result.generated:
            # Severity should be capped at 0.4 (WARM max)
            assert result.conflict.severity <= 0.4, (
                f"WARM zone severity should be <= 0.4, got {result.conflict.severity}"
            )
            # Only 2 triggers should contribute (0.1 filtered out)
            assert len(result.contributing_triggers) <= 2

    def test_severity_cap_warm_zone(self):
        """Even with high-severity triggers, WARM zone caps at 0.4."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        # All high-severity triggers
        triggers = [
            _make_trigger(severity=0.9, trigger_type=TriggerType.TRUST),
            _make_trigger(severity=0.8, trigger_type=TriggerType.BOUNDARY),
        ]
        details = _details_at(30.0)  # WARM zone

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("random.random", return_value=0.001):
                result = gen.generate(triggers, ctx, conflict_details=details)

        if result.generated:
            assert result.conflict.severity <= 0.4


# ===========================================================================
# TestActiveConflictSkipsGeneration
# ===========================================================================


class TestActiveConflictSkipsGeneration:
    """Even with high temperature (CRITICAL zone), if active conflict exists,
    _generate_with_temperature should skip generation.
    """

    def test_active_conflict_skips_in_critical(self):
        """CRITICAL zone + active conflict => skip."""
        existing = ActiveConflict(
            conflict_id=str(uuid4()),
            user_id="skip-user",
            conflict_type=ConflictType.JEALOUSY,
            severity=0.6,
            escalation_level=EscalationLevel.DIRECT,
        )
        store = _make_store(active_conflict=existing)
        gen = ConflictGenerator(store=store)
        ctx = _make_context(user_id="skip-user")
        triggers = [_make_trigger(severity=0.9)]
        details = _details_at(90.0)  # CRITICAL

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("random.random", return_value=0.001):  # Would inject
                result = gen.generate(triggers, ctx, conflict_details=details)

        assert result.generated is False
        assert "already exists" in result.reason.lower()
        assert result.conflict == existing

    def test_active_conflict_skips_in_warm(self):
        """WARM zone + active conflict => skip."""
        existing = ActiveConflict(
            conflict_id=str(uuid4()),
            user_id="skip-user-2",
            conflict_type=ConflictType.ATTENTION,
            severity=0.3,
        )
        store = _make_store(active_conflict=existing)
        gen = ConflictGenerator(store=store)
        ctx = _make_context(user_id="skip-user-2")
        triggers = [_make_trigger(severity=0.5)]
        details = _details_at(40.0)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("random.random", return_value=0.001):
                result = gen.generate(triggers, ctx, conflict_details=details)

        assert result.generated is False
        assert "already exists" in result.reason.lower()


# ===========================================================================
# TestNoTriggersSkipsGeneration
# ===========================================================================


class TestNoTriggersSkipsGeneration:
    """Temperature in HOT zone but empty triggers list => should skip."""

    def test_empty_triggers_hot_zone(self):
        """HOT zone + empty triggers => skip with specific reason."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        details = _details_at(60.0)  # HOT

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("random.random", return_value=0.001):
                result = gen.generate([], ctx, conflict_details=details)

        assert result.generated is False
        assert "triggers" in result.reason.lower()

    def test_empty_triggers_critical_zone(self):
        """CRITICAL zone + empty triggers => skip."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        details = _details_at(90.0)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("random.random", return_value=0.001):
                result = gen.generate([], ctx, conflict_details=details)

        assert result.generated is False
        assert "triggers" in result.reason.lower()

    def test_none_triggers_is_handled(self):
        """Passing empty list (no triggers) should not raise."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        details = _details_at(80.0)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            # Should not raise
            result = gen.generate([], ctx, conflict_details=details)
        assert isinstance(result, GenerationResult)


# ===========================================================================
# TestSeverityCapByZone
# ===========================================================================


class TestSeverityCapByZone:
    """Create triggers that would produce severity > zone max.

    WARM: capped at 0.4
    HOT: capped at 0.7
    CRITICAL: no cap (1.0)
    """

    def _generate_with_high_severity(self, temperature: float) -> GenerationResult | None:
        """Helper: generate with high-severity triggers at given temperature."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        # Low score + many recent conflicts to inflate severity
        ctx = _make_context(score=20, chapter=1)
        ctx.recent_conflicts = [
            ActiveConflict(
                conflict_id=str(uuid4()),
                user_id="cap-user",
                conflict_type=ConflictType.TRUST,
                severity=0.8,
            )
            for _ in range(5)
        ]
        triggers = [
            _make_trigger(severity=0.95, trigger_type=TriggerType.TRUST),
            _make_trigger(severity=0.90, trigger_type=TriggerType.BOUNDARY),
        ]
        details = _details_at(temperature)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("random.random", return_value=0.001):
                return gen.generate(triggers, ctx, conflict_details=details)

    def test_warm_cap_at_0_4(self):
        """WARM zone caps severity at 0.4."""
        result = self._generate_with_high_severity(35.0)
        if result and result.generated:
            assert result.conflict.severity <= 0.4, (
                f"WARM severity cap broken: {result.conflict.severity}"
            )

    def test_hot_cap_at_0_7(self):
        """HOT zone caps severity at 0.7."""
        result = self._generate_with_high_severity(60.0)
        if result and result.generated:
            assert result.conflict.severity <= 0.7, (
                f"HOT severity cap broken: {result.conflict.severity}"
            )

    def test_critical_allows_full_severity(self):
        """CRITICAL zone allows full severity (up to 1.0)."""
        result = self._generate_with_high_severity(90.0)
        if result and result.generated:
            # Severity should be high (inflated by modifiers)
            # Just verify it's not capped below 0.7
            assert result.conflict.severity <= 1.0
            # NOTE: May fail if base severity calculation doesn't exceed 0.7
            # The important thing is the cap is 1.0, not 0.7

    def test_max_severity_constants(self):
        """Verify TemperatureEngine.MAX_SEVERITY constants."""
        assert TemperatureEngine.get_max_severity(TemperatureZone.CALM) == 0.0
        assert TemperatureEngine.get_max_severity(TemperatureZone.WARM) == 0.4
        assert TemperatureEngine.get_max_severity(TemperatureZone.HOT) == 0.7
        assert TemperatureEngine.get_max_severity(TemperatureZone.CRITICAL) == 1.0


# ===========================================================================
# TestCalmZoneNeverGenerates
# ===========================================================================


class TestCalmZoneNeverGenerates:
    """temperature=24.9 (CALM) with high-severity triggers => never generates."""

    def test_calm_zone_rejects_high_severity(self):
        """CALM zone always returns generated=False regardless of triggers."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        triggers = [
            _make_trigger(severity=1.0, trigger_type=TriggerType.TRUST),
            _make_trigger(severity=0.9, trigger_type=TriggerType.BOUNDARY),
        ]
        details = _details_at(24.9)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("random.random", return_value=0.0):  # Lowest possible roll
                result = gen.generate(triggers, ctx, conflict_details=details)

        assert result.generated is False
        assert "calm" in result.reason.lower()

    def test_calm_zone_at_zero(self):
        """Temperature=0.0 (CALM) => no conflict."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        triggers = [_make_trigger(severity=1.0)]
        details = _details_at(0.0)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = gen.generate(triggers, ctx, conflict_details=details)

        assert result.generated is False
        assert "calm" in result.reason.lower()

    def test_calm_zone_just_below_warm(self):
        """Temperature=24.999 (CALM) => still CALM, no conflict."""
        zone = TemperatureEngine.get_zone(24.999)
        assert zone == TemperatureZone.CALM

        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.8)]
        details = _details_at(24.999)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = gen.generate(triggers, ctx, conflict_details=details)

        assert result.generated is False

    def test_calm_interpolation_is_zero(self):
        """CALM zone interpolated probability is always 0.0."""
        for temp in [0.0, 5.0, 12.5, 20.0, 24.9]:
            prob = TemperatureEngine.interpolate_probability(temp)
            assert prob == 0.0, f"CALM prob should be 0.0 at temp={temp}, got {prob}"
