# Plan: Spec 109 — Systemic Cleanup

**Spec**: `specs/109-systemic-cleanup/spec.md`
**Implementation order**: US-1 (ConflictStore) → US-2 (LLM Retry) → US-3 (DI Dedup)
**Rationale**: US-1 touches `conflicts/detector.py` and `conflicts/resolution.py` which are also US-2 targets. Complete store removal first so US-2 applies retry to the already-cleaned modules.

---

## Dependency Graph

```
T1.1 (delete store, clean __init__)
 ├→ T1.2 (generator.py)
 ├→ T1.3 (detector.py)
 ├→ T1.4 (escalation.py)
 ├→ T1.5 (resolution.py)
 ├→ T1.6 (breakup.py)
 └→ T1.7 (server_tools.py cleanup)
      └→ T1.8 (rewrite conflict test fixtures) ← blocks on all T1.2-T1.7
          └→ T1.9 (remove temperature flag patches) ← blocks on T1.1

T2.1 (create retry utility + settings)
 └→ T2.2 (retry utility tests)
     ├→ T2.3 (apply to scoring analyzer)
     ├→ T2.4 (apply to boss judgment)
     ├→ T2.5 (apply to engagement detection)
     └→ T2.6 (apply to conflict detector + resolution) ← blocks on T1.3, T1.5

T3.1 (extract DI factory)
 └→ T3.2 (factory tests)
```

---

## US-1: Remove ConflictStore Dead Code

### T1.1: Delete store.py and clean __init__.py

**ID**: T1.1
**Estimated**: 1 hour
**Dependencies**: None
**Files**:
- DELETE: `nikita/conflicts/store.py` (416 lines)
- MODIFY: `nikita/conflicts/__init__.py`

**Implementation**:
1. Delete `nikita/conflicts/store.py`
2. In `__init__.py`: remove `from nikita.conflicts.store import ConflictStore, get_conflict_store` (line 45)
3. Remove `is_conflict_temperature_enabled()` function (lines 77-89)
4. Remove from `__all__`: `"ConflictStore"`, `"get_conflict_store"`, `"is_conflict_temperature_enabled"` (lines 106-107, 134)
5. Update module docstring to remove ConflictStore from usage example (lines 17-18)

**Acceptance Criteria**:
- AC-1: `nikita/conflicts/store.py` does not exist
- AC-2: `rg "ConflictStore|get_conflict_store|is_conflict_temperature_enabled" nikita/conflicts/__init__.py` → 0 results
- AC-3: `python -c "from nikita.conflicts import TriggerDetector, ConflictGenerator"` succeeds (no import errors)

---

### T1.2: Migrate generator.py from store to DB

**ID**: T1.2
**Estimated**: 2 hours
**Dependencies**: T1.1
**Files**: `nikita/conflicts/generator.py`

**Implementation**:
1. Remove `from nikita.conflicts.store import ConflictStore` import
2. Constructor: remove `store: ConflictStore` parameter
3. Replace all `self._store.store_conflict(user_id, ...)` calls with `ConflictDetails(...).to_jsonb()` written to user model
4. Replace all `self._store.get_active_conflict(user_id)` with `ConflictDetails.from_jsonb(user.conflict_details)`
5. Add `user` parameter where needed (currently only has `user_id`)

**Pattern** (applied to all T1.2-T1.6):
```python
# BEFORE
conflict = self._store.get_active_conflict(user_id)

# AFTER
details = ConflictDetails.from_jsonb(user.conflict_details)
```

**Acceptance Criteria**:
- AC-1: `rg "ConflictStore|_store" nikita/conflicts/generator.py` → 0 results
- AC-2: All generator methods use `ConflictDetails.from_jsonb()` / `to_jsonb()`

---

### T1.3: Migrate detector.py from store to DB

**ID**: T1.3
**Estimated**: 2 hours
**Dependencies**: T1.1
**Files**: `nikita/conflicts/detector.py`

**Implementation**:
1. Remove `ConflictStore` import (line 16)
2. Remove `store` constructor parameter
3. Replace `self._store.get_user_triggers(user_id)` with loading from DB
4. Replace `self._store.store_trigger(user_id, ...)` with writing to DB
5. Ensure `_detect_with_llm()` (line 444) still works — this method is also a US-2 target

**Acceptance Criteria**:
- AC-1: `rg "ConflictStore|_store" nikita/conflicts/detector.py` → 0 results
- AC-2: Trigger detection reads/writes via `ConflictDetails.from_jsonb()`

