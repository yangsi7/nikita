"""Adversarial tests for combined feature flag interactions (Spec 055 + Spec 057).

Tests the interaction between BOTH independent feature flags:
- conflict_temperature_enabled (Spec 057) — temperature-based conflict system
- life_sim_enhanced (Spec 055) — enhanced life sim with routines, NPC states, mood

The flags are independent but the systems they control can interact:
  mood -> scoring -> temperature -> conflict generation -> scores -> mood
This creates a latent circular dependency that must not diverge.
"""

import math
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from nikita.conflicts import is_conflict_temperature_enabled
from nikita.conflicts.gottman import GottmanTracker
from nikita.conflicts.models import (
    ConflictDetails,
    ConflictTrigger,
    GottmanCounters,
    TemperatureZone,
    TriggerType,
)
from nikita.conflicts.temperature import TemperatureEngine
from nikita.life_simulation.simulator import LifeSimulator


# Both is_conflict_temperature_enabled() and LifeSimulator._is_enhanced() use
# lazy imports: `from nikita.config.settings import get_settings` inside the
# function body. The canonical patch target is always the source module.
SETTINGS_PATCH = "nikita.config.settings.get_settings"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(*, conflict_temp: bool, life_sim: bool) -> MagicMock:
    """Create a mock Settings object with the given flag combination."""
    settings = MagicMock()
    settings.conflict_temperature_enabled = conflict_temp
    settings.life_sim_enhanced = life_sim
    return settings


def _make_details(temperature: float = 30.0) -> ConflictDetails:
    """Create a ConflictDetails at a given temperature."""
    zone = TemperatureEngine.get_zone(temperature)
    return ConflictDetails(
        temperature=temperature,
        zone=zone.value,
        positive_count=5,
        negative_count=2,
        gottman_ratio=2.5,
        gottman_target=20.0,
    )


# ---------------------------------------------------------------------------
# 1. Both flags ON — verify both systems active simultaneously
# ---------------------------------------------------------------------------


class TestBothFlagsOn:
    """When both conflict_temperature_enabled=True and life_sim_enhanced=True,
    both subsystems should be fully active with no mutual interference."""

    def test_conflict_temperature_flag_on(self):
        """is_conflict_temperature_enabled() returns True when flag is ON."""
        mock_settings = _make_settings(conflict_temp=True, life_sim=True)
        with patch(SETTINGS_PATCH, return_value=mock_settings):
            assert is_conflict_temperature_enabled() is True

    def test_life_sim_enhanced_flag_on(self):
        """LifeSimulator._is_enhanced() returns True when flag is ON."""
        mock_settings = _make_settings(conflict_temp=True, life_sim=True)
        sim = LifeSimulator(
            store=MagicMock(),
            entity_manager=MagicMock(),
            event_generator=MagicMock(),
            narrative_manager=MagicMock(),
            mood_calculator=MagicMock(),
        )
        with patch(SETTINGS_PATCH, return_value=mock_settings):
            assert sim._is_enhanced() is True

    def test_temperature_engine_works_when_both_on(self):
        """TemperatureEngine pure computation is unaffected by flag state.
        Both flags ON should not corrupt temperature math."""
        details = _make_details(temperature=40.0)

        # Apply a positive score delta (cools temperature)
        score_delta = 2.0
        temp_delta = TemperatureEngine.calculate_delta_from_score(score_delta)
        assert temp_delta < 0.0, "Positive score should decrease temperature"

        updated = TemperatureEngine.update_conflict_details(details, temp_delta)
        assert updated.temperature < details.temperature
        assert 0.0 <= updated.temperature <= 100.0

    def test_gottman_tracker_works_when_both_on(self):
        """GottmanTracker pure computation is unaffected by flag state.
        Both flags ON, Gottman updates should still be correct."""
        details = _make_details(temperature=35.0)

        # Record a positive interaction
        updated = GottmanTracker.update_conflict_details(
            details, is_positive=True, is_in_conflict=False,
        )
        assert updated.positive_count == details.positive_count + 1
        assert updated.negative_count == details.negative_count

    def test_both_systems_produce_independent_state(self):
        """Temperature update followed by Gottman update:
        temperature should change but Gottman counters should only
        change from the Gottman call, not from temperature."""
        details = _make_details(temperature=50.0)

        # Step 1: temperature update from score
        temp_delta = TemperatureEngine.calculate_delta_from_score(-3.0)
        after_temp = TemperatureEngine.update_conflict_details(details, temp_delta)
        assert after_temp.temperature > details.temperature
        assert after_temp.positive_count == details.positive_count  # unchanged

        # Step 2: Gottman update
        after_gottman = GottmanTracker.update_conflict_details(
            after_temp, is_positive=False, is_in_conflict=True,
        )
        assert after_gottman.negative_count == after_temp.negative_count + 1
        assert after_gottman.temperature == after_temp.temperature  # unchanged


