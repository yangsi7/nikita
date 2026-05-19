# Feature Specification: Prompt Caching & Context Engineering

**Spec ID**: 060-prompt-caching
**Status**: Draft
**Priority**: P1 (prerequisite for Wave A specs 055-058)
**Estimated Effort**: 3-4 hours

## Overview

### Problem Statement

Every message to Nikita sends the full system prompt (~5,400 tokens for text, ~4,400 for voice) as fresh input tokens. The persona instructions (~400 tok) and template static sections (Identity ~400 tok, Immersion Rules ~200 tok, Psychology ~400 tok) are identical across ALL messages for ALL users — roughly 1,400 tokens per message that could be cached. At scale, this wastes ~26% of input token costs on redundant content.

Additionally:
- The template header claims "~4,800 tokens pre-enrichment" but actual measured sum is ~5,400 (text) — stale documentation causes silent budget miscalculations
- No telemetry exists on cache effectiveness — we can't measure savings or debug prompt bloat

### Proposed Solution

1. **Pydantic AI Native Cache Flag**: Enable `anthropic_cache_instructions=True` in `AnthropicModelSettings` so the Anthropic API automatically caches system instructions across messages within the TTL window (~5 min). Subsequent messages from the same user within the window pay ~90% less for cached tokens.
2. **Token Budget Correction**: Update the template header and enforce accurate budget constants matching actual section sizes.
3. **Cache Hit Telemetry**: Log `cache_read_tokens` and `cache_write_tokens` from Pydantic AI `RunUsage` for cost attribution and monitoring.

### Success Criteria

- [ ] SC-1: System instructions cached via Anthropic prompt caching on 2nd+ message in conversation
- [ ] SC-2: Token budget constants match actual template output within 10% tolerance
- [ ] SC-3: Cache hit/miss telemetry logged per API call
- [ ] SC-4: No regression — all 3,933+ existing tests pass
- [ ] SC-5: Measured input token reduction of ≥15% for multi-message conversations

## Functional Requirements

### FR-001: Enable Anthropic Prompt Cache via Pydantic AI
**Priority**: P1
**Description**: Enable prompt caching using Pydantic AI's native `AnthropicModelSettings(anthropic_cache_instructions=True)`. This automatically marks system instructions with `cache_control: { type: "ephemeral" }` breakpoints — no manual prompt restructuring needed.

**Implementation Details**:
- Pydantic AI v1.25.0 (installed) supports `anthropic_cache_instructions` flag
- When enabled, Pydantic AI automatically adds `cache_control` markers to the last system message block
- All system instructions (persona + template) are cached as a unit
- Current model `claude-sonnet-4-5-20250929` has 1,024 token minimum threshold
- Combined system instructions (~5,400 tokens text) far exceed the 1,024 minimum
- Cache TTL: 5 minutes default (fits active conversation cadence)
- Max 4 breakpoints per request (1 used for instructions)

### FR-002: Token Budget Correction
**Priority**: P1
**Description**: Update stale token budget documentation and enforcement constants to match actual template output.

**Changes**:
- `system_prompt.j2` header: Update "~4,800 tokens" → "~5,400 tokens (text) / ~4,400 tokens (voice)"
- `prompt_builder.py:50-54`: Validate TEXT_TOKEN_MIN/MAX (5500/6500) are still appropriate given actual 5,400 baseline
- Add per-section token count logging during prompt generation for ongoing budget monitoring

### FR-003: Cache Telemetry
**Priority**: P2
**Description**: Extract cache effectiveness metrics from Anthropic API responses and log them for cost monitoring.

**Metrics** (from `pydantic_ai.usage.RunUsage` first-class fields):
- `cache_read_tokens` — tokens served from cache (0.1x base cost)
- `cache_write_tokens` — tokens written to cache (1.25x base cost, first message only)
- Log via structured logger alongside existing LLM-DEBUG logs

## User Stories

### US-1: Enable Prompt Cache
**As a** system operator **I want** system instructions to be cached by the Anthropic API **so that** input token costs decrease by ≥15% for active conversations.

