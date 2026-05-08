"""Cumulative wizard state models for Spec 216-B1+B2 (B1.beta atomic).

Implements the agentic-design-patterns.md Hard Rules §1 (cumulative
server-side state) and §2 (Pydantic completion gate) for the new
13-slot wizard taxonomy:

  display_name, age, occupation, city, darkness_level, primary_hobbies,
  saturday_morning, geek_out_on, together_we_could, same_weird_if,
  voice_tone_pref, backstory_pick, phone

``WizardSlots`` — mutable accumulator, one optional field per slot.
  - ``apply(delta)`` → immutable update via ``model_copy(update=...)``
  - ``progress_pct`` — ``@computed_field`` of cumulative state
  - ``missing`` — ``@computed_field`` listing unfilled slot names
  - ``slots_dict()`` — plain dict of filled slots for FinalForm.model_validate()
  - ``agent_context_dict()`` — alias for slots_dict (no optional/required split)

``FinalForm`` — Pydantic completion gate. All 13 slots as non-optional
  fields + ``@model_validator(mode="after")`` cross-field business rules:
  age >= MIN_USER_AGE, voice_tone_pref="voice" requires phone,
  primary_hobbies non-empty.

  Usage: ``FinalForm.model_validate(slots.slots_dict())`` raises
  ValidationError on incomplete state. NEVER hardcode True/False.

``SlotDelta`` — lightweight input model for ``WizardSlots.apply()``.
  ``kind`` is a SlotKind StrEnum value (or "no_extraction" sentinel).

``TOTAL_SLOTS: Final[int] = 13``
  Current value: 13 (Spec 216-B1+B2, B1.beta lock-in 2026-05-02).
  Prior values: 6 (Spec 214 FR-11d) — superseded by 13-slot rewrite.
  Set in this rewrite. Do not change without updating FinalForm
  required fields AND the regression test in test_cumulative_state.py.
"""

from __future__ import annotations

from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError, computed_field, model_validator

from nikita.agents.onboarding.question_registry import SlotKind
from nikita.onboarding.tuning import MIN_USER_AGE

# ---------------------------------------------------------------------------
# Tuning constant (regression guard — see tuning-constants.md)
# ---------------------------------------------------------------------------

TOTAL_SLOTS: Final[int] = 13
"""Total wizard slots — one per SlotKind member.

Current value: 13 (Spec 216-B1+B2, B1.beta lock-in 2026-05-02).
Prior values: 6 (Spec 214 FR-11d, tasks-v2.md §T2) — superseded by the
13-slot redesign.

Rationale: 12 visual screens (some combine; together_we_could and
same_weird_if share one) plus identity split into display_name + age +
occupation = 13 distinct data slots.

Changing this requires updating:
  - FinalForm required fields (all 13 must be non-optional)
  - SlotKind enum (must have exactly 13 members)
  - ORDERED_QUESTIONS (must have exactly 13 entries)
  - test_cumulative_state.py::test_total_slots_constant_is_thirteen
"""

# Canonical list of slot names — derived from SlotKind enum (single source of truth).
# Excludes ``identity_pair`` (217-3A.3 FR-10a): it is a route-level pseudo-slot
# that decomposes into ``display_name`` + ``age``; it has no ``WizardSlots``
# field and is never persisted as a slot value.
_ALL_SLOT_NAMES: list[str] = [
    m.value for m in SlotKind if m is not SlotKind.identity_pair
]


# ---------------------------------------------------------------------------
# SlotDelta — input model for WizardSlots.apply()
# ---------------------------------------------------------------------------


class SlotDelta(BaseModel):
    """Represents a single turn's extraction result to merge into WizardSlots.

    ``kind`` must be one of the 13 canonical SlotKind values OR
    ``"no_extraction"`` (sentinel for clarification / off-topic turns).
    ``data`` is a free-form dict of slot-specific fields; the caller is
    responsible for providing valid data shapes. ``apply()`` stores
    ``data`` under the slot key, ignoring ``no_extraction`` turns.
    """

    model_config = ConfigDict(extra="forbid")

    # Allow any SlotKind value or the no_extraction sentinel.
    # Pydantic validates string membership against the enum at parse time.
    kind: str = Field(
        description="One of the 13 SlotKind values, or 'no_extraction' sentinel.",
    )
    data: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_kind(self) -> "SlotDelta":
        if self.kind == "no_extraction":
            return self
        if self.kind not in _ALL_SLOT_NAMES:
            raise ValueError(
                f"SlotDelta.kind {self.kind!r} is not a SlotKind member nor 'no_extraction'"
            )
        return self


