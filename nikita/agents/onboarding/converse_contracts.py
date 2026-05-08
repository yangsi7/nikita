"""Pydantic request/response contracts for POST /onboarding/converse.

``ConverseRequest`` sets ``extra="forbid"`` so a rogue ``user_id`` in the
body is rejected at the wire (AC-11d.3 / GH #350). Identity is derived
exclusively from the Bearer JWT by the endpoint.

``ConverseResponse`` mirrors technical-spec §2.3. ``nikita_reply`` wire
ceiling is 500 chars (Pydantic ``max_length``); the server enforces the
business cap of ``NIKITA_REPLY_MAX_CHARS=140`` via a post-validation
fallback (AC-T2.4.3).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Inline ControlSelection — Spec 216-B1+B2 absorbed control_selection.py here
# to allow that module to be DELETEd without forcing a B3-scope refactor.
# 216-B3 will replace ConverseRequest/Response with AnswerRequest/Response
# entirely; until then these inline types preserve the existing /converse
# wire contract.
# ---------------------------------------------------------------------------


class _BaseControl(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TextControl(_BaseControl):
    """User typed free-text into the chat input."""

    kind: Literal["text"] = "text"
    value: str = Field(min_length=1)


class ChipControl(_BaseControl):
    """User tapped a chip from the current-prompt options grid."""

    kind: Literal["chips"] = "chips"
    value: str = Field(min_length=1, max_length=64)


class SliderControl(_BaseControl):
    """User moved the 1-5 darkness slider."""

    kind: Literal["slider"] = "slider"
    value: int = Field(ge=1, le=5)


class ToggleControl(_BaseControl):
    """User tapped the voice / text toggle."""

    kind: Literal["toggle"] = "toggle"
    value: Literal["voice", "text"]


class CardsControl(_BaseControl):
    """User selected a backstory card."""

    kind: Literal["cards"] = "cards"
    value: str = Field(pattern=r"^[a-f0-9]{12}$")


ControlSelection = Annotated[
    Union[TextControl, ChipControl, SliderControl, ToggleControl, CardsControl],
    Field(discriminator="kind"),
]


class Turn(BaseModel):
    """Single conversation turn (role + content) in the request history."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["nikita", "user"]
    content: str = Field(max_length=2000)
    extracted: dict[str, Any] | None = None
    timestamp: datetime
    source: (
        Literal["llm", "fallback", "idempotent", "validation_reject"] | None
    ) = None


class ConverseRequest(BaseModel):
    """POST /onboarding/converse request body.

    ``extra="forbid"`` rejects unknown fields — most importantly, a
    spoofed ``user_id`` (AC-11d.3 / GH #350). Identity is derived from
    the Bearer JWT exclusively.
    """

    model_config = ConfigDict(extra="forbid")

    conversation_history: list[Turn] = Field(max_length=100)
    # str fallback for raw free-text; ControlSelection for chip/slider/etc.
    user_input: str | ControlSelection
    locale: Literal["en"] = "en"
    turn_id: UUID | None = None


class ConverseResponse(BaseModel):
    """POST /onboarding/converse response body.

    ``nikita_reply`` wire ceiling is 500 chars; the server post-validates
    against ``NIKITA_REPLY_MAX_CHARS`` (140) and substitutes a fallback
    when exceeded (AC-T2.4.3). The 500 ceiling exists purely as a
    defensive wire-level guard.

    ``link_code`` / ``link_expires_at`` — present only on the terminal turn
    (``conversation_complete=True``). The frontend reads these to render the
    deep-link QR / button for Telegram account binding (AC-11d.7/AC-11d.8).
    """

    model_config = ConfigDict(extra="forbid")

    nikita_reply: str = Field(max_length=500)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    confirmation_required: bool = False
    next_prompt_type: Literal[
        "text", "chips", "slider", "toggle", "cards", "none"
    ] = "text"
    next_prompt_options: list[str] | None = None
    progress_pct: int = Field(ge=0, le=100)
    conversation_complete: bool = False
    # `idempotent` = cache HIT short-circuit (B2 QA iter-1).
    # `validation_reject` = age<18 or schema-validation rejection mapped
    # to in-character reply (I9 QA iter-1, AC-11d.9).
    source: Literal["llm", "fallback", "idempotent", "validation_reject"]
    latency_ms: int = Field(ge=0)
    # AC-11d.7 / AC-11d.8 — minted on terminal turn only; None otherwise.
    link_code: str | None = None
    link_expires_at: datetime | None = None


class RateLimitResponse(BaseModel):
    """429 body for /converse rate-limit + spend-cap breaches.

    Distinct schema from ``ConverseResponse`` so OpenAPI advertises the
    correct shape (B4 QA iter-1). The endpoint returns this on:
      - per-user / per-IP rate-limit exceeded
      - daily LLM spend cap exceeded
    """

    model_config = ConfigDict(extra="forbid")

    nikita_reply: str = Field(max_length=500)
    source: Literal["fallback"]
    retry_after_sec: int = Field(ge=0)


