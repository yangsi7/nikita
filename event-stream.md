# Event Stream
<!-- Max 25 lines, prune oldest when exceeded -->
[2025-12-18T14:00:00Z] SDD_018: Created spec/plan/tasks/audit for Admin Prompt Viewing (018)
[2025-12-18T14:30:00Z] IMPL_018: 3 prompt endpoints (list/latest/preview) + skip_logging param
[2025-12-18T14:45:00Z] DEPLOY: nikita-api deployed to Cloud Run (revision nikita-api-00082-wcv)
[2025-12-18T14:50:00Z] E2E_START: Beginning E2E testing with real Telegram user
[2025-12-19T02:15:00Z] RESEARCH_OTP: Critical OTP bug research complete - root cause identified (template config)
[2025-12-19T02:30:00Z] RECOMMENDATION: Update Supabase Email Template ({{ .Token }} variable) to fix OTP flow
[2025-12-19T03:00:00Z] FIX_OTP_LOOP: Added otp_attempts field + retry limit (max 3 attempts before lockout)
[2025-12-19T03:15:00Z] MIGRATION: Applied add_otp_attempts_to_pending_registrations migration
[2025-12-19T03:20:00Z] DEPLOY: nikita-api deployed (revision nikita-api-00083-xss) with OTP retry limit fix
[2025-12-20T01:00:00Z] SECURITY_FIX: Atomic SQL increment for OTP attempts - prevent TOCTOU race condition
[2025-12-20T01:10:00Z] SECURITY_FIX: Fail-closed OTP verification - deny on any tracking failure
[2025-12-20T01:20:00Z] SECURITY_FIX: Delete pending BEFORE user creation - prevent limbo state
[2025-12-20T01:30:00Z] SECURITY_FIX: Use AuthApiError.code not string matching - per Supabase best practices
[2025-12-20T01:40:00Z] TEST_STATUS: 1248 passed, 18 skipped - ALL tests pass after security fixes
[2025-12-20T01:45:00Z] COMMITS: 3 atomic security commits created (race condition, fail-closed, error codes)
