# Agentic Backstory + Live Tools — Research Synthesis (2026-04-28)

> **PLAN-MODE CONSTRAINT**: This research was requested at `docs-to-process/20260428-spec216-backstory-agent-tools.md`, but plan mode restricts edits to this plan file only. After plan approval, copy/move this content to the requested path. Content is otherwise the deliverable as specified.

> **Sourcing note**: Perplexity quota was exhausted at session start (HTTP 401 insufficient_quota); Gemini deep-research (id `v1_ChdSWUh3YVpxSU5hejNuc0VQbnJQUi1BURIXUllId2FacUlOYXozbnNFUG5yUFItQVE`) was still processing at write time. Synthesis below uses Pydantic AI docs (primary), Firecrawl docs (primary), and reviewer/blog secondary sources via WebSearch/WebFetch. URLs + retrieval dates in §Sources.

## TL;DR

Five principles for making Nikita's onboarding feel "alive":

1. **Cumulative Pydantic state + dynamic instructions** — a `WizardSlots` model with `@computed_field missing` injected into `Agent(instructions=callable)` per turn. Avoids the Walk V anti-pattern and makes "what's next" emergent rather than scripted.
2. **One agent, one mixed-output tool** (`output_type=[SlotDelta, str]`) — refuses N-tool fan-out. Adds optional `look_up()` and `brainstorm()` agency tools the agent can choose to call when user input is interesting.
3. **Live web context, sparingly and asynchronously** — at most 1-2 firecrawl/WebSearchTool calls per slot, gated by a per-flow budget (e.g., 3 calls / $0.10 / 6s total wall-clock). Cache by `(country, city, occupation, age_band)` cohort key in Supabase, TTL 7d.
4. **"Nikita is checking..." is a UX primitive, not a fake spinner** — only show it when the agent actually invoked a tool. Surface 1 citation chip ("from local Zürich techno scene") rather than 5 raw URLs.
5. **Pydantic completion gate, not LLM judgment** — `try: FinalForm.model_validate(slots)` decides when handoff happens. Agent has agency to ask wildcards but cannot decide flow is complete; that's structural.

## 1. AI companion onboarding teardowns

