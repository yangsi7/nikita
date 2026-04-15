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
8. **Commit-hash verification** (mandatory after merge): run `git log origin/master --oneline -3` and confirm the PR's merge commit appears at the top. If the PR's GH status is "merged" but the commit is NOT on `origin/master`, STOP. Force-push wipes are silent and recoverable only via commit-hash audit. See PR #273 precedent (force-push wiped merged PR, recovered via #277). Also applicable to task-close operations: before `TaskUpdate(status=completed)` on any task referencing GH #NNN, verify `gh issue view NNN --json state` returns `"CLOSED"` OR `git log origin/master | rg "#NNN"` returns the merge commit. See `.claude/rules/task-verification.md`.

## Orchestrator Grep-Verify Gate (critical, before dispatching QA reviewer)

After every implementor-subagent dispatch, BEFORE sending the branch to `/qa-review`, the orchestrator MUST grep production code to verify the implementor's "fix complete" claim. Implementor reports are NOT reliable — PR #283 iter-2 saw a hallucinated "generate_preview() now calls get_envelope" report survive 2 QA iterations because mock-driven tests lied. Fresh-context reviewers can also produce phantom findings from stale checkouts (PR #283 iter-6). Apply the gate both directions:

- After implementor claim → `grep -n "<claimed pattern>" <production file>` must match. If not → redispatch implementor with the contradiction, do NOT pass to reviewer.
- After reviewer finding → `git fetch origin && git show origin/<branch>:<file> | grep "<flagged pattern>"` must confirm. If not → treat as phantom, do NOT dispatch fix.

Full rationale + precedent: `~/.claude/projects/.../memory/feedback_implementor_self_report_verification.md`.

## Sprint/Batch Exceptions
- Multiple issues MAY share a branch if tightly coupled (e.g., `test/146-147-boss-engagement`)
- Worktree agents commit to branches, orchestrator creates PRs
- Each PR still requires its own `/qa-review` pass

## Deployment
- Deploy to Cloud Run / Vercel only AFTER PR merged to master
- Never deploy from a feature branch
