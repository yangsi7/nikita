# Event Stream
<!-- Max 40 lines, prune oldest when exceeded -->
[2025-12-24T15:50:00Z] SECURITY: Neo4j credentials rotated - old instance 65a1f800 deleted, new instance 243a159d
[2025-12-24T15:53:00Z] SECURITY: SEC-04 (Secret Manager migration) now COMPLETE - all secrets in GCP
[2025-12-24T16:08:18Z] FEATURE: Created /post-compact command - parallel agents (5-9), 80% token savings
[2025-12-27T21:47:00Z] E2E_TEST: Clean slate test started - deleted user, OTP flow completed
[2025-12-27T21:48:00Z] E2E_COMPLETE: Phases 0-5 PASS, Phase 6 BLOCKED - 3 critical bugs found
[2025-12-27T21:50:00Z] BUG_FOUND: BUG-002 (Firecrawl not called), BUG-003 (venue attribute), BUG-004 (ThreadRepository)
[2025-12-27T22:15:00Z] GITHUB: Created issues #9, #10, #11 for all 3 bugs
[2025-12-27T22:30:00Z] COMMIT: fix - resolve BUG-002, BUG-003, BUG-004 (3 files, 66 insertions) (1f9076c)
[2025-12-27T22:40:00Z] DEPLOY: nikita-api-00109-mlc LIVE - all 3 bugs fixed, 100% traffic
[2025-12-27T18:15:00Z] E2E_COMPLETE: Spec 017 now 96% - 11/37 ACs verified via autonomous MCP testing
[2025-12-28T01:45:00Z] BUG_FOUND: BUG-005 (Issue #12) - Regression: service dependency injection broken
[2025-12-28T01:48:00Z] COMMIT: fix(telegram) - correct service dependency injection (c4f41f3)
[2025-12-28T01:57:00Z] DEPLOY: nikita-api-00110-grt LIVE - BUG-005 fixed, 100% traffic
[2025-12-28T01:58:00Z] GITHUB: Closed Issue #12 - dependency injection corrected
[2025-12-28T18:00:00Z] E2E_TEST: Firecrawl verification started - profile complete, testing venue research
[2025-12-28T18:00:02Z] BUG_FOUND: BUG-007 - Firecrawl SDK 4.x SearchData response parsing broken
[2025-12-28T18:07:00Z] FIX: BUG-007 - Changed results.get("web") to results.web (SDK 4.x compat)
[2025-12-28T18:08:00Z] COMMIT: fix(venue-research) - handle Firecrawl SDK 4.x SearchData (ebfe29f)
[2025-12-28T18:10:00Z] DEPLOY: nikita-api-00111-h6b LIVE - BUG-007 fixed, Firecrawl working
[2025-12-28T18:11:01Z] E2E_VERIFY: Firecrawl returned 10 results for Zurich/techno - PRIMARY PATH CONFIRMED
[2025-12-28T18:11:01Z] E2E_VERIFY: Venues cached in venue_cache table (zurich/techno, expires 2026-01-27)
[2025-12-28T18:11:02Z] BUG_FOUND: BUG-008 - BackstoryGenerator._call_llm is placeholder, not implemented
[2025-12-28T18:15:00Z] GITHUB: Created Issue #13 for BUG-008 - blocks custom backstory flow
[2025-12-28T18:16:00Z] E2E_RESULT: BUG-002/007 VERIFIED - Firecrawl integration working
[2025-12-28T18:17:00Z] E2E_BLOCKED: Neo4j/prompt tests blocked by BUG-008 (onboarding incomplete)
[2025-12-28T22:30:00Z] FIX: BUG-008 - Implemented _call_llm with Pydantic AI + enhanced prompts
[2025-12-28T22:32:00Z] DEPLOY: nikita-api-00112-7x5 LIVE - BUG-008 fix deployed
[2025-12-28T22:33:00Z] E2E_VERIFY: BUG-008 FIXED - Custom backstory extraction working, onboarding completed
[2025-12-28T22:33:23Z] E2E_VERIFY: First Nikita message sent - user transitioned to active conversation
[2025-12-28T22:45:00Z] GITHUB: Issue #13 CLOSED - BUG-008 verified via E2E testing
[2025-12-28T22:45:00Z] PERF: Neo4j cold start 83.8s causing post-onboarding response timeout
