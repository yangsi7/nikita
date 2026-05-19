# Architecture Validation Report

**Spec:** `specs/109-systemic-cleanup/spec.md`
**Validator:** sdd-architecture-validator
**Status:** PASS
**Timestamp:** 2026-02-25T14:00:00Z

## Summary

- CRITICAL: 0
- HIGH: 0
- MEDIUM: 3
- LOW: 3

## Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| 1 | MEDIUM | Module Organization | New `nikita/llm/retry.py` creates a new top-level package (`nikita/llm/`) that currently does not exist. The spec does not specify what `__init__.py` should export or whether this package may grow. | spec.md:198 | Add a note that `nikita/llm/__init__.py` should be created with `__all__` exporting the retry utility. Document whether `nikita/llm/` is intended as a general LLM utilities package or only for retry. A single-file utility could alternatively live at `nikita/utils/llm_retry.py` to avoid creating a new top-level package for one function. |
| 2 | MEDIUM | Separation of Concerns | The retry utility will be consumed by modules in two separate domains: `nikita/engine/` (scoring, chapters, engagement) and `nikita/conflicts/` (detector, resolution). The spec does not specify the interface contract -- should this be a decorator, a context manager, or a wrapper function? Different patterns have different testability and composability implications. | spec.md:62-86 | Specify the retry utility's public API shape. Recommended: a tenacity retry decorator factory (e.g., `llm_retry()`) that returns a configured `@retry` decorator, keeping call-site changes minimal (add one decorator to each `_call_*` method). |
| 3 | MEDIUM | Type Safety | The spec mentions configurable retry parameters (max retries, backoff base) but does not specify where configuration lives. Should these be in `nikita/config/settings.py` (Pydantic BaseSettings) or hardcoded in the retry utility? Currently no `llm_retry_*` settings exist in settings.py. | spec.md:81-82 | Add `llm_retry_max_attempts: int = Field(default=3)` and `llm_retry_base_wait: float = Field(default=1.0)` to `nikita/config/settings.py`. This follows the existing pattern where all tunables are centralized in Pydantic BaseSettings. |
| 4 | LOW | Factual Accuracy | Spec states MessageHandler.__init__ takes "13 params (5 required, 8 optional)" but actual count is 14 params (5 required, 9 optional -- `engagement_repository` is the missing one). | spec.md:97, `nikita/platforms/telegram/message_handler.py:79-94` | Update spec to say "14 params (5 required, 9 optional)". |
| 5 | LOW | Scope Completeness | `nikita/conflicts/__init__.py` contains a deprecated stub `is_conflict_temperature_enabled()` (line 77-89) marked "Will be deleted in Spec 109", but the spec does not mention removing it. 13 test files still reference this function. | `nikita/conflicts/__init__.py:77-89` | Either: (a) add removal of `is_conflict_temperature_enabled` to FR-001 scope and update the 13 test files, or (b) explicitly defer to a future spec and update the docstring. |
| 6 | LOW | Import Hygiene | After ConflictStore removal, `nikita/conflicts/__init__.py` lines 45, 106-107 export `ConflictStore` and `get_conflict_store` in `__all__`. The spec's AC-1.2 allows a "deprecation stub" in `__init__.py` but does not clarify what it should look like. | `nikita/conflicts/__init__.py:45, 106-107` | Clarify whether `__init__.py` should retain a runtime-error stub (`raise ImportError("Removed in Spec 109")`) or fully remove the symbols. Recommendation: full removal from `__all__` and the import line. |

## Proposed Structure

After implementation, the affected directory tree should look like:

```
nikita/
  llm/                          # NEW package
    __init__.py                  # exports: llm_retry (or chosen name)
    retry.py                     # tenacity retry utility for LLM calls
  conflicts/
    __init__.py                  # MODIFIED: remove ConflictStore exports
    models.py                    # UNCHANGED
    detector.py                  # MODIFIED: remove store import, add DB read
    generator.py                 # MODIFIED: remove store import, use ConflictDetails
    escalation.py                # MODIFIED: remove store import, use ConflictDetails
    resolution.py                # MODIFIED: remove store import, use ConflictDetails
    breakup.py                   # MODIFIED: remove store import, use ConflictDetails
    store.py                     # DELETED
    gottman.py                   # UNCHANGED
    migration.py                 # UNCHANGED
    persistence.py               # UNCHANGED
    temperature.py               # UNCHANGED
  engine/
    scoring/analyzer.py          # MODIFIED: add retry decorator
    chapters/judgment.py         # MODIFIED: add retry decorator
    engagement/detection.py      # MODIFIED: add retry decorator
  agents/voice/server_tools.py   # MODIFIED: remove ConflictStore comment
  api/routes/telegram.py         # MODIFIED: extract build_message_handler factory
  config/settings.py             # MODIFIED: add llm_retry_* settings (recommended)
```

## Module Dependency Graph

