"""Tests for validate_phone in nikita/onboarding/validation.py (Spec 212 PR B).

Table-driven tests covering:
- T010: Phone validation and normalization logic
- DEFAULT_COUNTRY_CODE regression guard (must be "41")

Failing until T014 (validate_phone implementation) is committed.
"""

from __future__ import annotations

import pytest


class TestValidatePhone:
    """Table-driven tests for validate_phone."""

    def test_e164_passthrough(self):
        """Full E.164 Swiss number passes through unchanged."""
        from nikita.onboarding.validation import validate_phone

        assert validate_phone("+41791234567") == "+41791234567"

    def test_nine_digit_bare_swiss_inference(self):
        """9-digit bare number gets +41 prefix inferred."""
        from nikita.onboarding.validation import validate_phone

        assert validate_phone("791234567") == "+41791234567"

    def test_ten_digit_leading_zero_swiss_inference(self):
        """10-digit number starting with 0 strips leading zero and infers +41."""
        from nikita.onboarding.validation import validate_phone

        assert validate_phone("0791234567") == "+41791234567"

    def test_non_swiss_e164_passthrough(self):
        """Non-Swiss E.164 number passes through without modification."""
        from nikita.onboarding.validation import validate_phone

        assert validate_phone("+1234567890") == "+1234567890"

    def test_invalid_raises_value_error(self):
        """Non-numeric junk raises ValueError."""
        from nikita.onboarding.validation import validate_phone

        with pytest.raises(ValueError):
            validate_phone("abc")

    def test_empty_string_returns_none(self):
        """Empty string returns None (skip validation)."""
        from nikita.onboarding.validation import validate_phone

        assert validate_phone("") is None

    def test_whitespace_only_returns_none(self):
        """Whitespace-only string returns None."""
        from nikita.onboarding.validation import validate_phone

        assert validate_phone("   ") is None

    def test_none_returns_none(self):
        """None input returns None (null = skip)."""
        from nikita.onboarding.validation import validate_phone

        assert validate_phone(None) is None

    def test_strips_spaces(self):
        """Spaces are stripped before validation."""
        from nikita.onboarding.validation import validate_phone

        assert validate_phone("+41 79 123 45 67") == "+41791234567"

    def test_strips_dashes_swiss_inference(self):
        """Dashes stripped; 10-digit result with leading 0 gets Swiss inference."""
        from nikita.onboarding.validation import validate_phone

        assert validate_phone("079-123-45-67") == "+41791234567"

    def test_strips_parentheses(self):
        """Parentheses are stripped before validation."""
        from nikita.onboarding.validation import validate_phone

        # After stripping '(', ')': "0791234567" → +41791234567
        assert validate_phone("(079)1234567") == "+41791234567"


class TestDefaultCountryCode:
    """Regression guard for DEFAULT_COUNTRY_CODE constant."""

    def test_default_country_code_is_41(self):
        """DEFAULT_COUNTRY_CODE must equal '41' (Switzerland).

        Regression: GH #<TBD> (Spec 212 PR B). Value must not silently drift.
        Any change requires updating this test AND the tuning-constants comment.
        """
        from nikita.onboarding.validation import DEFAULT_COUNTRY_CODE

        assert DEFAULT_COUNTRY_CODE == "41", (
            f"DEFAULT_COUNTRY_CODE changed from '41' to {DEFAULT_COUNTRY_CODE!r}. "
            "Update the tuning-constants comment, this assertion, and relevant docs."
        )
