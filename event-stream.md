# Event Stream
<!-- Max 100 lines, prune oldest when exceeded -->
[2026-03-10] DOCS: Post-PR#113 housekeeping — CLAUDE.md audit (7 files: pipeline 9→10 stages, api routes+admin auth, context legacy banner, conftest gotcha, nav entry), ROADMAP sync (tests 5225→5387, deploy rev, dates), GH #105+#106 closed, #108+#110 partial-fix comments. Auto-memory updated.
[2026-03-10] REVIEW: PR #113 review fixes — _decode_jwt DRY refactor (3→1 JWT decode path), null-safe email Input, transition display underscore replace, session.refresh after PUT /settings commit. 5 new tests, 98 vitest + 62 backend auth/settings tests pass. Portal build clean.
[2026-03-07] DEPLOY: Backend → Cloud Run rev nikita-api-00222-2bl (fix/portal-bugs-93-100 branch). Health: all services healthy. Portal already on Vercel.
[2026-03-06] LIVE-E2E: Player portal exhaustive E2E — 14 routes tested via Chrome browser automation. PASS: dashboard, conversations (list), nikita hub, nikita/day, nikita/mind, nikita/circle, nikita/stories, diary, settings (timezone save, delete dialog). ISSUES: conversation detail timestamps all "—" (#107), insights page broken (#108), vices 0% engagement (#109), engagement no active state (#110), Link Telegram fails (#111), hydration systemic (#112), settings email empty (#105), notifications toggle missing (#106). GH #94-#100 closed with verification. 8 new issues filed (#105-#112).
[2026-03-05] FIX: Portal bugs GH #94-#100 — 7 fixes on fix/portal-bugs-93-100. #97 safeDate() + NaN guard. #98 regex replaceAll. #94 stage name badge. #95 sidebar rename. #99 telegram_linked backend field. #100 admin conversations days=30. #96 hydration: useState+useEffect for client-only dates. 4 new GH issues filed (#101-#104). GH #93 closed. 358 backend tests pass. Portal build clean.
[2026-03-05] LIVE-E2E: Comprehensive portal E2E testing via Chrome browser automation (claude-in-chrome MCP). 13 player routes tested (12 PASS, 1 FAIL), 9 admin routes tested (all PASS). GH #93 timeline bar: FIXED (renders proportional). GH #94 event_type: CONFIRMED. GH #95 missing nav: CONFIRMED. 5 new bugs filed: GH #96 (React #418 hydration — systemic), #97 (conversation detail crash "Invalid time value" — P0), #98 (engagement "OUT OF_ZONE" underscore), #99 (Telegram "Not connected" despite telegram_id), #100 (admin /text empty). Data verified against Supabase: score 59.7, ch2, 8 vices, 4 conversations, all KPIs match.
[2026-03-04] LIVE-TEST: Spec 110 portal live testing — /admin pages verified (overview, users, pipeline, text, voice, jobs, prompts). Conversation Inspector: empty state ✓, event display ✓ (10 test events inserted/verified/cleaned). 3 UI bugs filed: GH #93 (timeline bar empty), #94 (event_type vs stage name), #95 (missing Conversations nav link). Telegram MCP unavailable; tested via direct SQL insert.
[2026-03-04] DEPLOY: Portal → Vercel production. Backend → Cloud Run rev nikita-api-00220-kzz + nikita-api-00221-bvs (added ADMIN_EMAILS=simon.yang.ch@gmail.com). Admin auth: set user_metadata.role="admin" via Supabase SQL.
[2026-03-04] MERGE: PR #92 — Spec 110 Pipeline Observability Phase A. Squash merged to master (a549952). 2 commits (feat + review fixes). CI: pydantic-ai pinned <1.65.0 to fix pip resolution-too-deep (fastmcp extra).
[2026-03-04] IMPLEMENT: Spec 110 — Pipeline Observability & Event Stream (Phase A). 7 new files + 3 modified = 10 files. Backend: observability module (emitter, snapshots, types), PipelineEvent DB model, orchestrator instrumentation (snapshot/emit/flush), 2 admin API endpoints, feature flag. Frontend: Conversation Inspector page (/admin/conversations/[id]) with stage timeline, summary cards, collapsible JSON event viewer. DB: pipeline_events table + 4 indexes + RLS + pg_cron retention (30d). 37 new tests, 5225 total passing. Portal build clean.
[2026-03-03] SYNC: Reset local master to origin/master (9823884). Dropped 2 subsumed local commits (83f512a, 034a319). Cleaned worktree + 4 stale branches.
[2026-02-27T15:38:00Z] MERGE: PR #81 — Spec 109 systemic cleanup: ConflictStore removal, @llm_retry decorator (7 sites), DI dedup, configurable timeouts, model prefix normalization, CI gate fix. 4 review rounds, 8 GH issues (83-90). Squash merged to master (9823884).
[2026-02-27T14:00:00Z] FIX: PR #81 review round 2 — 8 findings (GH #83-#90). 4 parallel implementers + 4 cross-reviewers. 2 RED items fixed (mock_settings missing call_timeout, test_migrations graphiti assertion). 5188 tests pass. Commit 419d204, all issues closed.
[2026-02-27T10:00:00Z] REVIEW: PR #81 code review — 12 findings. Fixed: retry exception swallow (C1), asyncio.TimeoutError retry (C2), unused import (C3), boss ERROR state (B1-B4), logger placement (S1), type annotations (S2), import ordering (S3), Models.opus() consistency (S4), breakup comment (S5), statement_timeout on checkout (S6), LLM warmup guard (S7), CI condition (CI1). 5 new tests + 4 updated tests. GH issue TBD for future ERROR recovery scheduling.
[2026-02-25T03:00:00Z] FIX: PR #80 regression fixes — Supavisor compat, conflict JSONB, model strings, 4 regression test files. Commit 83f512a (later subsumed by PR #81).
[2026-02-25T01:45:00Z] AUDIT: Retroactive audit reports for specs 100-105. All PASS. Notable: Spec 105 FR-002 (game status audit trail) not implemented (HIGH). Committed 511a823.
[2026-02-25T01:00:00Z] MERGE: PR #79 — model registry, Spec 108 voice optimization, ConflictStore deprecation, Supavisor fix, haiku migration, temp flag cleanup. Squash merged to master (9f9cc85)
[2026-02-24T10:00:00Z] DOCS: Full documentation sync — README rewrite (Graphiti→pgVector, Alembic→Supabase MCP stubs, Docker→source deploy), ROADMAP fixes (74→75 complete, 5195→5347 tests, 30→90 migrations), module CLAUDE.md updates (db: 8→90 migrations, context: legacy banner), architecture overview stale banner, auto-memory patterns (migration stubs, hook portability, push notifications, anti-patterns)
[2026-02-24T09:00:00Z] MERGE: PR #76 fix/107-schema-drift-prevention — 88 migration stubs, Supabase Preview CI, 3 review rounds (8 code fixes), config.toml
[2026-02-23T15:00:00Z] FIX: Spec 107 — process-framework-remediation: grep -oP→sed in 3 hooks (macOS portability), jq -n in 4 hooks (JSON safety), ROADMAP.md dedup (81→75 rows), specs 001/002 added to Domain 1, HEAD~5 fallback. 5 files, +64/-57
[2026-02-23T14:00:00Z] PROCESS: Framework overhaul — ROADMAP.md (294 lines, 81 specs), /roadmap command, 3 hooks (pre-compact, roadmap-sync, validate-workflow GATE 0), master-plan.md trimmed (840→744), master-todo.md trimmed (387→39), system-intelligence-roadmap.md COMPLETE, specs/archive/ with 037, CLAUDE.md + generate-claude-md skill updated
[2026-02-23T12:30:00Z] DEPLOY: Phase 7 — Cloud Run rev nikita-api-00209-zf6, Vercel portal-iqdcswesd
[2026-02-23T12:15:00Z] COMMIT: 5dc8344 — squash merge to master (98 files, 6,921 insertions)
[2026-02-23T12:00:00Z] MERGE: Squash merge integration/specs-070-100-106 → master — Phase 7 complete
[2026-02-23T11:45:00Z] REGRESSION: 4,909 passed, 0 failures — full suite clean after Spec 106
[2026-02-23T11:30:00Z] IMPL: Spec 106 — vice visibility, decay warnings, cross-platform continuity, adaptive sensitivity (14 new tests)
[2026-02-23T11:00:00Z] MIGRATION: Supabase — cool_down_until, push_subscriptions, score_history index, drop graphiti_group_id
[2026-02-23T10:30:00Z] COMMIT: Specs 100-105 + 070 — 9 logical commits on integration/specs-070-100-106
[2026-02-23T10:00:00Z] GIT: Created integration/specs-070-100-106 from master, cleaned 2 stashes
[2026-02-22T22:30:00Z] COMMIT: Waves F+G — touchpoint wiring, voice enhancements, 5 TODO fixes. +83 tests (5,088 total). Reverted over-engineered handler extraction.
[2026-02-22T22:00:00Z] IMPL: Wave G Tier 3 — G6: cooldown check, G7: store_pending_response, G8: facts TODO obsolete, G9: admin email, G10: error_count_24h
[2026-02-22T21:00:00Z] IMPL: Wave G Tier 1 — G1: voice ready_prompt, G2: LLM transcript summarization, G3: VoiceCall model+repo+DB logging
[2026-02-22T19:30:00Z] IMPL: Wave F — Touchpoint event wiring: _evaluate_event_trigger(), life_events through pipeline, 23 tests
[2026-02-22T18:30:00Z] DEPLOY: Wave E — Cloud Run rev nikita-api-00208-5ng (100% traffic), /health OK, 7 pg_cron jobs, flags ON
[2026-02-22T18:00:00Z] SECURITY: Wave E — 3 Supabase migrations (RLS audit_logs, restrict error_logs+scheduled_events, fix 9 search_paths). 12/13 advisors fixed. 1 remaining: leaked password protection (dashboard only)
[2026-02-22T17:30:00Z] DOCS: Wave E — nikita/CLAUDE.md + pipeline/CLAUDE.md updated (9→10 stage pipeline), .gcloudignore excludes portal/
[2026-02-22T16:00:00Z] ANALYSIS: Project intelligence report — 8 dimensions, 345 parsed files, 12 actionable insights → docs-to-process/20260222-analysis-project-intel-report.md
[2026-02-22T14:00:00Z] COMPLETE: Specs 067-069 — PersistenceStage, context enrichment, flag activation — 13 files, +803 lines, 22 new tests, 5,005 total passing (9d4466e)
[2026-02-22T13:45:00Z] IMPL: Spec 069 — Psyche safeguards (API key check, MAX_BATCH_USERS=100, cost logging) + 5 flags ON
[2026-02-22T13:45:00Z] IMPL: Spec 068 — PromptBuilder loads historical thoughts/threads from DB, merges with extraction
[2026-02-22T13:30:00Z] IMPL: Spec 067 — PersistenceStage (non-critical, position 3), pipeline now 10 stages
[2026-02-22T13:00:00Z] COMMIT: b1cef9b — schema audit remnants (wire zombies, remove MessageEmbedding)
[2026-02-22T12:30:00Z] START: Table integration gap analysis — Specs 067-069 (2 parallel agents)
[2026-02-21T10:00:00Z] CLEANUP: docs-to-process/ — deleted 41 stale validation/research files (~750KB)
[2026-02-21T09:50:00Z] DEPLOY: Portal → Vercel production + Backend → Cloud Run (Wave D endpoints)
[2026-02-21T09:45:00Z] COMMIT: 63da5da — Wave D (Specs 061-063), 47 files, 4,908 tests pass
[2026-02-20T14:00:00Z] COMPLETE: Wave D — Portal 2.0 (Specs 061-063), 3 specs implemented in parallel
[2026-02-20T13:55:00Z] BUILD: Portal 25 routes, 0 TS errors, 55 backend tests pass, 3.8s compile
[2026-02-20T13:50:00Z] IMPL: Spec 063 — Data Viz (engagement timeline, decay sparkline, vice radar), notification center (client-side), data export (CSV/JSON), actionable toasts
[2026-02-20T13:30:00Z] IMPL: Spec 062 — Page transitions (Framer Motion), skeleton shimmer, mobile bottom nav (5 tabs), empty state CTAs, branded spinner
[2026-02-20T13:30:00Z] IMPL: Spec 061 — Error boundaries, offline detection, exponential backoff retry (3x), skip-link, aria-live, sr-announcer, Vercel Analytics/SpeedInsights
[2026-02-20T13:00:00Z] START: Wave D — Portal 2.0 (Specs 061-063), team portal-2-wave-d1 (2 parallel agents)
[2026-02-19T10:00:00Z] START: Wave C — Spec 059 (Portal: Nikita's Day) + Spec 060 verification
[2026-02-19T13:00:00Z] FIX: Voice tests — converted 20 tests from deprecated asyncio.get_event_loop().run_until_complete() to async/await (Python 3.13+ compat)
[2026-02-19T12:30:00Z] FIX: Local Supabase schema — applied Wave A/B migrations (3 tables, 7 columns) to local DB, 12/12 integration tests pass
[2026-02-19T12:45:00Z] REGRESSION: 4,908 passed, 0 failed — full suite clean after DB + voice fixes
[2026-02-19T11:40:00Z] DEPLOY: Portal → Vercel production (portal-phi-orcin.vercel.app), 25 routes, /dashboard/nikita/day live
[2026-02-19T11:00:00Z] IMPL: Spec 059 (Portal: Nikita's Day) — 12/12 tasks, 5 new backend tests, psyche-tips endpoint, PsycheTips+WarmthMeter components, 2-col day page, portal build 0 errors
[2026-02-19T10:05:00Z] VERIFY: Spec 060 (Prompt Caching) — 15/15 tests pass, all 11 tasks marked [x], already implemented
[2026-02-18T14:10:00Z] SMOKE: Wave B live — flags ON (rev 00206-c8k), pg_cron psyche-batch-daily@03:15UTC, /health OK, /tasks/psyche-batch 200 (0 processed), Telegram msg→response clean (13s, no errors), 0 ERROR logs since deploy
[2026-02-18T12:05:00Z] DEPLOY: Wave B → Cloud Run rev nikita-api-00205-5x9, healthy 12s, /health OK, /tasks/psyche-batch 401 (auth required ✓), all flags OFF
[2026-02-18T11:45:00Z] COMPLETE: Wave B — Spec 056 (Psyche Agent) + Spec 058 (Multi-Phase Boss), 65 files, +8,764 lines, 280 new tests, 4,891 total passing (ee1187e)
[2026-02-18T11:30:00Z] TEAM: sdd-impl-wave-b — 3-agent TDD pipeline (quality-lead + backend-056 + backend-058), 14/14 tasks complete
[2026-02-18T11:15:00Z] IMPL: Spec 058 — BossPhaseManager, 2-phase OPENING→RESOLUTION, PARTIAL outcome, 10 phase prompts, warmth bonus, vulnerability exchange, 117 tests
[2026-02-18T11:15:00Z] IMPL: Spec 056 — PsycheState model, psyche agent, 3-tier trigger, batch job, L3 prompt injection, circuit breaker, 163 tests
[2026-02-18T10:30:00Z] VALIDATE: GATE 2 — 12 validators PASS (0 CRITICAL, 0 HIGH across both specs)
[2026-02-18T10:25:00Z] PLAN: 056 plan.md (25 tasks) + 058 plan.md (24 tasks) generated
[2026-02-18T10:20:00Z] SPEC: 056 (Psyche Agent) + 058 (Multi-Phase Boss) spec.md extracted from Gate 4.5
[2026-02-18T10:15:00Z] FIX: Doom spiral — repair bypass in temperature calculation, 19 tests (50f6946)
[2026-02-18T08:15:00Z] COMMIT: Wave A — 3d58749, 52 files, +6,138 lines, 4,108 tests pass
[2026-02-18T08:00:00Z] COMPLETE: Spec 057 — Conflict System CORE (20 tasks, 167 tests)
[2026-02-18T06:00:00Z] COMPLETE: Spec 055 — Life Sim Enhanced (22 tasks, 33 tests)
[2026-02-18T04:00:00Z] FIX: GH #69-71 — vice field mismatches (ec0ed5d)
[2026-02-17] P1-P8: DONE — Prerequisites complete
[2026-02-17] AUDIT: Deep audit COMPLETE — CONDITIONAL GO
[2026-02-17] GATE_4.5: Architecture review → 6 specs (055-060)
[2026-02-15] E2E: Full test — 363 scenarios, 4 bugs (GH #69-72)