---

### T1.4: Migrate escalation.py from store to DB

**ID**: T1.4
**Estimated**: 2 hours
**Dependencies**: T1.1
**Files**: `nikita/conflicts/escalation.py`

**Implementation**:
1. Remove `ConflictStore` import (line 19)
2. Remove `store` constructor parameter
3. Replace `self._store.get_active_conflict(user_id)` → `ConflictDetails.from_jsonb(user.conflict_details)`
4. Replace `self._store.update_escalation(user_id, ...)` → update user.conflict_details JSONB

**Acceptance Criteria**:
- AC-1: `rg "ConflictStore|_store" nikita/conflicts/escalation.py` → 0 results
- AC-2: Escalation reads/writes via `ConflictDetails.from_jsonb()` / `to_jsonb()`

---

### T1.5: Migrate resolution.py from store to DB

**ID**: T1.5
**Estimated**: 2 hours
**Dependencies**: T1.1
**Files**: `nikita/conflicts/resolution.py`

**Implementation**:
1. Remove `ConflictStore` import (line 22)
2. Remove `store` constructor parameter
3. Replace `self._store.get_active_conflict(user_id)` → `ConflictDetails.from_jsonb(user.conflict_details)`
4. Replace `self._store.resolve_conflict(user_id, ...)` → clear/update conflict_details JSONB
5. Ensure `_evaluate_with_llm()` (line 401) still works — also a US-2 target

**Acceptance Criteria**:
- AC-1: `rg "ConflictStore|_store" nikita/conflicts/resolution.py` → 0 results
- AC-2: Resolution evaluation reads/writes via `ConflictDetails.from_jsonb()` / `to_jsonb()`

---

### T1.6: Migrate breakup.py from store to DB

**ID**: T1.6
**Estimated**: 2 hours
**Dependencies**: T1.1
**Files**: `nikita/conflicts/breakup.py`

**Implementation**:
1. Remove `ConflictStore` import (line 19)
2. Remove `store` constructor parameter
3. Replace all store reads: `self._store.get_active_conflict(user_id)` → `ConflictDetails.from_jsonb(user.conflict_details)`
4. Replace all store writes: escalation tracking, breakup risk updates → update JSONB

**Acceptance Criteria**:
- AC-1: `rg "ConflictStore|_store" nikita/conflicts/breakup.py` → 0 results
- AC-2: Breakup risk assessment reads/writes via `ConflictDetails.from_jsonb()` / `to_jsonb()`

---

### T1.7: Clean server_tools.py imports/comments

**ID**: T1.7
**Estimated**: 30 min
**Dependencies**: T1.1
**Files**: `nikita/agents/voice/server_tools.py`

**Implementation**:
1. Remove ConflictStore import (if any)
2. Clean comment at line 794 referencing ConflictStore
3. Verify line 795 already reads from `user.conflict_details` — no logic change needed

**Acceptance Criteria**:
- AC-1: `rg "ConflictStore" nikita/agents/voice/server_tools.py` → 0 results
- AC-2: Existing voice conflict lookup behavior unchanged

---

### T1.8: Rewrite conflict test fixtures

**ID**: T1.8
**Estimated**: 4 hours
**Dependencies**: T1.2, T1.3, T1.4, T1.5, T1.6, T1.7
**Files**: 11 test files in `tests/conflicts/`

**Implementation**:
1. Replace all `ConflictStore()` instantiations with `MagicMock` user objects
2. Replace `store.store_conflict(user_id, data)` with `user.conflict_details = ConflictDetails(...).to_jsonb()`
3. Replace `store.get_active_conflict(user_id)` assertions with `ConflictDetails.from_jsonb(user.conflict_details)` checks
4. Update constructor calls in tests (remove `store=` parameter)
5. Delete `tests/conflicts/test_feature_flag.py` (tests the deprecated flag stub)
6. Run `pytest tests/conflicts/ -v` — all must pass
7. Verify net test count is non-negative

**Fixture pattern**:
```python
@pytest.fixture
def user_with_conflict():
    user = MagicMock()
    user.conflict_details = ConflictDetails(
        temperature=0.7, zone="heated",
        positive_count=3, negative_count=5,
    ).to_jsonb()
    return user
```

**Acceptance Criteria**:
- AC-1: `pytest tests/conflicts/ -v` → all pass
- AC-2: `rg "ConflictStore" tests/conflicts/` → 0 results
- AC-3: Net test count in `tests/conflicts/` is >= pre-change count minus test_feature_flag.py tests

