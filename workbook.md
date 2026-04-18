# Handover — Spec 215 PR 215-E mid-execution + B1-B4 ready to dispatch

**Date**: 2026-04-18 18:30 · **Session**: post-intel-refresh; user-approved Plan v6.14 parallel batch

## 1. Resume command

```bash
cd /Users/yangsim/Nanoleq/sideProjects/nikita/.claude/worktrees/delightful-orbiting-ladybug
git branch --show-current   # expect feat/215-E-cron-heartbeat
git status --short          # expect untracked migration + script + diagram
gh issue list --label bug --state open --search "heartbeat OR touchpoints" | head -5
sed -n '2196,2400p' /Users/yangsim/.claude/plans/delightful-orbiting-ladybug.md  # v6.13+v6.14
```

## 2. Operating files (current session deliverables)

- `supabase/migrations/20260418141500_cron_heartbeat_engine.sql` — DRAFT, 3 cron jobs (heartbeat, daily-arcs, touchpoints — closes B1)
- `scripts/check_heartbeat_cron_jobs.py` — verification script (T6.2), exec-bit set
- `docs/diagrams/11-heartbeat-engine.md` — full ASCII flow + dep graph + failure tree (this session)
- `workbook.md` — THIS file
- `/Users/yangsim/.claude/plans/delightful-orbiting-ladybug.md` — Plan v1-v6.14 (v6.13 intel, v6.14 parallel matrix)
- ROADMAP.md — NOT YET UPDATED for Spec 215 (still pending)

## 3. Artifact trail

1. PRs MERGED on master `02911f0`: #331 #332 #333 #334 (Spec 215-A/B/C/D/F)
2. Cloud Run rev `nikita-api-00258-62c` LIVE since 16:11 (215-D code)
3. Integration test PASS: both endpoints return 200 `{"status":"disabled","reason":"feature_flag_off"}`
4. tree-of-thought + pr-codebase-intel agents synthesized → discovered B1-B4
5. GH issues filed: #335 (B1 CRITICAL), #336 (B2 HIGH), #337 (B3 HIGH), #338 (B4 MEDIUM)
6. User approved Plan v6.14 parallel matrix (auto-mode now off, was on at approval)

## 4. Current state

