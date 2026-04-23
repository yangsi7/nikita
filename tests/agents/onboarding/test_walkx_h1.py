"""Walk X H1 regression tests — GH #406.

Bug: contact_preference="voice" input on turn 5 triggers unrecoverable wedge.
Root cause: PhoneExtraction._voice_requires_phone model_validator requires
phone when phone_preference="voice", even on a preference-only turn before
the user has provided their phone number.  LLM emits
PhoneExtraction(phone_preference="voice", phone=None) -> Pydantic internal
ValidationError -> retries=4 exhausted -> UnexpectedModelBehavior ->
FALLBACK_REPLY ("hold on, let me try that again.") -> wizard wedged.

Fix direction: relax PhoneExtraction to allow phone_preference="voice" with
phone=None.  The phone-number requirement must only fire at the FinalForm
completion gate (state.py), not at the per-turn extraction schema level.

TDD: T1 tests written BEFORE implementation (RED phase).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nikita.agents.onboarding.extraction_schemas import PhoneExtraction


# ---------------------------------------------------------------------------
# T1-A: PhoneExtraction allows voice preference with no phone (per-turn turn)
# ---------------------------------------------------------------------------


class TestPhoneExtractionVoicePreference:
    """PhoneExtraction schema must NOT require phone on preference-only turns.

    The schema is used per-turn: when the user says 'voice', the LLM emits
    PhoneExtraction(phone_preference='voice', phone=None).  This is a valid
    two-step flow: first the user declares preference, then provides the number.

    The FinalForm completion gate (state.py) is responsible for requiring phone
    when preference is 'voice' — not the per-turn extraction schema.
    """

    def test_voice_preference_with_no_phone_is_valid(self):
        """T1-A-1: PhoneExtraction(phone_preference='voice', phone=None)
        must validate successfully.

        This test FAILS on master (before fix) because _voice_requires_phone
        model_validator raises ValueError when phone is None.
        """
        # This should NOT raise ValidationError after the fix.
        extraction = PhoneExtraction(phone_preference="voice", phone=None, confidence=0.9)
        assert extraction.phone_preference == "voice"
        assert extraction.phone is None

    def test_text_preference_with_no_phone_is_valid(self):
        """T1-A-2: text preference with no phone is valid (unchanged behavior)."""
        extraction = PhoneExtraction(phone_preference="text", phone=None, confidence=0.9)
        assert extraction.phone_preference == "text"
        assert extraction.phone is None

    def test_voice_preference_with_phone_is_valid(self):
        """T1-A-3: voice + phone provided is valid (unchanged behavior)."""
        extraction = PhoneExtraction(
            phone_preference="voice",
            phone="+14155552671",
            confidence=0.9,
        )
        assert extraction.phone_preference == "voice"
        assert extraction.phone == "+14155552671"

    def test_text_preference_with_phone_still_valid(self):
        """T1-A-4: text + phone is valid edge case (user changed mind, no harm)."""
        extraction = PhoneExtraction(
            phone_preference="text",
            phone="+14155552671",
            confidence=0.9,
        )
        assert extraction.phone_preference == "text"
        assert extraction.phone == "+14155552671"

    def test_invalid_phone_format_still_rejected(self):
        """T1-A-5: E.164 format validation on phone field is unchanged.

        The fix must NOT remove the E.164 validator on the phone field itself.
        """
        with pytest.raises(ValidationError) as exc_info:
            PhoneExtraction(phone_preference="voice", phone="not-a-phone", confidence=0.9)
        errors = exc_info.value.errors()
        assert any("phone" in str(err["loc"]) for err in errors)

    def test_voice_preference_confidence_bounds_preserved(self):
        """T1-A-6: confidence validation unaffected by the fix."""
        with pytest.raises(ValidationError):
            PhoneExtraction(phone_preference="voice", phone=None, confidence=1.5)
        with pytest.raises(ValidationError):
            PhoneExtraction(phone_preference="voice", phone=None, confidence=-0.1)


# ---------------------------------------------------------------------------
# T1-B: FinalForm still requires phone when voice preference is declared
# ---------------------------------------------------------------------------


class TestFinalFormVoiceRequiresPhone:
    """FinalForm completion gate must still enforce voice->phone requirement.

    After relaxing PhoneExtraction, the phone requirement for voice must
    be enforced at the FinalForm level (state.py), not at the extraction level.
    """

    def test_final_form_rejects_voice_with_no_phone(self):
        """T1-B-1: FinalForm.model_validate() raises if voice+no-phone.

        This verifies the constraint moved from extraction schema to FinalForm.
        """
        from nikita.agents.onboarding.state import FinalForm

        with pytest.raises(ValidationError) as exc_info:
            FinalForm.model_validate({
                "location": {"city": "Berlin", "confidence": 0.9},
                "scene": {"scene": "techno", "confidence": 0.9},
                "darkness": {"drug_tolerance": 3, "confidence": 0.9},
                "identity": {"name": "Max", "age": 28, "occupation": "designer", "confidence": 0.9},
                "backstory": {"chosen_option_id": "aabbccddeeff", "cache_key": "berlin-techno", "confidence": 0.9},
                "phone": {"phone_preference": "voice", "phone": None, "confidence": 0.9},
            })
        # ValidationError must reference phone/voice constraint
        errors = exc_info.value.errors()
        error_msgs = " ".join(str(e) for e in errors)
        assert "voice" in error_msgs.lower() or "phone" in error_msgs.lower()

    def test_final_form_accepts_voice_with_phone(self):
        """T1-B-2: FinalForm.model_validate() succeeds if voice+phone provided."""
        from nikita.agents.onboarding.state import FinalForm

        form = FinalForm.model_validate({
            "location": {"city": "Berlin", "confidence": 0.9},
            "scene": {"scene": "techno", "confidence": 0.9},
            "darkness": {"drug_tolerance": 3, "confidence": 0.9},
            "identity": {"name": "Max", "age": 28, "occupation": "designer", "confidence": 0.9},
            "backstory": {"chosen_option_id": "aabbccddeeff", "cache_key": "berlin-techno", "confidence": 0.9},
            "phone": {"phone_preference": "voice", "phone": "+14155552671", "confidence": 0.9},
        })
        assert form.phone["phone_preference"] == "voice"
        assert form.phone["phone"] == "+14155552671"

    def test_final_form_accepts_text_with_no_phone(self):
        """T1-B-3: FinalForm.model_validate() succeeds if text+no-phone."""
        from nikita.agents.onboarding.state import FinalForm

        form = FinalForm.model_validate({
            "location": {"city": "Berlin", "confidence": 0.9},
            "scene": {"scene": "techno", "confidence": 0.9},
            "darkness": {"drug_tolerance": 3, "confidence": 0.9},
            "identity": {"name": "Max", "age": 28, "occupation": "designer", "confidence": 0.9},
            "backstory": {"chosen_option_id": "aabbccddeeff", "cache_key": "berlin-techno", "confidence": 0.9},
            "phone": {"phone_preference": "text", "phone": None, "confidence": 0.9},
        })
        assert form.phone["phone_preference"] == "text"
