# Spec 109: Systemic Cleanup — ConflictStore Removal, LLM Retry, DI Deduplication

**Status**: Draft
**Priority**: High
**Domain**: Infrastructure
**Effort**: Medium (3-5 days)
**Dependencies**: None (all referenced systems are deployed and stable)

---

## Problem Statement

Three systemic issues were identified during E2E simulation testing and the Spec 108 voice optimization work. Each independently degrades reliability, maintainability, or correctness:

1. **ConflictStore (dead code)**: A 416-line in-memory dictionary store (`nikita/conflicts/store.py`) that is non-functional on Cloud Run serverless — state is lost on every cold start. The `conflict_details` JSONB column (Spec 057) replaced this pattern, but 6 production modules still import and call ConflictStore methods that always return `None`.

2. **LLM silent failures**: 7 LLM call sites across 5 modules have no retry logic. When Claude API returns a transient error (rate limit, timeout, 5xx), the call silently returns a neutral/zero-delta result. No alerting, no retry, no circuit breaker. The `tenacity>=9.0.0` library is already in dependencies but unused for LLM calls.

3. **DI duplication**: `_handle_message_with_fresh_session()` in `telegram.py` manually constructs 5 repositories and 3 services, duplicating the exact same dependency graph built by `get_message_handler()` 250 lines above. Any new dependency must be added in two places.

---

## Personas

- **Operator** (deployment/monitoring): Needs LLM failures to be visible and recoverable, not silently swallowed.
- **Developer** (maintenance): Needs dead code removed and DI consolidated to a single source of truth.
- **Player** (end user): Indirectly benefits from more reliable scoring, conflict detection, and boss encounters.

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| ConflictStore references in production code | 6 modules, ~50 call sites | 0 |
| LLM call sites with retry | 0 / 7 | 7 / 7 |
| DI construction points for MessageHandler | 2 (duplicated) | 1 (shared factory) |
| Dead code lines removed | 0 | ~500 (store.py + unused imports) |
| Test count change | 5,347+ | Net positive (rewritten, not deleted) |

---

## Functional Requirements

### FR-001: Remove ConflictStore (In-Memory Dead Code)

**What**: Delete `nikita/conflicts/store.py` and remove all ConflictStore usage from 6 production modules. Replace `store.get_active_conflict(user_id)` calls with `ConflictDetails.from_jsonb(user.conflict_details)` which reads from the DB.

**Why**: The in-memory store is non-functional on serverless (state lost on cold start/scale-to-zero). All production conflict data already flows through the `conflict_details` JSONB column on the users table (Spec 057). The store is dead code that creates false expectations.

**Evidence**:
- `nikita/conflicts/store.py`: 416 lines, 14 methods, in-memory dicts
- Callers: `generator.py`, `detector.py`, `escalation.py`, `resolution.py`, `breakup.py`, `server_tools.py`
- Replacement exists: `ConflictDetails.from_jsonb()` at `nikita/conflicts/models.py:399-406`
- 11 test files reference ConflictStore fixtures

**Includes**: Delete the `is_conflict_temperature_enabled()` deprecated stub at `nikita/conflicts/__init__.py:77-89` (self-documents as "Will be deleted in Spec 109") and update ~14 test files that patch it.

**Constraints**:
- `ConflictDetails.from_jsonb()` / `to_jsonb()` must remain the sole conflict state mechanism. All callers MUST use `ConflictDetails.from_jsonb(user.conflict_details)` which returns safe zero-state defaults when the column is NULL. Direct dict access on raw JSONB is prohibited.
- All existing conflict behavior (detection, escalation, resolution, breakup) must pass existing tests after migration
- `server_tools.py:794-797` (voice agent): already reads from DB JSONB — only comment/import cleanup needed
- No DB migration required — no DDL changes, no data backfill, no new columns

### FR-002: Add LLM Retry with Exponential Backoff

**What**: Wrap all 7 LLM call sites with retry logic using `tenacity` (already in deps). Add structured logging on retry attempts and final failure. Preserve existing fallback behavior (neutral analysis, rules-based fallback) as the final fallback after retries are exhausted.

**Why**: Transient Claude API errors (rate limits, timeouts, 5xx) currently cause silent degradation — zero-delta scores, hardcoded FAIL judgments, and unlogged failures. A single retry would recover most transient errors. Three retries with exponential backoff would recover nearly all.

**Evidence** — 7 call sites, all without retry:

| File | Method | On Failure (Current) |
|------|--------|---------------------|
| `engine/scoring/analyzer.py:208` | `_call_llm_raw` | `None` → zero-delta, confidence=0.5 |
| `engine/chapters/judgment.py:160` | `_call_llm` | FAIL hardcoded |
| `engine/chapters/judgment.py:300` | `_call_multi_phase_llm` | FAIL, confidence=0.0 |
| `engine/engagement/detection.py:508` | `_call_neediness_llm` | `Decimal("0.3")` |
| `engine/engagement/detection.py:543` | `_call_distraction_llm` | `Decimal("0.3")` |
| `conflicts/detector.py:444` | `_detect_with_llm` | `[]`, no log |
| `conflicts/resolution.py:401` | `_evaluate_with_llm` | rules fallback, no log |

**Retry exception classification**:
- RETRY: `anthropic.RateLimitError`, `anthropic.InternalServerError`, `httpx.ReadTimeout`, `httpx.ConnectTimeout`
- NO RETRY: `anthropic.AuthenticationError`, `anthropic.BadRequestError`, `pydantic.ValidationError`

**Constraints**:
- Max 3 retries per call (configurable via `nikita/config/settings.py`: `llm_retry_max_attempts`, `llm_retry_base_wait`)
- Exponential backoff: 1s, 2s, 4s (configurable base)
- Per-call timeout: 60s via `asyncio.wait_for()` to prevent hanging connections
- Retry only on classified transient errors (see above) — not on 4xx or validation errors
- After all retries exhausted, fall back to EXISTING fallback behavior (do not change current fallback logic)
- Log each retry attempt at WARNING level with attempt number, error class name, and wait time. Sanitize logs: never log full exception repr (may contain user conversation text or API keys). Log only `error.__class__.__name__`, HTTP status code, and `retry-after` header.
- Final failure logged at ERROR level with sanitized error details
- `tenacity>=9.0.0` is already in `pyproject.toml`
- Retry utility API: async decorator factory in `nikita/llm/retry.py` with `nikita/llm/__init__.py` exporting public API

### FR-003: Deduplicate Background Task DI

**What**: Extract a shared factory function `build_message_handler(session, bot)` that constructs `MessageHandler` with all repository and service dependencies. Use this factory in both the FastAPI DI path (`get_message_handler()`) and the background task path (`_handle_message_with_fresh_session()`).

**Why**: `telegram.py` constructs the same dependency graph in two places (~65 lines apart). Adding a new dependency requires updating both. This is a DRY violation that has already caused subtle bugs (background tasks missing dependencies that the request path has).

**Evidence**:
- `telegram.py:208-254` (`get_message_handler`): constructs 5 repos + 3 services
- `telegram.py:457-465` (`_handle_message_with_fresh_session`): manually duplicates 5 repos + 3 services
- `message_handler.py:79-94`: `MessageHandler.__init__` takes 14 params (5 required, 9 optional)

**Constraints**:
- Factory must accept `AsyncSession` and optional `Bot` as inputs
- Factory must construct ALL dependencies that `MessageHandler.__init__` expects
- Both call sites must use the same factory — no remaining manual construction
- Existing behavior must be identical (same repos, same services, same defaults)

---

## User Stories

### US-1: Remove ConflictStore Dead Code (P1 — Must Have)

**As a** developer maintaining the conflict system,
**I want** all in-memory ConflictStore code removed and replaced with DB-backed ConflictDetails,
**So that** there is no dead code creating false expectations about conflict state persistence.

**Acceptance Criteria**:

- **AC-1.1**: `nikita/conflicts/store.py` is deleted
- **AC-1.2**: `ConflictStore` and `is_conflict_temperature_enabled` are fully removed from production code and `__all__` exports (`rg "ConflictStore|is_conflict_temperature_enabled" nikita/ --type py` → 0 results)
- **AC-1.3**: `nikita/conflicts/generator.py` reads/writes conflict state via `ConflictDetails.from_jsonb()` / `to_jsonb()` using the user's `conflict_details` JSONB column
- **AC-1.4**: `nikita/conflicts/detector.py` reads conflict state from DB instead of store
- **AC-1.5**: `nikita/conflicts/escalation.py` reads/writes conflict state from/to DB
- **AC-1.6**: `nikita/conflicts/resolution.py` reads/writes conflict state from/to DB
- **AC-1.7**: `nikita/conflicts/breakup.py` reads/writes conflict state from/to DB
- **AC-1.8**: `nikita/agents/voice/server_tools.py` reads active conflict from `user.conflict_details` JSONB (already implemented — comment/import cleanup only)
- **AC-1.9**: All existing conflict-related tests pass (rewritten to use DB fixtures instead of ConflictStore mocks). Net test count must not decrease.
- **AC-1.10**: All `is_conflict_temperature_enabled` test patches removed (~94 patches across 11 files including `test_scoring_orchestrator.py`, `test_handler_chain_integration.py`, `test_feature_flag.py`, `test_service_temperature.py`, `test_all_flags.py`, `test_flag_group_c.py`, `test_combined_flags_adversarial.py`)

