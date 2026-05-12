"""Four firecrawl-backed wizard fetch_* tools (Spec 216-E).

Each tool is registered on the wizard agent via ``@agent.tool`` (custom,
application-side — NOT a Pydantic AI builtin). The pattern is uniform:

  1. Increment ``ctx.deps.fetch_invocations_this_turn``. If >1 → return
     static fallback immediately (per-turn budget guard, E1.3).
  2. Compute sha256 cache key. Hit the in-module text-snippet cache first
     (E1.4 — cache hits skip the live call entirely).
  3. Check cumulative fetch budget via
     ``CostGuard.check_fetch_budget(deps)``. Reject + log on overflow.
  4. ``await asyncio.wait_for(_firecrawl_search(...), timeout=...)``
     (E1.6/E1.11 — 3s per attempt, NOT cumulative).
  5. Summarize result to ≤200 chars, store in cache, increment cumulative
     cost. Emit structured log per E1.9.
  6. On any timeout or firecrawl error → return static cohort fallback
     (graceful degradation; user-facing response stays 200).

The API key is NEVER logged or returned (E1.10). Failures log only the
hashed cache key and a coarse error class.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Final

from pydantic_ai import RunContext

from nikita.agents.onboarding.cost_guard import CostGuard
from nikita.config.settings import get_settings


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tuning constants (per .claude/rules/tuning-constants.md)
# ---------------------------------------------------------------------------

FETCH_SNIPPET_MAX_CHARS: Final[int] = 200
"""Max length of a fetch_* tool's returned snippet, in characters.

Current value: 200 (Spec 216-E, E1.1 lock-in).
Prior values: N/A — introduced here.

Rationale: spec line 20 mandates each fetch tool returns ≤200 char text.
The system prompt is the bottleneck for total LLM cost; bounding each
fetch keeps the per-turn injected context predictable.
"""

FIRECRAWL_PER_CALL_USD: Final[Decimal] = Decimal("0.025")
"""Per-call firecrawl cost estimate, in USD.

