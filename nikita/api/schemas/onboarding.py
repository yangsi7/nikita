"""Discriminated-union response envelope for ``POST /onboarding/answer``.

Spec 217-3A AC-9.1bis. Declares a Pydantic ``Annotated[Union[...], Field(
discriminator="kind")]`` so FastAPI emits a stable OpenAPI ``oneOf``
schema for the route's 200 response — no surface drift across the 5
emission shapes the route layer can return.

The 5 ``kind`` discriminators map 1:1 to the route's dispatch branches:

  reaction              ← agent emitted ReactionOnly (slot NOT advanced)
  followup              ← agent emitted FollowUpQuestion (sidecar set)
  field_error           ← partial-validation failure (e.g. IdentityPair age bad)
  turn_failure          ← agent emitted TurnFailure or output_retries exhausted
  deterministic_advance ← deterministic happy path, slot advanced

This module ONLY declares the schema types. The route handler wires
them up via ``@router.post("/answer", response_model=AnswerResponse)``
in 217-3A.2 (out of scope for 217-3A.1).

Why this lives in 217-3A.1 (prereqs) not 217-3A.2 (wiring):
  - The ``response_model=`` annotation in 217-3A.2 needs the type to
    exist already.
  - Decoupling the schema lets 217-3B (FE) generate TS types from the
    OpenAPI document without waiting on the route refactor.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from nikita.agents.onboarding.converse_contracts import FollowUpQuestion


# ---------------------------------------------------------------------------
# Per-kind response envelopes
# ---------------------------------------------------------------------------


class ReactionResponse(BaseModel):
    """Route emits when the agent returned ``ReactionOnly``.

    The deterministic question stays pending — FE keeps the same
    next-prompt visible. Sidecar ``pending_followup`` is cleared on this
    branch (server-side, not in this envelope).
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["reaction"] = "reaction"
    reaction_text: str = Field(min_length=1, max_length=280)


class FollowUpResponse(BaseModel):
    """Route emits when the agent returned ``FollowUpQuestion``.

    The FE locks the deterministic input chrome until the followup is
    resolved. The sidecar JSONB persists the followup so the next turn
    knows it's in flight.

    Wire shape — ``question_text`` and ``target_slot`` are flattened onto
    the envelope (NOT nested under a ``payload:`` key) so all five
    ``AnswerResponse`` branches share a uniform shape: each branch's
    payload fields sit directly under the envelope. This keeps the
    OpenAPI ``oneOf`` consistent and FE TS codegen narrows by ``kind``
    without needing branch-specific ``.payload`` accessors.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["followup"] = "followup"
    question_text: str = Field(min_length=1, max_length=200)
    target_slot: str | None = None


class FieldErrorResponse(BaseModel):
    """Partial-validation failure — used for IdentityPair (FR-10a) and
    similar compound slots where some sub-fields are valid and some
    aren't. The valid sub-fields are persisted to ``WizardSlots`` server-
    side; the FE re-renders the form preserving valid entries.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["field_error"] = "field_error"
    errors: dict[str, str] = Field(
        ...,
        min_length=1,
        description=(
            "Map of sub-field name → human-readable error reason. Must "
            "contain at least one entry; empty dict is invalid (route "
            "layer should emit a different envelope when there are no "
            "field-level errors to report)."
        ),
    )


class TurnFailureResponse(BaseModel):
    """Route emits when the agent returned ``TurnFailure`` OR when
    ``output_retries`` were exhausted (``UnexpectedModelBehavior``
    converted by the route layer).
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["turn_failure"] = "turn_failure"
    explanation: str = Field(min_length=1)


class DeterministicAdvanceResponse(BaseModel):
    """Happy path — deterministic flow advanced. The agent did NOT
    intercept the turn (no ReactionOnly/FollowUp emitted), so the slot
    moved forward and the next deterministic question (or terminal
    state) is queued.

    ``next_slot_kind`` is typed as ``str | None`` to keep this schema
    module decoupled from ``SlotKind`` enum churn — the route layer
    serializes ``SlotKind`` values to their string form before emitting.

    ``archetype_cards`` is loosely typed (``list[dict] | None``) for
    the same reason — the actual ``ArchetypeCard`` model lives in the
    onboarding agent module and drags too many imports in for a schema
    file. Route layer dumps to dict before emitting.

    NOTE for 217-3A.2: when wiring ``response_model=AnswerResponse``,
    consider adding a ``TypedDict`` (``ArchetypeCardWire``) co-located
    here so OpenAPI emits a typed shape for FE codegen instead of
    ``dict[str, Any]``. Tracked as a follow-up nitpick — not blocking
    217-3A.1 prereqs.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["deterministic_advance"] = "deterministic_advance"
    next_slot_kind: str | None = None
    progress_pct: int = Field(ge=0, le=100)
    archetype_cards: list[dict[str, Any]] | None = None


# ---------------------------------------------------------------------------
# Discriminated union — the FastAPI ``response_model`` for /answer
# ---------------------------------------------------------------------------


AnswerResponse = Annotated[
    Union[
        ReactionResponse,
        FollowUpResponse,
        FieldErrorResponse,
        TurnFailureResponse,
        DeterministicAdvanceResponse,
    ],
    Field(discriminator="kind"),
]
"""Discriminated-union response envelope for ``POST /onboarding/answer``.

Wire example (deterministic happy path):

    {"kind": "deterministic_advance", "next_slot_kind": "city",
     "progress_pct": 23, "archetype_cards": null}

The FastAPI layer renders this as a ``oneOf`` schema in OpenAPI; the
discriminator field ``kind`` is what TypeScript codegen on the FE side
uses to narrow the response type.
"""


__all__ = [
    "AnswerResponse",
    "DeterministicAdvanceResponse",
    "FieldErrorResponse",
    "FollowUpResponse",
    "ReactionResponse",
    "TurnFailureResponse",
]
