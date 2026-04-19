"""Pydantic AI conversation agent for POST /converse (Spec 214 FR-11d).

Mirrors the main text-agent pattern (``nikita/agents/text/agent.py``):

- ``@lru_cache`` singleton via ``get_conversation_agent``.
- Anthropic prompt caching via
  ``AnthropicModelSettings(anthropic_cache_instructions=True)`` — the
  Pydantic AI equivalent of ``cache_control: {"type": "ephemeral"}`` on
  the system-prompt block.
- One ``@agent.tool_plain`` per extraction schema — the agent emits a
  tool call when it decides to extract a field; the endpoint reads the
  tool-call output off ``AgentRunResult``.

The agent is STATELESS — no memory, no chapter behavior, no pipeline
prompt injection. The endpoint passes the full conversation history in
each call. This matches tech-spec §2.1 ("No memory, no chapter context,
no recall_memory tool").
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModelSettings

from nikita.agents.onboarding.conversation_prompts import WIZARD_SYSTEM_PROMPT
from nikita.agents.onboarding.extraction_schemas import (
    BackstoryExtraction,
    ConverseResult,
    DarknessExtraction,
    IdentityExtraction,
    LocationExtraction,
    NoExtraction,
    PhoneExtraction,
    SceneExtraction,
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

    Kept minimal — the agent is stateless; the only state it needs is
    the caller's identity (for the endpoint-side authz gate) and the
    locale for future i18n. Conversation history is passed via the
    ``.run()`` call's ``message_history`` parameter, NOT through deps.
    """

    user_id: UUID
    locale: str = "en"


def _create_conversation_agent() -> Agent[ConverseDeps, ConverseResult]:
    """Build the Pydantic AI agent with six extraction tools registered."""
    agent: Agent[ConverseDeps, ConverseResult] = Agent(
        _MODEL_NAME,
        deps_type=ConverseDeps,
        output_type=ConverseResult,
        system_prompt=WIZARD_SYSTEM_PROMPT,
        retries=2,
    )

    # Six extraction tools. Each returns the typed schema instance; the
    # endpoint reads these off ``result.output`` (discriminated union of
    # the 6 schemas + NoExtraction sentinel).
    @agent.tool_plain
    def extract_location(city: str, confidence: float) -> LocationExtraction:
        """Commit a city extraction."""
        return LocationExtraction(city=city, confidence=confidence)

    @agent.tool_plain
    def extract_scene(
        scene: str,
        confidence: float,
        life_stage: str | None = None,
    ) -> SceneExtraction:
        """Commit a social-scene extraction (optionally with life stage)."""
        return SceneExtraction.model_validate(
            {
                "scene": scene,
                "confidence": confidence,
                "life_stage": life_stage,
            }
        )

    @agent.tool_plain
    def extract_darkness(
        drug_tolerance: int, confidence: float
    ) -> DarknessExtraction:
        """Commit a 1-5 darkness rating."""
        return DarknessExtraction(
            drug_tolerance=drug_tolerance, confidence=confidence
        )

    @agent.tool_plain
    def extract_identity(
        confidence: float,
        name: str | None = None,
        age: int | None = None,
        occupation: str | None = None,
    ) -> IdentityExtraction:
        """Commit identity fields (name / age / occupation)."""
        return IdentityExtraction(
            name=name,
            age=age,
            occupation=occupation,
            confidence=confidence,
        )

    @agent.tool_plain
    def extract_backstory(
        chosen_option_id: str, cache_key: str, confidence: float
    ) -> BackstoryExtraction:
        """Commit the user's backstory card selection."""
        return BackstoryExtraction(
            chosen_option_id=chosen_option_id,
            cache_key=cache_key,
            confidence=confidence,
        )

    @agent.tool_plain
    def extract_phone(
        phone_preference: str,
        confidence: float,
        phone: str | None = None,
    ) -> PhoneExtraction:
        """Commit the user's voice/text preference (+ phone if voice)."""
        return PhoneExtraction.model_validate(
            {
                "phone_preference": phone_preference,
                "phone": phone,
                "confidence": confidence,
            }
        )

    @agent.tool_plain
    def no_extraction(reason: str = "off_topic") -> NoExtraction:
        """Declare "no extraction" for off-topic / clarifying / backtracking."""
        return NoExtraction.model_validate({"reason": reason})

    return agent


@lru_cache(maxsize=1)
def get_conversation_agent() -> Agent[ConverseDeps, ConverseResult]:
    """Return the cached conversation-agent singleton.

    Lazy init mirrors the main text agent; avoids API-key errors during
    import/testing.
    """
    return _create_conversation_agent()


__all__ = [
    "CACHE_SETTINGS",
    "ConverseDeps",
    "get_conversation_agent",
]
