"""DA-03: Adversarial tests for ConflictDetails and ConflictTemperature models.

Targets: nikita/conflicts/models.py
- ConflictDetails: JSONB serialization, partial fields, wrong types, NaN/Inf
- ConflictTemperature: clamp_value validator, model_post_init zone auto-compute

These are pure model tests — synchronous, no DB, no mocks.
"""

import math

import pytest
from pydantic import ValidationError

from nikita.conflicts.models import (
    ConflictDetails,
    ConflictTemperature,
    TemperatureZone,
)


class TestFromJsonbPartialFields:
    """from_jsonb with only some fields present — rest should default."""

    def test_only_temperature(self):
        """Only temperature provided; all other fields should be defaults."""
        details = ConflictDetails.from_jsonb({"temperature": 42.0})
        assert details.temperature == 42.0
        assert details.zone == "calm"  # Default, NOT auto-synced to "warm"
        assert details.positive_count == 0
        assert details.negative_count == 0
        assert details.gottman_ratio == 0.0
        assert details.gottman_target == 20.0
        assert details.horsemen_detected == []
        assert details.repair_attempts == []
        assert details.last_temp_update is None
        assert details.session_positive == 0
        assert details.session_negative == 0

    def test_only_zone(self):
        """Only zone provided; temperature stays at default 0.0."""
        details = ConflictDetails.from_jsonb({"zone": "critical"})
        assert details.zone == "critical"
        assert details.temperature == 0.0

    def test_only_positive_count(self):
        """Only positive_count provided; rest default."""
        details = ConflictDetails.from_jsonb({"positive_count": 50})
        assert details.positive_count == 50
        assert details.negative_count == 0
        assert details.gottman_ratio == 0.0

    def test_session_counters_only(self):
        """Only session counters provided."""
        details = ConflictDetails.from_jsonb({
            "session_positive": 10,
            "session_negative": 3,
        })
        assert details.session_positive == 10
        assert details.session_negative == 3
        assert details.positive_count == 0
        assert details.negative_count == 0

    def test_horsemen_only(self):
        """Only horsemen_detected provided."""
        details = ConflictDetails.from_jsonb({
            "horsemen_detected": ["criticism", "contempt"],
        })
        assert details.horsemen_detected == ["criticism", "contempt"]
        assert details.temperature == 0.0


class TestFromJsonbExtraFields:
    """from_jsonb with extra unknown fields — should be silently ignored."""

    def test_extra_field_ignored(self):
        """Extra unknown fields should be filtered out by model_fields check."""
        details = ConflictDetails.from_jsonb({
            "temperature": 30.0,
            "some_unknown_field": "should_be_ignored",
            "another_unknown": 12345,
        })
        assert details.temperature == 30.0
        assert not hasattr(details, "some_unknown_field")
        assert not hasattr(details, "another_unknown")

    def test_nested_extra_field_ignored(self):
        """Extra nested object field should be ignored."""
        details = ConflictDetails.from_jsonb({
            "zone": "hot",
            "metadata": {"nested": True},
        })
        assert details.zone == "hot"
        assert not hasattr(details, "metadata")

    def test_all_valid_plus_extras(self):
        """All valid fields present plus extras — extras ignored, valid preserved."""
        data = {
            "temperature": 55.0,
            "zone": "hot",
            "positive_count": 10,
            "negative_count": 2,
            "gottman_ratio": 5.0,
            "gottman_target": 5.0,
            "horsemen_detected": ["criticism"],
            "repair_attempts": [],
            "last_temp_update": "2025-01-01T00:00:00Z",
            "session_positive": 3,
            "session_negative": 1,
            # Extras:
            "id": "uuid-123",
            "user_id": "user-456",
            "_internal_flag": True,
        }
        details = ConflictDetails.from_jsonb(data)
        assert details.temperature == 55.0
        assert details.zone == "hot"
        assert details.positive_count == 10


