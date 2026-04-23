"""Deterministic phone-number fallback for Spec 214 FR-11d AC-11d.4.

When the Pydantic AI agent emits the wrong extraction kind for phone-like
input (e.g. returns ``IdentityExtraction`` for "+1 415 555 0234"), this
module provides ``regex_phone_fallback`` — the deterministic recovery path
mandated by ``.claude/rules/agentic-design-patterns.md`` Hard Rule §5
(Validation layering, deterministic post-processing).

Design:
- Extract a candidate E.164 string from ``user_input`` via regex.
- Validate and normalize using ``PhoneExtraction._phone_format`` — the
  canonical validator from ``extraction_schemas.py``.  Single source of
  truth; no duplicated E.164 logic.
- Return ``SlotDelta(kind="phone", ...)`` or ``None``:
  - ``None`` if no E.164-like candidate is found.
  - ``None`` if the phone slot is already filled in ``slots`` (no-op, avoids
    overwriting a confirmed LLM extraction with a regex guess).
  - ``SlotDelta`` with ``phone_preference="voice"`` and the normalized
    phone string on success.

Wiring into POST /converse handler is T11 (PR-B scope).  This module is
standalone: import and call directly from the handler once T11 ships.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from nikita.agents.onboarding.extraction_schemas import PhoneExtraction
from nikita.agents.onboarding.state import SlotDelta, WizardSlots

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# E.164 candidate pattern — strips dashes/spaces/parens, requires leading +
# ---------------------------------------------------------------------------

# Matches a "+" followed by 7-15 digits with optional separators.
# Deliberately strict: must start with "+" so bare digit strings like "25"
# (age substrings) are never confused with international numbers.
_E164_PATTERN = re.compile(
    r"\+\d[\d\s\-().]{6,18}\d"  # + then 7-15 more digits (with optional separators)
)


def regex_phone_fallback(
    user_input: str | None,
    slots: WizardSlots,
) -> SlotDelta | None:
    """Try to extract an E.164 phone number from raw ``user_input``.

    Recovery path for when the LLM emits the wrong extraction kind on a turn
    that contains a phone number (AC-11d.4 + agentic-design-patterns §5).

    Args:
        user_input: Raw user message text (may be None or empty).
        slots: Current cumulative WizardSlots.  If the phone slot is already
               filled, returns ``None`` immediately (no-op).

    Returns:
        ``SlotDelta(kind="phone", data={"phone_preference": "voice",
        "phone": "<e164>"})`` on successful extraction,
        or ``None`` if no valid phone is found or slot is already filled.
    """
    # No-op: phone slot already filled — do not override a confirmed extraction.
    if slots.phone is not None:
        return None

    if not user_input:
        return None

    # Find a candidate E.164-like string in the input.
    match = _E164_PATTERN.search(user_input)
    if match is None:
        return None

    candidate = match.group(0)

    # Normalize via PhoneExtraction._phone_format — single source of truth.
    # This validator strips spaces/dashes and uses phonenumbers.parse for
    # canonical E.164 formatting.
    try:
        normalized = PhoneExtraction._phone_format(candidate)  # type: ignore[call-arg]
    except (ValueError, Exception):
        return None

    if normalized is None:
        return None

    return SlotDelta(
        kind="phone",
        data={
            "phone_preference": "voice",
            "phone": normalized,
        },
    )


__all__ = ["regex_phone_fallback"]
