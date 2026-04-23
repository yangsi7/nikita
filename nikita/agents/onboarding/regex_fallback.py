"""Deterministic phone-number fallback for Spec 214 FR-11d AC-11d.4.

When the Pydantic AI agent emits the wrong extraction kind for phone-like
input (e.g. returns ``IdentityExtraction`` for "+1 415 555 0234"), this
module provides ``regex_phone_fallback`` — the deterministic recovery path
mandated by ``.claude/rules/agentic-design-patterns.md`` Hard Rule §5
(Validation layering, deterministic post-processing).

Design:
- Extract a candidate E.164 string from ``user_input`` via regex.
- Validate and normalize using ``normalize_phone`` from extraction_schemas —
  the public wrapper around ``PhoneExtraction._phone_format``.  Single source
  of truth; no duplicated E.164 logic.
- Return ``SlotDelta(kind="phone", ...)`` or ``None``:
  - ``None`` if no E.164-like candidate is found.
  - ``None`` if the phone slot is already filled in ``slots`` (no-op, avoids
    overwriting a confirmed LLM extraction with a regex guess).
  - ``SlotDelta`` with ``phone_preference="voice"`` and the normalized
    phone string on success.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from nikita.agents.onboarding.extraction_schemas import normalize_phone
from nikita.agents.onboarding.state import SlotDelta, WizardSlots

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# E.164 candidate pattern — strips dashes/spaces/parens, requires leading +
# ---------------------------------------------------------------------------

# Matches "+" followed by 1-3 country-code digits, then 6-18 chars (digits
# or separators such as spaces/hyphens/dots/parens), ending with a digit.
# The trailing \d requirement reduces false positives on strings ending with
# punctuation.  Normalization is delegated to phonenumbers.parse via
# normalize_phone — the regex is a candidate filter only.
_E164_PATTERN = re.compile(
    r"\+\d{1,3}[\d\s\-().]{6,18}\d"
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

    # Normalize via normalize_phone (public wrapper, single source of truth).
    # Strips separators and uses phonenumbers.parse for canonical E.164.
    normalized = normalize_phone(candidate)

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
