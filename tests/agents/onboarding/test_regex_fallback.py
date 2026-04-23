"""Tests for nikita.agents.onboarding.regex_fallback.

AC coverage:
- AC-11d.4: regex_phone_fallback — E.164 happy path, rejects age-substring,
  returns None when phone slot already filled (no-op), reuses
  PhoneExtraction._phone_format logic for normalization.

Agentic-Flow mandatory test class 3 (testing.md §"Agentic-Flow Test
Requirements"): mock-LLM-emits-wrong-tool recovery — the fallback is the
deterministic recovery path when the agent returns IdentityExtraction
for phone-like input instead of PhoneExtraction.

Scenarios:
1. E.164 happy path — valid US phone string normalizes to E.164.
2. International number — valid non-US phone normalizes correctly.
3. Age substring rejection — string like "25" must NOT be treated as phone.
4. Non-numeric junk — rejected, returns None.
5. Already-filled slot — phone slot already in WizardSlots, returns None.
6. None input — returns None gracefully.
7. Voice preference requires phone (round-trip: fallback returns a PhoneSlot).
8. Text preference with no phone — None phone is valid.
"""

from __future__ import annotations

import pytest


def _import_fallback():
    from nikita.agents.onboarding.regex_fallback import (  # noqa: PLC0415
        regex_phone_fallback,
    )
    return regex_phone_fallback


def _import_state():
    from nikita.agents.onboarding.state import SlotDelta, WizardSlots  # noqa: PLC0415
    return SlotDelta, WizardSlots


# ---------------------------------------------------------------------------
# Mock-LLM-emits-wrong-tool recovery (Agentic-Flow mandatory test class 3)
# ---------------------------------------------------------------------------


class TestRegexPhoneFallbackRecovery:
    """Verify regex_phone_fallback is the deterministic recovery path.

    Scenario: LLM emits IdentityExtraction for "+1 415 555 0234" input
    instead of PhoneExtraction.  The fallback scans the raw user_input
    and recovers the phone number, preventing slot miss.
    """

    def test_recovery_from_phone_in_identity_input(self):
        """Fallback extracts phone when LLM returned wrong extraction kind."""
        regex_phone_fallback = _import_fallback()
        SlotDelta, WizardSlots = _import_state()
        # Simulate state where LLM returned IdentityExtraction for phone input
        # Phone slot is not yet filled
        slots = WizardSlots()
        result = regex_phone_fallback("+14155550234", slots)
        # Should return a SlotDelta with kind="phone"
        assert result is not None
        assert result.kind == "phone"
        assert result.data.get("phone") is not None

    def test_recovery_produces_normalized_e164(self):
        """Recovered phone is in E.164 format (+country code no spaces)."""
        regex_phone_fallback = _import_fallback()
        SlotDelta, WizardSlots = _import_state()
        slots = WizardSlots()
        result = regex_phone_fallback("+1 415 555 0234", slots)
        assert result is not None
        phone = result.data.get("phone")
        assert phone is not None
        assert phone.startswith("+")
        assert " " not in phone  # no spaces in E.164


# ---------------------------------------------------------------------------
# E.164 happy paths
# ---------------------------------------------------------------------------


class TestRegexPhoneFallbackHappyPaths:
    def test_valid_us_phone_no_spaces(self):
        """Compact E.164 US number is extracted."""
        regex_phone_fallback = _import_fallback()
        _, WizardSlots = _import_state()
        slots = WizardSlots()
        result = regex_phone_fallback("+14155550234", slots)
        assert result is not None
        assert result.kind == "phone"

    def test_valid_us_phone_with_spaces(self):
        """E.164 with spaces is normalized (spaces stripped)."""
        regex_phone_fallback = _import_fallback()
        _, WizardSlots = _import_state()
        slots = WizardSlots()
        result = regex_phone_fallback("+1 415 555 0234", slots)
        assert result is not None
        assert " " not in result.data.get("phone", "")

    def test_valid_de_international_number(self):
        """German international number is accepted."""
        regex_phone_fallback = _import_fallback()
        _, WizardSlots = _import_state()
        slots = WizardSlots()
        result = regex_phone_fallback("+4915123456789", slots)
        assert result is not None
        assert result.kind == "phone"

    def test_valid_uk_number_with_dashes(self):
        """UK number with dashes is normalized."""
        regex_phone_fallback = _import_fallback()
        _, WizardSlots = _import_state()
        slots = WizardSlots()
        # +44 7911 123456
        result = regex_phone_fallback("+44 7911 123456", slots)
        assert result is not None
        assert result.kind == "phone"
        phone = result.data.get("phone", "")
        assert phone.startswith("+44")


