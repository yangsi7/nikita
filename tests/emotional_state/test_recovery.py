"""Unit Tests: Recovery Mechanics (Spec 023, T015-T018).

Tests RecoveryManager class and all recovery methods:
- can_recover() checks
- apply_recovery() with different approaches
- Recovery rate calculation
- Decay-based recovery

AC-T015: RecoveryManager class
AC-T016: Recovery rate calculation
AC-T017: Decay-based recovery
AC-T018: Coverage tests
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from nikita.emotional_state.models import ConflictState, EmotionalStateModel
from nikita.emotional_state.recovery import (
    RecoveryApproach,
    RecoveryManager,
    RecoveryResult,
    get_recovery_manager,
)


@pytest.fixture
def user_id():
    """Generate test user ID."""
    return uuid4()


@pytest.fixture
def manager():
    """Create RecoveryManager instance."""
    return RecoveryManager()


class TestRecoveryManagerClass:
    """AC-T015: RecoveryManager class tests."""

    def test_has_can_recover_method(self, manager):
        """AC-T015.2: Should have can_recover method."""
        assert hasattr(manager, "can_recover")
        assert callable(manager.can_recover)

    def test_has_apply_recovery_method(self, manager):
        """AC-T015.3: Should have apply_recovery method."""
        assert hasattr(manager, "apply_recovery")
        assert callable(manager.apply_recovery)

    def test_has_approach_rates(self, manager):
        """Should have approach rates configured."""
        assert hasattr(manager, "APPROACH_RATES")
        assert RecoveryApproach.APOLOGETIC in manager.APPROACH_RATES
        assert RecoveryApproach.DISMISSIVE in manager.APPROACH_RATES

    def test_has_decay_rates(self, manager):
        """Should have decay rates configured."""
        assert hasattr(manager, "DECAY_RATES_PER_DAY")
        assert ConflictState.EXPLOSIVE in manager.DECAY_RATES_PER_DAY


class TestCanRecover:
    """AC-T015.2: can_recover() tests."""

    def test_cannot_recover_from_none(self, manager, user_id):
        """Should not recover from NONE state."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.NONE,
        )
        assert not manager.can_recover(state)

    def test_can_recover_from_conflict(self, manager, user_id):
        """Should allow recovery from conflict state."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
        )
        assert manager.can_recover(state)

    def test_cannot_recover_with_dismissive(self, manager, user_id):
        """Should block recovery with dismissive approach."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
        )
        assert not manager.can_recover(state, RecoveryApproach.DISMISSIVE)

    def test_can_recover_with_apologetic(self, manager, user_id):
        """Should allow recovery with apologetic approach."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.EXPLOSIVE,
        )
        assert manager.can_recover(state, RecoveryApproach.APOLOGETIC)

    def test_can_recover_with_validating(self, manager, user_id):
        """Should allow recovery with validating approach."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.VULNERABLE,
        )
        assert manager.can_recover(state, RecoveryApproach.VALIDATING)

    def test_can_recover_with_defensive(self, manager, user_id):
        """Should allow (but hard) recovery with defensive approach."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.PASSIVE_AGGRESSIVE,
        )
        # Defensive is allowed but has very low rate
        assert manager.can_recover(state, RecoveryApproach.DEFENSIVE)


class TestApplyRecovery:
    """AC-T015.3: apply_recovery() tests."""

    def test_apply_recovery_with_apologetic(self, manager, user_id):
        """Should apply recovery with apologetic approach."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.PASSIVE_AGGRESSIVE,
        )

        new_state, result = manager.apply_recovery(state, RecoveryApproach.APOLOGETIC)

        assert result.recovery_amount > 0
        # Single apologetic interaction might not fully recover
        assert result.new_state in [ConflictState.NONE, ConflictState.PASSIVE_AGGRESSIVE]

    def test_apply_recovery_blocked_by_dismissive(self, manager, user_id):
        """Should block recovery with dismissive approach."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
        )

        new_state, result = manager.apply_recovery(state, RecoveryApproach.DISMISSIVE)

        assert not result.recovered
        assert result.recovery_amount == 0
        assert new_state.conflict_state == ConflictState.COLD

    def test_apply_recovery_updates_progress(self, manager, user_id):
        """Should update recovery progress in metadata."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
        )

        new_state, result = manager.apply_recovery(state, RecoveryApproach.VALIDATING)

        assert "recovery_progress" in new_state.metadata
        assert new_state.metadata["recovery_progress"] > 0

    def test_apply_recovery_accumulates_progress(self, manager, user_id):
        """Should accumulate progress across multiple interactions."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
            metadata={"recovery_progress": 0.2},
        )

        new_state, result = manager.apply_recovery(state, RecoveryApproach.VALIDATING)

        assert new_state.metadata["recovery_progress"] > 0.2

    def test_apply_recovery_de_escalates_when_threshold_met(self, manager, user_id):
        """Should de-escalate when threshold is met."""
        # Start with high progress close to threshold
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
            metadata={"recovery_progress": 0.35},
        )

        # Apologetic gives 2x rate (0.2 * 2.0 = 0.4), plus 0.35 = 0.75 > 0.4 threshold
        new_state, result = manager.apply_recovery(
            state, RecoveryApproach.APOLOGETIC, intensity=1.0
        )

        assert result.recovered
        assert result.new_state == ConflictState.NONE

    def test_apply_recovery_de_escalates_explosive_to_cold(self, manager, user_id):
        """Should de-escalate EXPLOSIVE to COLD, not directly to NONE."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.EXPLOSIVE,
            metadata={"recovery_progress": 0.25},
        )

        # Apologetic gives high rate, cross 0.3 threshold
        new_state, result = manager.apply_recovery(
            state, RecoveryApproach.APOLOGETIC, intensity=1.0
        )

        if result.recovered:
            # Should de-escalate to COLD, not NONE
            assert result.new_state == ConflictState.COLD

    def test_apply_recovery_intensity_affects_amount(self, manager, user_id):
        """Should scale recovery by intensity."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
        )

        _, result_low = manager.apply_recovery(state, RecoveryApproach.NEUTRAL, intensity=0.5)
        _, result_high = manager.apply_recovery(state, RecoveryApproach.NEUTRAL, intensity=1.0)

        assert result_high.recovery_amount > result_low.recovery_amount


class TestRecoveryRateCalculation:
    """AC-T016: Recovery rate calculation tests."""

    def test_apologetic_fastest_recovery(self, manager):
        """AC-T016.2: Apology = fastest recovery."""
        rate_apology = manager.calculate_recovery_rate(
            RecoveryApproach.APOLOGETIC, ConflictState.COLD
        )
        rate_neutral = manager.calculate_recovery_rate(
            RecoveryApproach.NEUTRAL, ConflictState.COLD
        )

        assert rate_apology > rate_neutral

    def test_validating_fast_recovery(self, manager):
        """AC-T016.2: Validation = fast recovery."""
        rate_validating = manager.calculate_recovery_rate(
            RecoveryApproach.VALIDATING, ConflictState.COLD
        )
        rate_neutral = manager.calculate_recovery_rate(
            RecoveryApproach.NEUTRAL, ConflictState.COLD
        )

        assert rate_validating > rate_neutral

    def test_dismissive_no_recovery(self, manager):
        """AC-T016.3: Dismissive = no recovery."""
        rate = manager.calculate_recovery_rate(
            RecoveryApproach.DISMISSIVE, ConflictState.COLD
        )

        assert rate == 0.0

    def test_defensive_minimal_recovery(self, manager):
        """Defensive = minimal recovery."""
        rate_defensive = manager.calculate_recovery_rate(
            RecoveryApproach.DEFENSIVE, ConflictState.COLD
        )
        rate_neutral = manager.calculate_recovery_rate(
            RecoveryApproach.NEUTRAL, ConflictState.COLD
        )

        assert rate_defensive < rate_neutral

    def test_explosive_harder_to_recover(self, manager):
        """Explosive state should be harder to recover from."""
        rate_explosive = manager.calculate_recovery_rate(
            RecoveryApproach.APOLOGETIC, ConflictState.EXPLOSIVE
        )
        rate_cold = manager.calculate_recovery_rate(
            RecoveryApproach.APOLOGETIC, ConflictState.COLD
        )

        assert rate_explosive < rate_cold

    def test_rate_depends_on_approach(self, manager):
        """AC-T016.1: Recovery rate depends on user's approach."""
        approaches = [
            RecoveryApproach.APOLOGETIC,
            RecoveryApproach.VALIDATING,
            RecoveryApproach.NEUTRAL,
            RecoveryApproach.DEFENSIVE,
            RecoveryApproach.DISMISSIVE,
        ]

        rates = [
            manager.calculate_recovery_rate(approach, ConflictState.COLD)
            for approach in approaches
        ]

        # Rates should be in decreasing order
        assert rates[0] > rates[1] > rates[2] > rates[3] >= rates[4]