- Branch: `feat/215-E-cron-heartbeat`; HEAD = origin/master `02911f0`; 0 commits ahead
- Worktrees: 5 active (main + delightful-orbiting-ladybug + 214-c-e2e + 213 + serene-plotting-island)
- Pruned this session: agent-a024de80 (#304 merged), agent-ac595c68 (#332), agent-adeec65f (#333)
- Untracked in worktree: 2 hooks + 4 plans + diagram 11 + project-intel-cheatsheet + a11y spec + migration + check_heartbeat script (Plan v2 leftovers + this session)

## 5. Next concrete action — RESUME EXECUTION

### Immediate (in order):

1. **Add Spec 215 to ROADMAP.md** (CLAUDE.md SDD enforcement #1) — table row for `## Specs` section with status PARTIAL (Phase 1 cron registered, flag OFF)
2. **Pre-push HARD GATE**: `cd /Users/yangsim/Nanoleq/sideProjects/nikita/.claude/worktrees/delightful-orbiting-ladybug && uv run pytest -q` (full suite ~90s)
3. **Stage + commit + push 215-E PR**:
   ```bash
   git add supabase/migrations/20260418141500_cron_heartbeat_engine.sql \
           scripts/check_heartbeat_cron_jobs.py \
           docs/diagrams/11-heartbeat-engine.md \
           ROADMAP.md
   git commit -m "feat(215-E): register heartbeat + daily-arcs + touchpoints cron jobs (#335)"
   git push -u origin feat/215-E-cron-heartbeat
   gh pr create --title "feat(215-E): heartbeat + daily-arcs + touchpoints pg_cron registration" --body "<closes #335; bundle of 3 cron jobs in one migration; flag-OFF safe>"
   ```
4. **Dispatch 3 implementor subagents in parallel** (B2/B3/B4 per Plan v6.14 §subagent dispatch matrix):
   - Subagent-1 (B2 #336): `nikita/db/repositories/job_execution_repository.py` + `tasks.py:1384-1420` — implement `get_today_cost_usd` OR add hard cap
   - Subagent-2 (B3 #337): `tasks.py:1262-1298` — convert advisory lock to `pg_try_advisory_lock` + skip semantics
   - Subagent-3 (B4 #338): `nikita/heartbeat/planner.py:144-153` — `asyncio.wait_for(agent.run, timeout=30)` + `Final PLANNER_TIMEOUT_S=30.0`
   - Each: HARD CAP 25, isolation worktree, GH_TOKEN exported, TDD red-green, full pytest pre-push, gh pr create
5. **Run /qa-review --pr N for 215-E SEQUENTIALLY** (HARD CAP 5, scope = migration + script + diagram + ROADMAP)
6. **Apply migration via `mcp__supabase__apply_migration(name='cron_heartbeat_engine', query=<file contents>)`** AFTER 215-E merges
7. **Verify**: run `uv run python scripts/check_heartbeat_cron_jobs.py` after first :00 minute tick
8. **Sequentially merge B4 → B3 → B2** (Plan v6.14 merge-order rationale: avoid tasks.py conflicts; B4 is planner.py = no conflict)
9. **Address user's onboarding walk ask** (still pending; agent-browser + plus-alias)

## 6. Locked decisions (do NOT re-litigate)

1. **Cron via MIGRATION not MCP execute_sql** (PR-reviewable, version-controlled)
2. **B1 BUNDLED into 215-E migration** (single SQL surface; user approved "Fix all issues")
3. **Apply via `mcp__supabase__apply_migration`** post-merge (NOT `execute_sql`)
4. **Phase 1 ship-state**: cron-on with flag-OFF; B1-B4 are pre-flag-flip blockers; flag-flip is separate user decision after baseline
5. **Subagent dispatch matrix**: 3 parallel for B2/B3/B4; orchestrator owns 215-E + verification
6. **Merge order**: 215-E → B4 → B3 → B2 (minimize tasks.py rebase pain)
7. **Hardcoded Bearer matches 9-existing pattern**; vault cleanup deferred separately
8. **Generated arcs are write-only Phase 1**; intensity math offline-only Phase 1; Phase 2 wires both
9. **No flag-flip** until B1-B4 land + 24h baseline + onboarding walk passes

## 7. Caveats

- **Auto mode WAS ON during approval, now OFF** per system reminder; resume sub-tasks should ask before scope expansion
- **GH_TOKEN env may be empty in fresh shells**: `export GH_TOKEN=$(gh auth token)` before subagent dispatch (FIX C1)
- **Migration apply requires service-role connection**: `mcp__supabase__apply_migration` handles this; do NOT try via Cloud Run proxy
- **Pre-existing untracked files** (.claude/hooks, .claude/plans, docs/project-intel-cheatsheet, portal/e2e/a11y-gate, brief-spec215, ledgers) — NOT this session's; defer to separate cleanup PR
- **Worktree `serene-plotting-island`** unclear purpose; left intact (orchestrator did not investigate origin)
- **`a8dd1287` worktree** = feat/214-c-e2e-deploy = active Spec 214 work; do NOT prune
- **`ac71d488` worktree** = Spec 213 active per workbook precedent; do NOT prune
- **Dogfood**: plus-alias `simon.yang.ch+dogfood5@gmail.com` (1-3 burned + cleaned earlier per `feedback_dogfood_gmail_mcp_mismatch.md`)
- **B2 fix may require column-add migration** if `job_executions.cost_usd` doesn't exist; subagent should detect + scope appropriately
- **Cost-breaker degraded warning** lands in Cloud Run logs every daily-arc tick once flag flips — log-based alert routing TBD
- **Cron starts firing 5 min after migration apply** (touchpoints */5) and at next :00 (heartbeat); both will return `{"status":"disabled"}` until flag-flip — verify via `cron.job_run_details`
