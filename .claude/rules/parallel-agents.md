---
description: Prevent worktree cross-contamination and sub-agent planning loops
globs: ["**"]
---

# Parallel Agent & Worktree Safety

## Before Spawning Worktree Agents
- State the target branch name in the agent prompt
- After agent completes, verify branch: `git branch --show-current` + `git rev-parse --show-toplevel`
- Budget 5-10 min for branch untangling after parallel runs

## Sub-Agent Execution Constraints
- Give sub-agents action-oriented prompts with explicit deliverables
- Never let agents sit in planning mode — if blocked, return partial results with "BLOCKED:" prefix
- If a sub-agent is stuck (no progress after 5 tool calls), kill and retry with simplified prompt

## QA & PR Review Context
- Before reading diffs or running tests, confirm branch + worktree
- Cross-reference `git log` to verify changes belong to this PR (not contamination from parallel work)

## Batch Checkpointing
- For multi-item batch work, save progress after EACH item to `$CLAUDE_PROJECT_DIR/batch-progress.json`
- Commit per-item if applicable — rate limits only cost one retry, not full restart

## Subagent Dispatch Caps (mandatory)

Every Agent-tool dispatch (reviewer, researcher, explorer) MUST include in its prompt:

1. **Hard tool-call cap**: `HARD CAP: <N> tool calls max. Stop and report partial findings if exceeded.`
   - QA review: 5 (review only, no fix)
   - Codebase research: 10
   - Deep exploration: 15
2. **Explicit scope clause**: `Review/explore ONLY these files: X, Y, Z` — no scope creep allowed
3. **Defined exit criterion**: `Report CLEAN: 0 findings` OR `Return first 3 candidates` OR `Stop after <N> tool calls` — no open-ended

**Why mandatory**: PR #294 (2026-04-16) — first QA-review subagent dispatched without caps ran 87 tool calls / 40 min then crashed with `API ConnectionRefused`. Re-dispatched with `5 tool calls / 3 files / "report CLEAN or N findings"` cap, converged in seconds. The cost of caps is two prompt lines; the cost of uncapped crash is one full re-dispatch + lost context.

Enforcement: orchestrator must reject (not dispatch) any prompt missing all 3 elements. See auto-memory `feedback_subagent_dispatch_caps.md` (`~/.claude/projects/-Users-yangsim-Nanoleq-sideProjects-nikita/memory/`) for precedent.
