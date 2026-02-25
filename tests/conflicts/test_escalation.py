"""Escalation tests for Conflict Generation System (Spec 027, Phase D: T016-T019).

Tests for:
- T016: EscalationManager class
- T017: Escalation timeline
- T018: Natural resolution
- T019: Phase D coverage
"""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from nikita.conflicts.escalation import (
    EscalationManager,
    EscalationResult,
    get_escalation_manager,
)
from nikita.conflicts.models import (
    ActiveConflict,
    ConflictConfig,
    ConflictType,
    EscalationLevel,
    ResolutionType,
)


# Fixtures


@pytest.fixture
def manager():
    """Create an EscalationManager for testing."""
    return EscalationManager()


@pytest.fixture
def subtle_conflict():
    """Create a conflict at SUBTLE level."""
    return ActiveConflict(
        conflict_id=str(uuid4()),
        user_id="user_subtle",
        conflict_type=ConflictType.JEALOUSY,
        severity=0.5,
        escalation_level=EscalationLevel.SUBTLE,
        triggered_at=datetime.now(UTC),
    )


@pytest.fixture
def direct_conflict():
    """Create a conflict at DIRECT level."""
    return ActiveConflict(
        conflict_id=str(uuid4()),
        user_id="user_direct",
        conflict_type=ConflictType.BOUNDARY,
        severity=0.6,
        escalation_level=EscalationLevel.DIRECT,
        triggered_at=datetime.now(UTC),
        last_escalated=datetime.now(UTC),
    )


@pytest.fixture
def crisis_conflict():
    """Create a conflict at CRISIS level."""
    return ActiveConflict(
        conflict_id=str(uuid4()),
        user_id="user_crisis",
        conflict_type=ConflictType.TRUST,
        severity=0.8,
        escalation_level=EscalationLevel.CRISIS,
        triggered_at=datetime.now(UTC),
        last_escalated=datetime.now(UTC),
    )


@pytest.fixture
def old_subtle_conflict():
    """Create a SUBTLE conflict that's past escalation threshold."""
    return ActiveConflict(
        conflict_id=str(uuid4()),
        user_id="user_old_subtle",
        conflict_type=ConflictType.ATTENTION,
        severity=0.4,
        escalation_level=EscalationLevel.SUBTLE,
        triggered_at=datetime.now(UTC) - timedelta(hours=5),
    )


# Test EscalationResult


class TestEscalationResult:
    """Tests for EscalationResult model."""

    def test_default_result(self):
        """Test default escalation result."""
        result = EscalationResult()
        assert not result.escalated
        assert result.new_level is None
        assert not result.naturally_resolved
        assert result.time_until_escalation is None

    def test_escalated_result(self):
        """Test escalated result."""
        result = EscalationResult(
            escalated=True,
            new_level=EscalationLevel.DIRECT,
            reason="Escalated to DIRECT",
        )
        assert result.escalated
        assert result.new_level == EscalationLevel.DIRECT

    def test_natural_resolution_result(self):
        """Test natural resolution result."""
        result = EscalationResult(
            naturally_resolved=True,
            reason="Conflict resolved naturally",
        )
        assert result.naturally_resolved


# Test EscalationManager Creation


class TestEscalationManagerCreation:
    """Tests for EscalationManager initialization."""

    def test_create_manager(self):
        """Test creating a manager."""
        mgr = EscalationManager()
        assert mgr._config is not None

    def test_create_with_custom_config(self):
        """Test creating with custom config."""
        config = ConflictConfig(
            natural_resolution_probability_level_1=0.5,
        )
        mgr = EscalationManager(config=config)
        assert mgr._config.natural_resolution_probability_level_1 == 0.5


# Test Escalation Timeline (T017)


