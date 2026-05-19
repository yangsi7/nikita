# API Validation Report

**Spec:** `specs/109-systemic-cleanup/spec.md`
**Status:** PASS
**Timestamp:** 2026-02-25T12:00:00Z

## Summary

- CRITICAL: 0
- HIGH: 0
- MEDIUM: 4
- LOW: 3

## Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | LLM Retry | No specification of which pydantic_ai exception types map to "transient" vs "permanent" errors | spec.md:83 | Specify exact exception classes for retry: `httpx.ReadTimeout`, `httpx.ConnectTimeout`, `anthropic.RateLimitError`, `anthropic.InternalServerError`, `anthropic.APIConnectionError`. pydantic_ai wraps these; document whether to catch at the httpx/anthropic level or the pydantic_ai `ModelRetry`/`UnexpectedModelBehavior` level. |
| MEDIUM | LLM Retry | No timeout specification per individual LLM call (before retry starts) | spec.md:81-86 | Add per-call timeout (e.g., 30s or 60s) using `httpx` client timeout or `asyncio.wait_for`. Without this, a hanging connection could block for the default httpx timeout (undefined) before retry even triggers. |
| MEDIUM | LLM Retry | Retry utility interface/signature not defined | spec.md:62-86 | Define the proposed `nikita/llm/retry.py` interface: e.g., `@llm_retry` decorator vs `async def with_llm_retry(fn, *args)` wrapper. Specify whether it is a decorator, context manager, or higher-order function. The 7 call sites have different signatures (some are methods, some are module-level functions, some create the Agent inline inside the try block) which constrains the design. |
| MEDIUM | DI Factory | Spec claims "13 params" for MessageHandler.__init__ but actual signature has 14 params (5 required + 9 optional) | spec.md:97 | Update spec to reflect 14 params. Both existing DI paths currently pass 9 of 14 (missing: `scoring_service`, `onboarding_handler`, `boss_judgment`, `boss_state_machine`, `engagement_repository`). The factory must decide whether to pass all 14 or preserve the current subset of 9. |
| LOW | LLM Retry | No specification of whether retry utility should be sync-compatible or async-only | spec.md:62-86 | All 7 call sites are `async`. Document that the utility is async-only (uses `tenacity` with `AsyncRetrying` or `@retry` with `asyncio.sleep` via `wait` parameter). |
| LOW | DI Factory | No specification of factory function return type annotation | spec.md:88-103 | Define that `build_message_handler(session: AsyncSession, bot: TelegramBot) -> MessageHandler`. Include type hints in the spec for implementation clarity. |
| LOW | ConflictStore | Spec references `is_conflict_temperature_enabled()` stub at `__init__.py:77-89` but does not explicitly call out its removal | spec.md:45-60 | This deprecated stub (always returns True, no production callers) should be included in the deletion scope of FR-001. Add to AC-1.2 or create AC-1.10 for explicit cleanup of this stub. |

## API Inventory

This spec introduces NO new API routes. All changes are internal refactoring:

| Change Type | Scope | Impact on API Surface |
|-------------|-------|----------------------|
| FR-001: ConflictStore removal | Internal modules | None -- no public endpoints change |
| FR-002: LLM retry utility | Internal call wrappers | None -- no endpoint signatures change |
| FR-003: DI factory extraction | `telegram.py` internals | None -- webhook endpoint behavior unchanged |

### Existing Routes Affected (Indirectly)

| Method | Endpoint | Impact | Notes |
|--------|----------|--------|-------|
| POST | /api/v1/telegram/webhook | FR-003 DI refactor | Background task handler `_handle_message_with_fresh_session()` uses factory |
| POST | /api/v1/voice/server-tool | FR-001 ConflictStore removal | `server_tools.py:794` already reads from JSONB; comment cleanup only |
| N/A | Internal LLM calls | FR-002 retry addition | Scoring, boss judgment, engagement detection, conflict detection/resolution |

## Server Actions

Not applicable -- this is a Python/FastAPI backend, not Next.js. No server actions.

## Request/Response Schemas

No schema changes. All existing request/response contracts remain identical:

- `POST /telegram/webhook`: `TelegramUpdate` -> `WebhookResponse` (unchanged)
- `POST /voice/server-tool`: `ServerToolRequest` -> `ServerToolResponse` (unchanged)
- LLM retry is internal; no external schema impact
- ConflictStore removal replaces internal data access pattern; no API response changes

## Error Code Inventory

No new error codes. Existing error handling preserved:

| Code | Status | Description | Change |
|------|--------|-------------|--------|
| N/A | N/A | LLM failure fallbacks | FR-002 adds retry BEFORE existing fallbacks; fallback behavior unchanged |
| 403 | Forbidden | Invalid webhook signature | Unchanged |
| 500 | Internal Server Error | Unhandled exception | Unchanged (global handler) |

## Detailed Analysis

### FR-001: ConflictStore Removal -- Backend Impact

**Verified call sites** (via `rg "ConflictStore" nikita/`):
- `nikita/conflicts/store.py` -- 416 lines, to be DELETED
- `nikita/conflicts/__init__.py:17,45,106-107` -- imports and `__all__` entries
- `nikita/conflicts/generator.py:25,72,102,108` -- import + constructor param
- `nikita/conflicts/detector.py:17,111,117` -- import + constructor param
- `nikita/conflicts/escalation.py:19,48,55,61` -- import + constructor param
- `nikita/conflicts/resolution.py:23,80,108,115` -- import + constructor param
- `nikita/conflicts/breakup.py:19,120,126` -- import + constructor param
- `nikita/agents/voice/server_tools.py:794` -- comment only (code already reads JSONB)

All 6 production modules confirmed. The voice server_tools.py at line 794 is already using the JSONB pattern -- only the comment references ConflictStore.

