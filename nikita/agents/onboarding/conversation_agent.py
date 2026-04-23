"""Pydantic AI conversation agent for POST /converse (Spec 214 FR-11d).

Mirrors the main text-agent pattern (``nikita/agents/text/agent.py``):

- ``@lru_cache`` singleton via ``get_conversation_agent``.
- Anthropic prompt caching via
  ``AnthropicModelSettings(anthropic_cache_instructions=True)`` — the
  Pydantic AI equivalent of ``cache_control: {"type": "ephemeral"}`` on
  the system-prompt block.

**GH #402/#403 — consolidated discriminated-union output (AC-11d.5 path a)**

Walk W live evidence (2026-04-23): 7-tool fan-out caused the LLM to keep
emitting IdentityExtraction for phone and darkness inputs. Dynamic
instructions alone (path b) were insufficient because LLM tool-selection
bias operates before the system-prompt context is fully applied — the LLM
must still pick among 7 tools, and pick the wrong one.

Fix: remove all 7 ``@agent.tool`` registrations and replace with a single
``TurnOutput`` wrapper schema as ``output_type``. The LLM fills structured
fields rather than selecting among tools, eliminating the selection decision
entirely. Pydantic validates the ``SlotDelta.kind`` discriminator structurally.

``TurnOutput`` — single structured output per turn:
  - ``delta: SlotDelta | None`` — the extracted slot, or None for
    clarification / off-topic / backtracking turns.
  - ``reply: str`` — Nikita's conversational reply. Always required so
    every turn delivers both structured extraction AND a response.

The agent is STATELESS — no memory, no chapter behavior, no pipeline
prompt injection. The endpoint passes the full conversation history in
each call. This matches tech-spec §2.1 ("No memory, no chapter context,
no recall_memory tool").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.anthropic import AnthropicModelSettings

from nikita.agents.onboarding.conversation_prompts import (
    WIZARD_SYSTEM_PROMPT,
    render_dynamic_instructions,
)
from nikita.agents.onboarding.state import SlotDelta, WizardSlots
from nikita.config.models import Models

# Same model as the main text agent for voice consistency.
_MODEL_NAME = Models.sonnet()

# Spec 060 pattern: Anthropic prompt caching via model settings. Pydantic
# AI attaches ``cache_control: {"type": "ephemeral"}`` to the system
# block; the persona (long + stable) gets cached across turns.
CACHE_SETTINGS: AnthropicModelSettings = AnthropicModelSettings(
    anthropic_cache_instructions=True,
)


# ---------------------------------------------------------------------------
# TurnOutput — single structured output per turn (GH #402/#403)
# ---------------------------------------------------------------------------


class TurnOutput(BaseModel):
    """Wrapper schema for one conversation turn.

    The LLM fills both fields per turn:

    - ``delta``: the extracted slot (or None on clarification / off-topic /
      backtracking turns). ``SlotDelta.kind`` is a discriminated Literal so
      Pydantic validates structurally.
    - ``reply``: Nikita's conversational reply. Required on every turn so
      the endpoint always has a string to return to the frontend.

    Why a wrapper schema over ``output_type=[SlotDelta, str]``?
    The mixed-list form makes result.output EITHER a SlotDelta OR a str —
    never both. On extraction turns the reply would be missing. The wrapper
    ensures both are always present.

    AC-11d.5 path (a): single structured output, no @agent.tool registrations.
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


# ---------------------------------------------------------------------------
# ConverseDeps — per-run dependencies
# ---------------------------------------------------------------------------


@dataclass
class ConverseDeps:
    """Per-run dependencies for the conversation agent.

    ``state`` holds the cumulative WizardSlots reconstructed from the
    full conversation history BEFORE agent.run is called (T11, PR-B).
    The dynamic-instructions callable (render_dynamic_instructions) reads
    state.missing each turn to inject "STILL MISSING: ..." guidance.
    The output_validator updates state in-place after each turn.

    ``extracted`` is kept for import-compatibility (portal_onboarding.py
    still references it during the T4 transition window) but is never
    populated by the consolidated agent — use state.* instead.

    Spec 214 FR-11d / agentic-design-patterns.md §1 + §3.
    """

    user_id: UUID
    locale: str = "en"
    state: WizardSlots = field(default_factory=WizardSlots)


def _create_conversation_agent() -> Agent[ConverseDeps, TurnOutput]:
    """Build the Pydantic AI agent with consolidated TurnOutput output_type.

    GH #402/#403 (Walk W 2026-04-23): 7-tool fan-out removed. The agent
    emits a single TurnOutput per turn — no tool registrations, no
    tool-selection bias.

    GH #382 (D5, 2026-04-21): retries=4. First-turn structured-output
    schema mistakes need enough retries for the model to self-correct.
    """
    agent: Agent[ConverseDeps, TurnOutput] = Agent(
        _MODEL_NAME,
        deps_type=ConverseDeps,
        output_type=TurnOutput,
        system_prompt=WIZARD_SYSTEM_PROMPT,
        retries=4,
    )

    # Dynamic per-turn instructions — appended to system_prompt each turn.
    # Injects the list of slots still missing from cumulative WizardSlots
    # state, giving the LLM "what's left to collect" guidance.
    # Spec 214 FR-11d / agentic-design-patterns.md §3.
    agent.instructions(render_dynamic_instructions)

    # Output validator — post-output validation layer (agentic-design-patterns
    # §5, three-layer validation). Two responsibilities post-consolidation:
    #
    # 1. Validate reply quality: raise ModelRetry when wizard is incomplete
    #    and the reply is empty/missing.
    # 2. Apply the extracted delta to cumulative state so deps.state stays
    #    current for multi-turn runs in the same ConverseDeps instance.
    #    The endpoint's state_reconstruction path is the primary authority;
    #    this in-process update supports single-session multi-turn test
    #    scenarios.
    @agent.output_validator
    def _validate_and_apply(
        ctx: RunContext[ConverseDeps], output: TurnOutput
    ) -> TurnOutput:
        """Validate reply quality and apply delta to cumulative state."""
        # Enforce non-empty reply when wizard is still incomplete.
        if not ctx.deps.state.is_complete and not output.reply.strip():
            raise ModelRetry(
                "Reply is empty. You must always include a conversational "
                "reply in the 'reply' field."
            )

        # Apply the extraction delta to cumulative state (Hard Rule §1).
        if output.delta is not None:
            ctx.deps.state = ctx.deps.state.apply(output.delta)

        return output

    return agent


@lru_cache(maxsize=1)
def get_conversation_agent() -> Agent[ConverseDeps, TurnOutput]:
    """Return the cached conversation-agent singleton.

    Lazy init mirrors the main text agent; avoids API-key errors during
    import/testing.
    """
    return _create_conversation_agent()


__all__ = [
    "CACHE_SETTINGS",
    "ConverseDeps",
    "TurnOutput",
    "get_conversation_agent",
]
