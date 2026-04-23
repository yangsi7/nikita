"""Cumulative wizard state models for Spec 214 FR-11d PR-A.

Implements the agentic-design-patterns.md Hard Rule §1 (cumulative
server-side state) and §2 (Pydantic completion gate).

``WizardSlots`` — mutable accumulator, one optional field per slot:
  - Slots: location, scene, darkness, identity, backstory, phone
  - ``apply(delta)`` → immutable update via ``model_copy(update=...)``
  - ``progress_pct`` — ``@computed_field`` of cumulative state, NEVER
    of per-turn extraction (anti-pattern: ``_compute_progress(latest_kind)``).
  - ``missing`` — ``@computed_field`` listing unfilled slot names.
  - ``slots_dict()`` — plain dict for ``FinalForm.model_validate()``.

``FinalForm`` — Pydantic completion gate.  All 6 required slots as
  non-optional fields + ``@model_validator(mode="after")`` for cross-field
  business rules (age ≥ 18).  The validator IS the gate:
  ``try: FinalForm.model_validate(slots.slots_dict()); complete = True``
  ``except ValidationError: complete = False``
  NEVER hardcode ``complete = True / False`` in handler code.

``SlotDelta`` — lightweight input model for ``WizardSlots.apply()``.
  ``kind`` is a Literal discriminator; ``data`` carries slot-specific fields.

``TOTAL_SLOTS: Final[int] = 6`` — named constant, regression-guarded.
  Tuning-constants.md: prior values + PR; rationale in module docstring.
  Current value: 6 (one per extraction schema: location, scene, darkness,
  identity, backstory, phone). Set in Spec 214 FR-11d, tasks-v2.md §T2.
  Prior: N/A (new constant). Do not change without updating FinalForm
  required fields AND the regression test in test_wizard_state.py.
"""

from __future__ import annotations

from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, computed_field, model_validator

from nikita.onboarding.tuning import MIN_USER_AGE

# ---------------------------------------------------------------------------
# Tuning constant (regression guard — see tuning-constants.md)
# ---------------------------------------------------------------------------

TOTAL_SLOTS: Final[int] = 6
"""Total wizard slots.  One per extraction schema (location, scene, darkness,
identity, backstory, phone).

Current value: 6 (Spec 214 FR-11d, tasks-v2.md §T2).
Prior values: N/A — introduced here.

Rationale: six distinct data-collection topics; each topic is one slot
regardless of how many sub-fields it has (e.g. identity has name/age/
occupation but counts as one wizard step).

Changing this requires updating:
  - FinalForm required fields (all must be non-optional)
  - test_wizard_state.py::TestTuningConstants::test_total_slots_constant_is_six
"""

# ---------------------------------------------------------------------------
# Slot kinds
# ---------------------------------------------------------------------------

_SLOT_KINDS = Literal[
    "location", "scene", "darkness", "identity", "backstory", "phone"
]
_ALL_SLOT_NAMES: list[str] = [
    "location", "scene", "darkness", "identity", "backstory", "phone"
]

# ---------------------------------------------------------------------------
# SlotDelta — input model for WizardSlots.apply()
# ---------------------------------------------------------------------------


