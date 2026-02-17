# Implementation Plan: Spec 060 — Prompt Caching & Context Engineering

**Spec**: `specs/060-prompt-caching/spec.md`
**Created**: 2026-02-17
**Estimated Effort**: 3-4 hours (TDD)

## Architecture Overview

```
CURRENT FLOW:
  agent.py:506 → nikita_agent.run(user_message, deps, message_history, usage_limits)
                  ↓
  Anthropic API ← system instructions sent as fresh input tokens every call

AFTER SPEC 060:
  agent.py:506 → nikita_agent.run(..., model_settings=CACHE_SETTINGS)
                  ↓
  Anthropic API ← cache_control: {type: "ephemeral"} on system block
                  ↓ (2nd+ message within 5-min TTL)
                  RunUsage.cache_read_tokens > 0 → 90% cost reduction
                  ↓
  agent.py:514 → log_cache_telemetry(result) → structured log
```

## Files to Modify

| File | Change | US |
|------|--------|----|
| `nikita/agents/text/agent.py` | Add `model_settings` kwarg + telemetry logging | US-1, US-3 |
| `nikita/pipeline/stages/prompt_builder.py` | Review TOKEN constants, add per-section logging | US-2 |
| `nikita/pipeline/templates/system_prompt.j2` | Update header token count comment | US-2 |
| `tests/agents/text/test_prompt_caching.py` | NEW: cache wiring tests | US-1 |
| `tests/agents/text/test_cache_telemetry.py` | NEW: telemetry extraction tests | US-3 |
| `tests/pipeline/stages/test_token_budget.py` | NEW: budget validation test | US-2 |

## Implementation Tasks

### Task 1: Cache Flag Wiring (US-1) — TDD

**Files**: `tests/agents/text/test_prompt_caching.py`, `nikita/agents/text/agent.py`

**Tests First**:
1. `test_model_settings_passed_to_agent_run` — patch `nikita_agent.run`, verify `model_settings` kwarg contains `AnthropicModelSettings(anthropic_cache_instructions=True)`
2. `test_model_settings_includes_cache_instructions_true` — assert the specific flag value
3. `test_voice_transcript_agent_gets_cache_settings` — verify `extract_agent.run()` in `transcript.py` also gets cache settings (optional enhancement)
4. `test_graceful_fallback_no_cache_fields` — mock RunResult with no cache fields in usage, verify no crash

**Implementation**:
- At `agent.py:506`, add `model_settings` parameter:
  ```python
  from pydantic_ai.models.anthropic import AnthropicModelSettings

  CACHE_SETTINGS = AnthropicModelSettings(anthropic_cache_instructions=True)
  ```
- Pass to `nikita_agent.run(..., model_settings=CACHE_SETTINGS)`
- Define `CACHE_SETTINGS` as module-level constant near existing `DEFAULT_USAGE_LIMITS`

**Acceptance Criteria**: AC-1.1, AC-1.3, AC-1.4, AC-1.5

### Task 2: Token Budget Correction (US-2) — TDD

**Files**: `tests/pipeline/stages/test_token_budget.py`, `nikita/pipeline/stages/prompt_builder.py`, `nikita/pipeline/templates/system_prompt.j2`

**Tests First**:
1. `test_template_header_updated` — read `system_prompt.j2`, assert header contains "~5,400" and "~4,400"
2. `test_rendered_template_within_budget` — render template with representative mock data, verify token count falls within TEXT_TOKEN_MIN/MAX using `len(rendered) / 4` approximation
3. `test_per_section_token_logging` — mock logger, render prompt, verify structured log entries for per-section counts

**Implementation**:
- Update `system_prompt.j2:2`: `"~4,800 tokens"` → `"~5,400 tokens (text) / ~4,400 tokens (voice)"`
- Review TEXT_TOKEN_MIN=5500 / TEXT_TOKEN_MAX=6500 — likely still appropriate (5,400 base + enrichment)
- Add per-section token count logging in `_generate_prompt()` method:
  ```python
  logger.info(
      "[TOKEN-BUDGET] section=%s tokens=%d",
      section_name, approx_token_count
  )
  ```