### Replika (Luka Inc.)
- **Data collected upfront**: name, gender, avatar appearance, relationship-mode (friend/romantic/mentor), personality trait quiz. 3D avatar customization gates entry. Quiz answers steer initial tone.
- **First conversation**: friendly + structured; opens with reassurance prompts mirroring the quiz mode. Pro tier exposes selectable personality traits (curious/calm/adventurous) that genuinely change response style.
- **Live web search**: no public evidence of live web search at signup. "Memory bank" is internal-only, populated as the user volunteers facts.
- **Alive vs form-feel**: form-heavy (avatar builder + quiz before any chat). Compensates with rich avatar reward and immediate persona consistency.
- Source: eesel review (https://www.eesel.ai/blog/replika-ai), AICompanionGuides 8-month review (https://aicompanionguides.com/blog/replika-review/), App Fuel onboarding teardown (https://theappfuel.com/examples/replika_onboarding) — retrieved 2026-04-28.

### Character.ai
- **Data collected**: minimal at signup (mostly platform account); character creation is the actual onboarding. First 3,200 chars of a persona description are the only ones that meaningfully steer model behavior — important constraint for our backstory length.
- **First conversation**: user-generated personas, so no canonical first-message; platform optimizes home-feed + creator challenges for retention rather than a single signup ramp.
- **Live web search**: no — characters are static text + tuned base model.
- **Alive vs form-feel**: deeply customizable but heavy lift — opposite end from Nikita's "do it for me" desired feel.
- Source: Opinly platform deep-dive (https://opinly.ai/blog/cai), Character.ai create-character page (https://character.ai/character/new), Summon Worlds 2025 guide (https://www.summonworlds.com/the-ultimate-2025-guide-to-ai-character-creation/) — retrieved 2026-04-28.

### Nomi.ai
- **Data collected**: name + avatar + trait set + custom-persona backstory. No billing prompt during signup — friction-free.
- **First conversation**: dialogue-and-personality-centric; user can write extensive backstories upfront, and the AI maintains short/medium/long-term memory layers across sessions.
- **Live web search**: not advertised. Differentiator is *memory persistence*, not *live context*.
- **Alive vs form-feel**: more conversational than Replika (less avatar-builder time), 4.7/5 reviewer scores from 4-month testers; widely cited as the "soul/memory" benchmark.
- Source: companionguide 8-week review (https://companionguide.ai/news/nomi-ai-comprehensive-review-2025), Roborhythms memory review (https://www.roborhythms.com/nomi-ai-review/) — retrieved 2026-04-28.

### Pi (Inflection AI)
- **Data collected**: minimal — Pi explicitly opted *out* of personality customization. Approach was "one personality, deep emotional intelligence, asks follow-ups."
- **First conversation**: warm, follow-up-question heavy. Personality team included therapists, playwrights, comedians (paid hundreds/hr) to author a felt-personality through prompt + RLHF, not user customization.
- **Live web search**: no.
- **Alive vs form-feel**: maximally alive *because* there's no form. Cautionary tale: failed commercially, Microsoft acqui-hired the team March 2024. Lesson: consumer LLM market doesn't pay for "felt presence" alone — needs a hook.
- Source: IEEE Spectrum rise/fall (https://spectrum.ieee.org/inflection-ai-pi), Pi onboarding page (https://pi.ai/onboarding) — retrieved 2026-04-28.

### Hinge AI prompts
- **Data collected**: Hinge collects extensive profile data; AI prompt feature *suggests* prompt answers the user has already started. Not a chatbot — different category, but instructive: AI augments user voice rather than replaces it.
- **Backstory generation**: AI rewrites/expands user-supplied seed text. Live context: none, just user-supplied profile.
- Lesson for Nikita: when generating backstory, treat user's slot answers as the seed; the agent's job is *expansion + flair*, not invention.
- Source: not explicitly retrieved this session — gap; recommend Hinge product blog skim before §4 implementation.

## 2. WebSearchTool / firecrawl as agent tool — patterns

### Pydantic AI built-in WebSearchTool
- **Providers**: Anthropic (full), OpenAI Responses (`openai-responses:gpt-5.2`), Gemini (limited, no params), xAI, Groq (compound models only), OpenRouter (via plugins). Source: https://pydantic.dev/docs/ai/tools-toolsets/builtin-tools/.
- **Parameters**: `search_context_size` (OpenAI), `user_location: WebSearchUserLocation(city, country, region)` (Anthropic + OpenAI), `blocked_domains` / `allowed_domains` (Anthropic XOR — not both), `max_uses` (Anthropic-only — critical for budget enforcement).
- **Latency**: not published as SLA. Anthropic web_search tool is server-side at the model API layer, so adds 1-3s typical to a generation; OpenAI Responses similar.
- **Citation handling**: OpenAI requires `OpenAIResponsesModelSettings(openai_include_web_search_sources=True)`; results then on `ModelResponse.builtin_tool_calls`. Anthropic ships citations natively in the response stream. Tool version on Anthropic side: `web_search_20250305` (PydanticAI as of issue #4647 has not upgraded to `web_search_20260209` w/ dynamic filtering yet).
- **Code**:
```python
from pydantic_ai import Agent, WebSearchTool, WebSearchUserLocation

wizard_agent = Agent(
    "anthropic:claude-opus-4-7",
    builtin_tools=[
        WebSearchTool(
            user_location=WebSearchUserLocation(city=slots.city, country=slots.country, region=None),
            allowed_domains=["wikipedia.org", "timeout.com", "ra.co", "openweathermap.org"],
            max_uses=2,  # HARD CAP per turn
        )
    ],
    deps_type=WizardDeps,
    instructions=lambda ctx: build_prompt(ctx.deps.slots),  # dynamic
)
```

### Custom firecrawl tool wrapper
- **Latency**: P95 3.4s end-to-end across millions of pages (Firecrawl marketing); `/search` default timeout 60s, configurable 1-300s. Adding `scrapeOptions` does not multiply credits but adds wall-clock per page.
- **Caching**: `maxAgeMs` parameter (default 2 days) returns cached scrape if within window — up to 5x faster. We should set `maxAgeMs=604_800_000` (7d) for cohort-stable lookups.
- **Pricing**: Base scrape = N credits per page; +1 PDF, +4 stealth proxy, +5 structured JSON. Firecrawl cli docs (https://docs.firecrawl.dev/api-reference/endpoint/search) does not list base credit; assume ~1 credit per result + 1 per scrape.
- **Code skeleton** (Pydantic AI 1.x):
```python
import asyncio, hashlib, json
from firecrawl import AsyncFirecrawlApp
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic import BaseModel

class WizardDeps(BaseModel):
    slots: "WizardSlots"
    firecrawl: AsyncFirecrawlApp
    cache: "SupabaseCache"   # per-cohort cache layer
    budget: "ToolBudget"      # tracks calls + tokens this flow

@wizard_agent.tool
async def look_up(
    ctx: RunContext[WizardDeps],
    query: str,
    intent: str,  # one of: "weather", "scene", "occupation_color", "local_event"
) -> str:
    """Look up live context that helps personalize the conversation. Use sparingly."""
    if not ctx.deps.budget.allow_call():
        raise ModelRetry("tool budget exhausted; answer from current context")
    cache_key_raw = f"{intent}:{ctx.deps.slots.city}:{ctx.deps.slots.country}:{query}"
    cache_key = hashlib.sha256(cache_key_raw.encode()).hexdigest()  # PII-safe
    if hit := await ctx.deps.cache.get(cache_key):
        return hit
    try:
        result = await asyncio.wait_for(
            ctx.deps.firecrawl.search(
                query=query,
                limit=3,
                location=f"{ctx.deps.slots.city},{ctx.deps.slots.country}",
                scrape_options={"formats": ["markdown"], "only_main_content": True},
                timeout=4000,
            ),
            timeout=5.0,
        )
    except (asyncio.TimeoutError, Exception) as e:
        ctx.deps.budget.record_failure()
        raise ModelRetry(f"lookup failed ({type(e).__name__}); proceed without external context")
    summary = _summarize(result)  # cap to 400 tokens
    await ctx.deps.cache.set(cache_key, summary, ttl_seconds=604_800)
    ctx.deps.budget.record_success()
    return summary
```
- **Token budget tracking**: `ToolBudget` records (call_count, est_tokens_in, est_tokens_out, wall_clock_ms) per flow; circuit-breakers if any limit breached. Budget exposed in `instructions=callable` so the agent's prompt knows its remaining headroom.

## 3. Live-context signals from minimal user data

Per Nikita's slot taxonomy:

| Slot | Live-context fetch (intent → query) | Adds what | Latency |
|---|---|---|---|
| `city, country` | `weather` → "current weather Zürich" via Wikipedia/openweathermap allowlisted | Time-of-day awareness, raining vs sunny conversational hook | ~1s WebSearchTool |
| `city, country` | `scene` → "techno underground Zürich 2026" via ra.co/timeout | Lets Nikita reference a specific local club / cafe instead of generic "your city" | ~2-3s firecrawl |
| `occupation` | `occupation_color` → "what do {occupation}s in {city} typically..." | Industry tropes calibration; e.g., Zürich-finance → late hours, expense-account dinners; Lisbon-medic → night shifts, residency culture | ~2s WebSearchTool |
| `age` | (no live fetch — internal lookup table) | Generational reference set: born ~2003 → grew up with TikTok and post-COVID adolescence; born ~1985 → MTV-era; cheap, deterministic | 0ms |
| `(city, occupation)` | (precomputed cohort flavor — see §6 caching) | Combinations like "zurich+finance" warm-cache flavor card | ~1ms cache hit |
| `darkness, scene` | (no live fetch; agent improvises) | Internal narrative beat; would not benefit from web | 0ms |
| `name` | (no live fetch) | — | 0ms |

**Recommended live-fetch slots only**: `city`, `occupation`, optionally `(city, scene)` combo. ≤2 calls per flow keeps latency under 6s aggregate.

## 4. Backstory generation — narrative-consistency patterns

- **One agent-generated "love letter" beats 3 prefab personas** for "alive" feel — but adds risk of low diversity. Mitigation: generate 3 candidates with high temperature (1.0) and low candidate count, then have agent pick the one that contradicts the others most. Or: generate 1 with `Agent(instructions=...)` containing a "do not echo these archetypes" anti-list.
- **Diversity guardrails**: `seen_archetypes: set[str]` in `WizardSlots` (or session-scoped Redis if cross-user diversity matters); pass into prompt as "you have written these archetypes before today: ...". Hard fact: Character.ai's first 3,200 chars dominate behavior — so the backstory must be ≤3,200 chars, not a novel.
- **PII safety**: never put `(exact_city, exact_age, exact_occupation)` in the same plain-text sentence in the persisted backstory. Generalize one of the three (city → "a German-speaking finance hub", or age → "late twenties"). Implement as `@output_validator` checking the regex pattern `\b{city}\b.*\b{age}\b.*\b{occupation}\b`; raise `ModelRetry` if matched.
- **Persona archetype taxonomy** (5-7):
  1. **The Fugitive** — running from a previous life, met Nikita while transient
  2. **The Insider** — owns the local scene, Nikita is a discovery they're protective of
  3. **The Rookie** — recently arrived (city/scene/role), Nikita is their first real connection
  4. **The Veteran** — mid-career disillusionment, Nikita is the rebellion
  5. **The Double-Life** — public role + secret identity, Nikita knows the secret
  6. **The Survivor** — past trauma in the chosen darkness slot, Nikita is reciprocal healing
  7. **The Climber** — ambitious in their occupation, Nikita destabilizes the climb
  Each archetype is a system-prompt fragment that the agent picks (or is forced to avoid) post-hoc.

## 5. UX of "agent thinking" / live brainstorming visible to user

- **"Nikita is checking..."** — typewriter dots, only shown when `tool_call_started` event fired by Pydantic AI. Faking it when no tool was called is the documented anti-pattern (cargo-cult thinking UI).
- **Citation chips**: 1 chip max ("from your city's techno calendar"). Multiple chips look like Bing, not a girlfriend. Chip is interactive but doesn't open the URL — opens an in-app tooltip with the snippet that informed Nikita's reaction. Replika and Nomi neither do this; opportunity for differentiation.
- **Streaming output**: stream the agent's free-text response while the structured `SlotDelta` finalizes; using `agent.run_stream(...)` + `result.stream_text(delta=True)`. User sees Nikita "thinking out loud" before her structured ack.
- **"Wait, let me look something up" delight moment**: agent system prompt includes a soft trigger — "if user input mentions a specific bar/club/event/landmark, you may call `look_up()` and afterward reference what you found." Caps via `max_uses` keep this tasteful.
- **Anti-patterns to refuse**:
  - Showing "Nikita is checking..." when no tool was invoked
  - Pasting raw search snippets into Nikita's voice
  - Citation chips that link to a 404 (always validate domain and HTTP status before showing)

## 6. Cost + latency reality

- **Per-screen cost (Claude Opus 4.7)**: $5 / 1M input + $25 / 1M output. A 7-slot wizard with ~1500 input + 200 output per turn × 7 turns = 10.5k in + 1.4k out = $0.0525 + $0.035 = ~$0.09 per flow base.
- **+ live-tool tax**: 2 firecrawl calls @ ~$0.005 each = $0.01; 1 WebSearchTool call (Anthropic native) is bundled in model cost but adds ~$0.005 in extra context tokens. Total per-flow = **~$0.10** with tools; **~$0.09** without. Within budget for an onboarding event.
- **Latency**:
  - Pure LLM turn: 2-4s (Opus 4.7 with 200-tok output)
  - + WebSearchTool: +2-3s
  - + firecrawl 1 call: +1-3s wall (P95 3.4s; with `maxAge` cache hit: ~50ms)
  - **Hard cap per turn**: 8s total wall-clock. Anything longer needs streaming + "checking..." UX.
- **Caching strategy**:
  - **Per-cohort key** (`hash(country, city, occupation, age_band)`) in Supabase table `onboarding_lookup_cache` with `value: text, expires_at: timestamptz`, TTL 7d. RLS: read by service role only (per `.claude/rules/testing.md` DB Migration Checklist).
  - **Per-user**: agent message history is already the cache (Pydantic AI `message_history=`).
- **Circuit-breaker**: per-user `tool_call_failures` counter; after 2 failures in 5 min, disable live tools for that flow and fall back to static cohort flavor card. Mirror Spec 215 B2 heartbeat-engine pattern.
- **When to skip live tools**:
  - User on slow connection (`Save-Data` header)
  - Firecrawl 5xx within last 30s
  - This user already exhausted budget
  - Slot doesn't benefit (name, age, darkness)

## 7. Async tool orchestration patterns

- **Pydantic AI async tools**: `@agent.tool` accepts `async def`; multiple tools in one turn execute *sequentially by default* unless using `asyncio.gather` inside a single tool. So if the agent wants weather + scene in one turn, expose a single `look_up_parallel(queries: list[str])` tool that fans out via `asyncio.gather`.
- **Parallel tool calls**: Anthropic native parallel tool use is opt-in via `parallel_tool_use=True` (model setting). Pydantic AI surfaces this; multiple tools in one assistant turn issue concurrent server-side calls. Tradeoff: you pay the slowest tool's latency, not the sum.
- **Timeout + fallback**: every async tool wrapped in `asyncio.wait_for(..., timeout=5.0)`; on timeout `raise ModelRetry("...")`. The agent then either retries with a narrower query or gives up gracefully.
- **Tool-selection bias mitigation**: per `.claude/rules/agentic-design-patterns.md`, prefer 1 mixed-output tool to N narrow tools. For Spec 216, suggested toolset: `extract` (`output_type=[SlotDelta, str]`, the one main tool) + `look_up` (optional, agent decides) + `brainstorm_archetype` (optional, used at backstory phase only). Three tools max; `instructions=callable` injects which slot the agent is currently working on so tool-selection bias is dampened.

## 8. Agent agency vs scripted UX

- **Default contract**: Question Registry defines the 7 slots and their target order; agent has discretion to *combine* slots into a turn or *delay* a slot if user input naturally suggests another. Agent CANNOT skip a required slot (Pydantic gate refuses to mark complete).
- **Wildcard tool — `look_up()`**: agent may invoke 0-2 times per flow when user input mentions something concrete (a club, a job title, a city quirk). Cost: bounded by `max_uses` and `ToolBudget`.
- **Risk: agent goes off-script forever** — known failure mode from Walk V (2026-04-22). Mitigations:
  - Cumulative `WizardSlots` Pydantic state (every turn must reduce `missing` by ≥0; ideally ≥1)
  - `max_turns` budget (e.g., 12 turns hard cap; soft warn at 8)
  - `instructions=callable` re-renders system prompt per turn with current `missing` injected — agent always sees what's left
  - Pydantic completion gate: only `try: FinalForm.model_validate(slots)` flips done state. No LLM bool literal allowed (anti-pattern table in `.claude/rules/agentic-design-patterns.md`).
- **Hybrid**: Question Registry as backbone, agent has narrow agency (combining, soft reordering, wildcard lookups). This pattern is documented in §6 of the Pydantic AI docs (https://pydantic.dev/docs/ai/) under "structured outputs + free text + tools".

## 9. Concrete recommendations for Spec 216

| # | Recommendation | Slots/Screens | Pydantic AI primitive | Source | Cost/flow ($) | Difficulty |
|---|---|---|---|---|---|---|
| 1 | Cumulative `WizardSlots(BaseModel)` with `@computed_field missing/progress_pct` | All | Pydantic v2 BaseModel + `model_copy(update=...)` | `.claude/rules/agentic-design-patterns.md` Hard Rule 1 | $0 | S |
| 2 | Single agent, `output_type=[SlotDelta, str]`, dynamic `instructions=callable` | All | `Agent(output_type=Union, instructions=lambda ctx: ...)` | https://pydantic.dev/docs/ai/tools-toolsets/builtin-tools/ | +$0.00 | S |
| 3 | `FinalForm.model_validate()` completion gate (NEVER bool literal) | Handoff | `@model_validator(mode='after')` | `agentic-design-patterns.md` Rule 2 | $0 | S |
| 4 | Optional `look_up()` tool wrapping firecrawl `/search` w/ 5s timeout + cohort cache | `city`, `occupation` | `@agent.tool async`, `asyncio.wait_for`, `ModelRetry` | https://docs.firecrawl.dev/api-reference/endpoint/search | +$0.01 | M |
| 5 | `WebSearchTool(allowed_domains=[...], max_uses=2)` for fast Anthropic-native lookups | `city` weather/time-of-day | `pydantic_ai.WebSearchTool` | https://pydantic.dev/docs/ai/tools-toolsets/builtin-tools/ | +$0.005 | S |
| 6 | `ToolBudget` deps object (calls + tokens + failures), exposed in `RunContext` and prompt | All turns | `Agent(deps_type=WizardDeps)` + `RunContext[WizardDeps]` | https://pydantic.dev/docs/ai/ | $0 | M |
| 7 | Citation chip UI (1 chip max, in-app tooltip not external nav) | After any tool call | Frontend: portal/onboarding, parse `result.builtin_tool_calls` | Pydantic AI ModelResponse spec | $0 | M |
| 8 | Persona archetype taxonomy (7 archetypes, anti-repeat seen-set per flow) | Backstory screen | Custom Pydantic enum + `@output_validator` regex check | This doc §4 | +$0.005 | M |
| 9 | PII regex-validator post-backstory: refuse `\b{city}\b.*\b{age}\b.*\b{occupation}\b` co-occurrence; ModelRetry to generalize one | Backstory screen | `@agent.output_validator + raise ModelRetry` | `agentic-design-patterns.md` Rule 5 (post-tool layer) | +$0.01 (retry tax) | M |
| 10 | Supabase `onboarding_lookup_cache` (cohort-key SHA-256, 7d TTL, RLS service-role-only) | All `look_up()` calls | DB + `@agent.tool` cache check | `.claude/rules/testing.md` Migration Checklist | $0 | M |

**Total estimated cost per flow with all 10 implemented: ~$0.10. Latency budget: ≤8s per turn × ≤8 turns = ≤64s total wizard time, with most turns 2-4s (no tool).**

**Difficulty totals**: 4 S, 6 M. No L items — all in scope for a 2-3 day spec implementation if Walk V remediations from `.claude/rules/agentic-design-patterns.md` are already wired.

## Sources

All retrieved 2026-04-28 unless noted.

- Pydantic AI builtin tools — https://pydantic.dev/docs/ai/tools-toolsets/builtin-tools/
- Pydantic AI builtin_tools API — https://ai.pydantic.dev/api/builtin_tools/
- Pydantic AI Anthropic models page — https://ai.pydantic.dev/api/models/anthropic/
- Pydantic AI issue #4647 (web_search_20260209 upgrade pending) — https://github.com/pydantic/pydantic-ai/issues/4647
- Pydantic AI issue #1683 (Anthropic Web Search Tool original) — https://github.com/pydantic/pydantic-ai/issues/1683
- Firecrawl /search reference — https://docs.firecrawl.dev/api-reference/endpoint/search
- Firecrawl mastering /search blog — https://www.firecrawl.dev/blog/mastering-firecrawl-search-endpoint
- Firecrawl AI platforms use-case — https://www.firecrawl.dev/use-cases/ai-platforms
- Firecrawl GitHub — https://github.com/firecrawl/firecrawl
- Replika eesel review — https://www.eesel.ai/blog/replika-ai
- Replika 2025 review — https://www.eesel.ai/blog/replika-ai-review
- Replika 2026 long-term review — https://aicompanionguides.com/blog/replika-review/
- Replika onboarding teardown — https://theappfuel.com/examples/replika_onboarding
- Replika vs Nomi 2025 — https://nomi.ai/ai-today/replika-vs-nomi-2026-finding-enduring-ai-companionship/
- Character.ai platform analysis — https://opinly.ai/blog/cai
- Character.ai create page — https://character.ai/character/new
- Character creation 2025 guide (Summon Worlds) — https://www.summonworlds.com/the-ultimate-2025-guide-to-ai-character-creation/
- Nomi.ai 8-week review — https://companionguide.ai/news/nomi-ai-comprehensive-review-2025
- Nomi.ai memory review (Roborhythms) — https://www.roborhythms.com/nomi-ai-review/
- Nomi.ai late-to-party 2026 review — https://aicompanionguides.com/blog/nomi-ai-late-to-party-worth-it/
- Pi rise and fall (IEEE Spectrum) — https://spectrum.ieee.org/inflection-ai-pi
- Pi onboarding page — https://pi.ai/onboarding
- Pi 2024 review (Fahimai) — https://www.fahimai.com/pi-ai
- Claude Opus 4.7 pricing analysis (Finout) — https://www.finout.io/blog/claude-opus-4.7-pricing-the-real-cost-story-behind-the-unchanged-price-tag
- LLM API pricing 2026 — https://www.tldl.io/resources/llm-api-pricing-2026
- Morph LLM real cost of AI coding — https://www.morphllm.com/ai-coding-costs

### Gaps / BLOCKED

- **Hinge AI prompts product blog**: not directly retrieved this session. Recommend follow-up WebFetch on Hinge engineering blog for first-message-suggestion patterns before §4 implementation.
- **Perplexity deep research**: API quota exhausted (HTTP 401 insufficient_quota). Re-run after billing top-up if a sourced second pass is needed for §1 (companion teardowns).
- **Gemini deep-research result**: still processing at write time (research id `v1_ChdSWUh3YVpxSU5hejNuc0VQbnJQUi1BURIXUllId2FacUlOYXozbnNFUG5yUFItQVE`); poll later via `gemini-check-research` and merge into §1/§5 if it adds substantively beyond current sources.
- **Firecrawl base credit cost per /search call**: not stated explicitly in retrieved docs. Estimate of $0.005/call is conservative; verify against Firecrawl pricing page before committing budget table to spec.
- **Pydantic AI WebSearchTool latency SLA**: not published. Estimate 2-3s based on Anthropic web_search tool behavior; verify with a smoke test in the worktree before committing to "8s per turn" hard cap.
