"""Wizard v2 cumulative state + completion gate + DAG (Spec 218).

Per ``.claude/rules/agentic-design-patterns.md`` Hard Rules §1 + §2:

- Cumulative server-side state (``WizardSlotsV2``) — one optional dict[str, Any]
  field per slot; merges are immutable via ``model_copy(update=...)``.
- Pydantic completion gate (``FinalForm``) — non-optional fields plus
  cross-field ``@model_validator(mode="after")`` rules. Handler code MUST
  call ``FinalForm.model_validate(slots.slots_dict())`` and never hardcode
  a True / False completion literal.

Phase 1 slot taxonomy (FR-006, 11 slots in dependency-respecting order):

  1. display_name
  2. age (DoB)
  3. city
  4. occupation
  5. primary_hobbies (chip_multi)
  6. hangouts_personalized (chip_multi from static cohort lookup)
  7. voice_or_text preference
  8. phone (only required when voice_or_text == "voice")
  9. saturday_morning
 10. darkness_level
 11. geek_out_on

DAG (FR-007):

  - hangouts_personalized depends_on: [city, age, occupation]
  - phone               depends_on: [voice_or_text]   # conditional via FR-007 + FinalForm
  - everything else: no dependencies

When a user back-edits city/age/occupation, the router MUST null-out
hangouts_personalized; when voice_or_text flips voice -> text, phone
becomes optional (FinalForm cross-field validator drops the requirement).

state_hash (FR-017):

  SHA-256 hex of canonical JSON dump of ``WizardSlotsV2`` (sorted keys,
  no whitespace) — used as the cache key for ``agent_envelope_cache``
  per FR-017. Stable across processes and across JSON serializer versions.

This module is PR-218-1 additive-only. PR-218-3 will atomically wire it
into the route handler and bulldoze v1 contracts (per spec 218 §23.10
vertical-slice atomicity rule).
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError, computed_field, model_validator

from nikita.onboarding.tuning import MIN_USER_AGE


# ---------------------------------------------------------------------------
# Tuning constants (regression-guarded — see .claude/rules/tuning-constants.md)
# ---------------------------------------------------------------------------

PHASE_1_REQUIRED_SLOTS: Final[int] = 11
"""Total Phase 1 required slots per FR-006.

Current value: 11 (Spec 218 FR-006 lock-in 2026-05-09).
Prior values: 13 (Spec 216-B1+B2, in legacy ``state.py``) — superseded by
the Spec 218 redesign which moves several legacy slots into Phase 2
open-bounce.

Changing this requires updating:
  - ``REQUIRED_ORDER`` in ``router.py`` (must have exactly 11 entries)
  - ``FinalForm`` required fields (all 11 must be non-optional except
    ``phone`` which is conditional on voice_or_text)
  - ``test_state_v2.py::test_phase_1_required_slots_constant``
"""

PHASE_2_MIN_TURNS: Final[int] = 4
"""Phase 2 minimum follow-up turns before agent may emit completion.

Current value: 4 (Spec 218 FR-008 lock-in 2026-05-09).
Rationale: industry consensus min-floor (Gemini deep-research synthesis
``.firecrawl/spec-218-gemini-deep-research.md``). Walk B6 may revise.
"""

PHASE_2_MAX_TURNS: Final[int] = 5
"""Phase 2 maximum follow-up turns; force-emit completion past this.

