"""Unit tests for nikita.agents.onboarding.extraction_schemas.

Covers AC-T2.2.1 (age<18 + phone E.164), AC-T2.2.2 (confidence bounds),
AC-T2.2.3 (ConverseResult 7-branch round trip).
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from nikita.agents.onboarding.extraction_schemas import (
    BackstoryExtraction,
    ConverseResult,
    DarknessExtraction,
    IdentityExtraction,
    LocationExtraction,
    NoExtraction,
    PhoneExtraction,
    SceneExtraction,
)


# ---------------------------------------------------------------------------
# AC-T2.2.1 — age/phone server-enforced validation
# ---------------------------------------------------------------------------


class TestIdentityAgeValidation:
    def test_identity_age_below_18_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            IdentityExtraction(age=17, confidence=0.9)
        # Error attached to the ``age`` field, not the model top-level.
        errors = exc_info.value.errors()
        assert any(err["loc"] == ("age",) for err in errors)

    def test_identity_age_18_accepted(self):
        model = IdentityExtraction(age=18, confidence=0.9)
        assert model.age == 18

    def test_identity_age_99_accepted(self):
        model = IdentityExtraction(age=99, confidence=0.9)
        assert model.age == 99

    def test_identity_age_100_rejected(self):
        with pytest.raises(ValidationError):
            IdentityExtraction(age=100, confidence=0.9)

    def test_identity_age_accepts_int_string(self):
        """GH #382 (D6): Anthropic tool use sometimes emits age as a
        string ('32') or float (32.0). The schema must coerce these to
        int rather than rejecting with a ValidationError that the agent
        then repeats on retry.
        """
        model = IdentityExtraction(age="32", confidence=0.9)  # type: ignore[arg-type]
        assert model.age == 32

    def test_identity_age_accepts_float(self):
        """GH #382 (D6): LLM may serialize age as 32.0 under some tool-
        use protocols. Coerce to int when value is integral."""
        model = IdentityExtraction(age=32.0, confidence=0.9)  # type: ignore[arg-type]
        assert model.age == 32

    def test_identity_age_rejects_non_numeric_string(self):
        """D6 safety rail: garbage strings must still reject."""
        with pytest.raises(ValidationError):
            IdentityExtraction(age="not-an-int", confidence=0.9)  # type: ignore[arg-type]

    def test_identity_age_rejects_non_integral_float(self):
        """D6 safety rail: 32.5 must reject (user can't be 32.5 years old
        in this context; must be a whole number).
        """
        with pytest.raises(ValidationError):
            IdentityExtraction(age=32.5, confidence=0.9)  # type: ignore[arg-type]

    def test_identity_requires_at_least_one_field(self):
        """AC-T2.2.1 supporting guard: empty identity extraction rejected."""
        with pytest.raises(ValidationError):
            IdentityExtraction(confidence=0.9)


class TestPhoneValidation:
    def test_phone_e164_parse_on_voice(self):
        """AC-T2.2.1: voice preference phone parsed via phonenumbers."""
        model = PhoneExtraction(
            phone_preference="voice",
            phone="+14155552671",
            confidence=0.95,
        )
        assert model.phone == "+14155552671"

    def test_phone_invalid_format_rejected_on_voice(self):
        with pytest.raises(ValidationError):
            PhoneExtraction(
                phone_preference="voice",
                phone="not-a-number",
                confidence=0.95,
            )

    def test_phone_missing_on_voice_rejected(self):
        with pytest.raises(ValidationError):
            PhoneExtraction(phone_preference="voice", confidence=0.95)

    def test_phone_text_no_phone_valid(self):
        model = PhoneExtraction(phone_preference="text", confidence=0.95)
        assert model.phone is None

    def test_phone_e164_normalizes_us_format(self):
        """Parser normalizes to E.164 canonical form."""
        model = PhoneExtraction(
            phone_preference="voice",
            phone="+1 415-555-2671",
            confidence=0.9,
        )
        assert model.phone == "+14155552671"


# ---------------------------------------------------------------------------
# AC-T2.2.2 — confidence bounds on every schema
# ---------------------------------------------------------------------------


class TestConfidenceBounds:
    @pytest.mark.parametrize(
        "schema_factory",
        [
            lambda c: LocationExtraction(city="Zurich", confidence=c),
            lambda c: SceneExtraction(scene="techno", confidence=c),
            lambda c: DarknessExtraction(drug_tolerance=3, confidence=c),
            lambda c: IdentityExtraction(name="Simon", confidence=c),
            lambda c: BackstoryExtraction(
                chosen_option_id="abcdef012345",
                cache_key="zurich|techno|3|tech|unknown|twenties|tech",
                confidence=c,
            ),
            lambda c: PhoneExtraction(phone_preference="text", confidence=c),
        ],
    )
    def test_confidence_out_of_range_422(self, schema_factory):
        """AC-T2.2.2: confidence > 1.0 rejected on every schema."""
        with pytest.raises(ValidationError):
            schema_factory(1.1)

    @pytest.mark.parametrize(
        "schema_factory",
        [
            lambda c: LocationExtraction(city="Zurich", confidence=c),
            lambda c: SceneExtraction(scene="techno", confidence=c),
            lambda c: DarknessExtraction(drug_tolerance=3, confidence=c),
            lambda c: IdentityExtraction(name="Simon", confidence=c),
            lambda c: PhoneExtraction(phone_preference="text", confidence=c),
        ],
    )
    def test_confidence_negative_rejected(self, schema_factory):
        with pytest.raises(ValidationError):
            schema_factory(-0.01)

    def test_confidence_boundary_zero_accepted(self):
        assert LocationExtraction(city="Zurich", confidence=0.0).confidence == 0.0

    def test_confidence_boundary_one_accepted(self):
        assert LocationExtraction(city="Zurich", confidence=1.0).confidence == 1.0


# ---------------------------------------------------------------------------
# AC-T2.2.3 — ConverseResult union round-trip
# ---------------------------------------------------------------------------


class TestConverseResultUnion:
    def test_converse_result_union_round_trip(self):
        """AC-T2.2.3: all 7 branches serialize and deserialize faithfully."""
        adapter = TypeAdapter(ConverseResult)
        cases = [
            LocationExtraction(city="Zurich", confidence=0.9),
            SceneExtraction(scene="techno", confidence=0.9),
            DarknessExtraction(drug_tolerance=3, confidence=0.9),
            IdentityExtraction(name="Simon", confidence=0.9),
            BackstoryExtraction(
                chosen_option_id="abcdef012345",
                cache_key="zurich|techno|3|tech|unknown|twenties|tech",
                confidence=0.9,
            ),
            PhoneExtraction(phone_preference="text", confidence=0.9),
            NoExtraction(reason="off_topic"),
        ]
        for original in cases:
            dumped = adapter.dump_python(original)
            restored = adapter.validate_python(dumped)
            assert type(restored) is type(original), (
                f"{type(original).__name__} did not round-trip"
            )
            assert restored == original

    def test_union_rejects_unknown_kind(self):
        adapter = TypeAdapter(ConverseResult)
        with pytest.raises(ValidationError):
            adapter.validate_python({"kind": "bogus", "confidence": 0.9})

    def test_location_extraction_city_min_length(self):
        with pytest.raises(ValidationError):
            LocationExtraction(city="Z", confidence=0.9)

    def test_backstory_cache_key_pattern_enforced(self):
        with pytest.raises(ValidationError):
            BackstoryExtraction(
                chosen_option_id="abcdef012345",
                cache_key="INVALID UPPERCASE SPACE",
                confidence=0.9,
            )

    def test_backstory_chosen_option_id_pattern_enforced(self):
        with pytest.raises(ValidationError):
            BackstoryExtraction(
                chosen_option_id="not-hex!",
                cache_key="valid|key",
                confidence=0.9,
            )

    def test_darkness_bounds(self):
        with pytest.raises(ValidationError):
            DarknessExtraction(drug_tolerance=0, confidence=0.9)
        with pytest.raises(ValidationError):
            DarknessExtraction(drug_tolerance=6, confidence=0.9)