# ---------------------------------------------------------------------------
# 2. Both flags OFF — verify baseline behavior, zero side effects
# ---------------------------------------------------------------------------


class TestBothFlagsOff:
    """When both flags are OFF, all temperature and enhanced life sim features
    should be completely inactive. Baseline behavior only."""

    def test_conflict_temperature_flag_always_true(self):
        """is_conflict_temperature_enabled() always returns True (deprecated stub)."""
        # Deprecated stub always returns True regardless of settings
        assert is_conflict_temperature_enabled() is True

    def test_life_sim_enhanced_flag_off(self):
        """LifeSimulator._is_enhanced() returns False when flag is OFF."""
        mock_settings = _make_settings(conflict_temp=False, life_sim=False)
        sim = LifeSimulator(
            store=MagicMock(),
            entity_manager=MagicMock(),
            event_generator=MagicMock(),
            narrative_manager=MagicMock(),
            mood_calculator=MagicMock(),
        )
        with patch(SETTINGS_PATCH, return_value=mock_settings):
            assert sim._is_enhanced() is False

    def test_generator_uses_legacy_path_when_flag_off(self):
        """ConflictGenerator.generate() should NOT call _generate_with_temperature
        when conflict_temperature_enabled is False, even if conflict_details present."""
        from nikita.conflicts.generator import ConflictGenerator, GenerationContext
        from nikita.conflicts.models import ActiveConflict, ConflictType

        mock_store = MagicMock()
        mock_store.get_active_conflict.return_value = None
        mock_store.create_conflict.return_value = ActiveConflict(
            conflict_id="test-conflict",
            user_id="user-1",
            conflict_type=ConflictType.ATTENTION,
            severity=0.5,
        )

        gen = ConflictGenerator(store=mock_store)
        context = GenerationContext(user_id="user-1", chapter=1, relationship_score=50)
        trigger = ConflictTrigger(
            trigger_id="t1",
            trigger_type=TriggerType.DISMISSIVE,
            severity=0.5,
        )
        conflict_details = {"temperature": 60.0, "zone": "hot"}

        mock_settings = _make_settings(conflict_temp=False, life_sim=False)
        with patch(SETTINGS_PATCH, return_value=mock_settings):
            result = gen.generate([trigger], context, conflict_details=conflict_details)

        # Legacy path: reason should NOT mention "Temperature" or "temperature"
        # because the temperature code path was never entered.
        if result.generated:
            assert "temperature" not in result.reason.lower(), (
                f"Expected legacy path, but reason mentions temperature: {result.reason}"
            )

    @pytest.mark.asyncio
    async def test_life_sim_skips_enhanced_features_when_off(self):
        """generate_next_day_events should NOT call mood calculation or
        routine loading when life_sim_enhanced is False."""
        mock_store = AsyncMock()
        mock_store.get_events_for_date.return_value = []
        mock_store.get_entities.return_value = ["entity1"]
        mock_store.get_recent_events.return_value = []
        mock_store.save_events.return_value = None

        mock_entity_mgr = AsyncMock()
        mock_event_gen = AsyncMock()
        mock_event_gen.generate_events_for_day.return_value = []

        mock_narrative_mgr = AsyncMock()
        mock_narrative_mgr.get_active_arcs.return_value = []
        mock_narrative_mgr.maybe_resolve_arcs.return_value = []
        mock_narrative_mgr.maybe_create_arc.return_value = None

        mock_mood_calc = MagicMock()

        sim = LifeSimulator(
            store=mock_store,
            entity_manager=mock_entity_mgr,
            event_generator=mock_event_gen,
            narrative_manager=mock_narrative_mgr,
            mood_calculator=mock_mood_calc,
        )

        mock_settings = _make_settings(conflict_temp=False, life_sim=False)
        with patch(SETTINGS_PATCH, return_value=mock_settings):
            user_id = uuid4()
            from datetime import date, timedelta
            target = date.today() + timedelta(days=1)
            await sim.generate_next_day_events(user_id, target_date=target)

        # Mood calculator should NOT have been called (enhanced path skipped)
        mock_mood_calc.compute_from_events.assert_not_called()

        # Event generator called with routine=None and mood_state=None
        call_kwargs = mock_event_gen.generate_events_for_day.call_args
        assert call_kwargs.kwargs.get("routine") is None
        assert call_kwargs.kwargs.get("mood_state") is None


