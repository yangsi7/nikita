"""Wizard v2 8-shape ``AskUnion`` discriminated-union envelope (FR-005).

Per spec 218 §23.1 + FR-005, the wizard supports exactly 8 component
shapes — NO MORE. Each shape maps 1:1 to a shadcn/ui registry primitive
(per ``portal/components.json``). Reaction-only beats are NOT a separate
shape; reaction text is folded into the next Ask's ``prompt`` field.

8 shapes:

  1. ``text_short``     — short text input (Input + Button + dictation toggle)
  2. ``text_long``      — long text input (Textarea + dictation toggle)
  3. ``single_select``  — radio choice (RadioGroup)
  4. ``chip_multi``     — multi-chip selection (Button[] toggles)
  5. ``slider``         — numeric slider (Slider)
  6. ``calendar``       — date picker (Calendar + Popover)
  7. ``phone``          — phone-number input (Input + libphonenumber)
  8. ``complete``       — terminal celebration + handoff

The discriminator field is ``component`` (string Literal per shape).
``AskUnion = Annotated[Union[...], Field(discriminator="component")]``
is the FastAPI ``response_model`` for the v2 ``/onboarding/answer`` route
(wired in PR-218-3).

Per pattern-scout REUSE lock (spec 218 §20): mirror the
``Annotated[Union, Field(discriminator=...)]`` pattern from
``nikita/api/schemas/onboarding.py:206-216``. Each branch uses
``ConfigDict(extra="forbid")`` so the FE / BE wire is strict on shape;
unknown fields are rejected at parse time.

PR-218-1 ships the schema only. PR-218-2 wires the decorator agent's
``output_type`` to this union via ``ToolOutput`` wrappers. PR-218-3
wires the route handler ``response_model``.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared sub-types
# ---------------------------------------------------------------------------


class Option(BaseModel):
    """One choice in a ``single_select`` or ``chip_multi`` Ask.

    ``value`` is the canonical machine-readable string the BE persists.
    ``label`` is the human-readable text rendered in the UI.
    ``blurb`` is an optional 1-line decoration shown below the option.
    """

    model_config = ConfigDict(extra="forbid")

    value: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=140)
    blurb: str | None = Field(default=None, max_length=280)


# ---------------------------------------------------------------------------
# Per-shape Ask envelopes
# ---------------------------------------------------------------------------


class TextShortAsk(BaseModel):
    """Short single-line free-text input.

    ``prompt`` is the agent-voiced narrator line; reaction text from the
    prior turn is folded in here (no separate reaction beat — see
    spec 218 §23.1 + FR-005).

    ``handler`` (Slice 218-2 / plan R14): always ``"v2"`` for shapes the
    v2 decorator emits. FE dispatcher switches on this field BEFORE
    ``component`` so the v2-prefix-with-v1-tail model is transparent.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    component: Literal["text_short"] = "text_short"
    handler: Literal["v2"] = "v2"
    slot: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=560)
    placeholder: str = Field(default="", max_length=140)
    max_chars: int = Field(default=80, ge=1, le=500)
    dictation: bool = False
    autocomplete: bool = False
    progress_pct: int | None = Field(default=None, ge=0, le=100)


class TextLongAsk(BaseModel):
    """Long multi-line free-text input (Phase 2 only typically)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    component: Literal["text_long"] = "text_long"
    handler: Literal["v2"] = "v2"
    slot: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=560)
    placeholder: str = Field(default="", max_length=280)
    max_chars: int = Field(default=500, ge=1, le=2000)
    dictation: bool = False
    progress_pct: int | None = Field(default=None, ge=0, le=100)


class SingleSelectAsk(BaseModel):
    """Radio-style single-select choice."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    component: Literal["single_select"] = "single_select"
    handler: Literal["v2"] = "v2"
    slot: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=560)
    options: list[Option] = Field(min_length=2, max_length=8)
    progress_pct: int | None = Field(default=None, ge=0, le=100)


