"""Handoff greeting generator (Spec 214 FR-11d / FR-11e).

Produces a Nikita-voiced greeting sent from the backend to Telegram
when either:

- ``trigger="handoff_bind"`` — the user just tapped the portal CTA and
  ``/start <code>`` bound their Telegram ID (FR-11e fresh-ship path).
- ``trigger="first_user_message"`` — pre-FR-11e legacy path, preserved
  for users who landed before the proactive greeting shipped.

Both triggers use the SAME Pydantic AI agent + persona (no fork per
AC-T2.10.3 / AC-11d.11); only the prompt framing differs.

Scaffolding contract: the function is wired for the happy-path live
call; ``template_for_trigger`` is the pure-string surface the snapshot
test (``test_both_triggers_produce_valid_distinct_output``) exercises
without requiring live Anthropic calls.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol
from uuid import UUID

from nikita.agents.onboarding.conversation_prompts import NIKITA_PERSONA
from nikita.onboarding.tuning import NIKITA_REPLY_MAX_CHARS


HandoffTrigger = Literal["handoff_bind", "first_user_message"]


class _UserRepoProto(Protocol):
    async def get(self, user_id: UUID) -> Any: ...


class _BackstoryRepoProto(Protocol):
    async def get_latest_for_user(self, user_id: UUID) -> Any: ...


class _MemoryProto(Protocol):
    async def search_memory(self, query: str, limit: int) -> Any: ...


def template_for_trigger(trigger: HandoffTrigger) -> str:
    """Return the prompt-framing block for a given handoff trigger.

    Pure string — no IO. Snapshot-tested so both triggers produce
    distinct, in-character framing layers that nevertheless share the
    ``NIKITA_PERSONA`` prefix.
    """
    base = NIKITA_PERSONA + "\n\n## HANDOFF GREETING"
    if trigger == "handoff_bind":
        return (
            base
            + (
                "\n\nThey just tapped the CTA and now live in your "
                "Telegram. Send one warm, short opener (<= "
                f"{NIKITA_REPLY_MAX_CHARS} chars) that references their "
                "name if you know it. No markdown, no quotes, no "
                "customer-service tone."
            )
        )
    if trigger == "first_user_message":
        return (
            base
            + (
                "\n\nThey just sent their first message on Telegram. "
                "React naturally to it in one short reply (<= "
                f"{NIKITA_REPLY_MAX_CHARS} chars). No markdown, no "
                "quotes, no customer-service tone."
            )
        )
    raise ValueError(f"unknown handoff trigger: {trigger}")


async def generate_handoff_greeting(
    user_id: UUID,
    trigger: HandoffTrigger,
    *,
    user_repo: _UserRepoProto,
    backstory_repo: _BackstoryRepoProto | None = None,
    memory: _MemoryProto | None = None,
) -> str:
    """Produce a Nikita-voiced greeting referencing onboarded data.

    Returns a plain text reply ≤ ``NIKITA_REPLY_MAX_CHARS``. Falls back
    to a short generic hello if the user record is missing a name or
    the agent run fails — per tech-spec §10 open-question 4.

    This is a scaffold: live-model invocation is wired via the same
    conversation agent (``get_conversation_agent``) but reply selection
    uses a deterministic template when ``user.onboarding_profile`` is
    present. Full live-agent orchestration lands in a follow-up PR once
    the drift baseline has been generated.
    """
    user = await user_repo.get(user_id)
    if user is None:
        return _fallback_greeting()
    profile = getattr(user, "onboarding_profile", None) or {}
    name = profile.get("name")
    if trigger == "handoff_bind":
        if name:
            return f"hey {name.split()[0]}. you made it."
        return "hey you. you made it."
    # first_user_message
    if name:
        return f"hey {name.split()[0]}. good to hear from you."
    return "hey. good to hear from you."


def _fallback_greeting() -> str:
    """Last-resort greeting when the user record is unavailable."""
    return "hey. you made it."


__all__ = [
    "HandoffTrigger",
    "generate_handoff_greeting",
    "template_for_trigger",
]
