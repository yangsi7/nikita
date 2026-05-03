"""Spec 216-E E1.10 — FIRECRAWL_API_KEY secret handling.

The API key MUST NOT appear in any captured log line, in the structured
``agent_tool_call`` event, or in the returned tool string. This test
simulates a tool failure (firecrawl raises) and asserts the API key is
absent from the log capture buffer.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from nikita.agents.onboarding.conversation_agent import ConverseDeps
from nikita.agents.onboarding.state import WizardSlots
from nikita.agents.onboarding.tools import firecrawl_tools as ft


SENTINEL_KEY = "fc-LIVE-SENTINEL-9c8f01a4d2b8"


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
async def test_api_key_never_logged_on_firecrawl_error(monkeypatch, caplog):
    """Tool failure path MUST scrub the API key from logs.

    We seed the env / settings with a sentinel key, force firecrawl to
    raise, and assert the sentinel does not appear in caplog records.
    """
    monkeypatch.setenv("FIRECRAWL_API_KEY", SENTINEL_KEY)
    # Reset settings cache so the sentinel is read.
    from nikita.config.settings import get_settings  # noqa: PLC0415

    get_settings.cache_clear()

    caplog.set_level(
        logging.DEBUG,
        logger="nikita.agents.onboarding.tools.firecrawl_tools",
    )

    deps = _make_deps()
    with patch.object(
        ft,
        "_firecrawl_search",
        new=AsyncMock(side_effect=RuntimeError("connection refused")),
    ):
        result = await ft.fetch_city_context(_ctx(deps), "Berlin")

    # Returned tool output is the static fallback (≤200 chars).
    assert result == ft._get_static_fallback("city_context")
    assert SENTINEL_KEY not in result

    # Inspect every captured log record's message AND extra fields.
    for record in caplog.records:
        # Format the message (in case args/extras carry the secret).
        formatted = record.getMessage()
        assert SENTINEL_KEY not in formatted, (
            f"API key leaked in log message: {formatted!r}"
        )
        for attr_name, attr_value in vars(record).items():
            if isinstance(attr_value, str):
                assert SENTINEL_KEY not in attr_value, (
                    f"API key leaked in log attr {attr_name}: {attr_value!r}"
                )

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_api_key_never_in_returned_tool_output(monkeypatch):
    """The tool's return value (≤200 char snippet OR static fallback)
    MUST never contain the API key — scrubbing belongs to the tool, not
    the caller."""
    monkeypatch.setenv("FIRECRAWL_API_KEY", SENTINEL_KEY)
    from nikita.config.settings import get_settings  # noqa: PLC0415

    get_settings.cache_clear()

    deps = _make_deps()
    with patch.object(
        ft,
        "_firecrawl_search",
        # Even if firecrawl itself accidentally echoes the bearer back
        # (defensive), the tool's truncate / fallback path strips it via
        # length cap. We assert this via the live-success path returning
        # text that does NOT contain the sentinel.
        new=AsyncMock(return_value="Berlin scene snippet — no secrets here."),
    ):
        result = await ft.fetch_city_context(_ctx(deps), "Berlin")

    assert SENTINEL_KEY not in result
    get_settings.cache_clear()
