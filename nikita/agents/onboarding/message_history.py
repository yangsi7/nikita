"""Conversation history → Pydantic AI ModelMessage hydration (GH #382 D1).

The portal wizard sends ``ConverseRequest.conversation_history: list[Turn]``
with every /converse call. Before GH #382 the endpoint discarded this
history and called ``agent.run(user_input, deps=deps)`` without
``message_history=``, so every turn was effectively cold: the LLM had
no idea what the prior wizard prompt was, guessed the wrong tool-call
shape, and the retry loop exhausted on the same error.

This module converts the wire-level ``Turn`` objects into Pydantic AI
``ModelMessage`` objects the agent can consume via ``agent.run(...,
message_history=...)``. The mapping is intentionally simple:

- ``role="user"`` → ``ModelRequest(parts=[UserPromptPart(content=...)])``
- ``role="nikita"`` → ``ModelResponse(parts=[TextPart(content=...)])``

Pydantic AI skips re-running the system prompt when ``message_history``
is non-empty (see pydantic_ai docs). ``WIZARD_SYSTEM_PROMPT`` is
deterministic, so losing the re-run is fine: the prompt that was in
scope when the history was produced is identical to what's in scope
now.

Reference: ``nikita/agents/text/history.py::HistoryLoader._convert_to_model_messages``
uses the same pattern for the main text agent's Spec 030 history loader.
"""

from __future__ import annotations

import logging

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from nikita.agents.onboarding.converse_contracts import Turn

logger = logging.getLogger(__name__)


def hydrate_message_history(turns: list[Turn]) -> list[ModelMessage]:
    """Convert wire-level Turn objects to Pydantic AI ModelMessage list.

    Args:
        turns: The ``conversation_history`` array from a ConverseRequest.

    Returns:
        A list of ``ModelMessage`` objects suitable for
        ``agent.run(..., message_history=...)``. Empty input returns
        an empty list (the caller should then NOT pass
        ``message_history=`` at all, so Pydantic AI re-runs the system
        prompt as for a fresh session).

    Notes:
        - ``superseded`` turns (AC-T3.7.2, rejected confirmations) are
          currently included. The reducer removes their UI affordance
          but the text stays in the log; if we were to elide them the
          LLM would see gaps in the conversation that don't match the
          user-visible transcript. Keep them for now; revisit if it
          causes confusion.
        - ``extracted`` and ``source`` are dropped — they're internal
          wire metadata and the LLM doesn't need them to reconstruct
          conversational state.
        - ``timestamp`` is also dropped; Pydantic AI ModelMessages do
          not expose a turn-timestamp field.
    """
    out: list[ModelMessage] = []
    for turn in turns:
        if turn.role == "user":
            out.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        elif turn.role == "nikita":
            out.append(ModelResponse(parts=[TextPart(content=turn.content)]))
        else:
            # Unknown role: skip + warn. Turn.role is a Literal['nikita','user']
            # so Pydantic validation at the wire layer already rejects anything
            # else; this is defensive against a future schema migration that
            # adds a new role (e.g. "system") without updating the hydrator.
            # PR #383 QA iter-1 nitpick: don't let a schema drift go silently.
            logger.warning(
                "message_history_unknown_role role=%s — hydrator needs update",
                turn.role,
            )
    return out


__all__ = ["hydrate_message_history"]