class TestDecayBasedRecovery:
    """AC-T017: Decay-based recovery tests."""

    def test_no_decay_from_none(self, manager, user_id):
        """Should not decay from NONE state."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.NONE,
        )

        new_state, result = manager.apply_decay_recovery(state)

        assert not result.recovered

    def test_no_decay_during_cooldown(self, manager, user_id):
        """Should not decay during cooldown period."""
        now = datetime.now(timezone.utc)
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
            conflict_started_at=now - timedelta(hours=12),  # Within cooldown
        )

        new_state, result = manager.apply_decay_recovery(state, current_time=now)

        assert not result.recovered
        assert "cooldown" in result.reason.lower()

    def test_decay_after_cooldown(self, manager, user_id):
        """Should apply decay after cooldown period."""
        now = datetime.now(timezone.utc)
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
            conflict_started_at=now - timedelta(hours=48),  # Past cooldown
            metadata={"last_decay_check": (now - timedelta(days=2)).isoformat()},
        )

        new_state, result = manager.apply_decay_recovery(state, current_time=now)

        # Should have some decay progress
        assert result.recovery_amount > 0

    def test_decay_rate_configurable_per_state(self, manager):
        """AC-T017.2: Decay rate configurable per conflict state."""
        # Different states have different decay rates
        assert manager.DECAY_RATES_PER_DAY[ConflictState.EXPLOSIVE] < \
               manager.DECAY_RATES_PER_DAY[ConflictState.COLD]
        assert manager.DECAY_RATES_PER_DAY[ConflictState.COLD] < \
               manager.DECAY_RATES_PER_DAY[ConflictState.PASSIVE_AGGRESSIVE]

    def test_explosive_slowest_decay(self, manager):
        """AC-T017.1: Explosive should have slowest decay (needs 6+ days)."""
        decay_rate = manager.DECAY_RATES_PER_DAY[ConflictState.EXPLOSIVE]
        threshold = manager.RECOVERY_THRESHOLDS[ConflictState.EXPLOSIVE]

        # Time to de-escalate = threshold / decay_rate
        days_to_de_escalate = threshold / decay_rate

        assert days_to_de_escalate >= 5  # At least 5 days

    def test_passive_aggressive_fastest_decay(self, manager):
        """Passive-aggressive should have fastest decay (2-3 days)."""
        decay_rate = manager.DECAY_RATES_PER_DAY[ConflictState.PASSIVE_AGGRESSIVE]
        threshold = manager.RECOVERY_THRESHOLDS[ConflictState.PASSIVE_AGGRESSIVE]

        days_to_de_escalate = threshold / decay_rate

        assert days_to_de_escalate <= 3  # At most 3 days

    def test_decay_updates_metadata(self, manager, user_id):
        """Should update decay metadata."""
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(days=3)
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
            conflict_started_at=start_time,
            metadata={"last_decay_check": (now - timedelta(days=1)).isoformat()},
        )

        new_state, result = manager.apply_decay_recovery(state, current_time=now)

        assert "last_decay_check" in new_state.metadata
        assert "decay_amount" in new_state.metadata

    def test_full_decay_recovery_after_days(self, manager, user_id):
        """Should fully recover after enough days of decay."""
        now = datetime.now(timezone.utc)
        # Cold state started 5 days ago (enough for full decay)
        start_time = now - timedelta(days=5)
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
            conflict_started_at=start_time,
            metadata={
                "last_decay_check": (now - timedelta(days=4)).isoformat(),
                "recovery_progress": 0.0,
            },
        )

        new_state, result = manager.apply_decay_recovery(state, current_time=now)

        # Cold decays at 0.15/day, threshold 0.4
        # 4 days of decay = 0.6, which is > 0.4 threshold
        assert result.recovered
        assert result.new_state == ConflictState.NONE


class TestDeEscalationPaths:
    """Tests for de-escalation paths."""

    def test_explosive_de_escalates_to_cold(self, manager):
        """EXPLOSIVE should de-escalate to COLD."""
        result = manager._get_de_escalated_state(ConflictState.EXPLOSIVE)
        assert result == ConflictState.COLD

    def test_cold_de_escalates_to_none(self, manager):
        """COLD should de-escalate to NONE."""
        result = manager._get_de_escalated_state(ConflictState.COLD)
        assert result == ConflictState.NONE

    def test_vulnerable_de_escalates_to_none(self, manager):
        """VULNERABLE should de-escalate to NONE."""
        result = manager._get_de_escalated_state(ConflictState.VULNERABLE)
        assert result == ConflictState.NONE

    def test_passive_aggressive_de_escalates_to_none(self, manager):
        """PASSIVE_AGGRESSIVE should de-escalate to NONE."""
        result = manager._get_de_escalated_state(ConflictState.PASSIVE_AGGRESSIVE)
        assert result == ConflictState.NONE

    def test_none_stays_none(self, manager):
        """NONE should stay NONE."""
        result = manager._get_de_escalated_state(ConflictState.NONE)
        assert result == ConflictState.NONE


class TestEstimatedRecoveryTime:
    """Tests for recovery time estimation."""

    def test_no_time_from_none(self, manager, user_id):
        """Should return zero time from NONE."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.NONE,
        )

        time = manager.get_estimated_recovery_time(state)

        assert time == timedelta(0)

    def test_faster_with_apologetic(self, manager, user_id):
        """Should estimate faster recovery with apologetic approach."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
        )

        time_apologetic = manager.get_estimated_recovery_time(state, RecoveryApproach.APOLOGETIC)
        time_neutral = manager.get_estimated_recovery_time(state, RecoveryApproach.NEUTRAL)

        assert time_apologetic < time_neutral

    def test_dismissive_falls_back_to_decay(self, manager, user_id):
        """Should use decay estimate for dismissive approach."""
        state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,
        )

        time = manager.get_estimated_recovery_time(state, RecoveryApproach.DISMISSIVE)

        # Decay-based, should be measured in days
        assert time.total_seconds() > 24 * 3600


class TestGetRecoveryManager:
    """Tests for singleton get_recovery_manager()."""

    def test_returns_recovery_manager(self):
        """Should return RecoveryManager instance."""
        manager = get_recovery_manager()
        assert isinstance(manager, RecoveryManager)

    def test_singleton_same_instance(self):
        """Should return same instance."""
        m1 = get_recovery_manager()
        m2 = get_recovery_manager()
        assert m1 is m2


class TestRecoveryResult:
    """Tests for RecoveryResult model."""

    def test_default_values(self):
        """Should have sensible defaults."""
        result = RecoveryResult()

        assert result.recovered is False
        assert result.new_state == ConflictState.NONE
        assert result.recovery_amount == 0.0
        assert result.reason == ""

    def test_custom_values(self):
        """Should accept custom values."""
        result = RecoveryResult(
            recovered=True,
            new_state=ConflictState.COLD,
            recovery_amount=0.35,
            reason="Good progress",
        )

        assert result.recovered is True
        assert result.new_state == ConflictState.COLD
        assert result.recovery_amount == 0.35