### US-2: Add LLM Retry with Exponential Backoff (P1 — Must Have)

**As an** operator monitoring Nikita's AI systems,
**I want** LLM calls to retry on transient errors with structured logging,
**So that** temporary API issues don't silently degrade scoring, boss encounters, or conflict detection.

**Acceptance Criteria**:

- **AC-2.1**: A shared retry utility exists (using `tenacity`) that retries on transient errors (rate limit, timeout, 5xx) with exponential backoff (1s, 2s, 4s)
- **AC-2.2**: `engine/scoring/analyzer.py:_call_llm_raw` uses the retry utility
- **AC-2.3**: `engine/chapters/judgment.py:_call_llm` and `_call_multi_phase_llm` use the retry utility
- **AC-2.4**: `engine/engagement/detection.py:_call_neediness_llm` and `_call_distraction_llm` use the retry utility
- **AC-2.5**: `conflicts/detector.py:_detect_with_llm` uses the retry utility
- **AC-2.6**: `conflicts/resolution.py:_evaluate_with_llm` uses the retry utility
- **AC-2.7**: Each retry attempt is logged at WARNING level with attempt number, error type, and wait time
- **AC-2.8**: Final failure (all retries exhausted) is logged at ERROR level and falls back to existing fallback behavior (unchanged)
- **AC-2.9**: Retry utility has dedicated unit tests covering: retry on transient errors (RateLimitError, InternalServerError, ReadTimeout), no-retry on permanent errors (AuthenticationError, BadRequestError), backoff timing verification, and log output verification via `caplog`

### US-3: Deduplicate Background Task DI (P2 — Should Have)

**As a** developer adding new dependencies to the message handler,
**I want** a single factory function that constructs `MessageHandler` with all dependencies,
**So that** I only need to update one place when adding or changing dependencies.

**Acceptance Criteria**:

- **AC-3.1**: A shared factory function `build_message_handler(session, bot)` exists and constructs `MessageHandler` with all 14 parameters
- **AC-3.2**: `get_message_handler()` (FastAPI DI) uses the shared factory
- **AC-3.3**: `_handle_message_with_fresh_session()` (background task) uses the shared factory
- **AC-3.4**: No manual repository/service construction remains outside the factory function
- **AC-3.5**: DI factory has a dedicated test verifying all 14 `MessageHandler.__init__` params are constructed

---

## Testing Strategy

### Test Pyramid (70-20-10)

- **Unit tests (70%)**: Retry utility logic, ConflictDetails.from_jsonb() NULL handling, DI factory param coverage
- **Integration tests (20%)**: Conflict modules with DB fixtures, LLM call sites with mocked retry, MessageHandler construction via factory
- **E2E tests (10%)**: Existing test suite regression — no new E2E required (backend-only refactoring)

### Coverage Targets

| Area | Target | Method |
|------|--------|--------|
| `nikita/llm/retry.py` | 95%+ | Unit tests for all retry/no-retry paths |
| `nikita/conflicts/` (post-removal) | Maintain existing | Rewrite fixtures, keep test count |
| `nikita/api/routes/telegram.py` (DI factory) | New coverage | Factory test + integration test |

### FR-001: ConflictStore Fixture Migration Pattern

Replace `ConflictStore` mock fixtures with `MagicMock` User objects with `conflict_details` populated via `ConflictDetails.to_jsonb()`:

```python
# BEFORE (ConflictStore mock)
store = ConflictStore()
store.store_conflict(user_id, conflict_data)

# AFTER (DB fixture via ConflictDetails)
user = MagicMock()
user.conflict_details = ConflictDetails(
    temperature=0.7, zone="heated",
    positive_count=3, negative_count=5
).to_jsonb()
```

**Files requiring fixture rewrite** (expanded scope from validator findings):
- 11 test files in `tests/conflicts/` (ConflictStore mocks)
- `tests/platforms/telegram/handlers/test_scoring_orchestrator.py` (11 `is_conflict_temperature_enabled` patches)
- `tests/platforms/telegram/handlers/test_handler_chain_integration.py` (3 patches)
- `tests/conflicts/test_feature_flag.py` (flag stub tests — delete entirely)

### FR-002: Tenacity Mock Strategy

Test retry logic without real sleeps or API calls:

```python
# Use tenacity.wait_none() to skip real delays
from unittest.mock import patch, AsyncMock
import tenacity

# Mock Agent.run() to raise transient errors then succeed
mock_agent = AsyncMock()
mock_agent.run.side_effect = [
    anthropic.RateLimitError(...),  # attempt 1: retry
    anthropic.RateLimitError(...),  # attempt 2: retry
    successful_result,               # attempt 3: succeed
]

# Verify retry count and log output via caplog
with caplog.at_level(logging.WARNING):
    result = await retry_decorated_fn(mock_agent, prompt)
assert mock_agent.run.call_count == 3
assert "attempt 2" in caplog.text
```