__all__ = [
    "CardsControl",
    "ChipControl",
    "ControlSelection",
    "ConverseRequest",
    "ConverseResponse",
    "FollowUpQuestion",
    "RateLimitResponse",
    "ReactionOnly",
    "SliderControl",
    "TextControl",
    "ToggleControl",
    "Turn",
    "TurnFailure",
]


# ---------------------------------------------------------------------------
# 217-3A: Emission union types (AC-5.1)
#
# Three Pydantic v2 BaseModels the conversation agent emits via Pydantic
# AI's ``output_type=[ToolOutput(...)*3]`` mechanism. The agent commits
# to exactly one emission per turn:
#
#   ReactionOnly       — narrator-style reaction, slot NOT advanced
#   FollowUpQuestion   — clarifying question, sidecar persisted
#   TurnFailure        — graceful re-ask on invalid input or retry exhaustion
#
# DISCRIMINATION MECHANISM — these classes intentionally do NOT carry
# a ``kind: Literal[...]`` field. Pydantic AI distinguishes them via
# the ``name=`` argument on each ``ToolOutput`` wrapper at agent-
# construction time (217-3A.2 in ``conversation_agent.py``); the agent
# selects which class to emit by selecting which named tool to call.
# The route-level wire envelope ``AnswerResponse`` (in
# ``nikita/api/schemas/onboarding.py``) IS a Pydantic discriminated
# union with a ``kind: Literal`` per branch — that lives at the HTTP
# boundary so FE TS codegen has a stable narrowing key. Don't add
# ``kind`` fields to these classes — that would conflict with the
# ToolOutput-name mechanism.
#
# Per .claude/rules/agentic-design-patterns.md Hard Rule §3 (tool
# consolidation) — replaces the prior coarse 2-tool union and the
# legacy 7-tool fan-out before that.
#
# DUPLICATION NOTE — a class named ``TurnFailure`` already exists at
# ``conversation_agent.py:102``. The 217-3A.2 dispatch updates
# ``conversation_agent.py`` to import from this module and removes the
# duplicate. Until 217-3A.2 lands, both definitions coexist; the
# wire-shape and field names are intentionally identical so the
# migration is import-rename only.
# ---------------------------------------------------------------------------


class ReactionOnly(BaseModel):
    """Narrator reaction without advancing the deterministic slot.

    The agent emits this when the user shares context, color, or mood
    that warrants acknowledgment but does NOT answer the next
    deterministic question. ``reaction_text`` is rendered to the user;
    the deterministic question stays pending and the slot does NOT
    advance. Sidecar ``pending_followup`` is cleared on this branch.

    Field discipline:
      - ``reaction_text``: 1..280 chars, no markdown; the route layer
        runs the existing ``validate_reply`` + ``sanitize_reply_punctuation``
        before emitting to FE.
    """

    model_config = ConfigDict(extra="forbid")

    reaction_text: str = Field(
        min_length=1,
        max_length=280,
        description=(
            "In-character reaction to the user's last message. Does NOT "
            "advance the deterministic slot — purely acknowledgment / "
            "narrator color."
        ),
    )


class FollowUpQuestion(BaseModel):
    """Clarifying question inserted before the deterministic flow advances.

    The agent emits this when the user's response was ambiguous, partial,
    or invited a tighter follow-up. The route layer persists this to
    ``users.onboarding_profile.pending_followup`` (JSONB) so the next
    turn knows a followup is in flight; the validator (``@output_validator``
    in 217-3A.2) rejects mirror-of-next + mirror-echo via ``ModelRetry``.

    Field discipline:
      - ``question_text``: 1..200 chars; agent's own follow-up question.
      - ``target_slot``: optional slot name the followup is probing
        (e.g., ``"saturday_morning"``); free-form string here so the
        contract stays decoupled from ``SlotKind`` enum churn.
    """

    model_config = ConfigDict(extra="forbid")

    question_text: str = Field(
        min_length=1,
        max_length=200,
        description="Agent's clarifying question, rendered as the next turn.",
    )
    target_slot: str | None = Field(
        default=None,
        description=(
            "Name of the deterministic slot this follow-up is probing, "
            "if any. Used by the FE to keep the slot context visible."
        ),
    )


class TurnFailure(BaseModel):
    """Graceful re-ask on invalid input or retry exhaustion.

    Emitted in-character when (a) the user provided invalid data
    (under-18, contradictions), or (b) the agent's ``output_retries``
    budget was exhausted (``UnexpectedModelBehavior`` lifted by the
    route to a TurnFailure emission per 217-3A.2 dispatch logic).
    The agent NEVER throws — the route layer catches and converts.

    Wire-compatible with ``conversation_agent.TurnFailure`` so 217-3A.2's
    import-rename consolidation is non-breaking. ``last_slot_kind`` is
    typed loosely (``str | None``) here to keep this contract module
    free of ``SlotKind`` enum dependencies; the agent module narrows it
    in 217-3A.2.
    """

    model_config = ConfigDict(extra="forbid")

    explanation: str = Field(
        min_length=1,
        description=(
            "In-character message explaining why the input was rejected, "
            "e.g. 'eighteen and up only.'"
        ),
    )
    last_slot_kind: str | None = Field(
        default=None,
        description="The slot that triggered the failure, if any.",
    )