**Positive pattern**: The spec correctly identifies that `ConflictDetails.from_jsonb()` at `nikita/conflicts/models.py:399-406` is the replacement mechanism, and it already exists and is battle-tested via Spec 057.

**Test migration scope**: 11 test files confirmed via `rg "ConflictStore" tests/`. This matches the spec's claim exactly.

### FR-002: LLM Retry Utility -- Backend Impact

**Verified all 7 call sites** against the spec's table:

1. `nikita/engine/scoring/analyzer.py:204-209` -- `_call_llm_raw`: catches all exceptions, returns `None`. Confirmed.
2. `nikita/engine/chapters/judgment.py:127-151` -- `_call_llm` (inline Agent creation): catches all exceptions, returns FAIL. Confirmed.
3. `nikita/engine/chapters/judgment.py:269-295` -- `_call_multi_phase_llm`: catches all exceptions, returns FAIL with confidence=0.0. Confirmed.
4. `nikita/engine/engagement/detection.py:500-519` -- `_call_neediness_llm`: catches all exceptions, returns Decimal("0.3"). Confirmed.
5. `nikita/engine/engagement/detection.py:534-553` -- `_call_distraction_llm`: catches all exceptions, returns Decimal("0.3"). Confirmed.
6. `nikita/conflicts/detector.py:437-472` -- `_detect_with_llm`: catches all exceptions, returns []. Confirmed.
7. `nikita/conflicts/resolution.py:390-411` -- `_evaluate_with_llm`: catches all exceptions, falls back to `_evaluate_with_rules()`. Confirmed.

**Design consideration**: Call sites 2 and 3 in `judgment.py` create the `Agent` instance INSIDE the try block (lines 129-133 and 270-274). The retry utility must wrap the `agent.run()` call specifically, not the Agent construction. The spec should note this pattern distinction.

**Positive pattern**: The spec preserves all existing fallback behavior after retry exhaustion. This is the correct design -- retry is additive, not replacement.

### FR-003: DI Factory Extraction -- Backend Impact

**Verified both DI construction sites**:

1. `nikita/api/routes/telegram.py:208-251` -- `get_message_handler()`: Passes 9 of 14 params.
2. `nikita/api/routes/telegram.py:437-477` -- `_handle_message_with_fresh_session()`: Passes same 9 of 14 params.

**Parameter analysis** of `MessageHandler.__init__` (`nikita/platforms/telegram/message_handler.py:79-94`):

| Param | Required | get_message_handler | _handle_message_fresh | Notes |
|-------|----------|--------------------|-----------------------|-------|
| user_repository | Yes | Yes | Yes | |
| conversation_repository | Yes | Yes | Yes | |
| text_agent_handler | Yes | Yes | Yes | |
| response_delivery | Yes | Yes | Yes | |
| bot | Yes | Yes | Yes | |
| rate_limiter | Optional | Yes | Yes | |
| scoring_service | Optional | No (None) | No (None) | Defaults to None |
| profile_repository | Optional | Yes | Yes | |
| backstory_repository | Optional | Yes | Yes | |
| onboarding_handler | Optional | No (None) | No (None) | Intentionally None (avoid circular dep) |
| boss_judgment | Optional | No (None) | No (None) | Defaults to None |
| boss_state_machine | Optional | No (None) | No (None) | Defaults to None |
| engagement_repository | Optional | No (None) | No (None) | Defaults to None |
| metrics_repository | Optional | Yes | Yes | |

Both sites pass identical 9 params. 5 optional params are intentionally left as None. The factory should preserve this pattern. The spec's claim of "13 params" at line 97 should be corrected to "14 params" (or "9 active params + 5 defaulted to None").

**Positive pattern**: Both sites are already identical -- the factory extraction is a clean DRY refactor with zero behavior change risk.

## Recommendations

1. **MEDIUM (FR-002)**: Define the exact pydantic_ai/anthropic/httpx exception types that constitute "transient" errors. Suggested classification:
   - **Retry**: `anthropic.RateLimitError` (429), `anthropic.InternalServerError` (500/502/503), `anthropic.APIConnectionError`, `httpx.ReadTimeout`, `httpx.ConnectTimeout`
   - **Do NOT retry**: `anthropic.AuthenticationError` (401), `anthropic.BadRequestError` (400), `anthropic.PermissionDeniedError` (403), `pydantic.ValidationError`

2. **MEDIUM (FR-002)**: Add per-call timeout to prevent retry from hanging on slow connections. Suggest `asyncio.wait_for(agent.run(prompt), timeout=60)` or httpx client-level timeout.

3. **MEDIUM (FR-002)**: Define the retry utility interface explicitly. Given that call sites 2-3 (judgment.py) create Agent instances inline inside try blocks, suggest a decorator pattern:
   ```python
   @llm_retry(max_retries=3, backoff_base=1.0)
   async def _call_llm_raw(self, prompt: str) -> ResponseAnalysis | None:
       result = await self.agent.run(prompt)
       return result.output
   ```
   This requires the decorator to know which exceptions to NOT catch (the original fallback return must happen outside the retry scope).

4. **MEDIUM (FR-003)**: Correct the param count from "13" to "14" in the spec. Document that the factory passes 9 active params and leaves 5 as None defaults.

5. **LOW**: Include removal of `is_conflict_temperature_enabled()` stub at `nikita/conflicts/__init__.py:77-89` in the ConflictStore cleanup scope.

6. **LOW**: Add type signature for the proposed factory: `async def build_message_handler(session: AsyncSession, bot: TelegramBot) -> MessageHandler`.

7. **LOW**: Document that the retry utility must be async-only (all 7 call sites are async coroutines).
