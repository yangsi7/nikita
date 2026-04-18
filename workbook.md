# Handover — Spec 215 Heartbeat Engine, Parallel Orchestration BLOCKED on prune decision

**Date**: 2026-04-18 · **Session**: post-/plan-rewrite Wave 1+2+3, awaiting user input on worktree prune

## 1. Resume command

```bash
cd /Users/yangsim/Nanoleq/sideProjects/nikita/.claude/worktrees/delightful-orbiting-ladybug
git fetch origin && git status                           # confirm on master, clean
sed -n '1562,2200p' /Users/yangsim/.claude/plans/delightful-orbiting-ladybug.md  # Plan v6 + v6.12
git worktree list                                        # confirm 9 worktrees still present
```

## 2. Operating files

- `/Users/yangsim/.claude/plans/delightful-orbiting-ladybug.md` — **Plan v6 (parallel orchestration brief, lines 1562-1995) + v6.12 (Wave 3 fix patches, lines ~1880-1995)** — AUTHORITATIVE for next steps
- `specs/215-heartbeat-engine/{spec,plan,tasks,validation-findings}.md` — SDD artifacts (GATE 2 PASS iter-2)
- `specs/215-heartbeat-engine/contracts.md` — **DOES NOT EXIST YET** (P2 prereq creates it; literal content embedded in Plan v6.3 P2)
- `nikita/heartbeat/intensity.py` (PR 215-B, frozen) — math module symbols 215-F imports
- `nikita/db/repositories/heartbeat_repository.py` (PR 215-A, frozen) — `NikitaDailyPlanRepository.upsert_plan` 215-C+D consume
- `nikita/api/routes/tasks.py:902-982` — `/refresh-voice-prompts` pattern 215-D mirrors
- `nikita/agents/text/agent.py:1-66` — Pydantic AI client pattern 215-C mirrors

## 3. Artifact trail (chronological, all in `/Users/yangsim/.claude/plans/delightful-orbiting-ladybug.md`)

