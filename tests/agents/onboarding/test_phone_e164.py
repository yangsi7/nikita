"""Tests for phone E.164 validator (closes GH #490, Walk A1 M4).

Per .claude/rules/agentic-design-patterns.md Hard Rule §5: deterministic
post-processor for the phone slot. Three test classes:
  1. Valid E.164 + valid-after-formatting-strip happy paths
  2. Invalid shapes that MUST be rejected
  3. Idempotence + edge cases (Unicode whitespace, NBSP, empty/None)
"""

from __future__ import annotations

import pytest

from nikita.agents.onboarding.validators import (
    is_valid_phone_e164,
    normalize_phone_e164,
)


class TestValidE164Inputs:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            # Already canonical
            ("+14155550100", "+14155550100"),
            ("+447400123456", "+447400123456"),  # UK mobile
            ("+41441234567", "+41441234567"),    # Swiss landline
            ("+819012345678", "+819012345678"),  # Japan mobile
            # Common human-formatted variants (formatting stripped)
            ("+1 415 555 0100", "+14155550100"),
            ("+1-415-555-0100", "+14155550100"),
            ("+1.415.555.0100", "+14155550100"),
            ("+1 (415) 555-0100", "+14155550100"),
            ("  +14155550100  ", "+14155550100"),
        ],
    )
    def test_valid_inputs_canonicalize(self, raw: str, expected: str) -> None:
        assert normalize_phone_e164(raw) == expected
        assert is_valid_phone_e164(raw) is True


class TestInvalidInputsRejected:
    @pytest.mark.parametrize(
        "raw",
        [
            None,
            "",
            "   ",
            "abc",
            "abc123",
            "12345",                # no leading +
            "415-555-0100",         # domestic, no country code
            "+0 415 555 0100",      # leading 0 in country code
            "+1",                   # too short
            "+12345",               # 5 digits, below minimum 7
            "+12 34 56",            # 6 digits, below minimum 7
            "+1234567890123456",    # 16 digits, above max 15
            "+1 (415) 555-0100 ext. 5",  # extension not E.164
            "555-0100",             # subscriber-only
            "tel:+14155550100",     # URI scheme
            "+1 abc 555 0100",      # mixed alpha
        ],
    )
    def test_invalid_inputs_return_none(self, raw: str | None) -> None:
        assert normalize_phone_e164(raw) is None
        assert is_valid_phone_e164(raw) is False


class TestEdgeCases:
    def test_idempotent(self) -> None:
        canonical = normalize_phone_e164("+1 415 555 0100")
        assert canonical == "+14155550100"
        assert normalize_phone_e164(canonical) == canonical

    def test_nbsp_treated_as_whitespace(self) -> None:
        # Some keyboards emit NBSP via shift-space. Validator should strip it.
        raw = "+1 415 555 0100"
        assert normalize_phone_e164(raw) == "+14155550100"

    def test_minimum_length_boundary(self) -> None:
        # 7 digits total → ok; 6 digits → reject
        assert normalize_phone_e164("+1234567") == "+1234567"
        assert normalize_phone_e164("+123456") is None

    def test_maximum_length_boundary(self) -> None:
        # 15 digits → ok; 16 digits → reject
        assert normalize_phone_e164("+123456789012345") == "+123456789012345"
        assert normalize_phone_e164("+1234567890123456") is None
