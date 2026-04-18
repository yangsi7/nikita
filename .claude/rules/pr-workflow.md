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
3. **Pre-push local-test gate (HARD GATE)** — before `git push` or `gh pr create`, run the full suite for every area the diff touches. Not "the tests for the new code." THE FULL SUITE — regressions in other files via shared imports/config/types/build are exactly what this gate catches. Minimum commands, union across touched areas:
   - `nikita/**`, `tests/**`, `supabase/migrations/**`, `scripts/**` → `uv run pytest -q` (or narrower `uv run pytest tests/<module>/ -q` if you are certain the diff is truly local; when in doubt, full suite)
   - `portal/**` → `(cd portal && npm run test -- --run && npm run lint && npm run build)`
   - CI-equivalent, not a subset. CI runs the full suite on every push; running it locally first is the cheap version of the round-trip.
   - Skip only if: (a) the change is docs-only (`*.md` outside `portal/src/`, `docs/**`, `specs/**` without spec.md touching implementation), (b) config-only files (`.github/**`, `.claude/**`, hooks) that have no test coverage. "No test file exists for my new file" is NOT a valid skip — see anti-rationalization table below.
   - Record pass/fail in the PR body under a `## Local tests` section.
4. `gh pr create --title "..." --body "..."`
5. `/qa-review --pr N` — auto-dispatch via Agent (subagent). Fix all findings, then dispatch a NEW review agent (fresh context). Repeat until the fresh review returns **0 findings across ALL severities** (0 blocking + 0 important + 0 nitpick). Never self-certify a fix — the fresh reviewer is the authority. Never prompt user for permission — this loop is mandatory. **Every dispatch MUST include `HARD CAP: 5 tool calls` + explicit changed-files list** (per `.claude/rules/parallel-agents.md` Subagent Dispatch Caps). PR #294 precedent: uncapped first dispatch ran 40 min and crashed with `API ConnectionRefused`; capped re-dispatch converged in seconds.
6. Squash merge ONLY after a fresh QA review returns absolute zero findings + CI green
7. `gh issue close N --comment "Fixed in PR #M"`
8. Post-merge verification (auto-dispatched subagent): smoke test the deployed change (curl probe, log sweep, or dogfood scenario as appropriate). Do not skip. Do not ask permission.
9. **Commit-hash verification** (mandatory after merge): run `git log origin/master --oneline -3` and confirm the PR's merge commit appears at the top. If the PR's GH status is "merged" but the commit is NOT on `origin/master`, STOP. Force-push wipes are silent and recoverable only via commit-hash audit. See PR #273 precedent (force-push wiped merged PR, recovered via #277). Also applicable to task-close operations: before `TaskUpdate(status=completed)` on any task referencing GH #NNN, verify `gh issue view NNN --json state` returns `"CLOSED"` OR `git log origin/master | rg "#NNN"` returns the merge commit. See `.claude/rules/task-verification.md`.

## Anti-Rationalization — Pre-Push Test Gate

| Rationalization | Response |
|---|---|
| "There's no test file for my new code, so there's nothing to run" | Wrong — run the *full suite* for the touched area. Regressions often land in OTHER files (shared types, build config, imports, globals). PR #329 (2026-04-18) shipped a new 1907-line page; author ran lint+build but skipped vitest; user had to prompt. Would have silently passed a stricter TS/import change that broke unrelated tests. |
| "Lint passed + build passed, same signal as tests" | No. Build catches type + parse errors. Unit tests catch behavioral regressions in shared modules. Both are required. |
| "The change is confined to one file" | Then the test run is fast — no reason to skip. `uv run pytest -q` runs the nikita suite in ~90 s. |
| "CI will catch it" | CI catches it but costs a round-trip, user-facing noise, and GH Actions minutes. User rule (feedback_compact_and_local_tests.md): run locally before push to not waste Actions. |
| "I'm in a worktree, tests might behave differently" | Worktree tests are identical; pytest/vitest resolve from the worktree root. If it fails locally it would fail on CI. |
| "`uv run pytest` is slow" | `-q` + scoped path is fast enough. Even a 2-min local run beats a failed CI round-trip. |

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