class TestFromJsonbWrongTypes:
    """from_jsonb with wrong types — test Pydantic coercion behavior."""

    def test_temperature_as_string(self):
        """temperature as string "50.0" — Pydantic should coerce to float."""
        details = ConflictDetails.from_jsonb({"temperature": "50.0"})
        assert details.temperature == 50.0
        assert isinstance(details.temperature, float)

    def test_positive_count_as_float(self):
        """positive_count as float 5.0 — Pydantic may coerce to int or raise."""
        # NOTE: Pydantic v2 strict mode would reject; default mode coerces
        try:
            details = ConflictDetails.from_jsonb({"positive_count": 5.0})
            # If coercion succeeds, value should be 5
            assert details.positive_count == 5
        except ValidationError:
            # Acceptable: Pydantic rejects float-to-int coercion
            pass

    def test_zone_as_int(self):
        """zone as int — should raise ValidationError (can't coerce int to str)."""
        # NOTE: Pydantic v2 actually coerces int to str
        try:
            details = ConflictDetails.from_jsonb({"zone": 42})
            # If it coerces, zone becomes "42"
            assert details.zone == "42"
        except ValidationError:
            # Also acceptable
            pass

    def test_temperature_as_non_numeric_string(self):
        """temperature as "not_a_number" — should raise ValidationError."""
        with pytest.raises(ValidationError):
            ConflictDetails.from_jsonb({"temperature": "not_a_number"})

    def test_negative_count_as_negative(self):
        """negative_count as -5 — should fail ge=0 constraint."""
        with pytest.raises(ValidationError):
            ConflictDetails.from_jsonb({"negative_count": -5})

    def test_temperature_as_bool(self):
        """temperature as True — Pydantic may coerce bool to float (1.0)."""
        # NOTE: In Pydantic v2, bool is not coerced to float by default
        try:
            details = ConflictDetails.from_jsonb({"temperature": True})
            assert details.temperature == 1.0
        except ValidationError:
            pass

    def test_gottman_ratio_as_negative(self):
        """gottman_ratio as -1.0 — should fail ge=0.0 constraint."""
        with pytest.raises(ValidationError):
            ConflictDetails.from_jsonb({"gottman_ratio": -1.0})


class TestFromJsonbNone:
    """from_jsonb(None) returns defaults."""

    def test_none_returns_defaults(self):
        """None input should return a ConflictDetails with all defaults."""
        details = ConflictDetails.from_jsonb(None)
        assert details.temperature == 0.0
        assert details.zone == "calm"
        assert details.positive_count == 0
        assert details.negative_count == 0
        assert details.gottman_ratio == 0.0
        assert details.gottman_target == 20.0
        assert details.horsemen_detected == []
        assert details.repair_attempts == []
        assert details.last_temp_update is None
        assert details.session_positive == 0
        assert details.session_negative == 0


class TestFromJsonbEmptyDict:
    """from_jsonb({}) returns defaults."""

    def test_empty_dict_returns_defaults(self):
        """Empty dict should return a ConflictDetails with all defaults."""
        details = ConflictDetails.from_jsonb({})
        assert details.temperature == 0.0
        assert details.zone == "calm"
        assert details.positive_count == 0
        assert details.negative_count == 0

    def test_empty_dict_equals_none(self):
        """Empty dict and None should produce equivalent defaults."""
        from_none = ConflictDetails.from_jsonb(None)
        from_empty = ConflictDetails.from_jsonb({})
        assert from_none.model_dump() == from_empty.model_dump()


class TestRoundtripConsistency:
    """to_jsonb() -> from_jsonb() roundtrip should preserve data."""

    def test_default_roundtrip(self):
        """Default ConflictDetails survives roundtrip."""
        original = ConflictDetails()
        jsonb = original.to_jsonb()
        restored = ConflictDetails.from_jsonb(jsonb)
        assert original.model_dump() == restored.model_dump()

    def test_populated_roundtrip(self):
        """Fully populated ConflictDetails survives roundtrip."""
        original = ConflictDetails(
            temperature=67.5,
            zone="hot",
            positive_count=15,
            negative_count=3,
            gottman_ratio=5.0,
            gottman_target=5.0,
            horsemen_detected=["criticism", "contempt"],
            repair_attempts=[{"at": "2025-01-01T00:00:00Z", "quality": "good", "temp_delta": -5.0}],
            last_temp_update="2025-06-15T12:00:00Z",
            session_positive=4,
            session_negative=1,
        )
        jsonb = original.to_jsonb()
        restored = ConflictDetails.from_jsonb(jsonb)
        assert original.model_dump() == restored.model_dump()

    def test_boundary_values_roundtrip(self):
        """Boundary values (0.0, 100.0) survive roundtrip."""
        for temp in [0.0, 25.0, 50.0, 75.0, 100.0]:
            original = ConflictDetails(temperature=temp)
            jsonb = original.to_jsonb()
            restored = ConflictDetails.from_jsonb(jsonb)
            assert restored.temperature == temp

    def test_large_repair_history_roundtrip(self):
        """Large repair_attempts list survives roundtrip."""
        repairs = [
            {"at": f"2025-01-{i+1:02d}T00:00:00Z", "quality": "good", "temp_delta": -2.0}
            for i in range(100)
        ]
        original = ConflictDetails(repair_attempts=repairs)
        jsonb = original.to_jsonb()
        restored = ConflictDetails.from_jsonb(jsonb)
        assert len(restored.repair_attempts) == 100


