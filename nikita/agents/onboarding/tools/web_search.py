"""WebSearchTool builtin wrapper for the wizard agent (Spec 216-E E1.5/E1.12).

Distinct from the firecrawl ``@agent.tool`` decorators: ``WebSearchTool``
is a Pydantic AI provider-native builtin (Anthropic-served). The wizard's
route handler calls ``prepared_web_search(ctx)`` and forwards the result
(or absent value) into ``agent.run(..., builtin_tools=[...])`` per turn.

Returns ``None`` on turn 0 (before the user's city is collected) so a
WebSearchTool isn't burned on a turn that can't be localized.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Final

from pydantic_ai import RunContext
from pydantic_ai.builtin_tools import WebSearchTool, WebSearchUserLocation

if TYPE_CHECKING:
    from nikita.agents.onboarding.conversation_agent import ConverseDeps


# ---------------------------------------------------------------------------
# Tuning constants (per .claude/rules/tuning-constants.md)
# ---------------------------------------------------------------------------

WEBSEARCH_CONTEXT_SIZE: Final[str] = "low"
"""WebSearchTool context size — Spec 216-E E1.5.

Current value: "low" (Spec 216-E lock-in).
Prior values: N/A — introduced here.
Rationale: low context size minimizes per-call cost while still grounding
short, ≤140 char wizard replies. ``medium``/``high`` would be wasted
budget at this turn shape.
"""

WEBSEARCH_MAX_USES: Final[int] = 2
"""Max WebSearchTool invocations per agent.run, Spec 216-E E1.5.

Current value: 2 (Spec 216-E lock-in).
Rationale: each turn budget allows up to 2 web searches to compensate
for thin firecrawl signal; tighter than 5+ to bound per-turn p99 latency.
"""


# ---------------------------------------------------------------------------
# City → ISO country mapping (lru-cached)
# ---------------------------------------------------------------------------

# Hand-curated subset; covers seed cohorts + common metros. Unknown cities
# fall back to ``None`` and the WebSearchUserLocation is dropped so the
# search still runs without a country filter.
_CITY_COUNTRY_MAP: Final[dict[str, str]] = {
    "zurich": "CH",
    "geneva": "CH",
    "bern": "CH",
    "basel": "CH",
    "lausanne": "CH",
    "london": "GB",
    "manchester": "GB",
    "edinburgh": "GB",
    "berlin": "DE",
    "munich": "DE",
    "hamburg": "DE",
    "frankfurt": "DE",
    "paris": "FR",
    "lyon": "FR",
    "marseille": "FR",
    "amsterdam": "NL",
    "rotterdam": "NL",
    "stockholm": "SE",
    "gothenburg": "SE",
    "copenhagen": "DK",
    "oslo": "NO",
    "helsinki": "FI",
    "vienna": "AT",
    "madrid": "ES",
    "barcelona": "ES",
    "rome": "IT",
    "milan": "IT",
    "lisbon": "PT",
    "dublin": "IE",
    "warsaw": "PL",
    "prague": "CZ",
    # North America
    "new york": "US",
    "nyc": "US",
    "brooklyn": "US",
    "manhattan": "US",
    "san francisco": "US",
    "sf": "US",
    "los angeles": "US",
    "la": "US",
    "seattle": "US",
    "austin": "US",
    "boston": "US",
    "chicago": "US",
    "miami": "US",
    "denver": "US",
    "portland": "US",
    "toronto": "CA",
    "vancouver": "CA",
    "montreal": "CA",
    # APAC
    "tokyo": "JP",
    "osaka": "JP",
    "seoul": "KR",
    "singapore": "SG",
    "hong kong": "HK",
    "sydney": "AU",
    "melbourne": "AU",
    "auckland": "NZ",
}


@lru_cache(maxsize=512)
def detect_country(city: str | None) -> str | None:
    """Return ISO country code for ``city`` (best-effort), else None.

    Lookup is case-insensitive and ignores leading/trailing whitespace.
    Unknown cities → ``None`` so the caller drops ``user_location`` and
    the WebSearchTool runs without a country hint (still functional).
    """
    if not city or not isinstance(city, str):
        return None
    key = city.strip().lower()
    return _CITY_COUNTRY_MAP.get(key)


def _extract_city(deps: "ConverseDeps") -> str | None:
    """Pull the user's collected city string from cumulative state.

    The 13-slot taxonomy stores ``city`` as ``dict[str, Any]`` on
    ``WizardSlots``; the canonical value lives at ``city["city"]``.
    Returns ``None`` if the slot is unfilled or malformed.
    """
    state = getattr(deps, "state", None)
    if state is None:
        return None
    city_slot = getattr(state, "city", None)
    if not isinstance(city_slot, dict):
        return None
    raw = city_slot.get("city")
    if not isinstance(raw, str) or not raw.strip():
        return None
    return raw.strip()


async def prepared_web_search(
    ctx: "RunContext[ConverseDeps]",
) -> WebSearchTool | None:
    """Return a configured ``WebSearchTool`` or ``None`` for the current turn.

    - Turn 0 (no city collected) → ``None`` so no builtin is attached and
      the search isn't burned on an unlocalizable turn.
    - Turn 1+ (city present) → ``WebSearchTool`` configured with
      ``user_location`` (best-effort country) + ``search_context_size="low"``
      + ``max_uses=2``.

    Caller wires this into ``agent.run(..., builtin_tools=[result])`` when
    the result is non-None.
    """
    city = _extract_city(ctx.deps)
    if city is None:
        return None

    country = detect_country(city)
    user_location: WebSearchUserLocation | None = None
    if country:
        # WebSearchUserLocation requires city + country; region/timezone
        # left empty (Anthropic accepts partial location).
        user_location = WebSearchUserLocation(
            city=city,
            country=country,
            region="",
            timezone="",
        )

    return WebSearchTool(
        user_location=user_location,
        search_context_size=WEBSEARCH_CONTEXT_SIZE,  # type: ignore[arg-type]
        max_uses=WEBSEARCH_MAX_USES,
    )


__all__ = [
    "WEBSEARCH_CONTEXT_SIZE",
    "WEBSEARCH_MAX_USES",
    "detect_country",
    "prepared_web_search",
]