```
nikita/llm/retry.py (NEW)
    depends on: tenacity, nikita.config.settings
    consumed by: engine/scoring/analyzer.py
                 engine/chapters/judgment.py
                 engine/engagement/detection.py
                 conflicts/detector.py
                 conflicts/resolution.py

nikita/conflicts/ (MODIFIED)
    store.py DELETED
    generator.py ──depends on──> models.py (ConflictDetails.from_jsonb)
    detector.py  ──depends on──> models.py (ConflictDetails.from_jsonb)
    escalation.py ──depends on──> models.py (ConflictDetails)
    resolution.py ──depends on──> models.py (ConflictDetails)
    breakup.py ──depends on──> models.py (ConflictDetails)
    (All five modules: store.py import REMOVED, no new circular deps)

nikita/api/routes/telegram.py (MODIFIED)
    build_message_handler() factory function
        consumed by: get_message_handler() (FastAPI Depends)
                     _handle_message_with_fresh_session() (background task)
    No new external dependencies introduced.
```

## Separation of Concerns Analysis

| Layer | Responsibility | Spec Impact | Violations |
|-------|---------------|-------------|------------|
| Data Access | ConflictDetails.from_jsonb/to_jsonb reads from User.conflict_details JSONB | FR-001 migrates 5 modules from in-memory store to this pattern | None -- clean migration to existing DB abstraction |
| Business Logic | Conflict detection, escalation, resolution, breakup scoring | Unchanged -- only storage mechanism swapped | None |
| Cross-Cutting (retry) | LLM call reliability | FR-002 adds tenacity retry as a decorator/wrapper | Clean -- retry is a cross-cutting concern properly isolated in `nikita/llm/retry.py` |
| DI / Wiring | MessageHandler construction | FR-003 extracts factory function | Clean -- DRY improvement, no logic changes |
| Configuration | Settings for retry params | Not yet specified in spec | MEDIUM -- should be added to settings.py |

## Import Pattern Checklist

- [x] No circular dependencies introduced (llm/retry.py is a leaf module)
- [x] ConflictStore removal eliminates imports from 5 modules + __init__.py (6 total import sites)
- [x] New `nikita/llm/` package does not conflict with existing packages
- [x] DI factory in telegram.py is file-local (no new cross-module imports)
- [ ] `nikita/llm/__init__.py` not specified in spec -- needs to be created with proper `__all__`
- [x] tenacity is already in pyproject.toml dependencies (line 46)

## Security Architecture

- [x] No new authentication/authorization surfaces introduced
- [x] ConflictStore removal does not affect security boundaries (in-memory store had no auth)
- [x] Retry utility does not expose internal error details externally (logs only)
- [x] DI factory does not change request validation or signature verification
- [x] No secrets management changes
- [x] No new input parsing points that require sanitization

## Error Handling Architecture

- [x] FR-002 preserves existing fallback behavior after retry exhaustion (spec lines 83-84)
- [x] WARNING-level logging per retry attempt, ERROR-level on final failure (spec lines 85)
- [x] Max total delay is bounded: 1s + 2s + 4s = 7s per call site (spec line 174)
- [ ] No specification of whether retry attempts should be counted/reported to monitoring systems (e.g., Prometheus metrics, structured log fields for alerting)
- [x] Background task error handling in telegram.py preserved -- factory function does not change error flow

## Backward Compatibility

- [x] ConflictStore already has deprecation warning in __init__ (since prior commit)
- [x] All 11 test files will be rewritten (spec AC-1.9), net test count preserved
- [x] No public API changes (no REST endpoint changes)
- [x] DI factory is internal to telegram.py -- no external consumers
- [x] Retry is purely additive -- no existing behavior changed, only enhanced

## Recommendations

1. **(MEDIUM)** Specify the `nikita/llm/retry.py` public API in the spec. Recommended pattern:

   ```python
   # nikita/llm/retry.py
   from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
   from nikita.config.settings import get_settings

   def is_transient_error(error: Exception) -> bool:
       """Check if error is transient (rate limit, timeout, 5xx)."""
       ...

   def llm_retry():
       """Return configured tenacity retry decorator for LLM calls."""
       settings = get_settings()
       return retry(
           stop=stop_after_attempt(settings.llm_retry_max_attempts),
           wait=wait_exponential(multiplier=settings.llm_retry_base_wait, max=10),
           retry=retry_if_exception(is_transient_error),
           before_sleep=_log_retry,
           after=_log_final_failure,
       )
   ```

2. **(MEDIUM)** Add retry configuration to `nikita/config/settings.py`:
   ```python
   llm_retry_max_attempts: int = Field(default=3, description="Max LLM retry attempts")
   llm_retry_base_wait: float = Field(default=1.0, description="Base wait seconds for exponential backoff")
   ```

3. **(MEDIUM)** Define what exceptions count as "transient" in the spec. The spec says "rate limit, timeout, 5xx" but does not specify the exception types from `pydantic_ai` / `anthropic` SDK. The implementer needs to know which exception classes to catch (e.g., `anthropic.RateLimitError`, `anthropic.APITimeoutError`, `anthropic.InternalServerError`).

4. **(LOW)** Correct MessageHandler param count from 13 to 14 in spec.md line 97.

5. **(LOW)** Decide on `is_conflict_temperature_enabled()` removal. Since 13 test files reference it and it was already marked for Spec 109 removal, include it in FR-001 scope to avoid carrying the technical debt forward.

6. **(LOW)** Clarify `__init__.py` stub strategy for ConflictStore -- recommend full removal since the deprecation warning has been active and no external consumers exist.