class SlotDelta(BaseModel):
    """Represents a single turn's extraction result to merge into WizardSlots.

    ``kind`` must be one of the 6 canonical slot names OR "no_extraction".
    ``data`` is a free-form dict of slot-specific fields — the caller is
    responsible for providing valid data shapes (extracted from
    extraction_schemas.py models).  ``apply()`` stores the data under the
    slot key, ignoring ``no_extraction`` turns.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "location",
        "scene",
        "darkness",
        "identity",
        "backstory",
        "phone",
        "no_extraction",
    ]
    data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# WizardSlots — cumulative accumulator
# ---------------------------------------------------------------------------


class WizardSlots(BaseModel):
    """Cumulative wizard state — one optional field per slot.

    Each field is ``None`` until the corresponding extraction is received.
    Merges are IMMUTABLE: use ``apply(delta)`` which returns a new
    ``WizardSlots`` via ``model_copy(update=...)``.  The caller must
    reassign the reference:  ``slots = slots.apply(delta)``.

    ``progress_pct`` and ``missing`` are ``@computed_field`` properties —
    derived entirely from the current cumulative state, never from the
    latest per-turn extraction.  This enforces monotonicity by construction:
    slots are only added, never removed.
    """

    model_config = ConfigDict(extra="forbid")

    location: dict[str, Any] | None = None
    scene: dict[str, Any] | None = None
    darkness: dict[str, Any] | None = None
    identity: dict[str, Any] | None = None
    backstory: dict[str, Any] | None = None
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
        return min(100, int(filled * 100 // TOTAL_SLOTS))

    def apply(self, delta: SlotDelta) -> "WizardSlots":
        """Return a new WizardSlots with ``delta`` merged in.

        ``no_extraction`` turns are silently ignored (state unchanged).
        Duplicate slot applications (same kind twice) are idempotent — the
        newest data overwrites the previous value but does not push
        progress above 100.
        """
        if delta.kind == "no_extraction":
            return self
        return self.model_copy(update={delta.kind: delta.data})

    def slots_dict(self) -> dict[str, Any]:
        """Return a plain dict of filled slot data for FinalForm.model_validate().

        Only includes slots with non-None values.
        """
        result: dict[str, Any] = {}
        for name in _ALL_SLOT_NAMES:
            value = getattr(self, name)
            if value is not None:
                result[name] = value
        return result

    @computed_field  # type: ignore[misc]
    @property
    def is_complete(self) -> bool:
        """Pydantic-only completion gate (AC-11d.3).

        Delegates to ``FinalForm.model_validate(self.slots_dict())`` — the
        canonical single source of truth for the completion check.  NEVER
        hardcode True or False in handler code; use this property instead.
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
    """Completion gate: all 6 required slots as non-optional fields.

    Usage (handler code):
        try:
            form = FinalForm.model_validate(state.slots.slots_dict())
            complete = True
        except ValidationError:
            complete = False

    NEVER hardcode ``complete = True`` or ``complete = False`` in handler
    code.  The validator IS the gate.

    Cross-field business rules enforced via ``@model_validator(mode="after")``
    (AC-11d.9 — age ≥ 18, identity not all-None).
    """

    model_config = ConfigDict(extra="forbid")  # slots_dict emits exactly the 6 slot keys

    location: dict[str, Any]
    scene: dict[str, Any]
    darkness: dict[str, Any]
    identity: dict[str, Any]
    backstory: dict[str, Any]
    phone: dict[str, Any]

    @model_validator(mode="after")
    def _identity_age_minimum(self) -> "FinalForm":
        """Enforce age >= MIN_USER_AGE (AC-11d.9)."""
        age = self.identity.get("age")
        if age is not None and age < MIN_USER_AGE:
            raise ValueError(
                f"identity.age must be >= {MIN_USER_AGE}; got {age}"
            )
        return self

    @model_validator(mode="after")
    def _identity_not_all_none(self) -> "FinalForm":
        """Identity slot must have at least one of name/age/occupation."""
        id_data = self.identity
        if (
            id_data.get("name") is None
            and id_data.get("age") is None
            and id_data.get("occupation") is None
        ):
            raise ValueError(
                "identity slot must have at least one of name/age/occupation"
            )
        return self

    @model_validator(mode="after")
    def _voice_requires_phone(self) -> "FinalForm":
        """At completion, voice preference requires a phone number (GH #406 fix).

        Moved from PhoneExtraction per-turn schema to FinalForm completion gate
        so the two-step voice flow works: declare preference → provide number.
        Per-turn validation no longer blocks the preference-only turn.
        """
        phone_preference = self.phone.get("phone_preference")
        phone = self.phone.get("phone")
        if phone_preference == "voice" and not phone:
            raise ValueError(
                "phone_preference='voice' requires a phone number at completion"
            )
        return self


# ---------------------------------------------------------------------------
# WizardState — envelope used by the endpoint (slots + messages)
# ---------------------------------------------------------------------------


class WizardState(BaseModel):
    """Top-level envelope combining WizardSlots with conversation messages.

    This is the object the endpoint loads on each turn and persists back
    to the database after merging the latest extraction.
    """

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
