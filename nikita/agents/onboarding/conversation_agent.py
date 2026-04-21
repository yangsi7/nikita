"""Pydantic AI conversation agent for POST /converse (Spec 214 FR-11d).

Mirrors the main text-agent pattern (``nikita/agents/text/agent.py``):

- ``@lru_cache`` singleton via ``get_conversation_agent``.
- Anthropic prompt caching via
  ``AnthropicModelSettings(anthropic_cache_instructions=True)`` — the
  Pydantic AI equivalent of ``cache_control: {"type": "ephemeral"}`` on
  the system-prompt block.
- One ``@agent.tool`` per extraction schema — the agent emits a tool
  call when it decides to extract a field. Each tool appends the typed
  schema instance to ``ctx.deps.extracted`` (a sidecar list) and
  returns a short acknowledgement string consumed by the model. The
  endpoint reads the natural-language reply off ``result.output`` and
  the structured extraction off ``deps.extracted``.

The agent is STATELESS — no memory, no chapter behavior, no pipeline
prompt injection. The endpoint passes the full conversation history in
each call. This matches tech-spec §2.1 ("No memory, no chapter context,
no recall_memory tool").

QA iter-1 fix (B1, 2026-04-19): `output_type` was `ConverseResult`,
which forced the agent to emit structured output and made it impossible
to source `nikita_reply` from `result.output`. Refactored to
`output_type=str` + deps-scoped extraction sink so reply text comes
from the LLM and extraction comes from the tool calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from uuid import UUID

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModelSettings

from nikita.agents.onboarding.conversation_prompts import WIZARD_SYSTEM_PROMPT
from nikita.agents.onboarding.extraction_schemas import (
    BackstoryExtraction,
    ConverseResult,
    DarknessExtraction,
    DrugToleranceValue,
    IdentityExtraction,
    LifeStageValue,
    LocationExtraction,
    NoExtraction,
    NoExtractionReasonValue,
    PhoneExtraction,
    PhonePreferenceValue,
    SceneExtraction,
    SceneValue,
)
from nikita.config.models import Models

# Same model as the main text agent for voice consistency.
_MODEL_NAME = Models.sonnet()

# Spec 060 pattern: Anthropic prompt caching via model settings. Pydantic
# AI attaches ``cache_control: {"type": "ephemeral"}`` to the last system
# block; the persona (long + stable) gets cached across turns.
CACHE_SETTINGS: AnthropicModelSettings = AnthropicModelSettings(
    anthropic_cache_instructions=True,
)


@dataclass
class ConverseDeps:
    """Per-run dependencies for the conversation agent.

    The ``extracted`` list is the deps-scoped sidecar collector for
    structured extractions emitted by tool calls during the agent run
    (B1, QA iter-1). The endpoint reads it after ``agent.run`` returns.
    Conversation history is passed via the ``.run()`` call's
    ``message_history`` parameter, NOT through deps.
    """

    user_id: UUID
    locale: str = "en"
    extracted: list[ConverseResult] = field(default_factory=list)


def _create_conversation_agent() -> Agent[ConverseDeps, str]:
    """Build the Pydantic AI agent with six extraction tools registered.

    GH #382 (D5, 2026-04-21): retries raised from 2 to 4. First-turn
    tool-call schema mistakes (e.g. LLM omits all three identity fields,
    Pydantic rejects via _at_least_one_field; LLM emits no_extraction
    with a freeform reason; etc.) need enough retries for the model to
    self-correct from the error message rather than surfacing as
    user-facing validation_reject responses.
    """
    agent: Agent[ConverseDeps, str] = Agent(
        _MODEL_NAME,
        deps_type=ConverseDeps,
        output_type=str,
        system_prompt=WIZARD_SYSTEM_PROMPT,
        retries=4,
    )

    # Six extraction tools + 1 sentinel. Each appends the typed schema
    # instance to ``ctx.deps.extracted`` and returns a short
    # acknowledgement string consumed by the model. The endpoint reads
    # the structured extraction off ``deps.extracted`` after the run.

    @agent.tool
    def extract_location(
        ctx: RunContext[ConverseDeps], city: str, confidence: float
    ) -> str:
        """Commit a city extraction."""
        ctx.deps.extracted.append(
            LocationExtraction(city=city, confidence=confidence)
        )
        return "ok"

    @agent.tool
    def extract_scene(
        ctx: RunContext[ConverseDeps],
        scene: SceneValue,
        confidence: float,
        life_stage: LifeStageValue | None = None,
    ) -> str:
        """Commit a social-scene extraction (optionally with life stage).

        GH #382 D4b (Walk R 2026-04-21): `scene` and `life_stage` must
        match the Literal set SceneExtraction accepts. Before this fix,
        the LLM could emit `scene="techno_club"` / `"bar"` / anything,
        which flowed past the tool boundary into SceneExtraction and
        raised ValidationError. Walk R observed this directly with
        loc=scene type=literal_error. Type aliases (SceneValue,
        LifeStageValue) live in ``extraction_schemas.py`` as the single
        source of truth — DO NOT re-declare Literal sets here.
        """
        ctx.deps.extracted.append(
            SceneExtraction.model_validate(
                {
                    "scene": scene,
                    "confidence": confidence,
                    "life_stage": life_stage,
                }
            )
        )
        return "ok"

    @agent.tool
    def extract_darkness(
        ctx: RunContext[ConverseDeps],
        drug_tolerance: DrugToleranceValue,
        confidence: float,
    ) -> str:
        """Commit a 1-5 darkness rating.

        GH #382 D4b (QA iter-1): drug_tolerance uses the shared
        ``DrugToleranceValue = Annotated[int, Field(ge=1, le=5)]``
        alias so the LLM can't emit 0 / 6 / 99 past the tool boundary.
        """
        ctx.deps.extracted.append(
            DarknessExtraction(
                drug_tolerance=drug_tolerance, confidence=confidence
            )
        )
        return "ok"

    @agent.tool
    def extract_identity(
        ctx: RunContext[ConverseDeps],
        confidence: float,
        name: str | None = None,
        age: int | None = None,
        occupation: str | None = None,
    ) -> str:
        """Commit identity fields (name / age / occupation)."""
        ctx.deps.extracted.append(
            IdentityExtraction(
                name=name,
                age=age,
                occupation=occupation,
                confidence=confidence,
            )
        )
        return "ok"

    @agent.tool
    def extract_backstory(
        ctx: RunContext[ConverseDeps],
        chosen_option_id: str,
        cache_key: str,
        confidence: float,
    ) -> str:
        """Commit the user's backstory card selection."""
        ctx.deps.extracted.append(
            BackstoryExtraction(
                chosen_option_id=chosen_option_id,
                cache_key=cache_key,
                confidence=confidence,
            )
        )
        return "ok"

    @agent.tool
    def extract_phone(
        ctx: RunContext[ConverseDeps],
        phone_preference: PhonePreferenceValue,
        confidence: float,
        phone: str | None = None,
    ) -> str:
        """Commit the user's voice/text preference (+ phone if voice).

        GH #382 D4b: `phone_preference` constrained to PhoneExtraction's
        Literal[2] at the tool boundary, matching the D4 pattern.
        """
        ctx.deps.extracted.append(
            PhoneExtraction.model_validate(
                {
                    "phone_preference": phone_preference,
                    "phone": phone,
                    "confidence": confidence,
                }
            )
        )
        return "ok"

    @agent.tool
    def no_extraction(
        ctx: RunContext[ConverseDeps],
        reason: NoExtractionReasonValue = "off_topic",
    ) -> str:
        """Declare "no extraction" for off-topic / clarifying / backtracking.

        GH #382 (D4): `reason` is constrained to the 4 Literal values
        the schema (NoExtraction.reason) accepts. Pydantic AI rejects
        freeform strings at the tool-call boundary with a clear error
        message the LLM can act on, instead of bubbling a
        NoExtraction.model_validate ValidationError up through
        agent.run.
        """
        ctx.deps.extracted.append(
            NoExtraction.model_validate({"reason": reason})
        )
        return "ok"

    return agent


