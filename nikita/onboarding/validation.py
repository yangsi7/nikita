"""Shared validation utilities for onboarding inputs (PR-2 / GH #198).

Both entry points must use this module — the portal profile API
(`nikita/api/routes/onboarding.py`) and the Telegram text-onboarding
fallback (`nikita/platforms/telegram/onboarding/handler.py`) — to keep
rejection rules consistent across platforms.
"""

from __future__ import annotations

import re
import unicodedata

# Small blocklist of obvious placeholder inputs. Covers the concrete cases
# that leaked through prior validation (issue #198 caught "hey"). Keep this
# narrow: legitimate city names like "Nice" or "York" must still pass.
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
