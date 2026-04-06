"""Tests for PII masking utilities (SEC-005).

Ensures phone numbers are masked in log output to prevent PII leakage.
"""

import pytest

from nikita.utils.masking import mask_phone


class TestMaskPhone:
    """Test mask_phone utility."""

    def test_full_e164_number(self):
        """Full E.164 number masks all but last 4 digits."""
        assert mask_phone("+41787950009") == "***0009"

    def test_us_number(self):
        """US E.164 number masks correctly."""
        assert mask_phone("+12025551234") == "***1234"

    def test_short_number(self):
        """Numbers <= 4 chars get *** prefix."""
        assert mask_phone("1234") == "***1234"

    def test_very_short_number(self):
        """Very short numbers get *** prefix."""
        assert mask_phone("12") == "***12"

    def test_empty_string(self):
        """Empty string returns ***."""
        assert mask_phone("") == "***"

    def test_five_digit_number(self):
        """5-digit number shows last 4."""
        assert mask_phone("12345") == "***2345"
