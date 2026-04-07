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
- If a sub-agent is stuck (no progress after 2 tool calls), kill and retry with simplified prompt

## QA & PR Review Context
- Before reading diffs or running tests, confirm branch + worktree
- Cross-reference `git log` to verify changes belong to this PR (not contamination from parallel work)

## Batch Checkpointing
- For multi-item batch work, save progress after EACH item to `./batch-progress.json`
- Commit per-item if applicable — rate limits only cost one retry, not full restart
