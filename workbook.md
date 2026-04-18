# Handover — Spec 215 Phase 1 COMPLETE; flag-OFF; awaiting baseline + flag-flip decision

**Date**: 2026-04-18 19:05 · **Session**: post-compact resumption + parallel B2/B3/B4 dispatch + 215-E ship

## 1. Resume command

```bash
cd /Users/yangsim/Nanoleq/sideProjects/nikita/.claude/worktrees/delightful-orbiting-ladybug
git pull --ff-only                    # expect HEAD = ea67c32 (fix B2 cost breaker, latest)
gh pr list --state open               # expect empty (all 4 Spec 215 cleanup PRs merged)
gh issue list --state open --label heartbeat-blocker  # expect empty (B1-B4 all closed)
```

## 2. Operating files (current-state pointers)

- `supabase/migrations/20260418141500_cron_heartbeat_engine.sql` — APPLIED, 3 cron jobs registered
- `supabase/migrations/20260418160000_add_cost_usd_to_job_executions.sql` — APPLIED, B2 cost ledger column
- `nikita/heartbeat/planner.py` — `PLANNER_TIMEOUT_S = 30.0` + `asyncio.wait_for` (B4 fix)
- `nikita/api/routes/tasks.py` — heartbeat handler now uses `pg_try_advisory_lock` (B3 fix); daily-arcs handler uses `get_today_cost_usd` (B2 fix)
- `nikita/db/repositories/job_execution_repository.py` — `get_today_cost_usd()` method (B2 fix)
- `docs/diagrams/11-heartbeat-engine.md` — full ASCII flow + dep graph + failure tree (last refresh 2026-04-18 16:30)
- `ROADMAP.md` — Spec 215 status: Phase 1 COMPLETE; flag-OFF
- `/Users/yangsim/.claude/plans/delightful-orbiting-ladybug.md` — Plan v1-v6.14 + v6.13 intel + v6.14 parallel matrix

## 3. Artifact trail (this session, chronological)

1. **PR #339** (215-E cron registration + B1 close) — merged 05bd0df; migration applied
2. **PR #340** (B4 #338 planner timeout) — merged acf83f9; clean QA iter-1
3. **PR #341** (B3 #337 try_advisory_lock) — merged 9ab20a5; clean QA iter-1
4. **PR #342** (B2 #336 cost circuit breaker + cost_usd column) — merged ea67c32; clean QA iter-1; migration applied
5. **GH #343** (NEW) — pg_net 5s timeout vs Cloud Run cold-start (84% timeout rate, pre-existing systemic, cosmetic)

## 4. Current state

- Branch: `master`; HEAD = `ea67c32`; 0 commits behind origin/master
- Cloud Run: `nikita-api-00258-62c` (LIVE since 16:11 UTC; serves all Spec 215 endpoints)
- pg_cron: 12 active (10 nikita-* + 2 cleanup); heartbeat-hourly + touchpoints + arcs all firing
- 24h health: **0 job failures** of 633 completions; all 9 prior crons still functional
- Test baseline: **6326 passed, 0 failed** (172.59s, full nikita suite)
- Worktrees pruned: agent-a76f4cfe (B4), agent-a1c9b226 (B3), agent-a7ff64fa (B2) — back to ≤5
- Flag state: `HEARTBEAT_ENGINE_ENABLED=false` (default; Phase 1 ship-state)

## 5. Next concrete action (NEW session priorities)

### A. Onboarding live walk (Task #64, still pending)

Per workbook precedent — Spec 214 wizard live-walk verification using:
- `agent-browser` skill (NOT `chrome-devtools` — feedback_chrome_devtools_profile_lock.md)
- `simon.yang.ch+dogfood6@gmail.com` (next available alias; +1-5 burned earlier)
- Per `feedback_dogfood_gmail_mcp_mismatch.md`: Gmail MCP cannot read alias inbox; use generateLink workaround OR ask user to forward magic-link
- Cleanup user rows after walk via `mcp__supabase__execute_sql`

### B. Flag-flip decision (Spec 215 Phase 2 entry gate)

Now blocked only on `HEARTBEAT_ENGINE_ENABLED=true` user decision:
- All 4 pre-flag-flip blockers (B1-B4) closed
- 24h baseline observation: cron firing as scheduled, Cloud Run healthy, no errors
- User confirms: flip flag in Cloud Run env → first daily-arcs cron at 5:00 UTC will exercise full planner LLM path

### C. GH #343 pg_net timeout (separate PR)

Single migration to re-schedule all 12 cron jobs with `timeout_milliseconds := 30000`. Expected to drop timeout rate from 84% → <5%. Pre-existing systemic, NOT a Spec 215 blocker.

## 6. Locked decisions (do NOT re-litigate)

1. **Cron via MIGRATION** (`mcp__supabase__apply_migration`, NOT `execute_sql`) — locked
2. **B1 BUNDLED into 215-E migration** — done, single SQL surface
3. **Phase 1 ship-state**: cron-on with flag-OFF; B1-B4 all closed pre-flag-flip
4. **Subagent dispatch**: parallel B2/B3/B4 with `isolation: "worktree"` worked cleanly (3 subagents, 0 conflicts on tasks.py despite 2 of 3 touching it)
5. **Merge order**: B4 → B3 → B2 (no rebase pain encountered; all merged sequentially)
6. **pg_net timeout = pre-existing systemic, NOT Spec 215 issue** (84% timeout pre-dates Spec 215 by months)
7. **Generated arcs are write-only Phase 1; intensity math offline-only Phase 1; Phase 2 wires both** (separate spec cycle)
8. **No flag-flip until user explicitly approves** after baseline observation

## 7. Caveats

- **Auto mode currently OFF** per system reminder — fresh session should ask before scope expansion
- **GH_TOKEN may be empty in fresh shells**: `export GH_TOKEN=$(gh auth token)` before subagent dispatch (FIX C1)
- **5 active worktrees** (was 8, pruned 3 B-fix worktrees): main, agent-a8dd1287 (Spec 214-c), agent-ac71d488 (Spec 213), delightful-orbiting-ladybug, serene-plotting-island
- **`a8dd1287`, `ac71d488`** = active per workbook precedent; do NOT prune
- **`serene-plotting-island`** unclear purpose; left intact
- **Dogfood plus-aliases burned**: simon.yang.ch+dogfood1-5@gmail.com (1-3 cleanup confirmed; 4-5 status unknown — verify before reusing). Next: +dogfood6
- **pg_net 84% timeout rate is COSMETIC**: 633 job_executions completed in 24h with 0 failures; Cloud Run is processing work despite pg_net cutting connection. Not a real bug for Phase 1 (no live users producing scheduled_events). Becomes important post flag-flip — see GH #343.
- **`scheduled_events` table is empty** in 24h — no live users producing engagement events. Production traffic on Spec 215 cannot be measured until either (a) flag flips and synthetic touchpoints fire OR (b) onboarding walk lands a real user.