---

### T1.9: Remove is_conflict_temperature_enabled patches

**ID**: T1.9
**Estimated**: 2 hours
**Dependencies**: T1.1
**Files**: ~11 test files with ~94 patches

**Implementation**:
1. `rg "is_conflict_temperature_enabled" tests/ -l` to find all files
2. For each file: remove `@patch("nikita.conflicts.is_conflict_temperature_enabled", ...)` decorators
3. Remove the corresponding `mock_flag` parameters from test function signatures
4. Remove any `mock_flag.return_value = True/False` lines
5. If a test was testing dual-path behavior (flag True vs False), keep only the True path test
6. Run full test suite to verify

**Key files** (from validator findings):
- `tests/platforms/telegram/handlers/test_scoring_orchestrator.py` (11 patches)
- `tests/platforms/telegram/handlers/test_handler_chain_integration.py` (4 patches)
- `tests/engine/scoring/test_service_temperature.py` (7 patches)
- `tests/integration/test_all_flags.py` (2 patches)
- `tests/integration/test_flag_group_c.py` (10 patches)
- `tests/test_combined_flags_adversarial.py` (8 patches)
- Additional files in `tests/conflicts/` (covered by T1.8)

**Acceptance Criteria**:
- AC-1: `rg "is_conflict_temperature_enabled" tests/` → 0 results
- AC-2: `pytest tests/ -x -q` → all pass

---

## US-2: LLM Retry with Exponential Backoff

### T2.1: Create retry utility and config settings

**ID**: T2.1
**Estimated**: 2 hours
**Dependencies**: None (can start in parallel with US-1)
**Files**:
- CREATE: `nikita/llm/__init__.py`
- CREATE: `nikita/llm/retry.py`
- MODIFY: `nikita/config/settings.py`

**Implementation**:

1. Create `nikita/llm/__init__.py`:
```python
from nikita.llm.retry import llm_retry
__all__ = ["llm_retry"]
```

2. Create `nikita/llm/retry.py` with async decorator factory:
```python
import asyncio
import logging
from functools import wraps
from typing import TypeVar, Callable, Any

import anthropic
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)

from nikita.config.settings import get_settings

logger = logging.getLogger(__name__)

# Transient errors worth retrying
RETRYABLE_EXCEPTIONS = (
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
)

def llm_retry(func):
    """Async decorator: retry LLM calls on transient errors with exponential backoff.

    Uses tenacity with sanitized logging. Falls through to caller's
    existing fallback on final failure.
    """
    settings = get_settings()

    @retry(
        stop=stop_after_attempt(settings.llm_retry_max_attempts),
        wait=wait_exponential(multiplier=settings.llm_retry_base_wait, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=_log_retry_attempt,
        reraise=True,
    )
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.wait_for(
            func(*args, **kwargs),
            timeout=60.0,
        )

    return wrapper


def _log_retry_attempt(retry_state):
    """Custom before_sleep callback with sanitized logging."""
    exc = retry_state.outcome.exception()
    logger.warning(
        "LLM retry attempt %d/%d: %s (waiting %.1fs)",
        retry_state.attempt_number,
        retry_state.retry_object.stop.max_attempt_number,
        exc.__class__.__name__,
        retry_state.next_action.sleep,
    )
```

3. Add to `nikita/config/settings.py`:
```python
llm_retry_max_attempts: int = Field(default=3, description="Max LLM retry attempts")
llm_retry_base_wait: float = Field(default=1.0, description="Base wait for exponential backoff (seconds)")
```

**Acceptance Criteria**:
- AC-1: `from nikita.llm import llm_retry` succeeds
- AC-2: Settings have `llm_retry_max_attempts` and `llm_retry_base_wait` with defaults
- AC-3: `RETRYABLE_EXCEPTIONS` contains exactly: RateLimitError, InternalServerError, ReadTimeout, ConnectTimeout

---

### T2.2: Write retry utility unit tests

**ID**: T2.2
**Estimated**: 3 hours
**Dependencies**: T2.1
**Files**: CREATE `tests/llm/test_retry.py`