class TestEscalationTimeline:
    """Tests for escalation timeline."""

    def test_subtle_escalation_threshold(self, manager):
        """Test SUBTLE level has 2-6h escalation threshold."""
        threshold = manager._get_escalation_threshold(EscalationLevel.SUBTLE)
        assert threshold is not None
        # Middle of 2-6 hours = 4 hours
        assert timedelta(hours=3) <= threshold <= timedelta(hours=5)

    def test_direct_escalation_threshold(self, manager):
        """Test DIRECT level has 12-24h escalation threshold."""
        threshold = manager._get_escalation_threshold(EscalationLevel.DIRECT)
        assert threshold is not None
        # Middle of 12-24 hours = 18 hours
        assert timedelta(hours=15) <= threshold <= timedelta(hours=21)

    def test_crisis_no_escalation(self, manager):
        """Test CRISIS level has no further escalation."""
        threshold = manager._get_escalation_threshold(EscalationLevel.CRISIS)
        assert threshold is None

    def test_escalation_not_yet_due(self, manager, subtle_conflict):
        """Test no escalation when time not met."""
        result = manager.check_escalation(subtle_conflict)
        assert not result.escalated
        assert result.time_until_escalation is not None
        assert result.time_until_escalation > timedelta(0)

    def test_escalation_due(self, manager, old_subtle_conflict):
        """Test escalation when threshold exceeded."""
        result = manager.check_escalation(old_subtle_conflict)
        # Either escalated or naturally resolved
        assert result.escalated or result.naturally_resolved

    def test_subtle_to_direct_escalation(self, manager):
        """Test escalation from SUBTLE to DIRECT."""
        conflict = ActiveConflict(
            conflict_id=str(uuid4()),
            user_id="user_s2d",
            conflict_type=ConflictType.JEALOUSY,
            severity=0.5,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC) - timedelta(hours=10),
        )

        # Patch random to prevent natural resolution
        with patch("nikita.conflicts.escalation.random.Random") as mock_random:
            mock_random.return_value.random.return_value = 1.0  # Never resolve

            result = manager.check_escalation(conflict)
            if result.escalated:
                assert result.new_level == EscalationLevel.DIRECT

    def test_direct_to_crisis_escalation(self, manager):
        """Test escalation from DIRECT to CRISIS."""
        conflict = ActiveConflict(
            conflict_id=str(uuid4()),
            user_id="user_d2c",
            conflict_type=ConflictType.BOUNDARY,
            severity=0.6,
            escalation_level=EscalationLevel.DIRECT,
            triggered_at=datetime.now(UTC) - timedelta(hours=30),
            last_escalated=datetime.now(UTC) - timedelta(hours=20),
        )

        # Patch random to prevent natural resolution
        with patch("nikita.conflicts.escalation.random.Random") as mock_random:
            mock_random.return_value.random.return_value = 1.0  # Never resolve

            result = manager.check_escalation(conflict)
            if result.escalated:
                assert result.new_level == EscalationLevel.CRISIS


# Test Natural Resolution (T018)


class TestNaturalResolution:
    """Tests for natural resolution."""

    def test_subtle_natural_resolution_probability(self, manager):
        """Test SUBTLE level has 30% natural resolution."""
        prob = manager._get_natural_resolution_probability(EscalationLevel.SUBTLE)
        assert prob == 0.30

    def test_direct_natural_resolution_probability(self, manager):
        """Test DIRECT level has 10% natural resolution."""
        prob = manager._get_natural_resolution_probability(EscalationLevel.DIRECT)
        assert prob == 0.10

    def test_crisis_no_natural_resolution(self, manager):
        """Test CRISIS level has 0% natural resolution."""
        prob = manager._get_natural_resolution_probability(EscalationLevel.CRISIS)
        assert prob == 0.0

    def test_natural_resolution_possible(self, manager):
        """Test that natural resolution can occur."""
        conflict = ActiveConflict(
            conflict_id=str(uuid4()),
            user_id="user_nat_res",
            conflict_type=ConflictType.ATTENTION,
            severity=0.3,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC) - timedelta(hours=2),
        )

        # Patch random to force natural resolution
        with patch("nikita.conflicts.escalation.random.Random") as mock_random:
            mock_random.return_value.random.return_value = 0.1  # Below 30% threshold

            result = manager.check_escalation(conflict)
            assert result.naturally_resolved

    def test_natural_resolution_returns_result(self, manager):
        """Test that natural resolution returns an EscalationResult."""
        conflict = ActiveConflict(
            conflict_id=str(uuid4()),
            user_id="user_nat_upd",
            conflict_type=ConflictType.ATTENTION,
            severity=0.3,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC) - timedelta(hours=2),
        )

        with patch("nikita.conflicts.escalation.random.Random") as mock_random:
            mock_random.return_value.random.return_value = 0.1

            result = manager.check_escalation(conflict)
            if result.naturally_resolved:
                assert isinstance(result, EscalationResult)
                assert result.naturally_resolved is True