**Acceptance Criteria**:
- [ ] AC-1.1: `AnthropicModelSettings(anthropic_cache_instructions=True)` is passed to `agent.run()` via `model_settings` parameter
- [ ] AC-1.2: Cache is active — 2nd message in conversation shows `RunUsage.cache_read_tokens > 0`
- [ ] AC-1.3: Combined system instructions (persona + template ≈ 5,400 tokens) exceed 1,024 token minimum for Sonnet
- [ ] AC-1.4: Fallback gracefully if cache is unavailable (treat as normal tokens — Pydantic AI handles this)
- [ ] AC-1.5: Works with both text and voice agent configurations

### US-2: Token Budget Accuracy
**As a** developer **I want** token budget constants to accurately reflect template output **so that** budget enforcement doesn't silently truncate content or allow bloat.

**Acceptance Criteria**:
- [ ] AC-2.1: `system_prompt.j2` header updated to "~5,400 tokens (text) / ~4,400 tokens (voice)"
- [ ] AC-2.2: TEXT_TOKEN_MIN/MAX constants reviewed and adjusted if needed
- [ ] AC-2.3: Per-section token counts logged during prompt generation (structured logging, not print)
- [ ] AC-2.4: Test validates that a fully-rendered template with mock data falls within budget constants

### US-3: Cache Telemetry
**As a** system operator **I want** cache hit/miss data logged per API call **so that** I can measure cost savings and detect cache degradation.

**Acceptance Criteria**:
- [ ] AC-3.1: After `agent.run()`, extract `RunUsage` from result and log `cache_read_tokens`, `cache_write_tokens`
- [ ] AC-3.2: Log format: `[CACHE] read={N} write={N} input={N} cache_ratio={pct}%`
- [ ] AC-3.3: Null/zero values handled gracefully when caching is disabled or first message

## Testing Strategy

### Test Pyramid (7 Unit / 3 Integration / 0 E2E)

| Layer | Count | Focus |
|-------|-------|-------|
| Unit | 7 | model_settings wiring, token budget validation, telemetry extraction, graceful fallback |
| Integration | 3 | Multi-message cache sequencing, prompt builder + template budget, telemetry logging output |
| E2E | 0 | No E2E — cache behavior is API-side; verified via integration telemetry logs |

### Test File Organization

```
tests/agents/text/test_prompt_caching.py     # US-1: cache flag wiring (4 unit tests)
tests/pipeline/stages/test_token_budget.py   # US-2: budget validation (2 unit, 1 integration)
tests/agents/text/test_cache_telemetry.py    # US-3: telemetry extraction (1 unit, 2 integration)
```

### Mocking Strategy

**Mock RunResult for cache telemetry (AC-1.2, AC-3.1)**:
```python
from unittest.mock import AsyncMock, MagicMock
from pydantic_ai.result import RunResult
from pydantic_ai.usage import RunUsage

# RunUsage has first-class cache fields (not in details dict)
mock_usage = RunUsage(
    requests=1,
    input_tokens=6200,
    output_tokens=150,
    cache_read_tokens=5400,
    cache_write_tokens=0,
)

# Mock RunResult
mock_result = MagicMock(spec=RunResult)
mock_result.usage.return_value = mock_usage
mock_result.output = "mocked response"
```

**Mock for agent.run() (AC-1.1)**:
```python
# Patch agent.run to capture model_settings kwarg
with patch.object(nikita_agent, "run", new_callable=AsyncMock) as mock_run:
    mock_run.return_value = mock_result
    # ... call handler ...
    call_kwargs = mock_run.call_args.kwargs
    assert "model_settings" in call_kwargs
    settings = call_kwargs["model_settings"]
    assert settings.anthropic_cache_instructions is True
```

**Token budget test fixture (AC-2.4)**:
```python
# Render template with representative mock data, count tokens via tiktoken/len approximation
from nikita.pipeline.stages.prompt_builder import TEXT_TOKEN_MIN, TEXT_TOKEN_MAX

def test_rendered_template_within_budget():
    rendered = render_system_prompt(mock_user_profile, mock_memories, mode="text")
    # Approximate token count: len(text) / 4 (conservative for English)
    approx_tokens = len(rendered) / 4
    assert TEXT_TOKEN_MIN <= approx_tokens <= TEXT_TOKEN_MAX
```

