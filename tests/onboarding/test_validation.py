"""Tests for nikita.onboarding.validation (PR-2 / GH #198).

Covers:
- Accept real city names (incl. unicode + multi-word)
- Reject blank / whitespace-only / too-short / too-long / pure-numeric / junk words
- Reject control characters and format/zero-width characters
- Normalize runs of 3+ spaces to a single space
"""

import pytest

from nikita.onboarding.validation import validate_city


class TestValidateCityAccepts:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Zurich", "Zurich"),
            ("New York", "New York"),
            ("LA", "LA"),  # short but legit abbreviation
            ("São Paulo", "São Paulo"),  # unicode letters
            ("Saint-Étienne", "Saint-Étienne"),  # hyphen + accent
            ("  Berlin  ", "Berlin"),  # trim whitespace
            ("New    York", "New York"),  # collapse 4 spaces to 1
            ("City  With  Spaces", "City  With  Spaces"),  # 2 spaces preserved
        ],
    )
    def test_accepts_valid_cities(self, raw: str, expected: str) -> None:
        assert validate_city(raw) == expected


class TestValidateCityRejects:
    @pytest.mark.parametrize(
        "raw",
        [
            "",  # empty
            "   ",  # whitespace only
            "a",  # too short after strip
            "x" * 101,  # too long
            "12345",  # pure numeric
            "0",  # single digit
        ],
    )
    def test_rejects_structural_violations(self, raw: str) -> None:
        with pytest.raises(ValueError):
            validate_city(raw)

    @pytest.mark.parametrize(
        "raw",
        [
            "hey",
            "HEY",  # case-insensitive
            "hi",
            "test",
            "asdf",
            "foo",
            "bar",
            "none",
            "na",
            "n/a",
            "xxx",
        ],
    )
    def test_rejects_junk_words(self, raw: str) -> None:
        with pytest.raises(ValueError, match="real city"):
            validate_city(raw)

    @pytest.mark.parametrize(
        "raw",
        [
            "Zurich\x00",  # null byte
            "Zurich\x1f",  # unit separator
            "Zurich\u200b",  # zero-width space (format char)
            "\x07Berlin",  # bell
        ],
    )
    def test_rejects_control_characters(self, raw: str) -> None:
        with pytest.raises(ValueError, match="invalid characters"):
            validate_city(raw)
