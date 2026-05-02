"""Wrapped agent.run helper — Spec 216-B3 (T-B3-1, AC B1.11).

Single-purpose helper that wraps every ``agent.run`` call in
``capture_run_messages`` so an ``UnexpectedModelBehavior`` raised inside the
agent loop dumps the entire request/response exchange to logs for triage.

Per Pydantic AI 1.71.0 docs (Model Errors section,
https://pydantic.dev/docs/ai/core-concepts/agent#model-errors):

    with capture_run_messages() as messages:
        try:
            result = await agent.run(...)
        except UnexpectedModelBehavior as exc:
            # `messages` now contains the full exchange — log it then either
            # re-raise (caller picks fallback strategy) or fall through.

The helper is shared between the legacy /converse handler (T-B3-6 wiring)
and the new /answer handler (T-B3-3) so the diagnosis surface is uniform.

NOT covered by this helper:
  - asyncio.TimeoutError (asyncio.wait_for boundary; route layer owns)
  - pydantic.ValidationError (route layer owns; in-character reject template)
  - generic Exception (route layer's catch-all 200 fallback)

Those exceptions have dedicated handlers in the route layer with their own
log records and side effects (spend ledger charge, persist user turn, etc.).
Wrapping them here would dilute the captured-messages signal.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from pydantic_ai import capture_run_messages
from pydantic_ai.exceptions import UnexpectedModelBehavior

logger = logging.getLogger(__name__)


async def run_agent_with_capture(
    agent: Any,
    user_input: str,
    *,
    user_id: UUID,
    traceparent: str | None = None,
    **run_kwargs: Any,
) -> Any:
    """Run ``agent.run(user_input, **run_kwargs)`` wrapped in ``capture_run_messages``.

    On ``UnexpectedModelBehavior`` the captured exchange is logged with
    ``user_id`` and ``traceparent`` for Cloud Run triage, then the exception
    is re-raised so the caller can apply its own fallback strategy
    (always-200 in-character reply per AC B1.17).

    Other exceptions propagate without logging — they have dedicated handlers
    in the route layer.

    Args:
        agent: A Pydantic AI ``Agent`` instance whose ``.run`` is awaitable.
        user_input: The user message to send to the agent.
        user_id: The authenticated user's id, included in the log record so
            triage can filter Cloud Run logs by user.
        traceparent: Optional W3C traceparent header value for distributed
            trace correlation. If absent, an empty string is logged.
        **run_kwargs: Forwarded verbatim to ``agent.run`` (deps, message_history,
            model_settings, etc.).

    Returns:
        Whatever ``agent.run`` returns on success (typically an ``AgentRunResult``).

    Raises:
        UnexpectedModelBehavior: Re-raised after logging the captured exchange.
        Any other exception raised by ``agent.run``: propagated unchanged.
    """
    with capture_run_messages() as messages:
        try:
            return await agent.run(user_input, **run_kwargs)
        except UnexpectedModelBehavior as exc:
            try:
                dumped = [m.model_dump(mode="json") for m in messages]
            except Exception:
                # Defense in depth — never let log-formatting crash the
                # exception path. Fall back to repr if model_dump fails.
                dumped = [repr(m) for m in messages]
            logger.warning(
                "agent_run_unexpected_model_behavior "
                "exc=%s user_id=%s traceparent=%s captured_messages=%s",
                f"UnexpectedModelBehavior: {exc}",
                user_id,
                traceparent or "",
                dumped,
            )
            raise


__all__ = ["run_agent_with_capture"]