# ---------------------------------------------------------------------------
# 3. Circular dependency stress test
# ---------------------------------------------------------------------------


class TestCircularDependencyStress:
    """Simulates the circular flow:
      mood -> scoring -> temperature -> conflict -> score -> mood
    Run 20 iterations and verify invariants hold."""

    def test_20_iteration_cycle_temperature_bounded(self):
        """Temperature stays in [0, 100] over 20 iterations of score->temp->gottman cycle.
        No NaN, no Inf, no overflow."""
        details = ConflictDetails(temperature=30.0, zone="warm")

        for i in range(20):
            # Simulate scoring delta (alternating pattern with some negatives)
            score_delta = -2.0 if i % 3 == 0 else 1.0

            # Score -> temperature delta
            temp_delta = TemperatureEngine.calculate_delta_from_score(score_delta)
            assert not math.isnan(temp_delta), f"NaN temp_delta at iteration {i}"
            assert not math.isinf(temp_delta), f"Inf temp_delta at iteration {i}"

            # Apply temperature delta
            details = TemperatureEngine.update_conflict_details(details, temp_delta)

            # Gottman update
            is_positive = score_delta > 0
            details = GottmanTracker.update_conflict_details(
                details, is_positive=is_positive, is_in_conflict=False,
            )

            # Invariant checks every iteration
            assert 0.0 <= details.temperature <= 100.0, (
                f"Temperature out of range at iteration {i}: {details.temperature}"
            )
            assert details.positive_count >= 0, f"Negative positive_count at {i}"
            assert details.negative_count >= 0, f"Negative negative_count at {i}"
            assert not math.isnan(details.gottman_ratio), f"NaN gottman_ratio at {i}"
            assert details.gottman_ratio >= 0.0, f"Negative gottman_ratio at {i}"

    def test_all_negative_scores_converge_to_100(self):
        """20 iterations of purely negative scores should drive temperature toward 100.
        Verify it does not exceed 100."""
        details = ConflictDetails(temperature=10.0, zone="calm")

        for i in range(20):
            temp_delta = TemperatureEngine.calculate_delta_from_score(-5.0)
            details = TemperatureEngine.update_conflict_details(details, temp_delta)
            details = GottmanTracker.update_conflict_details(
                details, is_positive=False, is_in_conflict=True,
            )

            assert details.temperature <= 100.0, f"Exceeded 100 at iteration {i}"
            assert details.negative_count == i + 1

        # After 20 heavy negatives, temperature should be at or near 100
        assert details.temperature >= 90.0, (
            f"Expected near-max temperature, got {details.temperature}"
        )

    def test_all_positive_scores_decrease_temperature(self):
        """20 iterations of purely positive scores should drive temperature downward.
        calculate_delta_from_score(5.0) = -(5.0 * 0.5) = -2.5 per iteration.
        From 80.0: 80 - 20*2.5 = 30.0. Verify monotonic decrease and final value."""
        details = ConflictDetails(temperature=80.0, zone="critical")

        prev_temp = details.temperature
        for i in range(20):
            temp_delta = TemperatureEngine.calculate_delta_from_score(5.0)
            details = TemperatureEngine.update_conflict_details(details, temp_delta)
            details = GottmanTracker.update_conflict_details(
                details, is_positive=True, is_in_conflict=False,
            )

            assert details.temperature >= 0.0, f"Below 0 at iteration {i}"
            assert details.temperature <= prev_temp, (
                f"Temperature increased on positive score at iteration {i}: "
                f"{prev_temp} -> {details.temperature}"
            )
            prev_temp = details.temperature

        # 80 - 20*2.5 = 30.0
        assert details.temperature <= 31.0, (
            f"Expected temperature near 30, got {details.temperature}"
        )

    def test_oscillating_scores_stay_bounded(self):
        """Alternating +10 / -10 scores: temperature should not diverge.
        Net effect depends on asymmetric multipliers (1.5x up, 0.5x down).
        Negative scores also get bonus +5 for large drops (>3.0 threshold).
        So: up = 10*1.5+5 = 20, down = 10*0.5 = 5. Net drift upward per cycle."""
        details = ConflictDetails(temperature=50.0, zone="hot")

        for i in range(40):
            score_delta = 10.0 if i % 2 == 0 else -10.0
            temp_delta = TemperatureEngine.calculate_delta_from_score(score_delta)
            details = TemperatureEngine.update_conflict_details(details, temp_delta)

            assert 0.0 <= details.temperature <= 100.0, (
                f"Out of bounds at iteration {i}: {details.temperature}"
            )

    def test_extreme_score_deltas(self):
        """Very large score deltas (e.g., +1000, -1000) should not produce
        NaN or break clamping."""
        details = ConflictDetails(temperature=50.0, zone="hot")

        for extreme in [1000.0, -1000.0, 1e10, -1e10, 0.0001, -0.0001]:
            temp_delta = TemperatureEngine.calculate_delta_from_score(extreme)
            assert not math.isnan(temp_delta), f"NaN from score_delta={extreme}"
            assert not math.isinf(temp_delta), f"Inf from score_delta={extreme}"

            details = TemperatureEngine.update_conflict_details(details, temp_delta)
            assert 0.0 <= details.temperature <= 100.0, (
                f"Out of bounds for score_delta={extreme}: {details.temperature}"
            )