### Key Test Cases

| ID | AC | Test Description | Type |
|----|-----|-----------------|------|
| T1 | AC-1.1 | `model_settings` kwarg passed with `anthropic_cache_instructions=True` | Unit |
| T2 | AC-1.2 | Mock RunResult with `RunUsage.cache_read_tokens > 0` parsed correctly | Unit |
| T3 | AC-1.4 | Graceful fallback when usage has no cache fields | Unit |
| T4 | AC-1.5 | Both text and voice agents receive model_settings | Unit |
| T5 | AC-2.1 | Template header contains updated token counts | Unit |
| T6 | AC-2.4 | Rendered template falls within TEXT_TOKEN_MIN/MAX | Unit |
| T7 | AC-3.1 | Telemetry extracts cache_read/creation from Usage | Unit |
| T8 | AC-2.3 | Per-section token logging emits structured log entries | Integration |
| T9 | AC-3.2 | `[CACHE]` log line format matches spec | Integration |
| T10 | AC-3.3 | Zero/null cache values handled without error | Integration |

## Non-Functional Requirements

### NFR-001: Performance
- Adding `model_settings` parameter must add <1ms to agent.run() call setup
- No additional API calls — cache_control is metadata on existing messages

### NFR-002: Cost
- Target: ≥15% input token cost reduction for conversations with 3+ messages
- Cache creation cost (1.25x on first message) amortized over subsequent messages
- Cache read cost: 0.1x base price (90% savings)

### NFR-003: Backward Compatibility
- All existing tests must pass without modification (except prompt-specific unit tests)
- Prompt output for users must be functionally identical — same content, same behavior

## Constraints & Assumptions

- Anthropic prompt caching TTL is 5 minutes (as of Feb 2026); also supports 1-hour TTL via `'1h'` parameter
- Minimum cacheable content: 1,024 tokens for Sonnet 4.5 and Opus 4.6 (verified Feb 2026)
- Maximum 4 cache breakpoints per request
- Pydantic AI v1.25.0 supports `AnthropicModelSettings.anthropic_cache_instructions` natively
- Combined system instructions (~5,400 tokens) far exceed the 1,024 minimum — no threshold concern
- Current model: `claude-sonnet-4-5-20250929` configured in `nikita/config/settings.py:40`
- Cache pricing: write = 1.25x base (5-min TTL) or 2.0x (1-hour TTL); read = 0.1x base

## Out of Scope

- Manual prompt restructuring into blocks (Pydantic AI handles cache markers automatically)
- Voice prompt caching via ElevenLabs (different API, different caching model)
- Prompt compression or summarization (separate concern)
- Changes to persona.py or agent.py instruction decorators (P2/P3 already done)
- Template content changes (Section 1-11 content stays as-is)
- Database schema changes for telemetry (logging to structured logs, not DB columns)

## Dependencies

- **Upstream**: P2 (persona slim) ✅, P3 (chapter guard) ✅ — both complete
- **Downstream**: Specs 055-058 benefit from reduced token costs but don't depend on cache mechanically
- **External**: Anthropic API prompt caching (GA since 2024), Pydantic AI v1.25.0+ (installed)

## Research Findings (Resolved)

### Q-1: Pydantic AI Cache Support — RESOLVED ✅
Pydantic AI v1.25.0 natively supports Anthropic prompt caching via 4 mechanisms:
1. `anthropic_cache_instructions: bool` — auto-cache system instructions
2. `anthropic_cache_tool_definitions: bool` — auto-cache tool definitions
3. `anthropic_cache_messages: int` — cache N most recent conversation turns
4. Manual `CachePoint()` markers in message parts

For this spec, mechanism #1 (`anthropic_cache_instructions=True`) is sufficient. It adds `cache_control: { type: "ephemeral" }` to the last system message block automatically.

### Q-2: Token Threshold — RESOLVED ✅
Minimum cacheable content is 1,024 tokens for Sonnet 4.5 and Opus 4.6 (same threshold for both). Our combined system instructions (~5,400 tokens) are 5x above the minimum — no concern.