class TestTemperatureNaNInfinity:
    """NaN and Infinity in temperature — Pydantic ge/le validators should catch."""

    def test_nan_direct_construction(self):
        """temperature=NaN in direct construction. ge=0.0, le=100.0 should reject NaN."""
        # NOTE: May fail if Pydantic doesn't reject NaN via ge/le constraints.
        # NaN comparisons always return False, so NaN >= 0 is False.
        with pytest.raises(ValidationError):
            ConflictDetails(temperature=float("nan"))

    def test_positive_inf_direct_construction(self):
        """temperature=+inf should fail le=100.0 constraint."""
        with pytest.raises(ValidationError):
            ConflictDetails(temperature=float("inf"))

    def test_negative_inf_direct_construction(self):
        """temperature=-inf should fail ge=0.0 constraint."""
        with pytest.raises(ValidationError):
            ConflictDetails(temperature=float("-inf"))

    def test_nan_via_from_jsonb(self):
        """temperature=NaN via from_jsonb — should fail validation."""
        with pytest.raises(ValidationError):
            ConflictDetails.from_jsonb({"temperature": float("nan")})

    def test_positive_inf_via_from_jsonb(self):
        """temperature=+inf via from_jsonb."""
        with pytest.raises(ValidationError):
            ConflictDetails.from_jsonb({"temperature": float("inf")})

    def test_negative_inf_via_from_jsonb(self):
        """temperature=-inf via from_jsonb."""
        with pytest.raises(ValidationError):
            ConflictDetails.from_jsonb({"temperature": float("-inf")})

    def test_gottman_ratio_nan(self):
        """gottman_ratio=NaN — ge=0.0 should catch."""
        with pytest.raises(ValidationError):
            ConflictDetails(gottman_ratio=float("nan"))

    def test_gottman_ratio_inf(self):
        """gottman_ratio=+inf — no le constraint, may pass."""
        # NOTE: gottman_ratio has ge=0.0 but no le constraint.
        # +inf >= 0.0 is True, so this may succeed.
        try:
            details = ConflictDetails(gottman_ratio=float("inf"))
            assert details.gottman_ratio == float("inf")
        except ValidationError:
            # Also acceptable if Pydantic rejects it
            pass


class TestZoneTemperatureMismatch:
    """ConflictDetails does NOT auto-sync zone from temperature.

    Unlike ConflictTemperature which has model_post_init,
    ConflictDetails stores zone as a plain str field.
    """

    def test_critical_zone_low_temperature(self):
        """zone='critical' but temperature=10.0 — no auto-correction."""
        details = ConflictDetails(temperature=10.0, zone="critical")
        assert details.zone == "critical"
        assert details.temperature == 10.0
        # Zone does NOT get auto-corrected to "calm"

    def test_calm_zone_high_temperature(self):
        """zone='calm' but temperature=99.0 — no auto-correction."""
        details = ConflictDetails(temperature=99.0, zone="calm")
        assert details.zone == "calm"
        assert details.temperature == 99.0

    def test_arbitrary_zone_string(self):
        """zone='banana' — ConflictDetails allows any string."""
        details = ConflictDetails(zone="banana")
        assert details.zone == "banana"

    def test_empty_zone_string(self):
        """zone='' — ConflictDetails allows empty string."""
        details = ConflictDetails(zone="")
        assert details.zone == ""

    def test_roundtrip_preserves_mismatch(self):
        """Mismatch survives roundtrip — no correction during serialization."""
        original = ConflictDetails(temperature=5.0, zone="critical")
        jsonb = original.to_jsonb()
        restored = ConflictDetails.from_jsonb(jsonb)
        assert restored.temperature == 5.0
        assert restored.zone == "critical"