Current value: $0.025 (Spec 216-E spec line 73 estimate).
Prior values: N/A.
Rationale: firecrawl /search pricing approx $0.025 per low-context-size
query; used as the default ``additional_cost`` argument to
``CostGuard.check_fetch_budget``. Update when firecrawl repricing is
confirmed in production.
"""


# ---------------------------------------------------------------------------
# Module-level text-snippet cache (216-E)
# ---------------------------------------------------------------------------

# Process-local memo of firecrawl results, keyed by sha256-hex of the
# normalized query string. Returned snippets are ≤200 chars. Cohort
# CohortCache (cohort_chips.py) handles chip lookups; this cache handles
# free-text fetch results.
_FETCH_CACHE: dict[str, str] = {}

# Static fallback snippets used when (a) firecrawl is disabled, (b) the
# per-turn budget is exhausted, or (c) the live call times out. The fall-
# back text is intentionally generic so it never leaks user PII.
_STATIC_FALLBACKS: dict[str, str] = {
    "city_context": "A real city with its own rhythm; people, weather, places worth noticing.",
    "occupation_signal": "Work shapes how people structure their week and where they spend energy.",
    "time_of_day_signal": "The hour colors what's plausible right now — quiet streets or buzzing rooms.",
    "topic_specific": "A real-world thread worth pulling on; specifics matter more than abstractions.",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_key(*parts: str) -> str:
    """sha256-hex over ``"|"``-joined lowercased parts. Stable cache key."""
    normalized = "|".join(p.strip().lower() for p in parts if p)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _truncate(text: str, max_chars: int = FETCH_SNIPPET_MAX_CHARS) -> str:
    """Truncate to ≤``max_chars``, preserving full chars (no surrogate split)."""
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _emit_tool_log(
    *,
    tool_name: str,
    outcome: str,
    duration_ms: int,
    cohort_cache_used: bool,
    cost_usd_delta: Decimal,
    traceparent: str = "",
    cache_key_hash: str = "",
) -> None:
    """Emit the structured tool-call log per Spec 216-E E1.9.

    NEVER includes raw PII (city, occupation, topic) or the firecrawl API
    key — only a hashed cache key suffices to correlate cache hits.

    ``cost_usd_delta`` is serialized as ``float`` (not ``str``) so GCP
    Logging indexes the field as numeric and aggregations (sum/avg) work
    natively without client-side parsing. Decimal precision loss vs.
    float at this scale ($0.025) is negligible for log analytics.
    Closes PR #462 QA review N1.
    """
    logger.info(
        "agent_tool_call",
        extra={
            "event": "agent_tool_call",
            "tool_name": tool_name,
            "outcome": outcome,
            "duration_ms": duration_ms,
            "cohort_cache_used": cohort_cache_used,
            "cost_usd_delta": float(cost_usd_delta),
            "traceparent": traceparent,
            "cache_key_hash": cache_key_hash,
        },
    )


def _static_fallback(label: str) -> str:
    """Return the static-fallback snippet for ``label`` (≤200 chars)."""
    return _truncate(_STATIC_FALLBACKS.get(label, _STATIC_FALLBACKS["topic_specific"]))


async def _firecrawl_search(query: str, *, api_key: str) -> str:
    """Issue a firecrawl /search call and return a concatenated snippet.

    Implementation note: 216-E ships with a thin in-module HTTP client to
    avoid a hard dependency on the firecrawl-py SDK at this point in the
    rollout. The real call is gated by ``api_key`` presence; when the key
    is empty the function raises ``RuntimeError`` so the caller can fall
    through to the static cohort fallback in the standard exception path.

    NEVER logs or echoes ``api_key``. The query string itself is treated
    as PII-adjacent and is NOT logged.
    """
    if not api_key:
        # Firecrawl disabled (no secret in env). Caller logs the outcome
        # and falls back to the static snippet.
        raise RuntimeError("firecrawl_disabled")

    # Lazy import: keep ``httpx`` out of module-import path for tests that
    # mock this entire function via ``patch``.
    import httpx  # noqa: PLC0415

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.firecrawl.dev/v0/search",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"query": query, "limit": 3},
            timeout=None,  # Outer asyncio.wait_for owns the timeout.
        )
        response.raise_for_status()
        data = response.json()

    # Concatenate top result snippets, then truncate.
    results = data.get("data") or data.get("results") or []
    parts: list[str] = []
    for item in results[:3]:
        snippet = (
            item.get("description")
            or item.get("snippet")
            or item.get("content")
            or ""
        )
        if snippet:
            parts.append(snippet.strip())
    if not parts:
        raise RuntimeError("firecrawl_empty")
    return " ".join(parts)


async def _run_fetch(
    ctx: "RunContext",
    *,
    label: str,
    query: str,
    cache_key_hash: str,
) -> str:
    """Shared implementation for the 4 fetch_* tools.

    Encapsulates: per-turn budget cap, in-module cache lookup, cumulative
    fetch-budget guard, 3s asyncio.wait_for timeout, structured logging.
    """
    deps = ctx.deps
    settings = get_settings()
    started = time.monotonic()
    traceparent = getattr(deps, "traceparent", "") or ""

    # Per-turn budget guard (E1.3). Increment FIRST so even early-exits
    # bookkeep correctly.
    deps.fetch_invocations_this_turn = (
        getattr(deps, "fetch_invocations_this_turn", 0) + 1
    )
    if deps.fetch_invocations_this_turn > 1:
        _emit_tool_log(
            tool_name=label,
            outcome="budget_exceeded",
            duration_ms=int((time.monotonic() - started) * 1000),
            cohort_cache_used=False,
            cost_usd_delta=Decimal("0"),
            traceparent=traceparent,
            cache_key_hash=cache_key_hash,
        )
        return _static_fallback(label)

    # Cohort cache lookup BEFORE issuing live fetch (E1.4).
    cached = _FETCH_CACHE.get(cache_key_hash)
    if cached is not None:
        _emit_tool_log(
            tool_name=label,
            outcome="cache_hit",
            duration_ms=int((time.monotonic() - started) * 1000),
            cohort_cache_used=True,
            cost_usd_delta=Decimal("0"),
            traceparent=traceparent,
            cache_key_hash=cache_key_hash,
        )
        return cached

    # Cumulative fetch-budget guard (E1.3 hard ceiling).
    if not CostGuard.check_fetch_budget(deps, FIRECRAWL_PER_CALL_USD):
        _emit_tool_log(
            tool_name=label,
            outcome="budget_exceeded",
            duration_ms=int((time.monotonic() - started) * 1000),
            cohort_cache_used=False,
            cost_usd_delta=Decimal("0"),
            traceparent=traceparent,
            cache_key_hash=cache_key_hash,
        )
        return _static_fallback(label)

    # Live firecrawl call wrapped in per-attempt timeout (E1.6/E1.11).
    # Single source of truth: Pydantic Settings reads FIRECRAWL_API_KEY
    # from the env via case-insensitive matching. The prior `or os.environ.get(...)`
    # belt-and-suspenders fallback was dead code that masked Settings
    # misconfiguration. Closes PR #462 QA review N2.
    api_key = settings.firecrawl_api_key
    timeout_s = float(settings.firecrawl_timeout_s)
    try:
        raw = await asyncio.wait_for(
            _firecrawl_search(query, api_key=api_key),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        _emit_tool_log(
            tool_name=label,
            outcome="timeout",
            duration_ms=int((time.monotonic() - started) * 1000),
            cohort_cache_used=False,
            cost_usd_delta=Decimal("0"),
            traceparent=traceparent,
            cache_key_hash=cache_key_hash,
        )
        return _static_fallback(label)
    except Exception as exc:  # noqa: BLE001 — coarse class, never echo API key
        # ``str(exc)`` is intentionally sanitized: stringified RuntimeError
        # / httpx.HTTPStatusError contain the URL but NOT the bearer token.
        # The bearer token only ever lives in the request header.
        _emit_tool_log(
            tool_name=label,
            outcome=f"firecrawl_error:{type(exc).__name__}",
            duration_ms=int((time.monotonic() - started) * 1000),
            cohort_cache_used=False,
            cost_usd_delta=Decimal("0"),
            traceparent=traceparent,
            cache_key_hash=cache_key_hash,
        )
        return _static_fallback(label)

    # NOTE: firecrawl response snippets are NOT currently PII-stripped; tracked in
    # GH #463 as a follow-up enhancement. Spec 216-E does not require it explicitly
    # (E1.10 covers API-key handling only); deferred per PR #462 QA review.
    snippet = _truncate(raw)
    _FETCH_CACHE[cache_key_hash] = snippet

    # Track cumulative cost. ``fetch_cost_cumulative`` may be float or
    # Decimal depending on caller; coerce safely.
    current = deps.fetch_cost_cumulative
    if isinstance(current, Decimal):
        deps.fetch_cost_cumulative = current + FIRECRAWL_PER_CALL_USD
    else:
        deps.fetch_cost_cumulative = float(
            Decimal(str(current)) + FIRECRAWL_PER_CALL_USD
        )

    _emit_tool_log(
        tool_name=label,
        outcome="success",
        duration_ms=int((time.monotonic() - started) * 1000),
        cohort_cache_used=False,
        cost_usd_delta=FIRECRAWL_PER_CALL_USD,
        traceparent=traceparent,
        cache_key_hash=cache_key_hash,
    )
    return snippet


# ---------------------------------------------------------------------------
# The 4 fetch_* tools — registered as @agent.tool decorators in
# conversation_agent.py.
# ---------------------------------------------------------------------------


async def fetch_city_context(
    ctx: "RunContext", city: str
) -> str:
    """Return ≤200 char cultural snippet for ``city``.

    1-line cultural note + 2-3 distinctive landmarks/scenes. Uses
    firecrawl /search. Hits the in-module text-snippet cache before
    issuing a live call. On timeout / error / over-budget → returns the
    static city fallback (≤200 chars). NEVER raises.
    """
    cache_key_hash = _hash_key("city_context", city or "")
    query = f"{city} culture nightlife landmarks 2026"
    return await _run_fetch(
        ctx, label="city_context", query=query, cache_key_hash=cache_key_hash
    )


async def fetch_occupation_signal(
    ctx: "RunContext", occupation: str, city: str
) -> str:
    """Return ≤200 char snippet describing the ``occupation`` × ``city``
    professional scene.

    Used by the wizard turn that probes ``occupation`` for grounding the
    follow-up question in the user's likely day-to-day. NEVER raises.
    """
    cache_key_hash = _hash_key("occupation_signal", city or "", occupation or "")
    query = f"{occupation} professionals {city} routine 2026"
    return await _run_fetch(
        ctx, label="occupation_signal", query=query, cache_key_hash=cache_key_hash
    )


async def fetch_time_of_day_signal(
    ctx: "RunContext", city: str
) -> str:
    """Return ≤200 char snippet keyed to the current hour-of-day in
    ``city`` (UTC bucketed into morning/afternoon/evening/night).

    Lets the wizard ground replies in plausible scenes — e.g. "morning
    rush" vs "after-work crowd." NEVER raises.
    """
    now = datetime.now(timezone.utc)
    hour = now.hour
    if 5 <= hour < 12:
        bucket = "morning"
    elif 12 <= hour < 17:
        bucket = "afternoon"
    elif 17 <= hour < 22:
        bucket = "evening"
    else:
        bucket = "night"
    cache_key_hash = _hash_key("time_of_day_signal", city or "", bucket)
    query = f"{city} {bucket} scene typical activities"
    return await _run_fetch(
        ctx, label="time_of_day_signal", query=query, cache_key_hash=cache_key_hash
    )


async def fetch_topic_specific(
    ctx: "RunContext", topic: str, city: str
) -> str:
    """Return ≤200 char snippet about ``topic`` in ``city``.

    General-purpose probe used when a slot is open-ended (saturday_morning,
    geek_out_on, together_we_could). NEVER raises.
    """
    cache_key_hash = _hash_key("topic_specific", city or "", topic or "")
    query = f"{topic} in {city} 2026 specifics"
    return await _run_fetch(
        ctx, label="topic_specific", query=query, cache_key_hash=cache_key_hash
    )


# Test/debug helper — clears the in-module cache between test runs.
def _reset_fetch_cache_for_tests() -> None:
    """Test-only: clear ``_FETCH_CACHE``. Not part of the public API."""
    _FETCH_CACHE.clear()


__all__ = [
    "FETCH_SNIPPET_MAX_CHARS",
    "FIRECRAWL_PER_CALL_USD",
    "fetch_city_context",
    "fetch_occupation_signal",
    "fetch_time_of_day_signal",
    "fetch_topic_specific",
]


# Re-export the private helpers for tests.
def _get_fetch_cache() -> dict[str, str]:
    """Test-only accessor for the in-module cache."""
    return _FETCH_CACHE


def _get_static_fallback(label: str) -> str:
    """Test-only accessor for static fallback strings."""
    return _static_fallback(label)


# Mark explicit test-only API (single underscore convention).
def _set_cache_for_tests(key: str, value: str) -> None:
    """Test-only: prime the cache with a known value."""
    _FETCH_CACHE[key] = value


# Convenience wrappers used in tests instead of monkeypatching internals.
def _build_cache_key(*parts: str) -> str:  # exposed for tests
    return _hash_key(*parts)