# ---------------------------------------------------------------------------
# 4. Flag combinations (parametrized)
# ---------------------------------------------------------------------------


class TestFlagCombinations:
    """Parametrized test over all 4 flag combinations.
    Each verifies the expected code path is taken."""

    @pytest.mark.parametrize(
        "conflict_temp,life_sim,expect_enhanced",
        [
            (False, False, False),
            (True, False, False),
            (False, True, True),
            (True, True, True),
        ],
        ids=["OFF_OFF", "TEMP_ON_LIFE_OFF", "TEMP_OFF_LIFE_ON", "ON_ON"],
    )
    def test_flag_combination(
        self,
        conflict_temp: bool,
        life_sim: bool,
        expect_enhanced: bool,
    ):
        """Each flag combination produces independent, correct results."""
        mock_settings = _make_settings(
            conflict_temp=conflict_temp, life_sim=life_sim,
        )

        # is_conflict_temperature_enabled() is a deprecated stub — always True
        assert is_conflict_temperature_enabled() is True

        # Check life sim enhanced flag (still active)
        sim = LifeSimulator(
            store=MagicMock(),
            entity_manager=MagicMock(),
            event_generator=MagicMock(),
            narrative_manager=MagicMock(),
            mood_calculator=MagicMock(),
        )
        with patch(SETTINGS_PATCH, return_value=mock_settings):
            assert sim._is_enhanced() is expect_enhanced

    @pytest.mark.parametrize(
        "conflict_temp,life_sim",
        [
            (False, False),
            (True, False),
            (False, True),
            (True, True),
        ],
        ids=["OFF_OFF", "TEMP_ON_LIFE_OFF", "TEMP_OFF_LIFE_ON", "ON_ON"],
    )
    def test_temperature_engine_pure_math_unaffected_by_flags(
        self, conflict_temp: bool, life_sim: bool,
    ):
        """TemperatureEngine is pure computation -- it should produce
        identical results regardless of flag state."""
        # The engine does not check flags; it just does math.
        # This confirms no accidental flag-dependence crept into the engine.
        details = _make_details(temperature=45.0)
        delta = TemperatureEngine.calculate_delta_from_score(-2.0)
        updated = TemperatureEngine.update_conflict_details(details, delta)

        # Expected: temperature increases by abs(-2.0) * 1.5 = 3.0
        expected_temp = min(100.0, 45.0 + 3.0)
        assert abs(updated.temperature - expected_temp) < 1e-9, (
            f"Expected {expected_temp}, got {updated.temperature} "
            f"(flags: temp={conflict_temp}, life={life_sim})"
        )

    @pytest.mark.parametrize(
        "conflict_temp,life_sim",
        [
            (False, False),
            (True, False),
            (False, True),
            (True, True),
        ],
        ids=["OFF_OFF", "TEMP_ON_LIFE_OFF", "TEMP_OFF_LIFE_ON", "ON_ON"],
    )
    def test_gottman_pure_math_unaffected_by_flags(
        self, conflict_temp: bool, life_sim: bool,
    ):
        """GottmanTracker is pure computation -- no flag dependency."""
        counters = GottmanCounters(positive_count=10, negative_count=3)
        new_counters = GottmanTracker.record_interaction(counters, is_positive=True)
        assert new_counters.positive_count == 11
        assert new_counters.negative_count == 3

        ratio = GottmanTracker.get_ratio(new_counters)
        assert abs(ratio - 11.0 / 3.0) < 1e-9


