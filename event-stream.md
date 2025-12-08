# Event Stream
<!-- Max 25 lines, prune oldest when exceeded -->

[2025-12-05T15:45:00Z] FIX: telegram_id BigInteger migration (int32 overflow)
[2025-12-05T15:52:00Z] E2E: Telegram webhook VERIFIED - 200 OK, /start flow working
[2025-12-05T17:45:00Z] TEST: RegistrationHandler COMPLETE - 12 tests, 86 total telegram tests passing
[2025-12-05T18:15:00Z] SEC-02: DB rate limiting - migration + DatabaseRateLimiter class complete
[2025-12-05T18:30:00Z] SEC-03: HTML escaping added to bot.py - escape_html() + escape parameter
[2025-12-05T18:35:00Z] STATUS: Phase 1A Security Hardening COMPLETE - SEC-01/02/03 (SEC-04 deferred)
[2025-12-05T18:40:00Z] DEPLOY: Cloud Run revision 00030-mdh deployed - RegistrationHandler + SEC-02/03
[2025-12-05T18:48:00Z] DOCS: Synced todo.md with Phase 2 completion (spec 002 at 100%, SEC-01/02/03 done)
[2025-12-05T18:50:00Z] GIT: Pushed 3 commits to origin/master (789cb8a, 79e2fc0, f20ed0d)
[2025-12-05T23:00:00Z] BUG: User reported "something went wrong" on email submission
[2025-12-05T23:05:00Z] RCA: TelegramAuth async/await bug - sign_in_with_otp() not awaited
[2025-12-05T23:10:00Z] FIX: Changed Client→AsyncClient, added awaits, fixed tests - 86 tests passing
[2025-12-05T23:10:00Z] DEPLOY: Cloud Run revision 00031-wd2 deployed - TelegramAuth async fix
[2025-12-06T00:15:00Z] BUG: Magic link redirects to localhost:3000 (Supabase SITE_URL default)
[2025-12-06T00:20:00Z] RCA: Verified with Supabase docs - email_redirect_to parameter needed
[2025-12-06T00:25:00Z] FIX: Added email_redirect_to in auth.py + /auth/confirm endpoint
[2025-12-06T00:30:00Z] DEPLOY: Cloud Run revision 00032-nc8 deployed to gcp-transcribe-test
[2025-12-06T00:35:00Z] DOCS: Updated CLAUDE.md with strict documentation-first enforcement rule
[2025-12-07T01:00:00Z] BUG: Magic link shows error in fragment (#error=otp_expired) but displays JSON
[2025-12-07T01:15:00Z] RCA: /auth/confirm has no error handling, Supabase sends errors in URL fragment
[2025-12-07T01:30:00Z] FIX: Added error page + JS fragment extraction + dual registration flows
[2025-12-07T01:45:00Z] DEPLOY: Cloud Run revision 00033-wbl deployed - magic link error handling
