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
from typing import Any, Callable, Final
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

    PURE function (T-B3-12, closes GH #453 N1 nitpick): validate-or-retry only.
    State mutation moved to ``apply_turn_delta`` so route handlers explicitly
    own the timing of state application post-``agent.run``. Removing the
    mutation here closes a subtle bug class: a future contributor adding a
    ``raise ModelRetry`` check below the apply call would cause retries to
    double-merge the delta.

    On TurnOutput:
      - reject mirror-echo (last_value repeated >=2 times in reply, closes #443)
      - reject reply > REPLY_LENGTH_CAP chars (raise ModelRetry for self-correction)

    On TurnFailure:
      - pass-through; no length / mirror-echo guard. The FE renders the
        explanation as a graceful re-ask.

    Callers (route handlers): after ``agent.run`` returns successfully, call
    ``apply_turn_delta(state, result.output)`` to merge the extracted delta
    into the cumulative state.
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

    return output


def apply_turn_delta(
    state: WizardSlots,
    output: TurnOutput | TurnFailure,
) -> WizardSlots:
    """Merge a turn's extracted delta into cumulative wizard state.

    Pure function (immutable update via ``WizardSlots.apply``). No-ops on:
      - ``TurnFailure`` (graceful re-ask does not advance the wizard)
      - ``TurnOutput`` with ``delta=None`` (clarification / off-topic turns)

    Route handlers call this post-``agent.run`` to advance the cumulative
    state. Separated from ``_validate_output`` (T-B3-12, closes GH #453 N1)
    so state mutation timing is owned by the handler, not the validator.
    """
    if isinstance(output, TurnFailure):
        return state
    if output.delta is None:
        return state
    return state.apply(output.delta)


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
    - 4 firecrawl ``@agent.tool`` decorators (Spec 216-E E1.1/E1.12) —
      registered as application-side custom tools. WebSearchTool builtin
      removed in Spec 218 PR-218-PREREQ-A (firecrawl-only architecture per
      brief §23.2).
    """
    # Late import: tools depend on this module via TYPE_CHECKING.
    from nikita.agents.onboarding.tools.firecrawl_tools import (  # noqa: PLC0415
        fetch_city_context,
        fetch_occupation_signal,
        fetch_time_of_day_signal,
        fetch_topic_specific,
    )

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

    # Spec 216-E E1.1/E1.12: 4 application-side fetch_* tools (firecrawl).
    # Spec 218 PR-218-PREREQ-A removed the provider-native WebSearchTool
    # builtin — agent runs with firecrawl @agent.tool decorators only.
    agent.tool(fetch_city_context)
    agent.tool(fetch_occupation_signal)
    agent.tool(fetch_time_of_day_signal)
    agent.tool(fetch_topic_specific)

    return agent


@lru_cache(maxsize=1)
def get_conversation_agent() -> Agent[ConverseDeps, TurnOutput | TurnFailure]:
    """Return the cached conversation-agent singleton."""
    return _create_conversation_agent()


# ---------------------------------------------------------------------------
# 217-3A.2 — Emission union agent (ReactionOnly | FollowUpQuestion | TurnFailure)
#
# The agent layer for the deterministic-redesign emission contract per
# Spec 217-3A AC-5.x / 6.x / 7.x. Built as a PARALLEL agent so the
# legacy ``get_conversation_agent`` (which the /answer route still
# consumes via its TurnOutput-shaped dispatch) keeps working until
# 217-3A.3 swaps the route over.
#
# Deferral note (Spec 217-3A.2 PR scope decision):
#   AC-9.x (/answer route dispatch on emission union) and AC-10a
#   (IdentityPair BE partial-validation) are deferred to a follow-up
#   sub-PR (217-3A.3). The route refactor would invalidate ~77
#   legacy-shape assertions across 4 test files (~2164 LOC of legacy
#   tests) — a clean cut belongs in a dedicated PR. This sub-PR ships:
#     - schema (CompletionResponse 6th branch, AnswerResponse union)
#     - emission-union agent factory (this section)
#     - sidecar persistence helpers (sidecar_persistence.py)
#     - calibration fixtures + AC-T-1..5 + AC-7.4 tests
# ---------------------------------------------------------------------------


def build_emission_output_validator(
    converse_contracts_module: Any | None = None,
    validators_module: Any | None = None,
) -> Callable[[RunContext[ConverseDeps], Any], Any]:
    """Construct the emission-union output validator.

    AC-7.1 / AC-7.2 / AC-7.3 — reject ``FollowUpQuestion.question_text``
    AND ``ReactionOnly.reaction_text`` that mirror the next deterministic
    question (similarity > 0.85) OR mirror the user's last answer
    verbatim. Failures are lifted to ``ModelRetry`` for the Pydantic AI
    self-correction loop.

    Implemented as a builder so tests can inject mock validator modules
    without monkey-patching the importer (``.claude/rules/testing.md``
    "Patch source module, not importer" rule). The default lookup
    imports the production modules.

    Returns:
        Validator function suitable for ``@agent.output_validator``.
    """
    # Late imports — avoid module-load cycles with converse_contracts.
    from nikita.agents.onboarding import converse_contracts as _cc  # noqa: PLC0415
    from nikita.agents.onboarding import validators as _v  # noqa: PLC0415

    cc = converse_contracts_module or _cc
    v = validators_module or _v

    def _validator(
        ctx: RunContext[ConverseDeps],
        output: Any,
    ) -> Any:
        """Validate emission text against mirror-of-next + mirror-echo."""
        text: str | None = None
        if isinstance(output, cc.FollowUpQuestion):
            text = output.question_text
        elif isinstance(output, cc.ReactionOnly):
            text = output.reaction_text
        # TurnFailure (and any unknown type) passes unchanged — no text
        # to validate; the FE renders the explanation as a graceful re-ask.
        if text is None:
            return output

        next_q = ctx.deps.next_slot_hint or ""
        last_a = ctx.deps.last_value or ""

        try:
            v.validate_no_mirror_of_next(text, next_question=next_q)
            v.validate_no_mirror_echo(text, last_user_answer=last_a)
        except ValueError as exc:
            # Lift to ModelRetry per Pydantic AI self-correction
            # convention (AC-7.3).
            raise ModelRetry(str(exc)) from exc
        return output

    return _validator


def _create_emission_agent() -> Agent[ConverseDeps, Any]:
    """Build the 217-3A.2 emission-union agent (parallel to legacy).

    Wires the three-branch ``ToolOutput`` discriminated union:
      - ``ReactionOnly``  (name="emit_reaction") — slot NOT advanced
      - ``FollowUpQuestion`` (name="ask_followup") — sidecar persisted
      - ``TurnFailure``   (name="turn_failure") — graceful re-ask

    Per AC-5.2: ``output_type=[ToolOutput(...), ToolOutput(...), ToolOutput(...)]``.
    Per AC-6.1: dynamic per-turn instructions via ``@agent.instructions``
    decorator (NOT a static system prompt — Pydantic AI 1.56 docs:
    "dynamic instructions are always reevaluated").
    Per AC-6.3: ``output_retries=2`` for explicit retry budget on
    output validation; spec exhaustion → ``UnexpectedModelBehavior``
    raised → route layer converts to TurnFailure emission (217-3A.3
    scope).
    Per AC-7.x: ``@agent.output_validator`` rejects mirror-of-next +
    mirror-echo via ``ModelRetry``.
    """
    # Late imports — avoid load cycles + keep the legacy agent factory
    # decoupled from emission-union types.
    from pydantic_ai import ToolOutput  # noqa: PLC0415

    from nikita.agents.onboarding.converse_contracts import (  # noqa: PLC0415
        FollowUpQuestion,
        ReactionOnly,
    )
    from nikita.agents.onboarding.converse_contracts import (  # noqa: PLC0415
        TurnFailure as EmissionTurnFailure,
    )

    agent: Agent[ConverseDeps, Any] = Agent(
        _MODEL_NAME,
        deps_type=ConverseDeps,
        output_type=[
            ToolOutput(ReactionOnly, name="emit_reaction"),
            ToolOutput(FollowUpQuestion, name="ask_followup"),
            ToolOutput(EmissionTurnFailure, name="turn_failure"),
        ],
        output_retries=2,
    )

    # Dynamic per-turn instructions — AC-6.1 / AC-6.2.
    agent.instructions(inject_per_turn_context)

    # Output validator — AC-7.x mirror-of-next + mirror-echo + ModelRetry.
    validator_fn = build_emission_output_validator()

    @agent.output_validator
    def _wrapped(
        ctx: RunContext[ConverseDeps],
        output: Any,
    ) -> Any:
        return validator_fn(ctx, output)

    return agent


@lru_cache(maxsize=1)
def get_emission_agent() -> Agent[ConverseDeps, Any]:
    """Return the cached emission-union agent singleton (217-3A.2)."""
    return _create_emission_agent()


__all__ = [
    "CACHE_SETTINGS",
    "ConverseDeps",
    "TurnFailure",
    "TurnOutput",
    "_validate_output",
    "apply_turn_delta",
    "build_emission_output_validator",
    "get_conversation_agent",
    "get_emission_agent",
]
