---
description: Enforce PR-based workflow — never commit to master directly
globs: ["**"]
---

# PR Workflow Enforcement

## Hard Rules
- NEVER push directly to master. Always create a feature branch first.
- NEVER merge a branch without creating a PR via `gh pr create`.
- NEVER merge a PR without running `/qa-review --pr N` and reaching 0 findings across ALL severities (0 blocking + 0 important + 0 nitpick) via a fresh external review.
- NEVER close a GH issue without referencing the PR that resolved it.

## Per-Change Workflow
1. `git checkout -b {type}/{issue}-{description}`
2. Implement with TDD (tests first)
3. `gh pr create --title "..." --body "..."`
4. `/qa-review --pr N` — auto-dispatch via Agent (subagent). Fix all findings, then dispatch a NEW review agent (fresh context). Repeat until the fresh review returns **0 findings across ALL severities** (0 blocking + 0 important + 0 nitpick). Never self-certify a fix — the fresh reviewer is the authority. Never prompt user for permission — this loop is mandatory.
5. Squash merge ONLY after a fresh QA review returns absolute zero findings + CI green
6. `gh issue close N --comment "Fixed in PR #M"`
7. Post-merge verification (auto-dispatched subagent): smoke test the deployed change (curl probe, log sweep, or dogfood scenario as appropriate). Do not skip. Do not ask permission.

## Sprint/Batch Exceptions
- Multiple issues MAY share a branch if tightly coupled (e.g., `test/146-147-boss-engagement`)
- Worktree agents commit to branches, orchestrator creates PRs
- Each PR still requires its own `/qa-review` pass

## Deployment
- Deploy to Cloud Run / Vercel only AFTER PR merged to master
- Never deploy from a feature branch