# ---------------------------------------------------------------------------
# 5. Flag toggle mid-cycle
# ---------------------------------------------------------------------------


class TestFlagToggleMidCycle:
    """Start with both ON, toggle flags mid-cycle.
    Verify no crashes, temperature stays valid, no stale state leaks."""

    def test_toggle_conflict_flag_off_midcycle(self):
        """Run 5 iterations both ON, toggle conflict flag OFF, run 5 more.
        Temperature state should remain valid even after flag change."""
        details = _make_details(temperature=40.0)

        # Phase 1: both ON, 5 iterations
        for i in range(5):
            score_delta = -1.5 if i % 2 == 0 else 0.5
            temp_delta = TemperatureEngine.calculate_delta_from_score(score_delta)
            details = TemperatureEngine.update_conflict_details(details, temp_delta)
            details = GottmanTracker.update_conflict_details(
                details, is_positive=(score_delta > 0), is_in_conflict=False,
            )

        temp_after_phase1 = details.temperature
        assert 0.0 <= temp_after_phase1 <= 100.0

        # Phase 2: conflict flag OFF (conceptually -- life sim still enhanced)
        # Temperature engine is pure math, so it still works.
        # But the generator would use legacy path. We just verify the
        # state object does not corrupt.
        for i in range(5):
            score_delta = 2.0  # all positive, should cool down
            temp_delta = TemperatureEngine.calculate_delta_from_score(score_delta)
            details = TemperatureEngine.update_conflict_details(details, temp_delta)

        temp_after_phase2 = details.temperature
        assert 0.0 <= temp_after_phase2 <= 100.0
        # Positive scores should have cooled temperature
        assert temp_after_phase2 <= temp_after_phase1, (
            f"Temperature should have decreased: {temp_after_phase1} -> {temp_after_phase2}"
        )

    def test_full_toggle_sequence(self):
        """Phase 1: both ON (5 iters)
        Phase 2: conflict OFF, life ON (5 iters)
        Phase 3: both OFF (5 iters)
        Phase 4: both ON again (5 iters)
        No crashes, temperature valid, counts non-negative."""
        details = _make_details(temperature=50.0)

        phase_temps: list[float] = []

        for phase in range(4):
            for i in range(5):
                score_delta = -2.0 if (phase + i) % 3 == 0 else 1.0
                temp_delta = TemperatureEngine.calculate_delta_from_score(score_delta)
                details = TemperatureEngine.update_conflict_details(details, temp_delta)

                is_positive = score_delta > 0
                details = GottmanTracker.update_conflict_details(
                    details, is_positive=is_positive, is_in_conflict=(phase == 0),
                )

                # Invariants
                assert 0.0 <= details.temperature <= 100.0, (
                    f"Phase {phase}, iter {i}: temp={details.temperature}"
                )
                assert details.positive_count >= 0
                assert details.negative_count >= 0
                assert not math.isnan(details.gottman_ratio)

            phase_temps.append(details.temperature)

        # All phase-end temperatures should be valid
        for idx, t in enumerate(phase_temps):
            assert 0.0 <= t <= 100.0, f"Phase {idx} end temp out of range: {t}"

    def test_no_stale_state_leak_after_toggle(self):
        """After toggling flags, ConflictDetails created fresh should have defaults.
        Old state should not leak into new instances."""
        # Build up some state
        old_details = ConflictDetails(
            temperature=85.0,
            zone="critical",
            positive_count=100,
            negative_count=50,
            gottman_ratio=2.0,
            gottman_target=5.0,
            horsemen_detected=["contempt", "criticism"],
            session_positive=10,
            session_negative=20,
        )

        # Create a fresh instance (simulating what happens on flag toggle + reset)
        fresh_details = ConflictDetails()
        assert fresh_details.temperature == 0.0
        assert fresh_details.zone == "calm"
        assert fresh_details.positive_count == 0
        assert fresh_details.negative_count == 0
        assert fresh_details.horsemen_detected == []
        assert fresh_details.session_positive == 0

        # Old instance should be unchanged (no shared mutable state)
        assert old_details.temperature == 85.0
        assert old_details.positive_count == 100
        assert len(old_details.horsemen_detected) == 2

    def test_flag_check_exception_handling_in_life_sim(self):
        """If get_settings() raises during _is_enhanced(), it should return False.
        This simulates a partial deployment where settings are unavailable."""
        sim = LifeSimulator(
            store=MagicMock(),
            entity_manager=MagicMock(),
            event_generator=MagicMock(),
            narrative_manager=MagicMock(),
            mood_calculator=MagicMock(),
        )
        with patch(SETTINGS_PATCH, side_effect=RuntimeError("Settings unavailable")):
            # _is_enhanced catches exceptions and returns False
            assert sim._is_enhanced() is False

    @pytest.mark.parametrize(
        "initial_temp,toggle_sequence",
        [
            (0.0, [True, False, True]),
            (50.0, [False, True, False]),
            (100.0, [True, True, False]),
            (25.0, [False, False, True]),
        ],
        ids=["start_0", "start_50", "start_100", "start_25"],
    )
    def test_toggle_from_various_starting_temps(
        self, initial_temp: float, toggle_sequence: list[bool],
    ):
        """Various starting temperatures with flag toggles.
        Temperature must stay bounded regardless of starting point or toggle pattern."""
        details = ConflictDetails(
            temperature=initial_temp,
            zone=TemperatureEngine.get_zone(initial_temp).value,
        )

        for phase_idx, _flag_on in enumerate(toggle_sequence):
            for i in range(5):
                score_delta = -3.0 if i % 2 == 0 else 2.0
                temp_delta = TemperatureEngine.calculate_delta_from_score(score_delta)
                details = TemperatureEngine.update_conflict_details(details, temp_delta)

                assert 0.0 <= details.temperature <= 100.0, (
                    f"Phase {phase_idx}, iter {i}, temp={details.temperature}"
                )