**Test cases**:
1. `test_retries_on_rate_limit_error` — mock Agent.run raises RateLimitError twice then succeeds → 3 calls total
2. `test_retries_on_internal_server_error` — same for InternalServerError
3. `test_retries_on_read_timeout` — same for httpx.ReadTimeout
4. `test_no_retry_on_authentication_error` — AuthenticationError → immediate raise, 1 call
5. `test_no_retry_on_bad_request_error` — BadRequestError → immediate raise, 1 call
6. `test_no_retry_on_validation_error` — pydantic.ValidationError → immediate raise
7. `test_exhausted_retries_raises` — all 3 attempts fail → final exception raised
8. `test_retry_logging_warning` — caplog captures WARNING with attempt number and error class
9. `test_final_failure_logging_error` — caplog captures ERROR after exhaustion
10. `test_backoff_uses_settings` — verify settings.llm_retry_base_wait is respected

**Mock strategy**: Use `tenacity.wait_none()` patched via `@retry.retry_with()` or monkeypatch to avoid real sleeps.

**Acceptance Criteria**:
- AC-1: All 10 test cases pass
- AC-2: `pytest tests/llm/test_retry.py -v` → 10 passed, 0 failed
- AC-3: Tests complete in <5s (no real sleep/backoff)

---

### T2.3: Apply retry to scoring analyzer

**ID**: T2.3
**Estimated**: 1 hour
**Dependencies**: T2.2
**Files**: `nikita/engine/scoring/analyzer.py`

**Implementation**:
1. Import `from nikita.llm import llm_retry`
2. Apply `@llm_retry` decorator to `_call_llm_raw()` method (line 195)
3. Keep existing `try/except` as final fallback — the retry exhaustion will re-raise, caught by outer try/except which returns `None` → `_neutral_analysis()`
4. Update error log message to indicate "after retries"

**Acceptance Criteria**:
- AC-1: `_call_llm_raw` has `@llm_retry` decorator
- AC-2: Existing fallback to `_neutral_analysis()` still works after retry exhaustion
- AC-3: `pytest tests/engine/scoring/ -v` → all pass

---

### T2.4: Apply retry to boss judgment

**ID**: T2.4
**Estimated**: 1 hour
**Dependencies**: T2.2
**Files**: `nikita/engine/chapters/judgment.py`

**Implementation**:
1. Import `from nikita.llm import llm_retry`
2. Apply `@llm_retry` to `_call_llm()` (line 160) and `_call_multi_phase_llm()` (line 300)
3. Note: these methods create Agent inline inside the try block — may need to extract the `agent.run()` call into a separate `@llm_retry`-decorated async function
4. Keep existing FAIL fallbacks

**Acceptance Criteria**:
- AC-1: Both `_call_llm` and `_call_multi_phase_llm` use retry
- AC-2: Existing FAIL fallback preserved on retry exhaustion
- AC-3: `pytest tests/engine/chapters/ -v` → all pass

---

### T2.5: Apply retry to engagement detection

**ID**: T2.5
**Estimated**: 1 hour
**Dependencies**: T2.2
**Files**: `nikita/engine/engagement/detection.py`

**Implementation**:
1. Import `from nikita.llm import llm_retry`
2. Apply `@llm_retry` to `_call_neediness_llm()` (line 508) and `_call_distraction_llm()` (line 543)
3. Keep existing `Decimal("0.3")` fallback on retry exhaustion

**Acceptance Criteria**:
- AC-1: Both LLM methods have `@llm_retry` decorator
- AC-2: Existing Decimal("0.3") fallback preserved
- AC-3: `pytest tests/engine/engagement/ -v` → all pass

---

### T2.6: Apply retry to conflict detector + resolution

**ID**: T2.6
**Estimated**: 1.5 hours
**Dependencies**: T2.2, T1.3, T1.5 (conflict modules already migrated from store)
**Files**: `nikita/conflicts/detector.py`, `nikita/conflicts/resolution.py`

**Implementation**:
1. In `detector.py`: apply `@llm_retry` to `_detect_with_llm()` (line 444). Add `logger.error()` on final failure (currently silently returns `[]`).
2. In `resolution.py`: apply `@llm_retry` to `_evaluate_with_llm()` (line 401). Add `logger.error()` on final failure (currently silently falls back to rules).

**Acceptance Criteria**:
- AC-1: Both LLM methods have `@llm_retry` decorator
- AC-2: Final failure logged at ERROR level (was silent before)
- AC-3: `pytest tests/conflicts/ -v` → all pass

---

## US-3: DI Deduplication

### T3.1: Extract DI factory and wire both paths

**ID**: T3.1
**Estimated**: 2 hours
**Dependencies**: None (independent of US-1 and US-2)
**Files**: `nikita/api/routes/telegram.py`