**Key patterns**:
- Patch `tenacity.wait_fixed` / `wait_exponential` with `wait_none()` in test setup
- Use `httpx.HTTPStatusError` with `response.status_code=429` for rate limit simulation
- Use `caplog` fixture for log assertion (WARNING for retries, ERROR for final failure)
- Test permanent errors (AuthenticationError) are NOT retried

### FR-003: DI Factory Tests

```python
async def test_build_message_handler_constructs_all_deps():
    """Verify factory creates MessageHandler with all 14 params."""
    session = AsyncMock(spec=AsyncSession)
    bot = MagicMock(spec=Bot)
    handler = await build_message_handler(session, bot)
    assert isinstance(handler, MessageHandler)
    assert handler.user_repo is not None
    assert handler.conv_repo is not None
    # ... verify all 14 params
```

---

## Out of Scope

- **Chapter sensitivity double-apply**: Deferred to separate spec (boundary detection modifier logic requires scoring engine redesign)
- **ConflictStore replacement with Redis/external store**: Not needed — JSONB column is sufficient for current scale
- **LLM model failover** (e.g., Claude → OpenAI fallback): Out of scope — retry is within the same provider
- **Pipeline-level retry** (retrying entire pipeline stages): Out of scope — this is call-site retry only
- **New conflict detection logic**: Only replacing storage mechanism, not changing detection/escalation/resolution behavior
- **LLM retry for non-critical paths**: `backstory_generator.py`, `facts.py`, `event_generator.py` — these have existing fallback behavior and are not in the critical scoring/conflict/boss pipeline. Deferred to a future spec.

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| ConflictStore removal breaks untested code paths | Conflict behavior regression | Rewrite all 11 test files to use DB fixtures; run full test suite |
| Retry causes cascading delays on sustained outage | Response latency spikes | Max 3 retries + exponential backoff caps at 4s; total max delay = 7s per call |
| DI factory doesn't match all MessageHandler params | Background tasks missing dependencies | Verify factory against `MessageHandler.__init__` signature; add integration test |
| tenacity retry masks real errors | Silent degradation continues | ERROR-level logging after final failure; existing fallback behavior preserved |

---

## Technical Context

### Existing Patterns

- **ConflictDetails JSONB**: `nikita/conflicts/models.py:399-406` — `from_jsonb(data)` / `to_jsonb()` already used by Spec 057 conflict system
- **tenacity in deps**: `pyproject.toml` lists `tenacity>=9.0.0` — used elsewhere but not for LLM calls
- **DI pattern**: `nikita/api/dependencies.py` + `nikita/api/routes/telegram.py` — FastAPI Depends() pattern
- **Pydantic AI agents**: All LLM calls use `Agent.run()` from `pydantic_ai` — retry wraps this call

### Files to Modify

**FR-001 (ConflictStore)**:
- DELETE: `nikita/conflicts/store.py`
- MODIFY: `nikita/conflicts/__init__.py` (remove ConflictStore, get_conflict_store, is_conflict_temperature_enabled from imports and `__all__`)
- MODIFY: `nikita/conflicts/generator.py`, `detector.py`, `escalation.py`, `resolution.py`, `breakup.py`
- MODIFY: `nikita/agents/voice/server_tools.py` (comment/import cleanup only — already reads from JSONB)
- REWRITE: 11 test files in `tests/conflicts/` (ConflictStore → DB fixtures)
- REWRITE: `tests/platforms/telegram/handlers/test_scoring_orchestrator.py` (11 `is_conflict_temperature_enabled` patches)
- REWRITE: `tests/platforms/telegram/handlers/test_handler_chain_integration.py` (3 patches)
- DELETE: `tests/conflicts/test_feature_flag.py` (flag stub tests — entire file is dead)

**FR-002 (LLM Retry)**:
- CREATE: `nikita/llm/__init__.py`, `nikita/llm/retry.py` (shared retry utility)
- MODIFY: `nikita/config/settings.py` (add `llm_retry_max_attempts`, `llm_retry_base_wait`)
- MODIFY: `nikita/engine/scoring/analyzer.py`, `nikita/engine/chapters/judgment.py`, `nikita/engine/engagement/detection.py`, `nikita/conflicts/detector.py`, `nikita/conflicts/resolution.py`
- CREATE: `tests/llm/test_retry.py` (retry utility unit tests)

**FR-003 (DI Dedup)**:
- MODIFY: `nikita/api/routes/telegram.py` (extract factory, use in both paths)
- CREATE: `tests/api/test_di_factory.py` (factory integration test)
