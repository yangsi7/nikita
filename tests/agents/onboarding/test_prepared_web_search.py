"""Spec 216-E E1.5 — prepared_web_search builtin tool wrapper.

- Turn 0 (no city collected) → returns ``None`` (no builtin attached).
- Turn 1+ (city collected) → returns a configured ``WebSearchTool``.
- Country detection maps Berlin→DE, NYC→US, unknown→None (search runs
  without country hint).
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from nikita.agents.onboarding.conversation_agent import ConverseDeps
from nikita.agents.onboarding.state import SlotDelta, WizardSlots
from nikita.agents.onboarding.tools.web_search import (
    WEBSEARCH_CONTEXT_SIZE,
    WEBSEARCH_MAX_USES,
    detect_country,
    prepared_web_search,
)


def _ctx(deps: ConverseDeps) -> SimpleNamespace:
    return SimpleNamespace(deps=deps)


def _deps(slots: WizardSlots) -> ConverseDeps:
    return ConverseDeps(
        user_id=uuid4(),
        conversation_id=uuid4(),
        state=slots,
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


class TestDetectCountry:
    def test_known_european_cities(self):
        assert detect_country("Berlin") == "DE"
        assert detect_country("Zurich") == "CH"
        assert detect_country("London") == "GB"
        assert detect_country("Paris") == "FR"

    def test_known_us_cities(self):
        assert detect_country("New York") == "US"
        assert detect_country("Brooklyn") == "US"
        assert detect_country("San Francisco") == "US"

    def test_case_insensitive(self):
        assert detect_country("BERLIN") == "DE"
        assert detect_country("  berlin  ") == "DE"

    def test_unknown_returns_none(self):
        assert detect_country("Atlantis") is None
        assert detect_country("") is None
        assert detect_country(None) is None


class TestPreparedWebSearch:
    @pytest.mark.asyncio
    async def test_turn_zero_returns_none(self):
        deps = _deps(WizardSlots())
        result = await prepared_web_search(_ctx(deps))
        assert result is None

    @pytest.mark.asyncio
    async def test_turn_with_city_returns_tool(self):
        slots = WizardSlots().apply(
            SlotDelta(kind="city", data={"city": "Berlin"})
        )
        deps = _deps(slots)
        result = await prepared_web_search(_ctx(deps))
        assert result is not None
        # WebSearchTool surface contract: search_context_size + max_uses.
        assert result.search_context_size == WEBSEARCH_CONTEXT_SIZE
        assert result.max_uses == WEBSEARCH_MAX_USES
        assert result.user_location is not None
        # WebSearchUserLocation is a TypedDict at runtime.
        assert result.user_location["city"] == "Berlin"
        assert result.user_location["country"] == "DE"

    @pytest.mark.asyncio
    async def test_unknown_city_drops_user_location(self):
        slots = WizardSlots().apply(
            SlotDelta(kind="city", data={"city": "Atlantis"})
        )
        deps = _deps(slots)
        result = await prepared_web_search(_ctx(deps))
        assert result is not None
        # Unknown city → no country → user_location dropped.
        assert result.user_location is None
        # But the tool itself is still configured.
        assert result.search_context_size == WEBSEARCH_CONTEXT_SIZE

    @pytest.mark.asyncio
    async def test_malformed_city_slot_returns_none(self):
        # city slot present but value is not a string.
        slots = WizardSlots()
        # Cannot construct invalid slot via SlotDelta (Pydantic guards),
        # so we directly mutate to simulate corrupted state.
        slots = slots.model_copy(update={"city": {"city": ""}})
        deps = _deps(slots)
        result = await prepared_web_search(_ctx(deps))
        assert result is None