# ---------------------------------------------------------------------------
# WizardSlots — cumulative accumulator
# ---------------------------------------------------------------------------


class WizardSlots(BaseModel):
    """Cumulative wizard state — one optional field per slot (13 total).

    Each field is ``None`` until the corresponding extraction is received.
    Merges are IMMUTABLE: ``apply(delta)`` returns a new WizardSlots via
    ``model_copy(update=...)``. Caller must reassign:
    ``slots = slots.apply(delta)``.

    ``progress_pct`` and ``missing`` are ``@computed_field`` derived from
    current cumulative state — never from per-turn extraction. Monotonicity
    is by construction: slots are only added, never removed.

    ``primary_hobbies`` is multi-select (a list of strings inside the data
    dict); other slots store arbitrary dict payloads. The slot dict layout
    is ``{<slot_name>: <data dict carrying canonical fields>}`` — see
    ``slots_dict()`` for the FinalForm-input shape.
    """

    model_config = ConfigDict(extra="forbid")

    # All 13 slots are optional (None until filled). FinalForm enforces
    # non-None at completion time.
    display_name: dict[str, Any] | None = None
    age: dict[str, Any] | None = None
    occupation: dict[str, Any] | None = None
    city: dict[str, Any] | None = None
    darkness_level: dict[str, Any] | None = None
    primary_hobbies: dict[str, Any] | None = None
    saturday_morning: dict[str, Any] | None = None
    geek_out_on: dict[str, Any] | None = None
    together_we_could: dict[str, Any] | None = None
    same_weird_if: dict[str, Any] | None = None
    voice_tone_pref: dict[str, Any] | None = None
    backstory_pick: dict[str, Any] | None = None
    phone: dict[str, Any] | None = None

    @computed_field  # type: ignore[misc]
    @property
    def missing(self) -> list[str]:
        """Slot names not yet filled."""
        return [name for name in _ALL_SLOT_NAMES if getattr(self, name) is None]

    @computed_field  # type: ignore[misc]
    @property
    def progress_pct(self) -> int:
        """Percentage of slots filled (0-100), computed from cumulative state.

        Formula: (TOTAL_SLOTS - len(missing)) / TOTAL_SLOTS * 100.
        Monotonic by construction — slots are only added.
        """
        filled = TOTAL_SLOTS - len(self.missing)
        return min(100, (filled * 100) // TOTAL_SLOTS)

    def apply(self, delta: SlotDelta) -> "WizardSlots":
        """Return a new WizardSlots with ``delta`` merged in.

        ``no_extraction`` turns are silently ignored (state unchanged).
        Duplicate slot applications (same kind twice) overwrite the
        previous value (last-write-wins per slot).
        """
        if delta.kind == "no_extraction":
            return self
        return self.model_copy(update={delta.kind: delta.data})

    def slots_dict(self) -> dict[str, Any]:
        """Return a plain dict of filled slot data for FinalForm.model_validate().

        Includes every slot with non-None value, keyed by slot name.
        """
        result: dict[str, Any] = {}
        for name in _ALL_SLOT_NAMES:
            value = getattr(self, name)
            if value is not None:
                result[name] = value
        return result

    def agent_context_dict(self) -> dict[str, Any]:
        """Alias for ``slots_dict``; the new schema has no optional/required split.

        Retained for API compatibility with callers from the prior 6+2-slot
        schema. Returns the same dict as ``slots_dict()``.
        """
        return self.slots_dict()

    @computed_field  # type: ignore[misc]
    @property
    def is_complete(self) -> bool:
        """Pydantic-only completion gate (B1.2).

        Delegates to ``FinalForm.model_validate(self.slots_dict())`` — the
        canonical single source of truth. NEVER hardcode True or False
        in handler code; use this property instead.

        Note: as a ``@computed_field``, this is re-evaluated on every
        ``model_dump()`` and serialized into the state JSON. Cost is
        negligible at 13 slots (one Pydantic validate, sub-millisecond);
        kept as a computed_field rather than a method so JSONB persistence
        and FE wire payloads carry an explicit completion signal alongside
        the slot blob.
        """
        try:
            FinalForm.model_validate(self.slots_dict())
            return True
        except ValidationError:
            return False


# ---------------------------------------------------------------------------
# FinalForm — Pydantic completion gate (agentic-design-patterns.md §2)
# ---------------------------------------------------------------------------


class FinalForm(BaseModel):
    """Completion gate: all 13 slots as non-optional fields + cross-field rules.

    Usage (handler code):
        try:
            form = FinalForm.model_validate(slots.slots_dict())
            complete = True
        except ValidationError:
            complete = False

    NEVER hardcode ``complete = True`` or ``complete = False`` in handler
    code. The validator IS the gate (Hard Rule §2).

    Cross-field rules:
      - age >= MIN_USER_AGE (18)
      - voice_tone_pref="voice" requires phone non-empty
      - primary_hobbies must be a non-empty list
    """

    model_config = ConfigDict(extra="forbid")  # slots_dict emits exactly the 13 keys

    display_name: dict[str, Any]
    age: dict[str, Any]
    occupation: dict[str, Any]
    city: dict[str, Any]
    darkness_level: dict[str, Any]
    primary_hobbies: dict[str, Any]
    saturday_morning: dict[str, Any]
    geek_out_on: dict[str, Any]
    together_we_could: dict[str, Any]
    same_weird_if: dict[str, Any]
    voice_tone_pref: dict[str, Any]
    backstory_pick: dict[str, Any]
    phone: dict[str, Any]

    @model_validator(mode="after")
    def _age_minimum(self) -> "FinalForm":
        """Enforce age >= MIN_USER_AGE and presence of an age value."""
        age_val = self.age.get("age") if isinstance(self.age, dict) else None
        if age_val is None:
            raise ValueError("age slot must contain an 'age' value")
        if age_val < MIN_USER_AGE:
            raise ValueError(
                f"age must be >= {MIN_USER_AGE}; got {age_val}"
            )
        return self

    @model_validator(mode="after")
    def _voice_requires_phone(self) -> "FinalForm":
        """voice_tone_pref='voice' requires non-empty phone."""
        pref = (
            self.voice_tone_pref.get("voice_tone_pref")
            if isinstance(self.voice_tone_pref, dict)
            else None
        )
        phone_val = self.phone.get("phone") if isinstance(self.phone, dict) else None
        if pref == "voice" and not phone_val:
            raise ValueError(
                "voice_tone_pref='voice' requires a phone number at completion"
            )
        return self

    @model_validator(mode="after")
    def _primary_hobbies_non_empty(self) -> "FinalForm":
        """primary_hobbies must be a non-empty list."""
        hobbies = (
            self.primary_hobbies.get("primary_hobbies")
            if isinstance(self.primary_hobbies, dict)
            else None
        )
        if not isinstance(hobbies, list) or len(hobbies) == 0:
            raise ValueError(
                "primary_hobbies must be a non-empty list of hobby strings"
            )
        return self


# ---------------------------------------------------------------------------
# WizardState — envelope used by the endpoint (slots + messages)
# ---------------------------------------------------------------------------


class WizardState(BaseModel):
    """Top-level envelope combining WizardSlots with conversation messages."""

    model_config = ConfigDict(extra="forbid")

    slots: WizardSlots = Field(default_factory=WizardSlots)

    @property
    def is_complete(self) -> bool:
        """True iff FinalForm validates successfully over current slots."""
        try:
            FinalForm.model_validate(self.slots.slots_dict())
            return True
        except ValidationError:
            return False


__all__ = [
    "FinalForm",
    "SlotDelta",
    "TOTAL_SLOTS",
    "WizardSlots",
    "WizardState",
]
