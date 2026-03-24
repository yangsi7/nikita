---
description: Enforce PR-based workflow — never commit to master directly
globs: ["**"]
---

# PR Workflow Enforcement

## Hard Rules
- NEVER push directly to master. Always create a feature branch first.
- NEVER merge a branch without creating a PR via `gh pr create`.
- NEVER merge a PR without running `/qa-review --pr N` and reaching 0 blocking + 0 important issues.
- NEVER close a GH issue without referencing the PR that resolved it.

## Per-Change Workflow
1. `git checkout -b {type}/{issue}-{description}`
2. Implement with TDD (tests first)
3. `gh pr create --title "..." --body "..."`
4. `/qa-review --pr N` — fix issues, re-review, repeat until PASS
5. Squash merge after QA PASS + CI green
6. `gh issue close N --comment "Fixed in PR #M"`

## Sprint/Batch Exceptions
- Multiple issues MAY share a branch if tightly coupled (e.g., `test/146-147-boss-engagement`)
- Worktree agents commit to branches, orchestrator creates PRs
- Each PR still requires its own `/qa-review` pass

## Deployment
- Deploy to Cloud Run / Vercel only AFTER PR merged to master
- Never deploy from a feature branch