# ---------------------------------------------------------------------------
# Rejection cases
# ---------------------------------------------------------------------------


class TestRegexPhoneFallbackRejects:
    def test_age_substring_not_extracted_as_phone(self):
        """Short digit string like '25' must NOT be mistaken for a phone."""
        regex_phone_fallback = _import_fallback()
        _, WizardSlots = _import_state()
        slots = WizardSlots()
        result = regex_phone_fallback("25", slots)
        assert result is None, "age '25' should not be extracted as a phone"

    def test_bare_digits_without_country_code_rejected(self):
        """Numbers without + country code are not treated as E.164."""
        regex_phone_fallback = _import_fallback()
        _, WizardSlots = _import_state()
        slots = WizardSlots()
        result = regex_phone_fallback("4155550234", slots)
        assert result is None

    def test_junk_string_returns_none(self):
        """Non-phone gibberish returns None."""
        regex_phone_fallback = _import_fallback()
        _, WizardSlots = _import_state()
        slots = WizardSlots()
        result = regex_phone_fallback("I like techno", slots)
        assert result is None

    def test_none_input_returns_none(self):
        """None input is handled gracefully without error."""
        regex_phone_fallback = _import_fallback()
        _, WizardSlots = _import_state()
        slots = WizardSlots()
        result = regex_phone_fallback(None, slots)  # type: ignore[arg-type]
        assert result is None

    def test_empty_string_returns_none(self):
        """Empty string returns None."""
        regex_phone_fallback = _import_fallback()
        _, WizardSlots = _import_state()
        slots = WizardSlots()
        result = regex_phone_fallback("", slots)
        assert result is None


# ---------------------------------------------------------------------------
# Already-filled slot — no-op
# ---------------------------------------------------------------------------


class TestRegexPhoneFallbackNoOp:
    def test_phone_slot_already_filled_returns_none(self):
        """If phone slot is already filled, fallback is a no-op (returns None).

        This prevents overwriting a confirmed LLM extraction with a regex guess.
        """
        regex_phone_fallback = _import_fallback()
        SlotDelta, WizardSlots = _import_state()
        # Fill phone slot
        slots = WizardSlots()
        slots = slots.apply(
            SlotDelta(
                kind="phone",
                data={"phone_preference": "text", "phone": None},
            )
        )
        assert slots.phone is not None  # slot is filled
        # Even with a valid phone string, fallback must return None
        result = regex_phone_fallback("+14155550234", slots)
        assert result is None, "fallback must not override a filled phone slot"

    def test_other_slots_filled_does_not_block_fallback(self):
        """Filling non-phone slots does not suppress phone fallback."""
        regex_phone_fallback = _import_fallback()
        SlotDelta, WizardSlots = _import_state()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="location", data={"city": "NYC"}))
        # Phone slot is NOT filled yet; fallback should work
        result = regex_phone_fallback("+14155550234", slots)
        assert result is not None
        assert result.kind == "phone"


# ---------------------------------------------------------------------------
# phone_preference field
# ---------------------------------------------------------------------------


class TestRegexPhoneFallbackPreference:
    def test_result_includes_phone_preference_voice(self):
        """SlotDelta data includes phone_preference='voice' for a number."""
        regex_phone_fallback = _import_fallback()
        _, WizardSlots = _import_state()
        slots = WizardSlots()
        result = regex_phone_fallback("+14155550234", slots)
        assert result is not None
        assert result.data.get("phone_preference") == "voice"

    def test_result_slot_delta_kind_is_phone(self):
        """SlotDelta.kind must be 'phone' (not 'identity' or other kind)."""
        regex_phone_fallback = _import_fallback()
        _, WizardSlots = _import_state()
        slots = WizardSlots()
        result = regex_phone_fallback("+14155550234", slots)
        assert result is not None
        assert result.kind == "phone"
