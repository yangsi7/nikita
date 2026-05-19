# Tasks: Spec 109 — Systemic Cleanup

**Spec**: `specs/109-systemic-cleanup/spec.md`
**Plan**: `specs/109-systemic-cleanup/plan.md`
**Generated**: 2026-02-25
**Implementation Order**: US-1 → US-2 → US-3

---

## US-1: Remove ConflictStore Dead Code

### T1.1: Delete store.py and clean __init__.py

- **Status**: [ ] Not Started
- **Estimated**: 1 hour
- **Dependencies**: None
- **Files**:
  - DELETE: `nikita/conflicts/store.py` (416 lines)
  - MODIFY: `nikita/conflicts/__init__.py`

**Test Commit**: `test(109): verify ConflictStore removal from __init__ exports`
**Impl Commit**: `refactor(109): delete ConflictStore, remove deprecated flag stub`

**Acceptance Criteria**:
- [ ] AC-1: `nikita/conflicts/store.py` does not exist
- [ ] AC-2: `rg "ConflictStore|get_conflict_store|is_conflict_temperature_enabled" nikita/conflicts/__init__.py` → 0 results
- [ ] AC-3: `python -c "from nikita.conflicts import TriggerDetector, ConflictGenerator"` succeeds

---

### T1.2: Migrate generator.py from store to DB

- **Status**: [ ] Not Started
- **Estimated**: 2 hours
- **Dependencies**: T1.1
- **Files**: `nikita/conflicts/generator.py`

**Test Commit**: `test(109): add failing tests for generator DB migration`
**Impl Commit**: `refactor(109): migrate generator.py from ConflictStore to ConflictDetails JSONB`

**Acceptance Criteria**:
- [ ] AC-1: `rg "ConflictStore|_store" nikita/conflicts/generator.py` → 0 results
- [ ] AC-2: All generator methods use `ConflictDetails.from_jsonb()` / `to_jsonb()`

---

### T1.3: Migrate detector.py from store to DB

- **Status**: [ ] Not Started
- **Estimated**: 2 hours
- **Dependencies**: T1.1
- **Files**: `nikita/conflicts/detector.py`

**Test Commit**: `test(109): add failing tests for detector DB migration`
**Impl Commit**: `refactor(109): migrate detector.py from ConflictStore to ConflictDetails JSONB`

**Acceptance Criteria**:
- [ ] AC-1: `rg "ConflictStore|_store" nikita/conflicts/detector.py` → 0 results
- [ ] AC-2: Trigger detection reads/writes via `ConflictDetails.from_jsonb()`

---

### T1.4: Migrate escalation.py from store to DB

- **Status**: [ ] Not Started
- **Estimated**: 2 hours
- **Dependencies**: T1.1
- **Files**: `nikita/conflicts/escalation.py`

**Test Commit**: `test(109): add failing tests for escalation DB migration`
**Impl Commit**: `refactor(109): migrate escalation.py from ConflictStore to ConflictDetails JSONB`

**Acceptance Criteria**:
- [ ] AC-1: `rg "ConflictStore|_store" nikita/conflicts/escalation.py` → 0 results
- [ ] AC-2: Escalation reads/writes via `ConflictDetails.from_jsonb()` / `to_jsonb()`

---

### T1.5: Migrate resolution.py from store to DB

- **Status**: [ ] Not Started
- **Estimated**: 2 hours
- **Dependencies**: T1.1
- **Files**: `nikita/conflicts/resolution.py`

**Test Commit**: `test(109): add failing tests for resolution DB migration`
**Impl Commit**: `refactor(109): migrate resolution.py from ConflictStore to ConflictDetails JSONB`

**Acceptance Criteria**:
- [ ] AC-1: `rg "ConflictStore|_store" nikita/conflicts/resolution.py` → 0 results
- [ ] AC-2: Resolution evaluation reads/writes via `ConflictDetails.from_jsonb()` / `to_jsonb()`

---

### T1.6: Migrate breakup.py from store to DB

- **Status**: [ ] Not Started
- **Estimated**: 2 hours
- **Dependencies**: T1.1
- **Files**: `nikita/conflicts/breakup.py`

**Test Commit**: `test(109): add failing tests for breakup DB migration`
**Impl Commit**: `refactor(109): migrate breakup.py from ConflictStore to ConflictDetails JSONB`

**Acceptance Criteria**:
- [ ] AC-1: `rg "ConflictStore|_store" nikita/conflicts/breakup.py` → 0 results
- [ ] AC-2: Breakup risk assessment reads/writes via `ConflictDetails.from_jsonb()` / `to_jsonb()`

---

### T1.7: Clean server_tools.py imports/comments

- **Status**: [ ] Not Started
- **Estimated**: 30 min
- **Dependencies**: T1.1
- **Files**: `nikita/agents/voice/server_tools.py`

