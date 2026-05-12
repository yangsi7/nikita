"""V2 message_history hydrator — Phase-2 multi-turn primitive (GH #582).

Converts persisted v2 JSONB message list to Pydantic AI ModelMessage
objects suitable for ``agent.run(..., message_history=...)``.

Per ADR-009 Hard Rule §6: use the official Pydantic AI multi-turn
primitive instead of re-passing context in the request body.

JSONB wire shape (per v2 persistence contract):
    [
        {"role": "user",  "content": "..."},
        {"role": "agent", "content": "..."},
        ...
    ]

Distinct from the v1 hydrator (``nikita/agents/onboarding/message_history.py``)
which takes v1 ``Turn`` objects with ``role="nikita"``. The v2 JSONB uses
``role="agent"`` and has no ``Turn`` wrapper — raw dicts only.
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

logger = logging.getLogger(__name__)


def hydrate_v2_message_history(
    messages: list[dict] | None,
) -> list[ModelMessage]:
    """Convert v2 JSONB message dicts to Pydantic AI ModelMessage list.

    Args:
        messages: ``onboarding_profile["messages"]`` list. Each entry is
            ``{"role": "user"|"agent", "content": str}``. None or empty
            returns empty list.

    Returns:
        ModelMessage list suitable for ``agent.run(..., message_history=...)``.
        Empty input → empty list (caller should then NOT pass
        ``message_history=`` so Pydantic AI re-runs the system prompt
        as for a fresh session).

    Skips malformed entries silently (logs warning):
        - Non-dict entries.
        - Missing role or content keys.
        - role not in {"user", "agent"}.
        - content not a string.
    """
    if not messages:
        return []

    result: list[ModelMessage] = []
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            logger.warning("v2 hydrator: skip non-dict message at idx=%d", i)
            continue
        role = msg.get("role")
        content = msg.get("content")
        if not isinstance(content, str):
            logger.warning("v2 hydrator: skip non-str content at idx=%d", i)
            continue
        if role == "user":
            result.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "agent":
            result.append(ModelResponse(parts=[TextPart(content=content)]))
        elif role is None:
            # Distinguish missing-role from unknown-role so operators can
            # tell schema-drift (no role key) from wire-corruption
            # (unexpected role string) in logs.
            logger.warning("v2 hydrator: skip missing role at idx=%d", i)
        else:
            logger.warning(
                "v2 hydrator: skip unknown role=%r at idx=%d — expected 'user' or 'agent'",
                role,
                i,
            )
    return result


__all__ = ["hydrate_v2_message_history"]
