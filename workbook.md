# Workbook - Session Context
<!-- Max 300 lines, prune aggressively -->

## Current Session: E2E Testing Implementation (2025-12-17)

### Test Status Summary

| Category | Tests | Status |
|----------|-------|--------|
| Unit Tests | 1225 | ✅ All passing |
| E2E Tests | 31 | ✅ All passing |
| Skipped | 20 | ⏸️ Features disabled/integration |
| Total | ~1260 | 100% healthy |

### E2E Test Coverage (NEW)

| File | Tests | Coverage |
|------|-------|----------|
| test_auth_flow.py | 14 | Auth confirm endpoint, JWT, XSS |
| test_otp_flow.py | 9 | OTP registration flow (Spec 015) |
| test_message_flow.py | 10 | Webhook message handling |

**New Files Created:**
- `tests/e2e/helpers/telegram_helper.py` - Webhook simulator
- `tests/e2e/helpers/mock_agent_helper.py` - LLM mocking helper
- `tests/e2e/test_otp_flow.py` - OTP flow tests
- `tests/e2e/test_message_flow.py` - Message flow tests

**CI/CD Updated:**
- `.github/workflows/e2e.yml` - Runs all E2E tests
- **Required Secret**: `TELEGRAM_WEBHOOK_SECRET` in GitHub Secrets

### Fixed Issues (Session 2025-12-17)

1. **Import Error** - Added `tests/__init__.py` (was missing)
2. **EngagementState Enum** - Updated tests for 6-state model
3. **ResponseTimer Tests** - Now mock `get_settings()` for production mode
4. **Skip Handler Tests** - Marked as skipped (feature disabled for MVP)
5. **Fact Extraction Tests** - Marked as skipped (moved to post-processing)
6. **Test Isolation (7 tests)** - Root causes identified and fixed:
   - Created `tests/conftest.py` with `clear_singleton_caches` autouse fixture
   - Fixed `test_admin_debug.py` to create isolated FastAPI app (was importing prod app)
   - Fixed `test_tasks.py` mock patching location + TestClient config

### Temporarily Disabled Features (MVP)

| Feature | File | Reason |
|---------|------|--------|
| Skip Decision | handler.py:234-251 | Testing core flow first |
| Fact Extraction | handler.py:260-263 | Moved to post-processing |
| Response Delays | timing.py (dev mode) | Returns 0 in development |

### Key Architecture Notes

#### Message Flow (Telegram → Response)
```
Webhook → Auth → Rate Limit → Conversation → Text Agent → LLM → Response Queue
```

#### Post-Processing (15+ min after last message)
```
Session Detect → Extraction → Threads → Thoughts → Neo4j → Vice → Finalize
```

#### Disabled for MVP
- Skip probability (AC-5.2.x tests skipped)
- Inline fact extraction (moved to post-processor)
- Response delays (returns 0 in dev/debug mode)

## Next Actions

1. [x] ~~Fix async test isolation~~ → DONE (conftest.py + isolated apps)
2. [x] ~~Add E2E tests for OTP flow~~ → DONE (9 tests)
3. [x] ~~Add E2E tests for message flow~~ → DONE (10 tests)
4. [x] ~~Update CI/CD workflow~~ → DONE (e2e.yml)
5. [ ] Add TELEGRAM_WEBHOOK_SECRET to GitHub Secrets
6. [ ] Re-enable skip feature when core flow is stable
7. [ ] Validate post-processing fact extraction works end-to-end

## Anti-Patterns to Avoid

- Don't mock `get_settings()` globally - use `patch()` context manager
- Don't test disabled features without skip marker
- Don't run integration tests without DB connection
- Don't import production app in tests - create isolated FastAPI app per test
- Don't patch where function is defined - patch where it's USED (e.g., `nikita.api.routes.tasks.get_session_maker`, not `nikita.db.database.get_session_maker`)
- Don't forget `raise_server_exceptions=False` when testing 500 error responses

## Reference

- **Test Structure**: `tests/{module}/test_{feature}.py`
- **Run Unit Tests**: `python -m pytest tests/ -q --ignore=tests/integration --ignore=tests/e2e -k "not Integration"`
- **Run E2E Tests**: `TELEGRAM_WEBHOOK_SECRET="..." python -m pytest tests/e2e/ -v -k "not integration"`
- **Run Single Test**: `python -m pytest tests/path/test_file.py::TestClass::test_method -v`
- **E2E Webhook Secret**: Get from `gcloud secrets versions access latest --secret=nikita-telegram-webhook-secret --project=gcp-transcribe-test`