**Test Commit**: N/A (comment/import cleanup only — existing tests cover behavior)
**Impl Commit**: `refactor(109): clean ConflictStore references from server_tools.py`

**Acceptance Criteria**:
- [ ] AC-1: `rg "ConflictStore" nikita/agents/voice/server_tools.py` → 0 results
- [ ] AC-2: Existing voice conflict lookup behavior unchanged

---

### T1.8: Rewrite conflict test fixtures

- **Status**: [ ] Not Started
- **Estimated**: 4 hours
- **Dependencies**: T1.2, T1.3, T1.4, T1.5, T1.6, T1.7
- **Files**: 11 test files in `tests/conflicts/`

**Test Commit**: `test(109): rewrite conflict test fixtures from ConflictStore to DB`
**Impl Commit**: N/A (test-only task)

**Fixture Pattern**:
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
- [ ] AC-1: `pytest tests/conflicts/ -v` → all pass
- [ ] AC-2: `rg "ConflictStore" tests/conflicts/` → 0 results
- [ ] AC-3: Net test count in `tests/conflicts/` >= pre-change count minus `test_feature_flag.py` tests

---

### T1.9: Remove is_conflict_temperature_enabled patches

- **Status**: [ ] Not Started
- **Estimated**: 2 hours
- **Dependencies**: T1.1
- **Files**: ~11 test files with ~94 patches

**Test Commit**: `test(109): remove is_conflict_temperature_enabled patches across test suite`
**Impl Commit**: N/A (test-only task)

**Key Files**:
- `tests/platforms/telegram/handlers/test_scoring_orchestrator.py` (11 patches)
- `tests/platforms/telegram/handlers/test_handler_chain_integration.py` (4 patches)
- `tests/engine/scoring/test_service_temperature.py` (7 patches)
- `tests/integration/test_all_flags.py` (2 patches)
- `tests/integration/test_flag_group_c.py` (10 patches)
- `tests/test_combined_flags_adversarial.py` (8 patches)
- Additional files in `tests/conflicts/` (overlap with T1.8)

**Acceptance Criteria**:
- [ ] AC-1: `rg "is_conflict_temperature_enabled" tests/` → 0 results
- [ ] AC-2: `pytest tests/ -x -q` → all pass

---

## US-2: LLM Retry with Exponential Backoff

### T2.1: Create retry utility and config settings

- **Status**: [ ] Not Started
- **Estimated**: 2 hours
- **Dependencies**: None (can start in parallel with US-1)
- **Files**:
  - CREATE: `nikita/llm/__init__.py`
  - CREATE: `nikita/llm/retry.py`
  - MODIFY: `nikita/config/settings.py`

**Test Commit**: `test(109): add failing tests for LLM retry utility`
**Impl Commit**: `feat(109): create nikita/llm/retry.py with tenacity-based exponential backoff`

**Acceptance Criteria**:
- [ ] AC-1: `from nikita.llm import llm_retry` succeeds
- [ ] AC-2: Settings have `llm_retry_max_attempts` (default=3) and `llm_retry_base_wait` (default=1.0)
- [ ] AC-3: `RETRYABLE_EXCEPTIONS` contains: RateLimitError, InternalServerError, ReadTimeout, ConnectTimeout

---

### T2.2: Write retry utility unit tests

- **Status**: [ ] Not Started
- **Estimated**: 3 hours
- **Dependencies**: T2.1
- **Files**: CREATE `tests/llm/test_retry.py`

**Test Commit**: `test(109): add retry utility unit tests (10 cases)`
**Impl Commit**: N/A (test-only task)

**Test Cases**:
1. `test_retries_on_rate_limit_error` — RateLimitError twice then succeeds → 3 calls
2. `test_retries_on_internal_server_error` — InternalServerError → retry
3. `test_retries_on_read_timeout` — httpx.ReadTimeout → retry
4. `test_no_retry_on_authentication_error` — immediate raise, 1 call
5. `test_no_retry_on_bad_request_error` — immediate raise, 1 call
6. `test_no_retry_on_validation_error` — pydantic.ValidationError → immediate raise
7. `test_exhausted_retries_raises` — all 3 attempts fail → final exception raised
8. `test_retry_logging_warning` — caplog captures WARNING with attempt number
9. `test_final_failure_logging_error` — caplog captures ERROR after exhaustion
10. `test_backoff_uses_settings` — settings.llm_retry_base_wait is respected

**Mock Strategy**: `tenacity.wait_none()` to skip real delays.

**Acceptance Criteria**:
- [ ] AC-1: All 10 test cases pass
- [ ] AC-2: `pytest tests/llm/test_retry.py -v` → 10 passed, 0 failed
- [ ] AC-3: Tests complete in <5s (no real sleep/backoff)

---

