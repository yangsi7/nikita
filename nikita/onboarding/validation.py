"""Shared validation utilities for onboarding inputs (PR-2 / GH #198).

Both entry points must use this module — the portal profile API
(`nikita/api/routes/onboarding.py`) and the Telegram text-onboarding
fallback (`nikita/platforms/telegram/onboarding/handler.py`) — to keep
rejection rules consistent across platforms.
"""

from __future__ import annotations

import re
import unicodedata

# Swiss default country code for phone normalization.
# Value: "41" (Switzerland, ITU-T E.164 country code)
# Prior values: none — new in Spec 212 PR B (GH #TBD, 2026-04-13)
# Rationale: Nikita's primary user base is Swiss; bare 9/10-digit numbers
#   without an explicit country prefix are inferred to be Swiss mobile numbers.
#   E.g. "791234567" → "+41791234567", "0791234567" → "+41791234567".
#   Non-Swiss numbers supplied with a leading "+" pass through unchanged.
#   Changing this value requires updating the regression test in
#   tests/onboarding/test_phone_validation.py::TestDefaultCountryCode
#   and the tuning-constants comment above.
DEFAULT_COUNTRY_CODE = "41"

# E.164 pattern: "+" followed by 1-9 (no leading zero in country code),
# then 7-19 more digits. Total: 8–20 characters including "+".
_E164_REGEX = re.compile(r"^\+[1-9][0-9]{7,19}$")

# Characters to strip before E.164 validation: spaces, dashes, parentheses.
_STRIP_PATTERN = re.compile(r"[\s\-\(\)]")

# Small blocklist of obvious placeholder inputs. Covers the concrete cases
# that leaked through prior validation (issue #198 caught "hey"). Keep this
# narrow: legitimate city names like "Nice" or "York" must still pass.
#
# Known false-positives we're deliberately accepting:
#   - "bar" → Bar, Montenegro (pop. ~17k). Affected users can enter
#     "Bar, Montenegro" or similar disambiguation and the rule will pass.
_JUNK_WORDS = frozenset(
    {
        "hey",
        "hi",
        "test",
        "asdf",
        "foo",
        "bar",
        "none",
        "na",
        "n/a",
        "xxx",
    }
)

_MIN_LENGTH = 2
_MAX_LENGTH = 100


def validate_city(raw: str) -> str:
    """Validate and normalize a user-supplied city name.

    Rules (applied in order):
    1. Reject if ``raw`` is falsy.
    2. Strip leading/trailing whitespace.
    3. Reject if any character is a Unicode control (Cc) or format (Cf)
       char — catches NUL bytes, bells, zero-width spaces, etc.
    4. Collapse runs of 3 or more ASCII spaces into a single space (keeps
       normal "New York" / double-space typos intact).
    5. Enforce length between ``_MIN_LENGTH`` and ``_MAX_LENGTH`` chars.
    6. Reject purely numeric input (e.g. ``"12345"``, ``"0"``).
    7. Reject if the lowercased value matches the junk-word blocklist.

    Args:
        raw: The raw user input.

    Returns:
        The normalized city name.

    Raises:
        ValueError: If the input fails any of the rules above. The message
            is safe to surface to end users.
    """
    if not raw:
        raise ValueError("City cannot be blank")

    # Strip only ASCII whitespace + common Unicode space separators at the
    # edges. Python's default ``str.strip()`` additionally eats control
    # chars like ``\x1f``, which would hide them from the control-char
    # check below — strip them explicitly instead. The explicit set also
    # covers NBSP (``\u00a0``) and narrow no-break space (``\u202f``) which
    # users sometimes paste from websites or rich-text clients.
    v = raw.strip(" \t\n\r\v\f\u00a0\u2007\u202f")

    if any(unicodedata.category(c) in ("Cc", "Cf") for c in v):
        raise ValueError("City contains invalid characters")

    v = re.sub(r" {3,}", " ", v)

    if len(v) < _MIN_LENGTH or len(v) > _MAX_LENGTH:
        raise ValueError(
            f"City must be {_MIN_LENGTH}-{_MAX_LENGTH} characters"
        )

    if re.fullmatch(r"\d+", v):
        raise ValueError("City cannot be purely numeric")

    if v.lower() in _JUNK_WORDS:
        raise ValueError("Please enter a real city name")

    return v


def validate_phone(raw: str | None) -> str | None:
    """Validate and normalize a phone number to E.164 format.

    Returns None for empty/None input (phone is optional in portal profile).
    Infers Swiss country code (+41) for bare 9-digit or 0-prefixed 10-digit
    numbers. Non-Swiss numbers must include a leading "+".

    Rules (applied in order):
    1. Return None if ``raw`` is None or blank (empty/whitespace-only).
    2. Strip formatting characters: spaces, dashes, parentheses.
    3. Infer +41 for 9-digit bare numbers (e.g. "791234567" → "+41791234567").
    4. Infer +41 for 10-digit leading-zero numbers (e.g. "0791234567" → "+41791234567").
    5. Reject if result does not start with "+".
    6. Reject if result does not match the E.164 regex.

    Args:
        raw: The raw user-supplied phone string, or None.

    Returns:
        Normalized E.164 phone string, or None if input is blank/None.

    Raises:
        ValueError: If the input is non-blank but fails E.164 validation.
            The message is safe to surface in API error responses.
    """
    if not raw or not raw.strip():
        return None

    # Strip spaces, dashes, parentheses
    cleaned = _STRIP_PATTERN.sub("", raw.strip())

    # Swiss inference: bare 9-digit number (e.g. "791234567")
    if re.match(r"^[1-9][0-9]{8}$", cleaned):
        cleaned = f"+{DEFAULT_COUNTRY_CODE}{cleaned}"
    # Swiss inference: 10-digit with leading zero (e.g. "0791234567")
    elif re.match(r"^0[1-9][0-9]{8}$", cleaned):
        cleaned = f"+{DEFAULT_COUNTRY_CODE}{cleaned[1:]}"

    if not cleaned.startswith("+"):
        raise ValueError(
            f"Phone number must start with '+' and include a country code. Got: {cleaned!r}"
        )

    if not _E164_REGEX.match(cleaned):
        raise ValueError(
            f"Phone number is not valid E.164 format (e.g. +41791234567). Got: {cleaned!r}"
        )

    return cleaned