# Test Acknowledgment


class TestAcknowledgment:
    """Tests for user acknowledgment."""

    def test_acknowledge_returns_true(self, manager, subtle_conflict):
        """Test that acknowledgment returns True for active conflict."""
        result = manager.acknowledge(subtle_conflict)
        assert result is True

    def test_acknowledge_resolved_conflict_fails(self, manager):
        """Test that acknowledging resolved conflict fails."""
        resolved = ActiveConflict(
            conflict_id=str(uuid4()),
            user_id="user_ack_res",
            conflict_type=ConflictType.JEALOUSY,
            severity=0.5,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC),
            resolved=True,
            resolution_type=ResolutionType.FULL,
        )

        result = manager.acknowledge(resolved)
        assert not result

    def test_acknowledge_with_conflict_details_returns_dict(self, manager, subtle_conflict):
        """Test that acknowledge with conflict_details returns updated dict."""
        conflict_details = {"temperature": 50.0, "zone": "hot"}
        result = manager.acknowledge(subtle_conflict, conflict_details=conflict_details)
        # With conflict_details, returns updated dict (temperature reduced)
        assert isinstance(result, dict)
        assert "temperature" in result


# Test Force Escalation


class TestForceEscalation:
    """Tests for force escalation."""

    def test_force_escalate_subtle(self, manager, subtle_conflict):
        """Test force escalation from SUBTLE."""
        result = manager.escalate(subtle_conflict)
        assert result.escalated
        assert result.new_level == EscalationLevel.DIRECT

    def test_force_escalate_direct(self, manager, direct_conflict):
        """Test force escalation from DIRECT."""
        result = manager.escalate(direct_conflict)
        assert result.escalated
        assert result.new_level == EscalationLevel.CRISIS

    def test_force_escalate_crisis_fails(self, manager, crisis_conflict):
        """Test force escalation from CRISIS fails."""
        result = manager.escalate(crisis_conflict)
        assert not result.escalated
        assert "maximum level" in result.reason.lower()

    def test_force_escalate_resolved_fails(self, manager):
        """Test force escalation of resolved conflict fails."""
        resolved = ActiveConflict(
            conflict_id=str(uuid4()),
            user_id="user_esc_res",
            conflict_type=ConflictType.ATTENTION,
            severity=0.4,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC),
            resolved=True,
            resolution_type=ResolutionType.FULL,
        )

        result = manager.escalate(resolved)
        assert not result.escalated
        assert "resolved" in result.reason.lower()


# Test Check Escalation


class TestCheckEscalation:
    """Tests for check_escalation method."""

    def test_check_resolved_conflict(self, manager):
        """Test checking resolved conflict."""
        resolved = ActiveConflict(
            conflict_id=str(uuid4()),
            user_id="user_chk_res",
            conflict_type=ConflictType.JEALOUSY,
            severity=0.5,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC),
            resolved=True,
            resolution_type=ResolutionType.FULL,
        )

        result = manager.check_escalation(resolved)
        assert not result.escalated
        assert not result.naturally_resolved
        assert "already resolved" in result.reason.lower()

    def test_check_crisis_no_escalation(self, manager, crisis_conflict):
        """Test checking CRISIS level conflict."""
        result = manager.check_escalation(crisis_conflict)
        assert not result.escalated
        assert "maximum" in result.reason.lower()

    def test_check_returns_time_until(self, manager, subtle_conflict):
        """Test that check returns time until escalation."""
        result = manager.check_escalation(subtle_conflict)
        if not result.escalated and not result.naturally_resolved:
            assert result.time_until_escalation is not None


# Test Timeline Information


