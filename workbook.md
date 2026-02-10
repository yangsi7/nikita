# Workbook - Session Context
<!-- Max 300 lines, prune aggressively -->

## Current Session: Pipeline Proof Sprint (2026-02-10)

### Status: COMPLETE — Pipeline fixed, deployed, live E2E verified with proof

**Pipeline was 100% broken since Jan 29 deployment — now 100% working.**

**Bugs Fixed (6 bugs + 1 DB constraint):**

| Bug | Root Cause | Fix | Commit |
|-----|-----------|-----|--------|
| BUG-001 | `PipelineContext.conversation` always None | Added `conversation=`/`user=` to `process()` | a3d17c0 |
| BUG-001b | tasks.py never loaded User before calling pipeline | Added UserRepository lookup | a3d17c0 |
| BUG-002 | Extraction used `msg.role` on JSONB dicts | Changed to `msg.get('role')` | a3d17c0 |
| BUG-003 | MemoryUpdateStage expected `list[dict]`, got `list[str]` | Handle both formats | a3d17c0 |
| BUG-004 | `r.conversation_id` → should be `r.context.conversation_id` | Fixed attribute path | a3d17c0 |
| BUG-005 | pydantic-ai 1.x: `result_type` → `output_type` | Renamed in 7 files | 592fa15 |
| BUG-006 | emotional_tone CHECK only allowed pos/neu/neg | Added 'mixed' | Supabase SQL |

**Live E2E Proof (Conversation f50e12fd):**
- 6 Telegram messages exchanged with production bot
- Pipeline triggered via pg_cron, completed in 42.2s
- 14 facts extracted, summary stored, tone=mixed
- 4,163-token personalized system prompt generated in ready_prompts
- 5/9 stages PASS (2/2 critical), 4 non-critical failures (missing tables)
- Full report: `docs-to-process/20260210-pipeline-proof-report.md`

**Deployments:** rev 00190-gzg (bug fixes), rev 00191-7xc (pydantic-ai compat)

**Non-Critical Remaining (P2-P3):**
1. P2: Create `nikita_entities` + `scheduled_touchpoints` tables
2. P2: Summary stage greenlet error (transaction isolation)
3. P3: game_state logger kwargs mismatch
4. P3: prompt_builder Haiku enrichment api_key param

---

## Previous Session: Post-Release Verification & Hardening (2026-02-09)

### Status: COMPLETE — All 3 agents done, all gates PASS

**Team: nikita-post-release**

| Agent | Task | Status | Key Findings |
|-------|------|--------|--------------|
| live-tester | Live Telegram E2E | COMPLETE | Bot responsive, Supabase data verified, 0 Cloud Run errors |
| portal-e2e | Playwright E2E authoring | COMPLETE | 86 tests, 0 failures (was 37) |
| prod-hardener | Infra hardening audit | COMPLETE | 4/4 pg_cron healthy, 33/34 RLS, webhook CONFIRMED |

### Critical Findings (from prod-hardener)

**P0: 5 TODO stubs in `nikita/onboarding/voice_flow.py`** — DB lookup/save/update + ElevenLabs API call are stubbed. Voice onboarding will fail silently. Action: FIX.

**P1 Issues:**
1. Cloud Run `minInstances=0` → cold starts (~5-15s). Set to 1 ($5-10/mo).
2. RLS INSERT policies missing `WITH CHECK (auth.uid() = user_id)` on 6 tables.
3. Service-internal tables (`nikita_entities`, `nikita_life_events`, `nikita_narrative_arcs`) have `public ALL` policy — should be `service_role`.
4. Startup probe timeout 240s is too generous — masks slow-start bugs.

### Infrastructure Fixes Applied
- Installed `greenlet` (SQLAlchemy async requirement) — DB integration tests now pass (52/52)
- Installed `playwright` Python package — 14 auth-flow E2E tests now pass
- Enabled `DATABASE_URL_POOLER` in .env (was commented out)
- Full regression confirmed: **3,917 pass, 0 fail, 21 skip**

### Portal E2E Tests — 86 PASS, 0 FAIL

| File | Tests | Coverage |
|------|-------|----------|
| `global-setup.ts` | 1 | Auth storage state creation |
| `fixtures.ts` | — | Shared utilities (expectProtectedRoute, assertLoginPageElements) |
| `login.spec.ts` | 20 | Login form, dark theme, auth redirects (13 routes) |
| `auth-flow.spec.ts` | 12 | Redirects, form rendering, OTP mock, logout |
| `dashboard.spec.ts` | 13 | Score ring, timeline, radar, nav, empty states, skeletons |
| `admin.spec.ts` | 10 | Admin smoke tests, sidebar, auth redirect |
| `admin-mutations.spec.ts` | 16 | User list/detail, filters, error states, sidebar nav, confirmations |
| `accessibility.spec.ts` | 7 | axe-core WCAG 2.1 AA, keyboard nav, contrast |
| `player.spec.ts` | 8 | Player route smoke tests, sidebar, deep routes |

---

## Archived Sessions (Compact)

| Date | Session | Key Result |
|------|---------|------------|
| 2026-02-09 | Post-Release Sprint | 86 E2E tests, prod hardening report, all gates PASS |
| 2026-02-09 | Release Sprint | 5 GH issues closed, 37 E2E tests, spec hygiene |
| 2026-02-08 | Spec 044 Implementation | 94 files, 19 routes, 3,917 tests, Vercel deploy |
| 2026-02-08 | Spec 044 Enhancement | shadcn config, backend fixes, 20 new tests |
| 2026-02-07 | Iteration Sprint | E2E fix (19→0), doc cleanup, 3,895 tests |
| 2026-02-07 | Specs 042-044 SDD | Unified pipeline + system audit + portal respec |
| 2026-02-06 | Spec 042 SDD + Impl | 45/45 tasks, ~11K lines deleted, 3,797 tests |
| 2026-02-02 | Knowledge Transfer | Meta-prompt engineering command (750 lines) |
| 2026-01-28 | Full E2E Test | 6/6 phases PASS, scoring +1.35, context verified |
