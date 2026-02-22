"""Tests for Spec 057 temperature models.

Tests cover:
- TemperatureZone enum
- HorsemanType enum
- ConflictTemperature model (validation, zone auto-compute)
- GottmanCounters model (ratio calculation)
- ConflictDetails model (JSONB serialization)
- RepairRecord model
"""

import pytest
from datetime import UTC, datetime

from nikita.conflicts.models import (
    ConflictDetails,
    ConflictTemperature,
    GottmanCounters,
    HorsemanType,
    RepairRecord,
    TemperatureZone,
)


class TestTemperatureZone:
    """Test TemperatureZone enum."""

    def test_all_zones_exist(self):
        assert TemperatureZone.CALM == "calm"
        assert TemperatureZone.WARM == "warm"
        assert TemperatureZone.HOT == "hot"
        assert TemperatureZone.CRITICAL == "critical"

    def test_zone_count(self):
        assert len(TemperatureZone) == 4


class TestHorsemanType:
    """Test HorsemanType enum."""

    def test_all_horsemen_exist(self):
        assert HorsemanType.CRITICISM == "criticism"
        assert HorsemanType.CONTEMPT == "contempt"
        assert HorsemanType.DEFENSIVENESS == "defensiveness"
        assert HorsemanType.STONEWALLING == "stonewalling"

    def test_horseman_count(self):
        assert len(HorsemanType) == 4


class TestConflictTemperature:
    """Test ConflictTemperature model."""

    def test_default_values(self):
        temp = ConflictTemperature()
        assert temp.value == 0.0
        assert temp.zone == TemperatureZone.CALM

    def test_clamp_above_100(self):
        temp = ConflictTemperature(value=150.0)
        assert temp.value == 100.0

    def test_clamp_below_zero(self):
        temp = ConflictTemperature(value=-10.0)
        assert temp.value == 0.0

    def test_zone_auto_computed_calm(self):
        temp = ConflictTemperature(value=10.0)
        assert temp.zone == TemperatureZone.CALM

    def test_zone_auto_computed_warm(self):
        temp = ConflictTemperature(value=30.0)
        assert temp.zone == TemperatureZone.WARM

    def test_zone_auto_computed_hot(self):
        temp = ConflictTemperature(value=60.0)
        assert temp.zone == TemperatureZone.HOT

    def test_zone_auto_computed_critical(self):
        temp = ConflictTemperature(value=80.0)
        assert temp.zone == TemperatureZone.CRITICAL

    def test_boundary_25_is_warm(self):
        temp = ConflictTemperature(value=25.0)
        assert temp.zone == TemperatureZone.WARM

    def test_boundary_50_is_hot(self):
        temp = ConflictTemperature(value=50.0)
        assert temp.zone == TemperatureZone.HOT

    def test_boundary_75_is_critical(self):
        temp = ConflictTemperature(value=75.0)
        assert temp.zone == TemperatureZone.CRITICAL


class TestGottmanCounters:
    """Test GottmanCounters model."""

    def test_default_values(self):
        counters = GottmanCounters()
        assert counters.positive_count == 0
        assert counters.negative_count == 0
        assert counters.session_positive == 0
        assert counters.session_negative == 0

    def test_ratio_property_normal(self):
        counters = GottmanCounters(positive_count=10, negative_count=2)
        assert counters.ratio == 5.0

    def test_ratio_property_no_negatives(self):
        counters = GottmanCounters(positive_count=5, negative_count=0)
        assert counters.ratio == float("inf")

    def test_ratio_property_empty(self):
        counters = GottmanCounters()
        assert counters.ratio == 0.0


class TestConflictDetails:
    """Test ConflictDetails model."""

    def test_default_values(self):
        details = ConflictDetails()
        assert details.temperature == 0.0
        assert details.zone == "calm"
        assert details.positive_count == 0
        assert details.negative_count == 0
        assert details.gottman_ratio == 0.0
        assert details.gottman_target == 20.0
        assert details.horsemen_detected == []
        assert details.repair_attempts == []

    def test_from_jsonb_empty(self):
        details = ConflictDetails.from_jsonb(None)
        assert details.temperature == 0.0

    def test_from_jsonb_empty_dict(self):
        details = ConflictDetails.from_jsonb({})
        assert details.temperature == 0.0

    def test_from_jsonb_with_data(self):
        data = {
            "temperature": 45.0,
            "zone": "warm",
            "positive_count": 10,
            "negative_count": 2,
        }
        details = ConflictDetails.from_jsonb(data)
        assert details.temperature == 45.0
        assert details.zone == "warm"
        assert details.positive_count == 10

    def test_from_jsonb_extra_fields_ignored(self):
        data = {"temperature": 50.0, "unknown_field": "value"}
        details = ConflictDetails.from_jsonb(data)
        assert details.temperature == 50.0

    def test_to_jsonb_roundtrip(self):
        details = ConflictDetails(
            temperature=55.0, zone="hot",
            positive_count=15, negative_count=3,
        )
        jsonb = details.to_jsonb()
        restored = ConflictDetails.from_jsonb(jsonb)
        assert restored.temperature == 55.0
        assert restored.positive_count == 15

    def test_to_jsonb_serializable(self):
        import json
        details = ConflictDetails(temperature=50.0)
        jsonb = details.to_jsonb()
        # Should be JSON-serializable
        json_str = json.dumps(jsonb)
        assert "temperature" in json_str


class TestRepairRecord:
    """Test RepairRecord model."""

    def test_creation(self):
        record = RepairRecord(quality="good", temp_delta=-15.0)
        assert record.quality == "good"
        assert record.temp_delta == -15.0
        assert record.at is not None
