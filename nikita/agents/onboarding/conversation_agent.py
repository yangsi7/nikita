"""Pydantic AI conversation agent for the 13-slot wizard (Spec 216-B1+B2).

Replaces the prior 7-tool agent with a single ``output_type`` discriminated
union ``[TurnOutput, TurnFailure]``. The agent uses
``Agent(instructions=callable)`` for per-turn routing rules (Hard Rule §6
— routing rules MUST live in the dynamic callable, NOT in a static
``system_prompt``).

Validation layering (Hard Rule §5):
- Structured-output schema (Pydantic) at the LLM boundary
- ``@agent.output_validator`` post-output validation (mirror-echo, length)
- Deterministic post-processing in 216-B3 endpoint (216-B1+B2 ships only
  the agent-side gates).

``ConverseDeps`` (B1.19) — 14 fields per master-spec Type System Anchors.
The firecrawl-related fields and big5_confidence are initialised but
unused in 216-B1+B2; they get wired in 216-D-code and 216-E. Don't strip
them — 216-D-code/E need them present without contract churn.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Final
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.anthropic import AnthropicModelSettings

from nikita.agents.onboarding.conversation_prompts import inject_per_turn_context
from nikita.agents.onboarding.question_registry import SlotKind
from nikita.agents.onboarding.state import SlotDelta, WizardSlots
from nikita.config.models import Models

# Same model as the main text agent for voice consistency.
_MODEL_NAME = Models.sonnet()

# Anthropic prompt caching via model settings — caches the static FIXED
# instruction prefix across turns (B1.20 / NR-02).
CACHE_SETTINGS: AnthropicModelSettings = AnthropicModelSettings(
    anthropic_cache_instructions=True,
)


# ---------------------------------------------------------------------------
# Tuning constants (per .claude/rules/tuning-constants.md)
# ---------------------------------------------------------------------------

REPLY_LENGTH_CAP: Final[int] = 140
"""Wizard-agent reply-length cap, in characters.

Prior values:
  none (new in Spec 216-B, B1.5).