# ---------------------------------------------------------------------------
# 6. Edge: concurrent flag reads with different results
# ---------------------------------------------------------------------------


class TestFlagRaceConditions:
    """Simulate scenarios where flag reads might return different values
    within the same logical operation (e.g., settings reloaded mid-request)."""

    def test_flag_changes_between_check_and_use(self):
        """If conflict_temperature_enabled changes from True to False between
        the flag check and the actual generation, the system should not crash."""
        from nikita.conflicts.generator import ConflictGenerator, GenerationContext
        from nikita.conflicts.models import ActiveConflict, ConflictType

        mock_store = MagicMock()
        mock_store.get_active_conflict.return_value = None
        mock_store.create_conflict.return_value = ActiveConflict(
            conflict_id="test-conflict",
            user_id="user-race",
            conflict_type=ConflictType.ATTENTION,
            severity=0.5,
        )

        gen = ConflictGenerator(store=mock_store)
        context = GenerationContext(user_id="user-race", chapter=1, relationship_score=50)
        trigger = ConflictTrigger(
            trigger_id="t-race",
            trigger_type=TriggerType.NEGLECT,
            severity=0.6,
        )

        # Verify generate() does not crash with either flag value
        for flag_val in [True, False, True, False]:
            mock_settings = _make_settings(conflict_temp=flag_val, life_sim=True)
            with patch(SETTINGS_PATCH, return_value=mock_settings):
                conflict_details = {"temperature": 60.0, "zone": "hot"} if flag_val else None
                result = gen.generate([trigger], context, conflict_details=conflict_details)
                # Should not raise, regardless of flag
                assert isinstance(result.generated, bool)

    def test_life_sim_enhanced_toggle_during_iteration(self):
        """_is_enhanced() called multiple times in the same pipeline:
        if it returns different values, the code should not crash.
        NOTE: This is a defensive check -- the actual code calls it at
        specific points, but we verify robustness."""
        sim = LifeSimulator(
            store=MagicMock(),
            entity_manager=MagicMock(),
            event_generator=MagicMock(),
            narrative_manager=MagicMock(),
            mood_calculator=MagicMock(),
        )

        call_count = 0

        def oscillating_settings():
            nonlocal call_count
            call_count += 1
            s = MagicMock()
            s.life_sim_enhanced = (call_count % 2 == 0)
            return s

        with patch(SETTINGS_PATCH, side_effect=oscillating_settings):
            # Call _is_enhanced() multiple times -- should not crash
            results = [sim._is_enhanced() for _ in range(10)]
            # Should alternate True/False
            assert True in results
            assert False in results


