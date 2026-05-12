"""Spec 218 Slice 218-6 — v2 backstory generation for Phase-2 completion.

Generates a short backstory preview (≤560 chars) from the user's Phase-1
slots + Phase-2 conversation messages. The preview is surfaced in
`CompleteAsk.backstory_preview` on the celebration screen.

Design:
  - `generate_v2_backstory(slots, phase2_messages)` is the public entry point.
  - `_run_backstory_agent(slots, messages)` does the actual LLM call.
    Separated so tests can patch the inner call without patching the LLM SDK.
  - `BackstoryGenerationError` wraps all LLM failures so callers don't
    handle raw Pydantic AI exceptions (isolation boundary).
  - Output is truncated to 560 chars to satisfy `CompleteAsk.backstory_preview`
    `max_length` (FR-002 atomicity — the caller persists slots + preview
    in the same JSONB update that stamps `Phase.complete`).

The backstory is NOT stored separately in the DB (no new column); it lives
in the `onboarding_profile.completion.backstory_preview` JSONB key and
is embedded directly in `CompleteAsk.backstory_preview` for the FE.

Slice 218-7 (phone-demo wow) does NOT touch this module.
Slice 218-8 (atomic bulldoze) keeps this module unchanged.
"""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent

from nikita.agents.onboarding.v2.state import WizardSlotsV2
from nikita.config.models import Models


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BACKSTORY_PREVIEW_MAX_LEN: int = 560
"""Max chars for CompleteAsk.backstory_preview (mirrors envelope.py Field max_length)."""

_MODEL_NAME = Models.sonnet()


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class BackstoryGenerationError(Exception):
    """Raised by generate_v2_backstory when the LLM call fails.

    Wraps any internal exception (model timeout, ValidationError,
    Pydantic AI exception) so callers handle one known error type.
    """


# ---------------------------------------------------------------------------
# Internal agent call
# ---------------------------------------------------------------------------


async def _run_backstory_agent(
    slots: WizardSlotsV2,
    phase2_messages: list[dict[str, Any]],
) -> str:
    """Call the LLM to generate a backstory preview string.

    Separated from ``generate_v2_backstory`` for testability (tests patch
    this function, not the Pydantic AI Agent constructor).
    """
    # Summarise slots for the prompt
    slot_lines: list[str] = []
    if slots.display_name:
        slot_lines.append(f"Name: {slots.display_name.get('display_name', '')}")
    if slots.age:
        slot_lines.append(f"Age: {slots.age.get('age', '?')}")
    if slots.city:
        slot_lines.append(f"City: {slots.city.get('city', '?')}")
    if slots.occupation:
        slot_lines.append(f"Occupation: {slots.occupation.get('occupation', '?')}")
    if slots.primary_hobbies:
        hobbies = slots.primary_hobbies.get("primary_hobbies", [])
        slot_lines.append(f"Hobbies: {', '.join(hobbies)}")
    if slots.saturday_morning:
        slot_lines.append(
            f"Saturday morning: {slots.saturday_morning.get('saturday_morning', '?')}"
        )
    if slots.darkness_level:
        slot_lines.append(
            f"Darkness level: {slots.darkness_level.get('darkness_level', '?')}/10"
        )
    if slots.geek_out_on:
        slot_lines.append(f"Geeks out on: {slots.geek_out_on.get('geek_out_on', '?')}")

    slot_summary = "\n".join(slot_lines) or "(no slot data)"

    # Summarise Phase-2 messages
    p2_lines: list[str] = []
    for msg in phase2_messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "assistant":
            p2_lines.append(f"Nikita asked: {content}")
        elif role == "user":
            p2_lines.append(f"User said: {content}")
    phase2_summary = "\n".join(p2_lines) or "(no Phase-2 conversation)"

    system_prompt = f"""You are Nikita's narrator. Write ONE evocative sentence (≤120 chars)
that captures who this person IS — their energy, vibe, defining trait.
Think: the opening line of a great short story, not a CV summary.

User profile:
{slot_summary}

Phase-2 conversation:
{phase2_summary}

Return ONLY the sentence. No preamble, no quotation marks."""

    agent: Agent[None, str] = Agent(
        _MODEL_NAME,
        output_type=str,
        system_prompt=system_prompt,
    )
    result = await agent.run("")
    return result.output.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_v2_backstory(
    slots: WizardSlotsV2,
    phase2_messages: list[dict[str, Any]],
) -> str:
    """Generate a short backstory preview from Phase-1 slots + Phase-2 chat.

    Args:
        slots: Completed Phase-1 slot state.
        phase2_messages: Raw Phase-2 message dicts (role + content).
                         May be empty (e.g., forced complete at MAX_TURNS).

    Returns:
        A non-empty string ≤ 560 chars suitable for `CompleteAsk.backstory_preview`.

    Raises:
        BackstoryGenerationError: If the LLM call fails for any reason.
    """
    try:
        preview = await _run_backstory_agent(slots, phase2_messages)
    except Exception as exc:  # noqa: BLE001 — intentional isolation
        raise BackstoryGenerationError(
            f"backstory generation failed: {exc}"
        ) from exc

    # Truncate to max_length to be safe even if LLM ignores the 120-char hint
    return preview[:_BACKSTORY_PREVIEW_MAX_LEN]


__all__ = [
    "BackstoryGenerationError",
    "_run_backstory_agent",
    "generate_v2_backstory",
]
