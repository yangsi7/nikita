# Workbook - Session Context
<!-- Max 300 lines, prune aggressively -->

## Current Session: Post-Processing Sprint (2026-02-11)

### Status: 7/7 COMPLETE — Sprint DONE

**All Items:**

| Item | Fix | Status |
|------|-----|--------|
| W1 | base.py logging→structlog + prompt_builder timeout 30→90s | fb4ba33 |
| W2 | 5 voice_flow.py stubs (DB + ElevenLabs wiring) | c4e0814 |
| W3 | RLS: 3 tables→service_role, 2 DELETE policies added | Supabase MCP |
| W4 | Spec 037 closed as SUPERSEDED by Spec 042 | 92a19a1 |
| W5 | pg_cron: deliver */1→*/5, cron-cleanup job (7-day) | Supabase MCP |
| W6 | CLAUDE.md minInstances=0 rule | dd65f02 |
| W7 | Deploy rev 00197-xvg — health PASS | Cloud Run |

**Deployed:** rev 00197-xvg — health check PASS, DB+Supabase connected

**Lessons Learned:** https://github.com/yangsi7/sdd-team-skill/issues/4

**RLS Final State (21 policies across 7 tables):**
- user_backstories: SELECT(own+admin)/INSERT/UPDATE/DELETE — `auth.uid() = user_id`
- user_profiles: SELECT(own+admin)/INSERT/UPDATE/DELETE — `auth.uid() = id`
- user_social_circles: SELECT/INSERT/UPDATE/DELETE — `auth.uid() = user_id`
- user_narrative_arcs: SELECT/INSERT/UPDATE/DELETE — `auth.uid() = user_id`
- nikita_entities/life_events/narrative_arcs: ALL → `service_role` only

**pg_cron Final State (6 jobs):**
- decay(hourly), deliver(*/5), summary(23:59), cleanup(hourly:30), process-conversations(*/5), cron-cleanup(3AM/7-day)

**Pipeline issues still open (non-critical):**
1. life_sim: SQL `:user_id` — valid SQLAlchemy syntax, cascading failure
2. memory_facts: Not persisting (SAWarning during cascaded failures)

---

## Previous Sessions (Compact)

| Date | Session | Key Result |
|------|---------|------------|
| 2026-02-11 | Post-Processing Sprint | 7/7 items, rev 00197-xvg, RLS+pg_cron, 3,922 tests |
| 2026-02-10 | Pipeline Caller Fixes | 7 bugs fixed (051fe92), rev 00195-xrx, live E2E PASS |
| 2026-02-10 | Live E2E Fix Sprint | 6 fixes, mark_processed, pg_cron restored |
| 2026-02-09 | Post-Release Sprint | 86 E2E tests, prod hardening, all gates PASS |
| 2026-02-09 | Release Sprint | 5 GH issues closed, 37 E2E tests, spec hygiene |
| 2026-02-08 | Spec 044 Implementation | 94 files, 19 routes, 3,917 tests, Vercel deploy |
| 2026-02-07 | Iteration Sprint | E2E fix (19→0), doc cleanup, 3,895 tests |
| 2026-02-06 | Spec 042 SDD + Impl | 45/45 tasks, ~11K lines deleted, 3,797 tests |