class TestConflictTemperatureModel:
    """ConflictTemperature model: clamp_value validator + model_post_init zone auto-compute."""

    def test_negative_value_clamps_to_zero(self):
        """value=-5 should be clamped to 0.0 by clamp_value validator."""
        ct = ConflictTemperature(value=-5.0)
        assert ct.value == 0.0
        assert ct.zone == TemperatureZone.CALM

    def test_over_100_clamps_to_100(self):
        """value=150 should be clamped to 100.0."""
        ct = ConflictTemperature(value=150.0)
        assert ct.value == 100.0
        assert ct.zone == TemperatureZone.CRITICAL

    def test_large_negative_clamps_to_zero(self):
        """value=-10000 should clamp to 0."""
        ct = ConflictTemperature(value=-10000.0)
        assert ct.value == 0.0

    def test_large_positive_clamps_to_100(self):
        """value=99999 should clamp to 100."""
        ct = ConflictTemperature(value=99999.0)
        assert ct.value == 100.0

    def test_zone_auto_compute_calm(self):
        """value=0 -> CALM zone."""
        ct = ConflictTemperature(value=0.0)
        assert ct.zone == TemperatureZone.CALM

    def test_zone_auto_compute_warm(self):
        """value=30 -> WARM zone."""
        ct = ConflictTemperature(value=30.0)
        assert ct.zone == TemperatureZone.WARM

    def test_zone_auto_compute_hot(self):
        """value=60 -> HOT zone."""
        ct = ConflictTemperature(value=60.0)
        assert ct.zone == TemperatureZone.HOT

    def test_zone_auto_compute_critical(self):
        """value=80 -> CRITICAL zone."""
        ct = ConflictTemperature(value=80.0)
        assert ct.zone == TemperatureZone.CRITICAL

    def test_zone_boundary_24_99(self):
        """value=24.99 -> CALM (boundary below 25)."""
        ct = ConflictTemperature(value=24.99)
        assert ct.zone == TemperatureZone.CALM

    def test_zone_boundary_25(self):
        """value=25.0 -> WARM (boundary at 25)."""
        ct = ConflictTemperature(value=25.0)
        assert ct.zone == TemperatureZone.WARM

    def test_zone_boundary_49_99(self):
        """value=49.99 -> WARM (boundary below 50)."""
        ct = ConflictTemperature(value=49.99)
        assert ct.zone == TemperatureZone.WARM

    def test_zone_boundary_50(self):
        """value=50.0 -> HOT."""
        ct = ConflictTemperature(value=50.0)
        assert ct.zone == TemperatureZone.HOT

    def test_zone_boundary_74_99(self):
        """value=74.99 -> HOT (boundary below 75)."""
        ct = ConflictTemperature(value=74.99)
        assert ct.zone == TemperatureZone.HOT

    def test_zone_boundary_75(self):
        """value=75.0 -> CRITICAL."""
        ct = ConflictTemperature(value=75.0)
        assert ct.zone == TemperatureZone.CRITICAL

    def test_zone_overrides_explicit_zone(self):
        """Explicit zone=CALM but value=80 -> model_post_init overrides to CRITICAL."""
        ct = ConflictTemperature(value=80.0, zone=TemperatureZone.CALM)
        assert ct.zone == TemperatureZone.CRITICAL

    def test_nan_value(self):
        """value=NaN — clamp_value explicitly catches NaN and maps to 0.0 (safe default).

        FIXED: Previously NaN silently mapped to 100.0 (CRITICAL zone) via
        Python 3.13's min/max behavior. Now explicitly guarded.
        """
        ct = ConflictTemperature(value=float("nan"))
        assert ct.value == 0.0, "NaN should map to 0.0 (safe default)"
        assert ct.zone == TemperatureZone.CALM

    def test_inf_value_clamps_to_zero(self):
        """value=+inf — clamp_value explicitly catches Inf and maps to 0.0 (safe default).

        FIXED: Previously +inf mapped to 100.0. Now explicitly guarded.
        """
        ct = ConflictTemperature(value=float("inf"))
        assert ct.value == 0.0, "+inf should map to 0.0 (safe default)"
        assert ct.zone == TemperatureZone.CALM

    def test_negative_inf_clamps_to_zero(self):
        """value=-inf — clamp_value: max(0, -inf) = 0. Should work."""
        ct = ConflictTemperature(value=float("-inf"))
        assert ct.value == 0.0
        assert ct.zone == TemperatureZone.CALM

    def test_string_value_coercion(self):
        """value="50.0" — clamp_value does float(v), should coerce."""
        ct = ConflictTemperature(value="50.0")
        assert ct.value == 50.0
        assert ct.zone == TemperatureZone.HOT

    def test_non_numeric_string_raises(self):
        """value="abc" — float("abc") raises ValueError inside clamp_value."""
        with pytest.raises((ValidationError, ValueError)):
            ConflictTemperature(value="abc")
