"""Spec 216-E E1.1, E1.3, E1.4, E1.9 — firecrawl_tools test suite.

Covers:
- Each of the 4 tools returns ≤200 char text on the happy path.
- Per-turn budget guard rejects the 2nd call (returns static fallback).
- Cohort/in-module cache hits before issuing live fetch.
- Structured tool-call log shape per E1.9.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from nikita.agents.onboarding.conversation_agent import ConverseDeps
from nikita.agents.onboarding.state import WizardSlots
from nikita.agents.onboarding.tools import firecrawl_tools as ft


def _ctx(deps: ConverseDeps) -> SimpleNamespace:
    """Mimic ``RunContext`` enough for the tool functions (they read deps only)."""
    return SimpleNamespace(deps=deps)


def _make_deps(**overrides) -> ConverseDeps:
    defaults = dict(
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
    defaults.update(overrides)
    return ConverseDeps(**defaults)


@pytest.fixture(autouse=True)
def _reset_cache():
    ft._reset_fetch_cache_for_tests()
    yield
    ft._reset_fetch_cache_for_tests()


class TestFourToolsReturnSnippets:
    """E1.1 — every tool returns ≤200 char text on the happy path."""

    @pytest.mark.asyncio
    async def test_city_context_returns_le_200_chars(self):
        deps = _make_deps()
        with patch.object(
            ft, "_firecrawl_search", new=AsyncMock(return_value="Z" * 500)
        ):
            with patch.object(
                ft.get_settings.__wrapped__,
                "__call__",
                return_value=ft.get_settings(),
            ):
                result = await ft.fetch_city_context(_ctx(deps), "Berlin")
        assert isinstance(result, str)
        assert len(result) <= ft.FETCH_SNIPPET_MAX_CHARS

    @pytest.mark.asyncio
    async def test_occupation_signal_returns_le_200_chars(self):
        deps = _make_deps()
        with patch.object(
            ft, "_firecrawl_search", new=AsyncMock(return_value="Q" * 500)
        ):
            result = await ft.fetch_occupation_signal(
                _ctx(deps), "designer", "Berlin"
            )
        assert isinstance(result, str)
        assert len(result) <= ft.FETCH_SNIPPET_MAX_CHARS

    @pytest.mark.asyncio
    async def test_time_of_day_signal_returns_le_200_chars(self):
        deps = _make_deps()
        with patch.object(
            ft, "_firecrawl_search", new=AsyncMock(return_value="X" * 500)
        ):
            result = await ft.fetch_time_of_day_signal(_ctx(deps), "Tokyo")
        assert isinstance(result, str)
        assert len(result) <= ft.FETCH_SNIPPET_MAX_CHARS

    @pytest.mark.asyncio
    async def test_topic_specific_returns_le_200_chars(self):
        deps = _make_deps()
        with patch.object(
            ft, "_firecrawl_search", new=AsyncMock(return_value="Y" * 500)
        ):
            result = await ft.fetch_topic_specific(
                _ctx(deps), "weekend markets", "London"
            )
        assert isinstance(result, str)
        assert len(result) <= ft.FETCH_SNIPPET_MAX_CHARS


class TestPerTurnBudgetGuard:
    """E1.3 — second fetch_* call in a single turn returns static fallback."""

    @pytest.mark.asyncio
    async def test_second_call_within_turn_returns_static_fallback(self):
        deps = _make_deps()
        with patch.object(
            ft, "_firecrawl_search", new=AsyncMock(return_value="ok " * 50)
        ):
            first = await ft.fetch_city_context(_ctx(deps), "Berlin")
            assert "ok" in first or first == ft._get_static_fallback("city_context")
            # Second call within same "turn" (deps.fetch_invocations_this_turn==1)
            second = await ft.fetch_topic_specific(_ctx(deps), "techno", "Berlin")
        assert second == ft._get_static_fallback("topic_specific")
        # Cumulative invocation counter advanced past the cap.
        assert deps.fetch_invocations_this_turn >= 2


class TestCohortCacheHitsBeforeLiveFetch:
    """E1.4 — when the in-module cache has the key, no live call is made."""

    @pytest.mark.asyncio
    async def test_cache_hit_skips_firecrawl(self):
        deps = _make_deps()
        cache_key = ft._build_cache_key("city_context", "berlin")
        ft._set_cache_for_tests(cache_key, "cached snippet")
        mock_search = AsyncMock(return_value="should-not-be-called")
        with patch.object(ft, "_firecrawl_search", new=mock_search):
            result = await ft.fetch_city_context(_ctx(deps), "Berlin")
        assert result == "cached snippet"
        mock_search.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cache_miss_writes_through_and_subsequent_call_hits(self):
        deps = _make_deps()
        deps2 = _make_deps()  # fresh per-turn budget
        with patch.object(
            ft, "_firecrawl_search", new=AsyncMock(return_value="live snippet text")
        ):
            first = await ft.fetch_city_context(_ctx(deps), "Berlin")
        # Re-call on a fresh deps (next turn) — should now be a cache hit.
        with patch.object(
            ft,
            "_firecrawl_search",
            new=AsyncMock(side_effect=AssertionError("should not be called")),
        ):
            second = await ft.fetch_city_context(_ctx(deps2), "Berlin")
        assert first == second
        assert "live snippet text" in second or second == first


class TestStructuredLogShape:
    """E1.9 — every tool emits a structured agent_tool_call log line."""

    @pytest.mark.asyncio
    async def test_log_contains_required_fields(self, caplog):
        import logging

        caplog.set_level(logging.INFO, logger="nikita.agents.onboarding.tools.firecrawl_tools")
        deps = _make_deps(traceparent="00-trace-span-01")
        with patch.object(
            ft, "_firecrawl_search", new=AsyncMock(return_value="payload " * 5)
        ):
            await ft.fetch_city_context(_ctx(deps), "Berlin")
        # Find the agent_tool_call record.
        records = [r for r in caplog.records if r.message == "agent_tool_call"]
        assert records, "no agent_tool_call log line emitted"
        rec = records[-1]
        # Required keys per E1.9.
        assert getattr(rec, "event") == "agent_tool_call"
        assert getattr(rec, "tool_name") == "city_context"
        assert getattr(rec, "outcome") in {
            "success",
            "cache_hit",
            "timeout",
            "budget_exceeded",
        } or getattr(rec, "outcome").startswith("firecrawl_error:")
        assert isinstance(getattr(rec, "duration_ms"), int)
        assert isinstance(getattr(rec, "cohort_cache_used"), bool)
        # cost_usd_delta is float for native GCP Logging numeric aggregation
        # (PR #462 QA review N1 — switched from str(Decimal) to float).
        assert isinstance(getattr(rec, "cost_usd_delta"), float)
        assert getattr(rec, "traceparent") == "00-trace-span-01"
        # cache_key_hash is hex (sha256) — never the raw city.
        cache_key = getattr(rec, "cache_key_hash")
        assert "berlin" not in cache_key.lower()


class TestCumulativeCostTracked:
    """E1.7 — successful fetch increments cumulative cost by ~$0.025."""

    @pytest.mark.asyncio
    async def test_successful_call_increments_cost(self):
        deps = _make_deps()
        with patch.object(
            ft, "_firecrawl_search", new=AsyncMock(return_value="payload")
        ):
            await ft.fetch_city_context(_ctx(deps), "Berlin")
        # Default fetch_cost_cumulative starts as 0.0 (float). After a
        # success the value should be approximately $0.025.
        assert Decimal(str(deps.fetch_cost_cumulative)) >= Decimal("0.024")
        assert Decimal(str(deps.fetch_cost_cumulative)) <= Decimal("0.026")