@lru_cache(maxsize=1)
def get_conversation_agent() -> Agent[ConverseDeps, str]:
    """Return the cached conversation-agent singleton.

    Lazy init mirrors the main text agent; avoids API-key errors during
    import/testing.
    """
    return _create_conversation_agent()


def pick_primary_extraction(
    extracted: list[ConverseResult],
) -> ConverseResult | None:
    """Pick the highest-priority extraction from the deps-scoped sink.

    Mirrors ``validators.pick_primary_tool_call`` but operates on schema
    instances rather than tool-name strings. Used by the endpoint to
    collapse multi-tool turns into a single committed extraction (per
    AC-T2.5.9 priority order).
    """
    if not extracted:
        return None
    # Lazy-import to avoid circular dep at module load.
    from nikita.agents.onboarding.validators import TOOL_CALL_PRIORITY

    kind_to_tool = {
        "location": "extract_location",
        "scene": "extract_scene",
        "darkness": "extract_darkness",
        "identity": "extract_identity",
        "backstory": "extract_backstory",
        "phone": "extract_phone",
        "no_extraction": "no_extraction",
    }
    known = [
        item
        for item in extracted
        if kind_to_tool.get(item.kind) in TOOL_CALL_PRIORITY
    ]
    if not known:
        return None
    return min(
        known,
        key=lambda item: TOOL_CALL_PRIORITY.index(kind_to_tool[item.kind]),
    )


__all__ = [
    "CACHE_SETTINGS",
    "ConverseDeps",
    "get_conversation_agent",
    "pick_primary_extraction",
]
