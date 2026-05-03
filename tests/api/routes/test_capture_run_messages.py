"""T-B3-1 (Spec 216-B3): run_agent_with_capture helper wraps agent.run.

Per spec B1.11 + Pydantic AI 1.71.0 docs (Model Errors section):
  with capture_run_messages() as messages:
      try:
          result = await agent.run(...)
      except UnexpectedModelBehavior:
          # `messages` now holds the exchange — log it for diagnosis

This test exercises the new ``run_agent_with_capture`` helper introduced in
T-B3-1. Both /converse (existing handler) and /answer (T-B3-3 new handler)
will call this helper so that EVERY agent.run is wrapped — uniform diagnosis
surface, single place to evolve the logging contract.

Rule cross-references:
  - .claude/rules/agentic-design-patterns.md Hard Rule §5 (validation layering)
  - .claude/rules/testing.md "Tests That Don't Test" (asserts present, mocks of
    the source module not the importer)
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


class TestRunAgentWithCapture:
    """B1.11: agent.run is wrapped in capture_run_messages.

    On UnexpectedModelBehavior the captured messages list MUST be logged
    so Cloud Run logs surface the exchange for triage. The helper re-raises
    so callers can apply their own fallback strategy.
    """

    @pytest.mark.asyncio
    async def test_happy_path_returns_agent_result(self) -> None:
        """No exception → returns the agent result unchanged."""
        from nikita.agents.onboarding.agent_runner import run_agent_with_capture

        sentinel_result = MagicMock(name="agent_run_result")
        agent = MagicMock()
        agent.run = AsyncMock(return_value=sentinel_result)

        result = await run_agent_with_capture(
            agent,
            "Zürich",
            user_id=USER_ID,
        )

        assert result is sentinel_result, (
            "Helper must return agent.run result verbatim on success."
        )
        agent.run.assert_awaited_once_with("Zürich")

    @pytest.mark.asyncio
    async def test_unexpected_model_behavior_logs_captured_messages_and_reraises(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """B1.11 falsifier: on UnexpectedModelBehavior, captured messages
        appear in logs AND the exception is re-raised for caller fallback.

        If the helper does NOT wrap with capture_run_messages, the log
        record will not carry the captured-messages marker and this test
        fails RED.
        """
        from nikita.agents.onboarding.agent_runner import run_agent_with_capture

        agent = MagicMock()
        agent.run = AsyncMock(
            side_effect=UnexpectedModelBehavior(
                "Tool 'extract_city' exceeded max retries count of 2"
            )
        )

        with caplog.at_level(logging.WARNING, logger="nikita.agents.onboarding.agent_runner"):
            with pytest.raises(UnexpectedModelBehavior):
                await run_agent_with_capture(
                    agent,
                    "Zürich",
                    user_id=USER_ID,
                    traceparent="00-aabbccddeeff-1122334455667788-01",
                )

        # The wrapping is the falsifier. Two signals must appear:
        # 1. A log record with "captured_messages" key.
        # 2. The exception type name + user_id in the same record so triage
        #    can filter Cloud Run logs.
        relevant = [
            r
            for r in caplog.records
            if "captured_messages" in (r.getMessage() or "")
        ]
        assert relevant, (
            "Expected a log record carrying captured_messages on "
            "UnexpectedModelBehavior. Without capture_run_messages wrapping, "
            "the messages list cannot be reconstructed. "
            f"All records: {[r.getMessage() for r in caplog.records]}"
        )
        message = relevant[0].getMessage()
        assert "UnexpectedModelBehavior" in message, (
            "Expected exception type in log record so triage can filter "
            "Cloud Run logs by exception class."
        )
        assert str(USER_ID) in message, (
            "Expected user_id in log record for per-user triage."
        )

    @pytest.mark.asyncio
    async def test_helper_passes_run_kwargs_through(self) -> None:
        """Helper must forward arbitrary kwargs (deps, message_history,
        model_settings) to agent.run unchanged — otherwise B1.10 message_history
        wiring breaks.
        """
        from nikita.agents.onboarding.agent_runner import run_agent_with_capture

        agent = MagicMock()
        agent.run = AsyncMock(return_value=MagicMock())

        deps_sentinel = MagicMock()
        history_sentinel = [MagicMock()]
        settings_sentinel = MagicMock()

        await run_agent_with_capture(
            agent,
            "Zürich",
            user_id=USER_ID,
            deps=deps_sentinel,
            message_history=history_sentinel,
            model_settings=settings_sentinel,
        )

        agent.run.assert_awaited_once_with(
            "Zürich",
            deps=deps_sentinel,
            message_history=history_sentinel,
            model_settings=settings_sentinel,
        )

    @pytest.mark.asyncio
    async def test_other_exceptions_propagate_without_logging(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Non-UnexpectedModelBehavior exceptions (TimeoutError, ValidationError,
        plain Exception) propagate WITHOUT the captured-messages log — those
        have their own dedicated handlers in the route layer (per /converse
        existing structure at portal_onboarding.py:903-989).
        """
        from nikita.agents.onboarding.agent_runner import run_agent_with_capture

        agent = MagicMock()
        agent.run = AsyncMock(side_effect=TimeoutError("agent timeout"))

        with caplog.at_level(logging.WARNING, logger="nikita.agents.onboarding.agent_runner"):
            with pytest.raises(TimeoutError):
                await run_agent_with_capture(agent, "x", user_id=USER_ID)

        assert not any(
            "captured_messages" in (r.getMessage() or "") for r in caplog.records
        ), (
            "Helper must NOT log captured_messages for non-UnexpectedModelBehavior "
            "exceptions; those are handled by the route layer's own catch blocks."
        )
