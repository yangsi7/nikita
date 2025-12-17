# Event Stream
<!-- Max 25 lines, prune oldest when exceeded -->
[2025-12-16T10:05:00Z] DEPLOY: nikita-api-00072-526 - Firecrawl SDK integration live (venue research now works)
[2025-12-16T12:27:00Z] FIX: Disabled skip decision + added timing logs to diagnose 2-min cold start
[2025-12-16T12:50:00Z] FIX: Messages now stored in DB (SQLAlchemy mutation → assignment)
[2025-12-16T12:55:00Z] DEPLOY: nikita-api-00074-cwv - Message persistence + template fix live
[2025-12-16T14:00:00Z] MIGRATION: rls_security_hardening - RLS on job_executions, policies, search_path fixes
[2025-12-16T14:30:00Z] MIGRATION: performance_optimization_indexes_rls_initplan - Indexes + 13 RLS policies fixed
[2025-12-16T14:45:00Z] AUDIT_COMPLETE: DB security/perf audit - 0 CRITICAL, 17 initplan fixed, 4 indexes fixed
[2025-12-16T21:00:00Z] TDD_TESTS: Added 28 tests for 4 post-processing fixes (TDD compliance restored)
[2025-12-16T22:00:00Z] TEST_FIX: Fixed tests/__init__.py (import error), EngagementState enum (6-state model)
[2025-12-16T22:05:00Z] TEST_FIX: ResponseTimer tests now mock settings for production mode testing
[2025-12-16T22:10:00Z] TEST_FIX: Skip/fact tests marked as skipped (features disabled/moved for MVP)
[2025-12-16T22:15:00Z] TEST_STATUS: 1218 passed, 18 skipped, 7 isolation issues (pass individually)
[2025-12-17T01:00:00Z] TEST_FIX: Created tests/conftest.py with clear_singleton_caches fixture (LRU cache + rate limiter reset)
[2025-12-17T01:05:00Z] TEST_FIX: Fixed test_admin_debug.py (isolated app) + test_tasks.py (mock location + TestClient config)
[2025-12-17T01:10:00Z] TEST_STATUS: 1225 passed, 18 skipped, 0 failed - ALL ISOLATION ISSUES RESOLVED
[2025-12-17T10:00:00Z] E2E_CREATE: tests/e2e/helpers/telegram_helper.py - Webhook simulator for E2E testing
[2025-12-17T10:05:00Z] E2E_CREATE: tests/e2e/helpers/mock_agent_helper.py - LLM mocking for E2E tests
[2025-12-17T10:10:00Z] E2E_CREATE: tests/e2e/test_otp_flow.py - 9 OTP registration tests (Spec 015)
[2025-12-17T10:15:00Z] E2E_CREATE: tests/e2e/test_message_flow.py - 10 message flow tests
[2025-12-17T10:20:00Z] E2E_STATUS: 31 passed, 2 skipped, 4 integration - Total E2E tests now 31
[2025-12-17T10:25:00Z] CI_UPDATE: .github/workflows/e2e.yml - Added OTP/message tests + TELEGRAM_WEBHOOK_SECRET