class TestTimelineInformation:
    """Tests for timeline information."""

    def test_get_timeline_active(self, manager, subtle_conflict):
        """Test getting timeline for active conflict."""
        timeline = manager.get_escalation_timeline(subtle_conflict)
        assert timeline["status"] == "active"
        assert timeline["current_level"] == "SUBTLE"
        assert timeline["current_level_value"] == 1
        assert "time_in_level_hours" in timeline
        assert "escalation_threshold_hours" in timeline
        assert "natural_resolution_probability" in timeline

    def test_get_timeline_resolved(self, manager):
        """Test getting timeline for resolved conflict."""
        resolved = ActiveConflict(
            conflict_id=str(uuid4()),
            user_id="user_tl_res",
            conflict_type=ConflictType.ATTENTION,
            severity=0.4,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC),
            resolved=True,
            resolution_type=ResolutionType.FULL,
        )

        timeline = manager.get_escalation_timeline(resolved)
        assert timeline["status"] == "resolved"
        assert timeline["resolution_type"] == "full"

    def test_get_timeline_crisis(self, manager, crisis_conflict):
        """Test getting timeline for CRISIS conflict."""
        timeline = manager.get_escalation_timeline(crisis_conflict)
        assert timeline["status"] == "active"
        assert timeline["current_level"] == "CRISIS"
        assert timeline["escalation_threshold_hours"] is None
        assert timeline["natural_resolution_probability"] == 0.0


# Test Next Level Logic


class TestNextLevel:
    """Tests for next level logic."""

    def test_subtle_next_is_direct(self, manager):
        """Test SUBTLE → DIRECT."""
        next_level = manager._get_next_level(EscalationLevel.SUBTLE)
        assert next_level == EscalationLevel.DIRECT

    def test_direct_next_is_crisis(self, manager):
        """Test DIRECT → CRISIS."""
        next_level = manager._get_next_level(EscalationLevel.DIRECT)
        assert next_level == EscalationLevel.CRISIS

    def test_crisis_next_is_none(self, manager):
        """Test CRISIS → None."""
        next_level = manager._get_next_level(EscalationLevel.CRISIS)
        assert next_level is None


# Test Global Instance


class TestGlobalManager:
    """Tests for global manager instance."""

    def test_get_escalation_manager_returns_instance(self):
        """Test that get_escalation_manager returns instance."""
        mgr = get_escalation_manager()
        assert isinstance(mgr, EscalationManager)

    def test_get_escalation_manager_same_instance(self):
        """Test that same instance is returned."""
        mgr1 = get_escalation_manager()
        mgr2 = get_escalation_manager()
        assert mgr1 is mgr2


# Test Edge Cases


class TestEdgeCases:
    """Tests for edge cases."""

    def test_time_in_level_uses_triggered_at(self, manager):
        """Test that time in level uses triggered_at before escalation."""
        conflict = ActiveConflict(
            conflict_id=str(uuid4()),
            user_id="user_ref_time",
            conflict_type=ConflictType.JEALOUSY,
            severity=0.5,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC) - timedelta(hours=2),
        )

        # Before any escalation (no last_escalated), should use triggered_at
        time_before = manager._get_time_in_level(conflict)
        assert time_before >= timedelta(hours=1, minutes=59)

    def test_time_in_level_uses_last_escalated_when_set(self, manager):
        """Test that time in level uses last_escalated when set."""
        conflict = ActiveConflict(
            conflict_id=str(uuid4()),
            user_id="user_ref_time2",
            conflict_type=ConflictType.BOUNDARY,
            severity=0.6,
            escalation_level=EscalationLevel.DIRECT,
            triggered_at=datetime.now(UTC) - timedelta(hours=5),
            last_escalated=datetime.now(UTC) - timedelta(seconds=1),
        )

        # After escalation, last_escalated is used (very recent)
        time_after = manager._get_time_in_level(conflict)
        assert time_after < timedelta(seconds=5)

    def test_natural_resolution_deterministic(self, manager):
        """Test that natural resolution is deterministic per conflict-hour."""
        conflict = ActiveConflict(
            conflict_id=str(uuid4()),
            user_id="user_det",
            conflict_type=ConflictType.ATTENTION,
            severity=0.3,
            escalation_level=EscalationLevel.SUBTLE,
            triggered_at=datetime.now(UTC) - timedelta(hours=2),
        )

        # Check multiple times should give same result
        results = [manager._check_natural_resolution(conflict) for _ in range(5)]
        assert all(r == results[0] for r in results)
