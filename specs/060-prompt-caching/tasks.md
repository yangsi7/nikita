# Tasks: Spec 060 — Prompt Caching & Context Engineering

**Generated**: 2026-02-17
**Source**: `specs/060-prompt-caching/plan.md`
**Total**: 10 tasks (4 stories)

---

## US-1: Enable Prompt Cache

### T1.1: Write cache wiring tests [TDD-RED]
**File**: `tests/agents/text/test_prompt_caching.py` (NEW)
**AC**: AC-1.1, AC-1.3, AC-1.4, AC-1.5
**Status**: [ ]
**Tests**:
- `test_model_settings_passed_to_agent_run` — patch `nikita_agent.run`, assert `model_settings` kwarg present
- `test_model_settings_has_cache_instructions_true` — assert `anthropic_cache_instructions is True`
- `test_graceful_fallback_no_cache_fields` — mock Usage with empty details, no crash
- `test_cache_settings_constant_defined` — verify `CACHE_SETTINGS` module-level constant exists
**Depends**: none

### T1.2: Implement cache flag wiring [TDD-GREEN]
**File**: `nikita/agents/text/agent.py`
**AC**: AC-1.1, AC-1.3, AC-1.5
**Status**: [ ]
**Changes**:
- Import `AnthropicModelSettings` from `pydantic_ai.models.anthropic`
- Define `CACHE_SETTINGS = AnthropicModelSettings(anthropic_cache_instructions=True)` as module constant
- Add `model_settings=CACHE_SETTINGS` to `nikita_agent.run()` call at line ~506
**Depends**: T1.1

### T1.3: Verify all T1 tests pass [TDD-VERIFY]
**Status**: [ ]
**Command**: `pytest tests/agents/text/test_prompt_caching.py -v`
**Depends**: T1.2

---

## US-2: Token Budget Accuracy

### T2.1: Write token budget tests [TDD-RED]
**File**: `tests/pipeline/stages/test_token_budget.py` (NEW)
**AC**: AC-2.1, AC-2.4
**Status**: [ ]
**Tests**:
- `test_template_header_updated` — read `system_prompt.j2`, assert "~5,400" in header
- `test_rendered_template_within_budget` — render with mock data, verify `TEXT_TOKEN_MIN <= len/4 <= TEXT_TOKEN_MAX`
**Depends**: none

### T2.2: Update template header + review constants [TDD-GREEN]
**File**: `nikita/pipeline/templates/system_prompt.j2`, `nikita/pipeline/stages/prompt_builder.py`
**AC**: AC-2.1, AC-2.2
**Status**: [ ]
**Changes**:
- `system_prompt.j2:2`: Update "~4,800 tokens" → "~5,400 tokens (text) / ~4,400 tokens (voice)"
- Review TEXT_TOKEN_MIN=5500 / TEXT_TOKEN_MAX=6500 (expected: still appropriate)
**Depends**: T2.1

### T2.3: Add per-section token logging [TDD-GREEN]
**File**: `nikita/pipeline/stages/prompt_builder.py`
**AC**: AC-2.3
**Status**: [ ]
**Changes**:
- In `_generate_prompt()`, log per-section token counts via structured logger
- Format: `[TOKEN-BUDGET] section=%s approx_tokens=%d`
**Depends**: T2.2

### T2.4: Verify all T2 tests pass [TDD-VERIFY]
**Status**: [ ]
**Command**: `pytest tests/pipeline/stages/test_token_budget.py -v`
**Depends**: T2.3

---

## US-3: Cache Telemetry

### T3.1: Write telemetry tests [TDD-RED]
**File**: `tests/agents/text/test_cache_telemetry.py` (NEW)
**AC**: AC-3.1, AC-3.2, AC-3.3
**Status**: [ ]
**Tests**:
- `test_cache_telemetry_extracts_from_usage` — mock RunResult with RunUsage cache fields, verify log
- `test_cache_telemetry_log_format` — assert `[CACHE] read=N write=N input=N cache_ratio=N%` format
- `test_cache_telemetry_handles_zero_values` — mock RunUsage with zero cache fields, verify `read=0 write=0`
**Depends**: none

### T3.2: Implement telemetry logging [TDD-GREEN]
**File**: `nikita/agents/text/agent.py`
**AC**: AC-3.1, AC-3.2, AC-3.3
**Status**: [ ]
**Changes**:
- Add `_log_cache_telemetry(result)` function after successful `agent.run()` return
- Extract `cache_read_tokens`, `cache_write_tokens` from `result.usage()` (first-class RunUsage fields)
- Log in specified format; wrap in try/except for graceful degradation
**Depends**: T3.1, T1.2 (needs result object context)

### T3.3: Verify all T3 tests pass [TDD-VERIFY]
**Status**: [ ]
**Command**: `pytest tests/agents/text/test_cache_telemetry.py -v`
**Depends**: T3.2

---

## US-4: Integration Verification

### T4.1: Full regression test suite [VERIFY]
**Status**: [ ]
**Command**: `pytest tests/ -x -q`
**AC**: SC-4 (all 3,933+ tests pass)
**Depends**: T1.3, T2.4, T3.3

---

## Dependency Graph

```
T1.1 ──→ T1.2 ──→ T1.3 ─────────────┐
T2.1 ──→ T2.2 ──→ T2.3 ──→ T2.4 ────┤──→ T4.1
T3.1 ──→ T3.2 ──→ T3.3 ─────────────┘
         ↑
         T1.2 (dependency)
```

**Parallel tracks**: T1.x and T2.x are independent. T3.x depends on T1.2 for the result object context.

## Summary

| Story | Tasks | Tests | Source Files |
|-------|-------|-------|-------------|
| US-1 | 3 | 4 | agent.py |
| US-2 | 4 | 2+1 | prompt_builder.py, system_prompt.j2 |
| US-3 | 3 | 3 | agent.py |
| US-4 | 1 | all | regression |
| **Total** | **11** | **10 new** | **3 modified, 3 new test files** |
