# Subspec 216-E — Agentic Tools (Firecrawl + WebSearchTool)

**Parent**: `specs/216-onboarding-redesign-cinematic/spec.md` FR-07, FR-12, NR-02, NR-06
**PR boundary**: 216-E (parallel with 216-C; depends on 216-B merged for agent integration)
**Estimated**: ~200 LOC (4 tools + budget guard) + ~100 LOC tests
**Status**: Draft (GATE 1)

---

## Scope

Give the wizard agent live agency via 4 firecrawl-backed Pydantic AI tools + Anthropic `WebSearchTool` builtin. Always-fetch-something directive: when `state.location` is present, agent MUST call ≥1 fetch tool per turn (skip turn 0 before location is collected). Per-turn budget guard caps fetch invocations to 1; cumulative fetch budget $0.10-0.15/flow. Cohort cache (`cohort_chips.py` lookup) hits BEFORE issuing live fetch. Anthropic prompt caching on FIXED instructions block (≥60% hit rate).

Scoped to async Pydantic AI tool integration. Cost circuit-breaker integration with `CostGuard` from 216-B.

## Acceptance Criteria

| AC | Description | Severity |
|----|-------------|----------|
| **E1.1** | Four `fetch_*` async tools registered as Pydantic AI builtin_tools (or `@agent.tool` decorators): `fetch_city_context(city: str)`, `fetch_occupation_signal(occupation: str, city: str)`, `fetch_time_of_day_signal(city: str, dt: datetime)`, `fetch_topic_specific(topic: str, city: str)`. Each returns ≤200 char text. | HIGH |
| **E1.2** | Always-fetch-something directive: per turn (skip turn 0), agent MUST invoke ≥1 fetch tool when `state.location` is present. Verified via Cloud Run log filter `"fetch_*" call count >= 1` per turn (after turn 1). Fallback: if no fetch fires, use static fallback. | HIGH |
| **E1.3** | Per-turn budget guard: `RunContext.deps.fetch_invocations_this_turn <= 1`. Cumulative fetch budget tracked in `RunContext.deps.fetch_cost_cumulative`; hard ceiling $0.15/flow; soft warn at $0.10. | HIGH |
| **E1.4** | Cohort cache (`nikita/agents/onboarding/cohort_chips.py:lookup_cohort`) is consulted BEFORE issuing live fetch. Cache hits return immediately without firecrawl call. Cache key = sha256 hash of `(lowercase_city, lowercase_occupation)`. | HIGH |
| **E1.5** | `WebSearchTool` configured with `search_context_size="low"`, `max_uses=2`, `user_location=WebSearchUserLocation(city=state.location.value, country=detect_country(...))`. Anthropic provider (Claude Opus 4.7). Wired via `prepared_*` callable that returns `None` when `state.location` absent. | MED |
| **E1.6** | Per-tool 3s timeout via `asyncio.wait_for(...)`. On timeout: log + use cohort cache fallback OR `static_fallback_question` from `follow_up_registry.yaml`. NEVER block the turn (graceful degradation). | HIGH |
| **E1.7** | Cumulative `cost_usd` tracked across all LLM calls (Opus + Haiku + WebSearchTool) and fetch tools. Written to `users.cost_usd` column post-flow. <$0.50/flow hard ceiling enforced via `CostGuard.check_budget()`. | CRIT |
| **E1.8** | Anthropic prompt caching enabled on FIXED instructions block of `inject_per_turn_context` callable. Verified via Cloud Run logs: `cache_read_input_tokens / total_input_tokens >= 0.60` averaged across turns 3-12. | MED |
| **E1.9** | **Tool failure log shape** (closes api-validator HIGH-7, testing-validator MEDIUM-4): every firecrawl tool call emits structured Cloud Run log per master spec §HTTP API Contracts: `{event: "agent_tool_call", tool_name, outcome ∈ {success, cache_hit, timeout, firecrawl_error, budget_exceeded}, duration_ms, cohort_cache_used, cost_usd_delta, traceparent}`. User-facing response remains 200 (graceful degradation). G.5 W4 walk verification queries this exact event shape. | HIGH |
| **E1.10** | **`FIRECRAWL_API_KEY` secret handling** (closes api-validator HIGH-8): stored as Cloud Run secret env var (NOT in `.env` committed file). NEVER logged in plaintext. NEVER returned in any HTTP response or `ErrorEnvelope.detail`. Verified by `tests/agents/onboarding/test_firecrawl_secret_handling.py`: simulates a tool failure and asserts no captured log line contains the API key value. | HIGH |
| **E1.11** | Firecrawl 3s timeout is **per-attempt** (NOT cumulative across retries). Tools do NOT participate in `ModelRetry` loop (only the agent's `@output_validator` does). On firecrawl timeout → fall through to static fallback within the same attempt. (Closes api-validator MEDIUM-3.) | MED |
| **E1.12** | Tool registration mechanism disambiguated: `WebSearchTool` registers via `builtin_tools=[prepared_web_search]` (provider-native Anthropic builtin); the 4 `fetch_*` tools register via `@agent.tool` decorators (application-side custom tools). NOT conflated. Verify against Pydantic AI 1.71.0 `prepare_tools` API surface. (Closes api-validator MEDIUM-4 + MEDIUM-5.) | MED |

## Critical Files

### NEW Python modules
- `nikita/agents/onboarding/tools/__init__.py` (NEW) — namespace
- `nikita/agents/onboarding/tools/firecrawl_tools.py` (NEW) — 4 `fetch_*` async functions wrapping firecrawl MCP via `Firecrawl` Python SDK or HTTP client; cohort cache lookup; budget tracking; 3s timeout
- `nikita/agents/onboarding/tools/web_search.py` (NEW) — `prepared_web_search(ctx) -> WebSearchTool | None` callable returning configured tool or None
- `nikita/agents/onboarding/cost_guard.py` (NEW or extend if 216-B created it) — `CostGuard` class tracking cumulative cost across LLM + fetch + WebSearchTool

### EXTENDED
- `nikita/agents/onboarding/conversation_agent.py:127-197` — register `builtin_tools=[prepared_web_search, fetch_city_context, fetch_occupation_signal, fetch_time_of_day_signal, fetch_topic_specific]` on the agent.
- `nikita/agents/onboarding/state.py` — extend `ConverseDeps` with `fetch_invocations_this_turn: int`, `fetch_cost_cumulative: Decimal`, `cohort_cache: CohortCache`.

### CONFIG
- `nikita/config/settings.py` — add `FIRECRAWL_API_KEY` (Pydantic settings env var), `FIRECRAWL_TIMEOUT_S = 3.0`, `FETCH_BUDGET_HARD_USD = Decimal("0.15")`, `FETCH_BUDGET_WARN_USD = Decimal("0.10")`.

## Tools — Implementation Skeleton

### `fetch_city_context(ctx: RunContext[ConverseDeps], city: str) -> str`

```python
async def fetch_city_context(ctx: RunContext[ConverseDeps], city: str) -> str:
    """1-line cultural note + 2-3 distinctive landmarks/scenes for city."""
    ctx.deps.fetch_invocations_this_turn += 1
    if ctx.deps.fetch_invocations_this_turn > 1:
        return ctx.deps.cohort_cache.get_static_fallback("city_context")

    cache_key = hash_pii(city)
    if (cached := ctx.deps.cohort_cache.get(cache_key)):
        return cached

    try:
        result = await asyncio.wait_for(
            firecrawl.search(
                query=f"{city} culture nightlife landmarks 2026",
                limit=3,
                context_size="low",
            ),
            timeout=settings.FIRECRAWL_TIMEOUT_S,
        )
        snippet = summarize_firecrawl_results(result, max_chars=200)
        ctx.deps.cohort_cache[cache_key] = snippet
        ctx.deps.fetch_cost_cumulative += Decimal("0.025")  # firecrawl pricing approx
        return snippet
    except (asyncio.TimeoutError, FirecrawlError) as e:
        logger.warning("fetch_city_context_timeout", city_hash=cache_key, error=str(e))
        return ctx.deps.cohort_cache.get_static_fallback("city_context")
```

Other 3 tools follow the same pattern with topic-specific queries.

### `prepared_web_search(ctx: RunContext[ConverseDeps]) -> WebSearchTool | None`

```python
async def prepared_web_search(ctx: RunContext[ConverseDeps]) -> WebSearchTool | None:
    if not ctx.deps.state.location:
        return None  # Don't waste a tool on turn 0
    return WebSearchTool(
        user_location=WebSearchUserLocation(
            city=ctx.deps.state.location.value,
            country=detect_country(ctx.deps.state.location.value),
        ),
        search_context_size="low",
        max_uses=2,
    )
```

## Tests to Write

| Test File | Focus | AC |
|-----------|-------|-----|
| `tests/agents/onboarding/test_firecrawl_tools.py` | 4 tools return text ≤200 chars; per-turn budget guard rejects 2nd call; cohort cache hits before live fetch | E1.1, E1.3, E1.4 |
| `tests/agents/onboarding/test_firecrawl_timeout.py` | mock 4s delay; assert tool returns static fallback within 3.5s; logs warning | E1.6 |
| `tests/agents/onboarding/test_always_fetch_directive.py` | mocked agent + 12-turn sequence; assert ≥1 fetch fired per turn (after turn 1) | E1.2 |
| `tests/agents/onboarding/test_cost_guard.py` | mock LLM call returning $0.04; cumulative tracked; hard ceiling fires at $0.50 | E1.7 |
| `tests/agents/onboarding/test_prepared_web_search.py` | turn 0 (no location) → None; turn 1+ (location set) → configured tool | E1.5 |
| `tests/agents/onboarding/test_prompt_cache_hit_rate.py` | mocked Anthropic responses with cache_read_input_tokens metric; assert >=0.6 over turns 3-12 | E1.8 |

## Latency Budget

Per-turn p99 target: 8s. Composition:
- Pydantic AI agent.run (Opus): ~2-3s
- 1× Haiku Big5 judge (216-D): ~0.5s
- 1× firecrawl tool: ~1.5-2s (with 3s timeout)
- WebSearchTool (when fired): ~1.5-3s
- Network + DB read: ~0.3s
- **Total p99 budget**: <8s

When `state.location` absent (turn 0): no fetch fires; latency drops to ~3s.

## Open Questions

- **Q1**: Firecrawl tier — paid vs free; budget needs $0.025/call × 12 turns × beta-100-users = ~$30/100 users. Acceptable. Confirm key.
- **Q2**: Cost telemetry surface — Cloud Run log? Datadog metric? Default: Cloud Run structured log with `cost_usd_per_flow` field for SLO dashboards.
- **Q3**: WebSearchTool pricing visibility — Anthropic docs say "pay-per-use, see Anthropic pricing"; verify before launch.
- **Q4**: Cache eviction strategy for `CohortCache` — LRU? TTL? Default: TTL 7d (city contexts don't change fast).

## References

- Master spec FR-07, FR-12, NR-02, NR-06
- Pydantic AI builtin tools doc: https://ai.pydantic.dev/builtin-tools
- Firecrawl Python SDK: https://docs.firecrawl.dev/sdks/python
- `.claude/rules/agentic-design-patterns.md` Rule #5 (validation layering — fetch is layer 3 fallback)
- Spec 215 B2 — `cost_usd` column source