1. Plan v3 §A.1-A.6 (lines ~700-960) — math model authority (von Mises × Hawkes × Ogata)
2. Plan v4 (lines ~970-1310) — SDD handoff brief, Approach A1 locked
3. Plan v5 (lines ~1320-1560) — post-compaction resume runbook (single-agent serial path, NOW SUPERSEDED)
4. **Plan v6 (lines 1562-1880)** — parallel multi-worktree orchestration brief (Wave 1+2 evidence)
5. **Plan v6.12 (lines ~1880-1995)** — Wave 3 fix patches (devil's advocate + process auditor findings)
6. `specs/215-heartbeat-engine/{spec,plan,tasks,validation-findings}.md` (GATE 2 PASS)
7. `.claude/plans/handover-2026-04-18-spec215-pr215a.md` (predecessor session brief, pre-PR-#330)

## 4. Current state

- Branch: `master` at `a3ed2b3` (post-PR-#330 squash); local + origin in sync
- PRs merged: #326 (215-A), #328 (215-B), #329 (215-G), #330 (rules HARD GATE)
- Open PRs: none. Spec 215 remaining: 215-C planner, 215-D endpoints, 215-E pg_cron, 215-F parity validator
- Tests baseline: nikita 30/30 heartbeat pass; portal 632/632 pass
- Worktrees: 9 active (1 main + 8 sub) — exceeds Plan v6 L2 cap of ≤5 active
- `gh auth status` PASS (account `yangsi7`); `GH_TOKEN` env var EMPTY → must `export GH_TOKEN=$(gh auth token)` before subagent dispatch (per FIX C1)

## 5. Next concrete action — BLOCKED on user decision

**Plan v6 prerequisite P1 says prune 5 generic `worktree-agent-*` worktrees to ≤5 active before parallel dispatch. Live check 2026-04-18 found ALL 5 hold unmerged work**:

| Worktree | Branch | Ahead/Behind | Last commit | Working tree |
|---|---|---|---|---|
| agent-a4fbad53 | worktree-agent-a4fbad53 | 28/11 | F-05 onboarding fix (2026-04-15) | clean |
| agent-a624dc3c | worktree-agent-a624dc3c | 27/7 | 213-4 FR-2a tests (2026-04-15) | clean |
| agent-a75bd873 | worktree-agent-a75bd873 | 29/6 | profile_fields migration (2026-04-14) | clean |
| agent-ac71d488 | worktree-agent-ac71d488 | 27/1 | 213-4 pipeline-ready tests (2026-04-15) | **DIRTY: 9 modified files** |
| agent-ae4ab076 | worktree-agent-ae4ab076 | 26/6 | Spec 213 ROADMAP sync (2026-04-15) | clean |

Total ~130 unmerged commits across 5 branches. Likely stale (Spec 213 + 214 already shipped via squash-merge under different SHAs) but `--force` removal would discard. **Per Core Behavior #8 carve-out (a) destructive ops require user confirmation.** AskUserQuestion was loaded but not yet sent at end of session.

**Resume action**: surface the prune-or-keep decision via AskUserQuestion. Once decided:
- If prune → execute Plan v6.3 P1+P2+P3+P4 → dispatch 3 subagents per Plan v6.5 (PATCHED v6.12)
- If keep → revise L2 cap upward to 12, document reasoning in v6.12 → dispatch anyway

## 6. Locked decisions (do NOT re-litigate)

1. **Approach A1** (new endpoint + `nikita_daily_plan` table) — Plan v4 §v4.1
2. **OD1=Haiku 4.5** for daily arc generation (cost ceiling per G3)
3. **OD2=BOTH** `arc_json` + `narrative_text` columns
4. **OD7=LLM planner** Phase 1 (NOT rule-based)
5. **R7**: Phase 1 `arc_json` is throwaway; Phase 2 parallel `nikita_daily_intensity_state` table
6. **TouchpointEngine handoff** via `evaluate_and_schedule_for_user(trigger_reason="heartbeat")` — heartbeat NEVER writes `scheduled_events` directly (FR-007/R1)
7. **Pre-push HARD GATE** full test suite for touched area before `git push` (`.claude/rules/pr-workflow.md`)
8. **Plan v6 parallel orchestration**: subagent + `isolation: "worktree"`, NOT TeamCreate (experimental blockers per Anthropic docs); 3-shape contract-first; 215-C+215-F truly parallel; 215-D after contract lock; 215-E ops-only no worktree
9. **Iter-2 kill-switch on 215-D**: if 215-D fails second fresh QA review, halt parallel topology, pull 215-D into main session single-agent
10. **Implementor caps**: 25 tool calls for 215-C+215-F, 40 for 215-D (per Plan v6.12 FIX H2)

## 7. Caveats / dirty files

- 9 untracked files at worktree root (Plan v2 hook scripts + plan/ledger drafts + a11y-gate.spec.ts + project-intel-cheatsheet.md) — deferred per Plan v5 §5, do NOT auto-commit
- 5 stale-looking worktrees with 130+ unmerged commits (see §5) — DO NOT --force without user confirmation
- `GH_TOKEN` env empty — must export before any `gh` subagent dispatch (FIX C1)
- Plan v6 v6.5 dispatch prompts contain `git checkout -b` step which is WRONG for `isolation: worktree` (framework auto-creates branch); v6.12 FIX C2 overrides with `git fetch origin master && git branch -m HEAD <name> && git rebase origin/master`
- ROADMAP.md:112 already lists Spec 215 as PLANNED — status update to PARTIAL after 215-C ships, COMPLETE after 215-F
- Wave 3 reviewer agent IDs (for replay if needed): pr-devils-advocate `aed48776176f4ddd7`, pr-process-auditor `a7f66e6bd765451c3`. Wave 1 IDs: claude-code-guide `aa68b5dd2d3a09820`, general-purpose web `a2fd868aeafe399eb`, pr-codebase-intel `a4c17846d70fbbd4d`. Wave 2: pr-scope-reviewer `a23cffb1b21dffbca`