Current value: 5 (GH #623 — lowered from 8 on 2026-05-15).
Prior values:
  8 — Spec 218 FR-008 lock-in 2026-05-09 (industry consensus max-ceiling).
  5 — GH #623 walk evidence: turn_count=7, backstory_preview=null,
      onboarding_status=pending. Agent fixated on one topic and repeated
      the same question 5/7 turns. Lowering from 8 to 5 fires the
      forced-completion gate earlier, guaranteeing backstory generation
      before the user abandons.
Rationale: 5 turns is sufficient for backstory depth; I2 topic-diversity
check ensures coverage breadth within those turns.
"""

MAX_PHASE2_TURNS: Final[int] = PHASE_2_MAX_TURNS
"""Alias for PHASE_2_MAX_TURNS — verification grep gate target (GH #623).

Exported so downstream imports can use the shorter name.
Current value: 5 (mirrors PHASE_2_MAX_TURNS above).
"""


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------


class Phase(str, Enum):
    """Wizard phase per FR-002.

    ``phase1`` — deterministic router-driven required slot collection.
    ``phase2`` — open-bounce 4-8 follow-up turns ending in backstory commit.
    ``complete`` — terminal; backstory generated, handoff rendered.
    """

    phase1 = "phase1"
    phase2 = "phase2"
    complete = "complete"


# ---------------------------------------------------------------------------
# SlotKind v2 enum — Phase 1 only (Phase 2 turns are free-asked by the agent
# and do not occupy fixed SlotKind values).
# ---------------------------------------------------------------------------


class SlotKindV2(str, Enum):
    """Phase 1 slot taxonomy per FR-006.

    Order matters: ``REQUIRED_ORDER`` in ``router.py`` mirrors the
    enum-declaration order. Adding or reordering members requires
    coordinated updates to the router constant + tests.
    """

    display_name = "display_name"
    age = "age"
    city = "city"
    occupation = "occupation"
    primary_hobbies = "primary_hobbies"
    hangouts_personalized = "hangouts_personalized"
    voice_or_text = "voice_or_text"
    phone = "phone"
    saturday_morning = "saturday_morning"
    darkness_level = "darkness_level"
    geek_out_on = "geek_out_on"


_PHASE_1_SLOT_NAMES: list[str] = [m.value for m in SlotKindV2]


# ---------------------------------------------------------------------------
# DAG — slot dependencies for FR-007 invalidation
# ---------------------------------------------------------------------------


SLOT_DEPENDENCIES: Final[dict[str, tuple[str, ...]]] = {
    SlotKindV2.display_name.value: (),
    SlotKindV2.age.value: (),
    SlotKindV2.city.value: (),
    SlotKindV2.occupation.value: (),
    SlotKindV2.primary_hobbies.value: (),
    SlotKindV2.hangouts_personalized.value: (
        SlotKindV2.city.value,
        SlotKindV2.age.value,
        SlotKindV2.occupation.value,
    ),
    SlotKindV2.voice_or_text.value: (),
    SlotKindV2.phone.value: (SlotKindV2.voice_or_text.value,),
    SlotKindV2.saturday_morning.value: (),
    SlotKindV2.darkness_level.value: (),
    SlotKindV2.geek_out_on.value: (),
}
"""Per-slot dependency tuple. Empty tuple = no dependencies.

When ``edited_slot in deps`` for any filled downstream slot, the
downstream slot MUST be null-ed out per FR-007. The router's
``dag_invalidate`` helper computes the affected set.
"""


# ---------------------------------------------------------------------------
# SlotDelta — input model for WizardSlotsV2.apply()
# ---------------------------------------------------------------------------


class SlotDeltaV2(BaseModel):
    """One turn's extraction merged into ``WizardSlotsV2``.

    ``kind`` MUST be a ``SlotKindV2`` value or ``"no_extraction"`` sentinel.
    ``data`` is the slot-specific payload dict (validated downstream by
    the per-slot Pydantic schema in ``envelope.py``).
    """

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(
        description=(
            "One of the 11 SlotKindV2 values, or 'no_extraction' sentinel "
            "for clarification / off-topic turns."
        ),
    )
    data: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_kind(self) -> "SlotDeltaV2":
        if self.kind == "no_extraction":
            return self
        if self.kind not in _PHASE_1_SLOT_NAMES:
            raise ValueError(
                f"SlotDeltaV2.kind {self.kind!r} is not a SlotKindV2 member nor 'no_extraction'"
            )
        return self


# ---------------------------------------------------------------------------
# WizardSlotsV2 — cumulative accumulator
# ---------------------------------------------------------------------------


class WizardSlotsV2(BaseModel):
    """Cumulative wizard state — one optional dict per Phase 1 slot.

    Each field is ``None`` until the corresponding slot is accepted.
    Merges are IMMUTABLE: ``apply(delta)`` returns a new ``WizardSlotsV2``
    via ``model_copy(update=...)``. The caller MUST reassign:
    ``slots = slots.apply(delta)``.

    ``progress_pct`` and ``missing`` are ``@computed_field`` derived from
    cumulative state (Hard Rule §4 — monotonic by construction).

    DAG-invalidation on back-edit goes through ``invalidate_dependents``
    which returns a NEW WizardSlotsV2 with downstream slots null-ed out.
    """

    model_config = ConfigDict(extra="forbid")

    display_name: dict[str, Any] | None = None
    age: dict[str, Any] | None = None
    city: dict[str, Any] | None = None
    occupation: dict[str, Any] | None = None
    primary_hobbies: dict[str, Any] | None = None
    hangouts_personalized: dict[str, Any] | None = None
    voice_or_text: dict[str, Any] | None = None
    phone: dict[str, Any] | None = None
    saturday_morning: dict[str, Any] | None = None
    darkness_level: dict[str, Any] | None = None
    geek_out_on: dict[str, Any] | None = None

    # ---- Computed fields ----

    @computed_field  # type: ignore[misc]
    @property
    def missing(self) -> list[str]:
        """Phase 1 slot names not yet filled (in REQUIRED_ORDER)."""
        return [name for name in _PHASE_1_SLOT_NAMES if getattr(self, name) is None]

    @computed_field  # type: ignore[misc]
    @property
    def progress_pct(self) -> int:
        """0-100 percentage of Phase 1 slots filled, conditional-aware.

        When ``voice_or_text == "text"``, ``phone`` is excluded from the
        denominator (it is not required). Monotonic by construction —
        slots are only added during a normal advance; DAG-invalidation
        is the ONLY path that can reduce the numerator (and only inside
        ``invalidate_dependents``, which the router pairs with a new
        edit so progress eventually monotonically resumes).
        """
        denom_slots = self._effective_required_slots()
        filled = sum(1 for name in denom_slots if getattr(self, name) is not None)
        if not denom_slots:
            return 100
        return min(100, (filled * 100) // len(denom_slots))

    def _effective_required_slots(self) -> list[str]:
        """Required-slot list with conditional adjustments applied.

        Drops ``phone`` from the required set when ``voice_or_text == "text"``.
        Otherwise returns the full Phase 1 list.
        """
        if (
            isinstance(self.voice_or_text, dict)
            and self.voice_or_text.get("voice_or_text") == "text"
        ):
            return [n for n in _PHASE_1_SLOT_NAMES if n != SlotKindV2.phone.value]
        return list(_PHASE_1_SLOT_NAMES)

    @computed_field  # type: ignore[misc]
    @property
    def is_phase_1_complete(self) -> bool:
        """True iff every required Phase 1 slot is filled (conditional-aware)."""
        return all(getattr(self, name) is not None for name in self._effective_required_slots())

    # ---- Mutation ----

    def apply(self, delta: SlotDeltaV2) -> "WizardSlotsV2":
        """Return a new ``WizardSlotsV2`` with ``delta`` merged.

        ``no_extraction`` deltas are silently ignored (state unchanged).
        Duplicate slot applications overwrite the previous value
        (last-write-wins).
        """
        if delta.kind == "no_extraction":
            return self
        return self.model_copy(update={delta.kind: delta.data})

    def invalidate_dependents(self, edited_slot: str) -> tuple["WizardSlotsV2", list[str]]:
        """Null-out downstream filled slots that depend on ``edited_slot``.

        Returns ``(new_slots, invalidated)`` where ``invalidated`` is the
        list of slot names that were null-ed out. Per FR-007, the caller
        is responsible for the user-facing confirmation modal BEFORE
        calling this; this helper performs the state mutation only.
        """
        invalidated: list[str] = []
        update: dict[str, Any] = {}
        for name, deps in SLOT_DEPENDENCIES.items():
            if edited_slot in deps and getattr(self, name) is not None:
                update[name] = None
                invalidated.append(name)
        if not update:
            return self, []
        return self.model_copy(update=update), invalidated

    # ---- Serializers ----

    def slots_dict(self) -> dict[str, Any]:
        """Plain dict of filled slot data for ``FinalForm.model_validate``.

        Keys = slot names. Values = the slot's ``data`` dict. Excludes
        unfilled (``None``) slots.
        """
        result: dict[str, Any] = {}
        for name in _PHASE_1_SLOT_NAMES:
            value = getattr(self, name)
            if value is not None:
                result[name] = value
        return result


# ---------------------------------------------------------------------------
# state_hash — stable digest for cache key (FR-017)
# ---------------------------------------------------------------------------


def state_hash(slots: WizardSlotsV2) -> str:
    """Return SHA-256 hex digest of canonical JSON dump of ``slots``.

    Stable across processes (no Python hash randomization), stable
    across Pydantic / JSON serializer versions (``model_dump`` -> sorted
    ``json.dumps``). Used as the cache key in ``agent_envelope_cache``
    per FR-017.

    Example::

        h = state_hash(slots)         # "9b3f...c2"
        cache.get((user_id, target, h))
    """
    payload = slots.model_dump(mode="json", exclude={"missing", "progress_pct", "is_phase_1_complete"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# FinalForm — Pydantic completion gate (Hard Rule §2)
# ---------------------------------------------------------------------------


class FinalForm(BaseModel):
    """Phase 1 completion gate.

    Usage (handler code)::

        try:
            form = FinalForm.model_validate(slots.slots_dict())
            phase_1_complete = True
        except ValidationError:
            phase_1_complete = False

    NEVER hardcode ``phase_1_complete = True`` / ``= False`` in handler
    code. The validator IS the gate.

    Cross-field rules (``@model_validator(mode="after")``):
      - ``age >= MIN_USER_AGE`` (18)
      - ``voice_or_text == "voice"`` requires non-empty ``phone`` payload
      - ``primary_hobbies`` must be a non-empty list of strings
    """

    model_config = ConfigDict(extra="forbid")

    display_name: dict[str, Any]
    age: dict[str, Any]
    city: dict[str, Any]
    occupation: dict[str, Any]
    primary_hobbies: dict[str, Any]
    hangouts_personalized: dict[str, Any]
    voice_or_text: dict[str, Any]
    saturday_morning: dict[str, Any]
    darkness_level: dict[str, Any]
    geek_out_on: dict[str, Any]
    # phone is conditional — see _voice_requires_phone validator
    phone: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _age_minimum(self) -> "FinalForm":
        age_val = self.age.get("age") if isinstance(self.age, dict) else None
        if age_val is None:
            raise ValueError("age slot must contain an 'age' value")
        if age_val < MIN_USER_AGE:
            raise ValueError(f"age must be >= {MIN_USER_AGE}; got {age_val}")
        return self

    @model_validator(mode="after")
    def _voice_requires_phone(self) -> "FinalForm":
        pref = (
            self.voice_or_text.get("voice_or_text")
            if isinstance(self.voice_or_text, dict)
            else None
        )
        phone_val = (
            self.phone.get("phone") if isinstance(self.phone, dict) else None
        )
        if pref == "voice" and not phone_val:
            raise ValueError(
                "voice_or_text='voice' requires a phone number at completion"
            )
        return self

    @model_validator(mode="after")
    def _primary_hobbies_non_empty(self) -> "FinalForm":
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
# WizardStateV2 — top-level envelope (slots + phase + Phase 2 turn count)
# ---------------------------------------------------------------------------


class WizardStateV2(BaseModel):
    """Top-level v2 envelope: cumulative slots + Phase + Phase 2 turn count.

    ``phase_2_turn_count`` is incremented by the route handler each time
    a Phase 2 follow-up envelope is emitted; FR-008 enforces
    ``PHASE_2_MIN_TURNS <= count <= PHASE_2_MAX_TURNS`` before / for
    ``Phase.complete`` transitions.

    ``phase_2_started_at`` is an ISO-8601 string set in the same DB
    transaction as the final Phase 1 slot acceptance (FR-002 atomicity).
    """

    model_config = ConfigDict(extra="forbid")

    slots: WizardSlotsV2 = Field(default_factory=WizardSlotsV2)
    phase: Phase = Phase.phase1
    phase_2_turn_count: int = Field(default=0, ge=0)
    phase_2_started_at: str | None = None

    @property
    def is_phase_2_eligible(self) -> bool:
        """True iff Phase 1 is complete via FinalForm validation."""
        try:
            FinalForm.model_validate(self.slots.slots_dict())
            return True
        except ValidationError:
            return False


__all__ = [
    "FinalForm",
    "MAX_PHASE2_TURNS",
    "PHASE_1_REQUIRED_SLOTS",
    "PHASE_2_MAX_TURNS",
    "PHASE_2_MIN_TURNS",
    "Phase",
    "SLOT_DEPENDENCIES",
    "SlotDeltaV2",
    "SlotKindV2",
    "WizardSlotsV2",
    "WizardStateV2",
    "state_hash",
]