**Acceptance Criteria**: AC-2.1, AC-2.2, AC-2.3, AC-2.4

### Task 3: Cache Telemetry Logging (US-3) — TDD

**Files**: `tests/agents/text/test_cache_telemetry.py`, `nikita/agents/text/agent.py`

**Tests First**:
1. `test_cache_telemetry_extracted_from_result` — mock RunResult with `usage()` returning RunUsage with cache fields, verify log contains `[CACHE] read=5400 write=0`
2. `test_cache_telemetry_log_format` — verify exact log format: `[CACHE] read={N} write={N} input={N} cache_ratio={pct}%`
3. `test_cache_telemetry_handles_zero_values` — mock RunUsage with zero cache fields, verify graceful handling (logs `read=0 write=0 cache_ratio=0%`)

**Implementation**:
- After `result = await asyncio.wait_for(...)` at `agent.py:513`, add telemetry extraction:
  ```python
  def _log_cache_telemetry(result) -> None:
      """Extract and log Anthropic prompt cache metrics from RunResult."""
      try:
          usage = result.usage()
          cache_read = getattr(usage, "cache_read_tokens", 0)
          cache_write = getattr(usage, "cache_write_tokens", 0)
          total_input = getattr(usage, "input_tokens", 0)
          ratio = (cache_read / total_input * 100) if total_input > 0 else 0
          logger.info(
              f"[CACHE] read={cache_read} write={cache_write} "
              f"input={total_input} cache_ratio={ratio:.1f}%"
          )
      except Exception as e:
          logger.debug(f"[CACHE] telemetry extraction failed: {e}")
  ```
- Call `_log_cache_telemetry(result)` after the successful LLM response at line ~515

**Acceptance Criteria**: AC-3.1, AC-3.2, AC-3.3

### Task 4: Integration Verification

**Run full test suite**:
```bash
pytest tests/ -x -q
```
- Verify all 3,933+ existing tests pass (SC-4)
- Verify 10 new tests pass (7 unit + 3 integration)
- No import errors from `pydantic_ai.models.anthropic`

## Dependency Order

```
Task 1 (cache flag) ─── independent ───┐
Task 2 (token budget) ─ independent ───┤
Task 3 (telemetry) ──── depends T1 ────┘──→ Task 4 (integration verify)
```

Tasks 1 and 2 are independent (can be parallelized). Task 3 depends on Task 1's `result` object being available. Task 4 runs after all implementation is complete.

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| `AnthropicModelSettings` import path changed | Verified: `pydantic_ai.models.anthropic` in v1.25.0 |
| `result.usage()` API different in v1.25 | Verified: returns `RunUsage` with `.cache_read_tokens`, `.cache_write_tokens` as first-class fields |
| Token budget too tight after enrichment | Keep existing 5500-6500 range; enrichment adds ~200-800 tokens above 5,400 base |
| Cache field names differ from Anthropic raw API | Pydantic AI normalizes to `cache_read_tokens`/`cache_write_tokens` (NOT `cache_read_input_tokens`/`cache_creation_input_tokens`) |

## Research Notes

- Pydantic AI v1.25.0 `AnthropicModelSettings` supports: `anthropic_cache_instructions`, `anthropic_cache_tool_definitions`, `anthropic_cache_messages`
- `result.usage()` returns `pydantic_ai.usage.RunUsage` with first-class fields: `cache_read_tokens: int`, `cache_write_tokens: int`, `input_tokens: int`, `output_tokens: int`
- Anthropic raw API uses `cache_read_input_tokens`/`cache_creation_input_tokens` but Pydantic AI normalizes these to `cache_read_tokens`/`cache_write_tokens`
- Anthropic cache TTL: 5 min default, refreshed on each hit
- Minimum cacheable: 1,024 tokens (Sonnet 4.5/Opus 4.6) — our ~5,400 exceeds 5x