**Implementation**:

1. Create `build_message_handler()` factory function:
```python
async def build_message_handler(
    session: AsyncSession,
    bot: TelegramBot,
) -> MessageHandler:
    """Construct MessageHandler with all dependencies.

    Single source of truth — used by both FastAPI DI and background tasks.
    """
    user_repo = UserRepository(session)
    conversation_repo = ConversationRepository(session)
    profile_repo = ProfileRepository(session)
    backstory_repo = BackstoryRepository(session)
    metrics_repo = UserMetricsRepository(session)

    rate_limiter = RateLimiter(cache=get_shared_cache())
    response_delivery = ResponseDelivery(bot=bot)
    text_agent_handler = TextAgentMessageHandler()

    return MessageHandler(
        user_repository=user_repo,
        conversation_repository=conversation_repo,
        text_agent_handler=text_agent_handler,
        response_delivery=response_delivery,
        bot=bot,
        rate_limiter=rate_limiter,
        profile_repository=profile_repo,
        backstory_repository=backstory_repo,
        metrics_repository=metrics_repo,
    )
```

2. Update `get_message_handler()` (line 208) to use factory:
```python
async def get_message_handler(session: SessionDep, bot: BotDep) -> MessageHandler:
    return await build_message_handler(session, bot)
```
Note: FastAPI DI injects `session` and `bot` — the factory just receives them.

3. Update `_handle_message_with_fresh_session()` (line 437) to use factory:
```python
async with session_maker() as session:
    try:
        handler = await build_message_handler(session, bot_instance)
        await handler.handle(message)
        await session.commit()
```

4. Keep the error handling wrapper in `_handle_message_with_fresh_session()` unchanged.

**Acceptance Criteria**:
- AC-1: `build_message_handler()` exists and constructs MessageHandler with all params
- AC-2: `get_message_handler()` calls `build_message_handler()`
- AC-3: `_handle_message_with_fresh_session()` calls `build_message_handler()`
- AC-4: `rg "UserRepository\(session\)" nikita/api/routes/telegram.py` → only inside `build_message_handler` (1 occurrence)

---

### T3.2: Write DI factory tests

**ID**: T3.2
**Estimated**: 1.5 hours
**Dependencies**: T3.1
**Files**: CREATE `tests/api/test_di_factory.py`

**Test cases**:
1. `test_build_message_handler_returns_handler` — factory returns MessageHandler instance
2. `test_build_message_handler_all_repos_initialized` — verify user_repo, conv_repo, profile_repo, backstory_repo, metrics_repo are not None
3. `test_build_message_handler_services_initialized` — verify rate_limiter, response_delivery, text_agent_handler are not None
4. `test_build_message_handler_bot_passed` — verify handler.bot is the bot argument
5. `test_get_message_handler_uses_factory` — mock build_message_handler, verify get_message_handler calls it

**Acceptance Criteria**:
- AC-1: `pytest tests/api/test_di_factory.py -v` → 5 passed
- AC-2: Tests use `AsyncMock(spec=AsyncSession)` and `MagicMock(spec=Bot)`

---

## Implementation Sequence

```
Day 1: T1.1 + T2.1 (parallel — store deletion + retry utility)
Day 1: T2.2 (retry tests, blocks on T2.1)
Day 2: T1.2-T1.7 (parallel — all 6 module migrations)
Day 2: T3.1 + T3.2 (parallel with T1 — DI factory)
Day 3: T1.8 + T1.9 (test rewrites, blocks on T1.2-T1.7)
Day 3: T2.3-T2.6 (apply retry to 7 call sites)
Day 4: Full test suite regression + cleanup
```

**Total estimated**: 26.5 hours across ~4 days

---

## Verification Checklist (Post-Implementation)

```bash
# FR-001: ConflictStore fully removed
rg "ConflictStore|get_conflict_store" nikita/ --type py           # 0 results
rg "is_conflict_temperature_enabled" nikita/ tests/ --type py     # 0 results
ls nikita/conflicts/store.py                                       # not found

# FR-002: LLM retry on all 7 sites
rg "llm_retry" nikita/ --type py                                   # 7+ results
rg "llm_retry_max_attempts" nikita/config/settings.py              # 1 result

# FR-003: DI factory
rg "build_message_handler" nikita/api/routes/telegram.py           # 3 results (def + 2 calls)

# Full regression
pytest tests/ -x -q                                                # all pass, net positive count
```