class ChipMultiAsk(BaseModel):
    """Multi-chip selection.

    ``min_pick`` / ``max_pick`` enforce client-side + server-side
    cardinality. Validator ensures ``min_pick <= max_pick <= len(options)``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    component: Literal["chip_multi"] = "chip_multi"
    handler: Literal["v2"] = "v2"
    slot: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=560)
    options: list[Option] = Field(min_length=2, max_length=24)
    min_pick: int = Field(default=1, ge=0)
    max_pick: int = Field(default=8, ge=1)
    progress_pct: int | None = Field(default=None, ge=0, le=100)

    def model_post_init(self, _ctx: object) -> None:
        if self.min_pick > self.max_pick:
            raise ValueError(
                f"chip_multi min_pick ({self.min_pick}) must be <= max_pick ({self.max_pick})"
            )
        if self.max_pick > len(self.options):
            raise ValueError(
                f"chip_multi max_pick ({self.max_pick}) must be <= len(options) ({len(self.options)})"
            )


class SliderAsk(BaseModel):
    """Numeric slider with labelled tick marks.

    ``labels`` is a sparse map from int value to label string (e.g.,
    ``{1: "vanilla", 5: "noir"}``); intermediate ticks are rendered
    unlabelled.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    component: Literal["slider"] = "slider"
    handler: Literal["v2"] = "v2"
    slot: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=560)
    min_val: int
    max_val: int
    step: int = Field(default=1, ge=1)
    labels: dict[int, str] = Field(default_factory=dict)
    progress_pct: int | None = Field(default=None, ge=0, le=100)

    def model_post_init(self, _ctx: object) -> None:
        if self.min_val >= self.max_val:
            raise ValueError(
                f"slider min_val ({self.min_val}) must be < max_val ({self.max_val})"
            )


class CalendarAsk(BaseModel):
    """Date picker with optional ISO-8601 min / max constraints."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    component: Literal["calendar"] = "calendar"
    handler: Literal["v2"] = "v2"
    slot: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=560)
    min_date: str | None = Field(default=None, max_length=10)
    max_date: str | None = Field(default=None, max_length=10)
    progress_pct: int | None = Field(default=None, ge=0, le=100)


class PhoneAsk(BaseModel):
    """Phone-number input with libphonenumber-driven validation.

    ``demo_call_after_submit`` triggers the FR-009 opt-in modal after
    the user submits a valid phone. Default ``True`` for the canonical
    Phase 1 phone slot; PR-218-6 wires the actual outbound call.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    component: Literal["phone"] = "phone"
    handler: Literal["v2"] = "v2"
    slot: Literal["phone"] = "phone"
    prompt: str = Field(min_length=1, max_length=560)
    default_country: str = Field(default="US", min_length=2, max_length=2)
    demo_call_after_submit: bool = True
    progress_pct: int | None = Field(default=None, ge=0, le=100)


class CompleteAsk(BaseModel):
    """Terminal envelope — wizard is complete; handoff next.

    ``next_route`` is the FE route the WizardThread should navigate to
    (typically ``/dashboard`` or a Telegram-bind QR handoff).
    ``backstory_preview`` is the optional first line of the generated
    backstory for the celebration screen.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    component: Literal["complete"] = "complete"
    handler: Literal["v2"] = "v2"
    next_route: str = Field(min_length=1, max_length=256)
    backstory_preview: str | None = Field(default=None, max_length=560)
    progress_pct: int | None = Field(default=None, ge=0, le=100)


# ---------------------------------------------------------------------------
# AskUnion — discriminated-union envelope
# ---------------------------------------------------------------------------


AskUnion = Annotated[
    Union[
        TextShortAsk,
        TextLongAsk,
        SingleSelectAsk,
        ChipMultiAsk,
        SliderAsk,
        CalendarAsk,
        PhoneAsk,
        CompleteAsk,
    ],
    Field(discriminator="component"),
]
"""Discriminated-union envelope for ``POST /onboarding/answer`` v2.

Wire example (chip_multi for personalized hangouts)::

    {
      "component": "chip_multi",
      "slot": "hangouts_personalized",
      "prompt": "noticed you're a software engineer in Berlin — which of these vibe?",
      "options": [
        {"value": "berghain", "label": "Berghain"},
        {"value": "kitkat", "label": "KitKat"},
        {"value": "tresor", "label": "Tresor"}
      ],
      "min_pick": 1,
      "max_pick": 3
    }

FastAPI emits this as a stable ``oneOf`` schema in OpenAPI; FE
TypeScript codegen narrows on ``component`` discriminator (mirror in
``portal/src/app/onboarding/v2/types/envelope.ts``).
"""


__all__ = [
    "AskUnion",
    "CalendarAsk",
    "ChipMultiAsk",
    "CompleteAsk",
    "Option",
    "PhoneAsk",
    "SingleSelectAsk",
    "SliderAsk",
    "TextLongAsk",
    "TextShortAsk",
]
