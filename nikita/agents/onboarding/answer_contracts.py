"""HTTP contracts for POST /answer + GET /state — Spec 216-B3 (T-B3-2).

Pydantic v2 schemas for the new stateful onboarding endpoints. The discriminated
``output`` union on ``AnswerResponse`` uses envelope wrappers around the agent
contracts ``TurnOutput`` / ``TurnFailure`` so the 216-B1+B2 schemas stay frozen
— the wrappers add the literal ``kind`` discriminator without mutating the
agent layer.

Schema source: master spec.md "HTTP API Contracts".

216-D-code wired (this PR):
  - ``TurnOutputEnvelope.cohort_chips`` — ``list[ChipOption] | None`` (D1.7)
  - ``TurnOutputEnvelope.archetype_cards`` — ``list[ArchetypeCard] | None`` (D1.6)

Both default to ``None`` and are populated by the route layer only on the
specific slots they target: ``cohort_chips`` on ``primary_hobbies``,
``archetype_cards`` on ``backstory_pick``. 216-E will wire the actual
populators in the /answer handler; this contract is what 216-E preserves.

NR-05 enforcement:
  - No ``big5_vector`` field on any response model
  - Test suite at ``tests/agents/onboarding/test_answer_contracts.py``
    grep-audits ``model_dump_json()`` for personality-axis term leakage.

Rule cross-references:
  - .claude/rules/agentic-design-patterns.md Hard Rule §2 (Pydantic completion gate)
  - master spec.md "HTTP API Contracts" + NR-05
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from nikita.agents.onboarding.archetypes import ArchetypeCard
from nikita.agents.onboarding.cohort_chips import ChipOption
from nikita.agents.onboarding.conversation_agent import TurnFailure, TurnOutput
from nikita.agents.onboarding.question_registry import SlotKind


# ---------------------------------------------------------------------------
# Envelopes — discriminator carriers around agent-layer contracts
# ---------------------------------------------------------------------------


class TurnOutputEnvelope(TurnOutput):
    """``TurnOutput`` plus the ``kind`` discriminator + 216-D-code placeholder fields.

    Inheriting from ``TurnOutput`` keeps the 216-B1+B2 agent contract frozen
    (the agent emits raw ``TurnOutput``); the route layer wraps the agent
    output in this envelope before serializing to ``AnswerResponse``.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["success"] = "success"
    cohort_chips: list[ChipOption] | None = Field(
        default=None,
        description=(
            "Hand-seeded chip suggestions for the hobbies turn (D1.7). "
            "Populated by the route layer only on the primary_hobbies slot; "
            "None on every other turn."
        ),
    )
    archetype_cards: list[ArchetypeCard] | None = Field(
        default=None,
        description=(
            "3-card backstory selector content (D1.6). Populated by the route "
            "layer only on the backstory_pick slot; None on every other turn."
        ),
    )


class TurnFailureEnvelope(TurnFailure):
    """``TurnFailure`` plus the ``kind`` discriminator."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["failure"] = "failure"


# ---------------------------------------------------------------------------
# AnswerRequest
# ---------------------------------------------------------------------------


class AnswerRequest(BaseModel):
    """POST /api/v1/onboarding/answer request body."""

    model_config = ConfigDict(extra="forbid")

    slot_kind: SlotKind = Field(
        description="Which slot the user is answering. One of the SlotKind values.",
    )
    value: Annotated[str, StringConstraints(min_length=1, max_length=2000)] | dict[str, Any] = Field(
        description=(
            "The user's literal answer text (post-FE sanitization, 1..2000 "
            "chars), OR a dict of sub-fields when ``slot_kind == identity_pair`` "
            "(217-3A.3 FR-10a; e.g. ``{name: str, age: int}``). Dict values "
            "are validated against the compound-slot Pydantic model in the "
            "route handler."
        ),
    )
    turn_id: UUID = Field(
        description=(
            "Idempotency key — server caches the response under "
            "(user_id, turn_id) for 5 minutes. Replays return the cached body."
        ),
    )
    conversation_id: UUID | None = Field(
        default=None,
        description=(
            "Server-issued on the first /answer call when client supplies None. "
            "Client echoes on subsequent turns. If client supplies a UUID the "
            "server doesn't recognize, server creates a new id and returns it."
        ),
    )


# ---------------------------------------------------------------------------
# AnswerResponse
# ---------------------------------------------------------------------------


class LegacyAnswerResponse(BaseModel):
    """LEGACY POST /api/v1/onboarding/answer response body — superseded by 217-3A.3.

    Renamed from ``AnswerResponse`` in 217-3A.3 to make room for the new
    discriminated-union ``AnswerResponse`` at ``nikita/api/schemas/onboarding.py``.
    Survives ONLY because the personality-leak runtime-dump regression
    test still imports it; it will be deleted once that test is migrated
    to the new envelope shape (217-3A.3+ follow-up). NEVER used by the
    /answer route on or after 217-3A.3.
    """

    model_config = ConfigDict(extra="forbid")

    output: TurnOutputEnvelope | TurnFailureEnvelope = Field(
        discriminator="kind",
        description="Discriminated union on `kind` — 'success' or 'failure'.",
    )
    progress_pct: int = Field(
        ge=0,
        le=100,
        description=(
            "Cumulative completion percentage from WizardSlots.progress_pct. "
            "Monotonic by construction across turns. NEVER per-turn snapshot."
        ),
    )
    is_complete: bool = Field(
        description=(
            "Result of FinalForm.model_validate(state.slots_dict()). "
            "Pydantic-only completion gate per Hard Rule §2 — never a hardcoded literal."
        ),
    )
    link_code: str | None = Field(
        default=None,
        description=(
            "Set on the terminal turn (when is_complete becomes True for the first time) "
            "and persisted; subsequent successful idempotent replays return the same code "
            "until expiry."
        ),
    )
    conversation_id: UUID = Field(
        description="Server-issued conversation identifier; FE echoes on next turn.",
    )
    meta: dict[str, str] | None = Field(
        default=None,
        description=(
            "Carries fallback_reason (e.g. 'UnexpectedModelBehavior'), "
            "source ('llm' | 'idempotent' | 'fallback'), and similar metadata "
            "the FE may surface for support triage but never as user-facing copy."
        ),
    )


# ---------------------------------------------------------------------------
# StateResponse
# ---------------------------------------------------------------------------


class StateResponse(BaseModel):
    """GET /api/v1/onboarding/state response body — read-only state projection."""

    model_config = ConfigDict(extra="forbid")

    last_assistant_turn: dict[str, Any] | None = Field(
        description=(
            "Last assistant turn dict from users.onboarding_profile.conversation, "
            "or None if no turns have been recorded yet."
        ),
    )
    progress_pct: int = Field(
        ge=0,
        le=100,
        description="Cumulative completion percentage. Same source as AnswerResponse.progress_pct.",
    )
    is_complete: bool = Field(
        description="FinalForm.model_validate(state.slots_dict()) result.",
    )
    link_code: str | None = Field(
        default=None,
        description="Persisted post-completion link code or None if not yet issued.",
    )
    elided_extracted: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Cumulative carryover dict for slots whose original turn rolled "
            "off the conversation log (CONVERSATION_TURN_CAP=100). Read-only."
        ),
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Active conversation identifier or None if no /answer turn has been taken.",
    )


__all__ = [
    "AnswerRequest",
    "LegacyAnswerResponse",
    "StateResponse",
    "TurnFailureEnvelope",
    "TurnOutputEnvelope",
]
