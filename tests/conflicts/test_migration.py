"""Tests for Spec 057 migration utility.

Tests cover:
- Enum to temperature mapping
- Gottman initialization from score history
- ConflictDetails output structure
"""

import pytest

from nikita.conflicts.migration import migrate_user_conflict_state
from nikita.emotional_state.models import ConflictState


class TestMigrateUserConflictState:
    """Test migration from enum to temperature model."""

    def test_none_maps_to_zero(self):
        details = migrate_user_conflict_state("none")
        assert details.temperature == 0.0
        assert details.zone == "calm"

    def test_passive_aggressive_maps_to_40(self):
        details = migrate_user_conflict_state("passive_aggressive")
        assert details.temperature == 40.0
        assert details.zone == "warm"

    def test_cold_maps_to_50(self):
        details = migrate_user_conflict_state("cold")
        assert details.temperature == 50.0
        assert details.zone == "hot"

    def test_vulnerable_maps_to_30(self):
        details = migrate_user_conflict_state("vulnerable")
        assert details.temperature == 30.0
        assert details.zone == "warm"

    def test_explosive_maps_to_85(self):
        details = migrate_user_conflict_state("explosive")
        assert details.temperature == 85.0
        assert details.zone == "critical"

    def test_enum_input_accepted(self):
        details = migrate_user_conflict_state(ConflictState.COLD)
        assert details.temperature == 50.0

    def test_invalid_state_defaults_to_none(self):
        details = migrate_user_conflict_state("invalid_state")
        assert details.temperature == 0.0

    def test_gottman_initialized_from_history(self):
        entries = [
            {"delta": "2.5"},
            {"delta": "-1.0"},
            {"delta": "3.0"},
        ]
        details = migrate_user_conflict_state("none", score_history_entries=entries)
        assert details.positive_count == 2
        assert details.negative_count == 1

    def test_empty_history(self):
        details = migrate_user_conflict_state("none", score_history_entries=[])
        assert details.positive_count == 0
        assert details.negative_count == 0

    def test_has_last_temp_update(self):
        details = migrate_user_conflict_state("none")
        assert details.last_temp_update is not None

    def test_gottman_target_in_conflict(self):
        # Temperature >= 25 means in conflict
        details = migrate_user_conflict_state("passive_aggressive")
        assert details.gottman_target == 5.0  # Conflict target

    def test_gottman_target_no_conflict(self):
        details = migrate_user_conflict_state("none")
        assert details.gottman_target == 20.0  # Normal target

    def test_empty_repair_attempts(self):
        details = migrate_user_conflict_state("cold")
        assert details.repair_attempts == []

    def test_empty_horsemen(self):
        details = migrate_user_conflict_state("cold")
        assert details.horsemen_detected == []


class TestConflictStateTemperatureFromEnum:
    """Test the static method on ConflictState."""

    def test_none(self):
        assert ConflictState.temperature_from_enum(ConflictState.NONE) == 0.0

    def test_passive_aggressive(self):
        assert ConflictState.temperature_from_enum(ConflictState.PASSIVE_AGGRESSIVE) == 40.0

    def test_cold(self):
        assert ConflictState.temperature_from_enum(ConflictState.COLD) == 50.0

    def test_vulnerable(self):
        assert ConflictState.temperature_from_enum(ConflictState.VULNERABLE) == 30.0

    def test_explosive(self):
        assert ConflictState.temperature_from_enum(ConflictState.EXPLOSIVE) == 85.0