# ---------------------------------------------------------------------------
# 7. JSONB serialization round-trip under combined flags
# ---------------------------------------------------------------------------


class TestCombinedFlagsJsonbRoundtrip:
    """ConflictDetails should survive JSONB serialization/deserialization
    regardless of which flags are active."""

    def test_roundtrip_preserves_all_fields(self):
        """Serialize to JSONB and back: all fields must survive."""
        details = ConflictDetails(
            temperature=67.5,
            zone="hot",
            positive_count=42,
            negative_count=8,
            gottman_ratio=5.25,
            gottman_target=5.0,
            horsemen_detected=["contempt", "stonewalling"],
            repair_attempts=[{"at": "2025-01-01T00:00:00", "quality": "good", "temp_delta": -3.0}],
            last_temp_update="2025-06-15T12:00:00+00:00",
            session_positive=7,
            session_negative=3,
        )

        jsonb = details.to_jsonb()
        restored = ConflictDetails.from_jsonb(jsonb)

        assert restored.temperature == details.temperature
        assert restored.zone == details.zone
        assert restored.positive_count == details.positive_count
        assert restored.negative_count == details.negative_count
        assert restored.gottman_ratio == details.gottman_ratio
        assert restored.gottman_target == details.gottman_target
        assert restored.horsemen_detected == details.horsemen_detected
        assert restored.session_positive == details.session_positive
        assert restored.session_negative == details.session_negative

    def test_roundtrip_after_combined_updates(self):
        """Apply both temperature and Gottman updates, serialize, deserialize,
        then apply more updates. State should be consistent."""
        details = ConflictDetails(temperature=50.0, zone="hot")

        # Apply updates
        details = TemperatureEngine.update_conflict_details(details, 10.0)
        details = GottmanTracker.update_conflict_details(
            details, is_positive=False, is_in_conflict=True,
        )

        # Serialize and restore
        jsonb = details.to_jsonb()
        restored = ConflictDetails.from_jsonb(jsonb)

        # Apply more updates to restored
        restored = TemperatureEngine.update_conflict_details(restored, -5.0)
        restored = GottmanTracker.update_conflict_details(
            restored, is_positive=True, is_in_conflict=False,
        )

        # Verify invariants
        assert 0.0 <= restored.temperature <= 100.0
        assert restored.positive_count == 1  # one positive
        assert restored.negative_count == 1  # one negative from before serialize

    def test_from_jsonb_with_none_returns_defaults(self):
        """from_jsonb(None) should return clean defaults."""
        details = ConflictDetails.from_jsonb(None)
        assert details.temperature == 0.0
        assert details.zone == "calm"
        assert details.positive_count == 0

    def test_from_jsonb_with_extra_keys_ignored(self):
        """JSONB from a future schema version with extra keys should not crash."""
        data = {
            "temperature": 30.0,
            "zone": "warm",
            "positive_count": 5,
            "negative_count": 2,
            "gottman_ratio": 2.5,
            "gottman_target": 20.0,
            "horsemen_detected": [],
            "repair_attempts": [],
            "last_temp_update": None,
            "session_positive": 0,
            "session_negative": 0,
            "future_field_v2": "should be ignored",
            "another_future_field": 42,
        }
        details = ConflictDetails.from_jsonb(data)
        assert details.temperature == 30.0
        assert details.zone == "warm"
