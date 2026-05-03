"""Spec 216-E E1.6 / E1.11 — firecrawl per-attempt 3s timeout.

A 4s mocked firecrawl delay must yield the static fallback within ~3.5s
and a structured log line with ``outcome="timeout"``.
"""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from nikita.agents.onboarding.conversation_agent import ConverseDeps
from nikita.agents.onboarding.state import WizardSlots
from nikita.agents.onboarding.tools import firecrawl_tools as ft


@pytest.fixture(autouse=True)
def _reset_cache():
    ft._reset_fetch_cache_for_tests()
    yield
    ft._reset_fetch_cache_for_tests()


def _ctx(deps: ConverseDeps) -> SimpleNamespace:
    return SimpleNamespace(deps=deps)


def _make_deps() -> ConverseDeps:
    return ConverseDeps(
        user_id=uuid4(),
        conversation_id=uuid4(),
        state=WizardSlots(),
        state_summary="",
        last_slot_kind=None,
        last_value=None,
        next_slot_kind=None,
        next_slot_hint=None,
        cost_budget_remaining_usd=1.0,
        fetch_invocations_this_turn=0,
        fetch_cost_cumulative=0.0,
        cohort_cache={},
        big5_confidence={},
        traceparent="",
    )


@pytest.mark.asyncio
async def test_timeout_returns_static_fallback_within_budget(monkeypatch, caplog):
    """A 4s firecrawl delay must time out at 3s and the tool returns the
    static fallback. Total wall time must be <3.5s."""

    async def slow_search(*_args, **_kwargs) -> str:  # noqa: ANN001
        await asyncio.sleep(4.0)
        return "never"

    deps = _make_deps()
    # Force firecrawl_timeout_s = 3.0 from defaults.
    started = time.monotonic()
    with patch.object(ft, "_firecrawl_search", side_effect=slow_search):
        result = await ft.fetch_city_context(_ctx(deps), "Berlin")
    elapsed = time.monotonic() - started

    # Returns static fallback string (≤200 chars).
    assert result == ft._get_static_fallback("city_context")
    # Did NOT wait the full 4s.
    assert elapsed < 3.5, f"expected <3.5s elapsed, got {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_timeout_emits_structured_log(caplog):
    """E1.6/E1.9 — timeout fires the agent_tool_call log with outcome=timeout."""
    import logging

    caplog.set_level(
        logging.INFO,
        logger="nikita.agents.onboarding.tools.firecrawl_tools",
    )

    async def slow_search(*_args, **_kwargs) -> str:  # noqa: ANN001
        await asyncio.sleep(4.0)
        return "never"

    deps = _make_deps()
    with patch.object(ft, "_firecrawl_search", side_effect=slow_search):
        await ft.fetch_city_context(_ctx(deps), "Berlin")

    timeout_records = [
        r for r in caplog.records
        if r.message == "agent_tool_call" and getattr(r, "outcome", None) == "timeout"
    ]
    assert timeout_records, "no timeout log line emitted"


@pytest.mark.asyncio
async def test_firecrawl_error_returns_static_fallback():
    """Non-timeout errors (HTTP 5xx, network) also fall through to static."""
    deps = _make_deps()
    with patch.object(
        ft,
        "_firecrawl_search",
        new=AsyncMock(side_effect=RuntimeError("backend_500")),
    ):
        result = await ft.fetch_city_context(_ctx(deps), "Berlin")
    assert result == ft._get_static_fallback("city_context")