Rationale: Spec 216-B-agentic-wizard-core line 84 mandates ≤140 chars for
wizard turns ("dark luxe, slightly menacing, ≤140 chars, no emoji, no
markdown"). Intentionally tighter than the global
``NIKITA_REPLY_MAX_CHARS=280`` (nikita/onboarding/tuning.py:171) — the
main text agent allows two SMS segments for narrative flow, but the
wizard requires one tweet-length segment to keep the onboarding cadence
crisp. Regression-guarded by tests/agents/onboarding/test_validators.py
(@output_validator length cases).
"""


# ---------------------------------------------------------------------------
# TurnOutput / TurnFailure — discriminated union (B1.3)
# ---------------------------------------------------------------------------


class TurnOutput(BaseModel):
    """Happy-path turn output: extraction delta + reply + next routing hint.

    The LLM emits a SlotDelta when an extraction is appropriate, OR
    ``delta=None`` for clarification / off-topic / backtracking turns.
    ``reply`` is always required so every turn returns a string to FE.
    ``next_slot_kind`` is typed as ``SlotKind | None`` (B1.18) — not an
    inline ``Literal[...]``.
    """

    delta: SlotDelta | None = Field(
        default=None,
        description=(
            "The extracted wizard slot for this turn, or None for "
            "clarification / off-topic / backtracking turns."
        ),
    )
    reply: str = Field(
        min_length=1,
        description="Nikita's conversational reply. Always non-empty.",
    )
    next_slot_kind: SlotKind | None = Field(
        default=None,
        description=(
            "Routing hint for the next turn — which slot the LLM expects "
            "to ask about next. None means 'no preference'."
        ),
    )


class TurnFailure(BaseModel):
    """Graceful re-ask output when the user's input cannot be processed.

    Emitted in-character when the user provides invalid data (under-18,
    abusive, contradictions). The FE treats this as a graceful re-ask;
    the agent NEVER throws an exception (Hard Rule §5 — fail soft).
    """

    explanation: str = Field(
        min_length=1,
        description=(
            "In-character message explaining why the input was rejected, "
            "e.g. 'eighteen and up only.'"
        ),
    )
    last_slot_kind: SlotKind | None = Field(
        default=None,
        description="The slot that triggered the failure, if any.",
    )


# ---------------------------------------------------------------------------
# ConverseDeps — per-run dependencies (B1.19, 14 fields)
# ---------------------------------------------------------------------------


@dataclass
class ConverseDeps:
    """Per-run dependencies for the conversation agent (B1.19).

    14 fields per master-spec Type System Anchors. Fields used by 216-B1+B2:
      - state, state_summary, last_slot_kind, last_value, next_slot_kind,
        next_slot_hint, traceparent, user_id, conversation_id

    Fields wired in later PRs (216-D-code, 216-E) but present here to
    avoid contract churn:
      - cost_budget_remaining_usd — wired by CostGuard (B1.8)
      - fetch_invocations_this_turn, fetch_cost_cumulative — wired by 216-E
      - cohort_cache, big5_confidence — wired by 216-D-code
    """

    user_id: UUID
    conversation_id: UUID = field(default_factory=uuid4)
    state: WizardSlots = field(default_factory=WizardSlots)
    state_summary: str = ""
    last_slot_kind: SlotKind | None = None
    last_value: str | None = None
    next_slot_kind: SlotKind | None = None
    next_slot_hint: str | None = None
    cost_budget_remaining_usd: float = 1.00
    fetch_invocations_this_turn: int = 0
    fetch_cost_cumulative: float = 0.0
    cohort_cache: dict[str, Any] = field(default_factory=dict)
    big5_confidence: dict[str, float] = field(default_factory=dict)
    traceparent: str = ""


# ---------------------------------------------------------------------------
# Output validator (B1.5) — mirror-echo + length + delta-apply
# ---------------------------------------------------------------------------


def _validate_output(
    ctx: RunContext[ConverseDeps],
    output: TurnOutput | TurnFailure,
) -> TurnOutput | TurnFailure:
    """B1.5 output validator — second of three validation layers.

    On TurnOutput:
      - reject mirror-echo (last_value repeated >=2 times in reply, closes #443)
      - reject reply > 140 chars (raise ModelRetry for self-correction)
      - apply delta to ``ctx.deps.state`` so cumulative state stays current
        across multi-turn runs in the same ConverseDeps instance.

    On TurnFailure:
      - pass-through; no length / mirror-echo guard. The FE renders the
        explanation as a graceful re-ask.
    """
    if isinstance(output, TurnFailure):
        return output

    # Mirror-echo guard (closes #443) — applies when the last slot was a
    # name-shaped slot and the reply repeats the user's literal value twice.
    last_kind = getattr(ctx.deps, "last_slot_kind", None)
    last_value = getattr(ctx.deps, "last_value", None)
    name_kinds = {SlotKind.display_name}
    if last_kind in name_kinds and last_value:
        # Two or more occurrences of the value (case-insensitive)
        lowered = output.reply.lower()
        token = last_value.lower()
        if token and lowered.count(token) >= 2:
            raise ModelRetry(
                "Reply mirror-echoes the user's name (>=2 occurrences). "
                "Acknowledge once and move on; rewrite without verbatim repetition."
            )

    # Length cap
    if len(output.reply) > REPLY_LENGTH_CAP:
        raise ModelRetry(
            f"Reply exceeds {REPLY_LENGTH_CAP} chars ({len(output.reply)}); compress."
        )

    # Apply delta to cumulative state (Hard Rule §1 wiring)
    if output.delta is not None:
        ctx.deps.state = ctx.deps.state.apply(output.delta)

    return output


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def _create_conversation_agent() -> Agent[ConverseDeps, TurnOutput | TurnFailure]:
    """Build the Pydantic AI agent.

    - ``output_type=[TurnOutput, TurnFailure]`` discriminated union (B1.3)
    - ``Agent(instructions=callable)`` per-turn (Hard Rule §6) — NO static
      ``system_prompt=`` for routing rules.
    - ``@agent.output_validator`` for mirror-echo + length + delta-apply (B1.5)
    - ``retries=2`` for self-correcting model behavior (B1.5).
    """
    agent: Agent[ConverseDeps, TurnOutput | TurnFailure] = Agent(
        _MODEL_NAME,
        deps_type=ConverseDeps,
        output_type=[TurnOutput, TurnFailure],
        retries=2,
    )

    # Dynamic per-turn instructions — Hard Rule §6.
    agent.instructions(inject_per_turn_context)

    # Output validator — Hard Rule §5 second layer.
    @agent.output_validator
    def _wrapped_validator(
        ctx: RunContext[ConverseDeps],
        output: TurnOutput | TurnFailure,
    ) -> TurnOutput | TurnFailure:
        return _validate_output(ctx, output)

    return agent


@lru_cache(maxsize=1)
def get_conversation_agent() -> Agent[ConverseDeps, TurnOutput | TurnFailure]:
    """Return the cached conversation-agent singleton."""
    return _create_conversation_agent()


__all__ = [
    "CACHE_SETTINGS",
    "ConverseDeps",
    "TurnFailure",
    "TurnOutput",
    "_validate_output",
    "get_conversation_agent",
]
