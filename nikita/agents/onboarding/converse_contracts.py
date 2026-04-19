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
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nikita.agents.onboarding.control_selection import ControlSelection


class Turn(BaseModel):
    """Single conversation turn (role + content) in the request history."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["nikita", "user"]
    content: str = Field(max_length=2000)
    extracted: dict[str, Any] | None = None
    timestamp: datetime
    source: Literal["llm", "fallback"] | None = None


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
    source: Literal["llm", "fallback"]
    latency_ms: int = Field(ge=0)


__all__ = [
    "ConverseRequest",
    "ConverseResponse",
    "Turn",
]