### T2.3: Apply retry to scoring analyzer

- **Status**: [ ] Not Started
- **Estimated**: 1 hour
- **Dependencies**: T2.2
- **Files**: `nikita/engine/scoring/analyzer.py`

**Test Commit**: `test(109): add scoring analyzer retry integration test`
**Impl Commit**: `feat(109): apply @llm_retry to scoring analyzer _call_llm_raw`

**Acceptance Criteria**:
- [ ] AC-1: `_call_llm_raw` has `@llm_retry` decorator
- [ ] AC-2: Existing fallback to `_neutral_analysis()` still works after retry exhaustion
- [ ] AC-3: `pytest tests/engine/scoring/ -v` → all pass

---

### T2.4: Apply retry to boss judgment

- **Status**: [ ] Not Started
- **Estimated**: 1 hour
- **Dependencies**: T2.2
- **Files**: `nikita/engine/chapters/judgment.py`

**Test Commit**: `test(109): add boss judgment retry integration test`
**Impl Commit**: `feat(109): apply @llm_retry to boss judgment LLM calls`

**Acceptance Criteria**:
- [ ] AC-1: Both `_call_llm` and `_call_multi_phase_llm` use retry
- [ ] AC-2: Existing FAIL fallback preserved on retry exhaustion
- [ ] AC-3: `pytest tests/engine/chapters/ -v` → all pass

---

### T2.5: Apply retry to engagement detection

- **Status**: [ ] Not Started
- **Estimated**: 1 hour
- **Dependencies**: T2.2
- **Files**: `nikita/engine/engagement/detection.py`

**Test Commit**: `test(109): add engagement detection retry integration test`
**Impl Commit**: `feat(109): apply @llm_retry to engagement detection LLM calls`

**Acceptance Criteria**:
- [ ] AC-1: Both `_call_neediness_llm` and `_call_distraction_llm` have `@llm_retry`
- [ ] AC-2: Existing `Decimal("0.3")` fallback preserved
- [ ] AC-3: `pytest tests/engine/engagement/ -v` → all pass

---

### T2.6: Apply retry to conflict detector + resolution

- **Status**: [ ] Not Started
- **Estimated**: 1.5 hours
- **Dependencies**: T2.2, T1.3, T1.5
- **Files**: `nikita/conflicts/detector.py`, `nikita/conflicts/resolution.py`

**Test Commit**: `test(109): add conflict detector/resolution retry integration tests`
**Impl Commit**: `feat(109): apply @llm_retry to conflict detector + resolution LLM calls`

**Acceptance Criteria**:
- [ ] AC-1: Both `_detect_with_llm` and `_evaluate_with_llm` have `@llm_retry`
- [ ] AC-2: Final failure logged at ERROR level (was silent before)
- [ ] AC-3: `pytest tests/conflicts/ -v` → all pass

---

## US-3: Deduplicate Background Task DI

### T3.1: Extract DI factory and wire both paths

- **Status**: [ ] Not Started
- **Estimated**: 2 hours
- **Dependencies**: None (independent of US-1 and US-2)
- **Files**: `nikita/api/routes/telegram.py`

**Test Commit**: `test(109): add failing tests for DI factory`
**Impl Commit**: `refactor(109): extract build_message_handler factory, deduplicate DI`

**Acceptance Criteria**:
- [ ] AC-1: `build_message_handler()` exists and constructs MessageHandler with all params
- [ ] AC-2: `get_message_handler()` calls `build_message_handler()`
- [ ] AC-3: `_handle_message_with_fresh_session()` calls `build_message_handler()`
- [ ] AC-4: `rg "UserRepository\(session\)" nikita/api/routes/telegram.py` → only inside `build_message_handler` (1 occurrence)

---

### T3.2: Write DI factory tests

- **Status**: [ ] Not Started
- **Estimated**: 1.5 hours
- **Dependencies**: T3.1
- **Files**: CREATE `tests/api/test_di_factory.py`

**Test Commit**: `test(109): add DI factory unit tests`
**Impl Commit**: N/A (test-only task)

**Test Cases**:
1. `test_build_message_handler_returns_handler` — returns MessageHandler instance
2. `test_build_message_handler_all_repos_initialized` — 5 repos not None
3. `test_build_message_handler_services_initialized` — rate_limiter, response_delivery, text_agent_handler not None
4. `test_build_message_handler_bot_passed` — handler.bot is the bot argument
5. `test_get_message_handler_uses_factory` — mock build_message_handler, verify called

**Acceptance Criteria**:
- [ ] AC-1: `pytest tests/api/test_di_factory.py -v` → 5 passed
- [ ] AC-2: Tests use `AsyncMock(spec=AsyncSession)` and `MagicMock(spec=Bot)`

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

**Total**: 13 tasks, ~26.5 hours, ~4 days

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
