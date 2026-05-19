# Spec 211 — Task Ledger Truth Audit

**Status**: PLANNED
**Registered**: 2026-04-13
**Triggered by**: PR-A of GH #201 sprint (PR #253) — discovered Task #17 was marked completed weeks prior while GH #184 + #233 remained OPEN and the code was never written.

## Problem

"Silently-complete tasks": tasks marked `completed` in the task list without the corresponding code landing on master. Survives compaction via session summaries and poisons downstream plans — PR-3 (GH #201) nearly built on a lie because the post-compaction handoff encoded the false state.

## Scope

Systematic audit of the completed-task ledger vs reality.

**Audit tasks:**
- Parse all completed tasks from the task list (`TaskList`) for GH issue references (`#NNN` in subject/description).
- For each match, run `gh issue view NNN --json state`.
- Cross-reference `git log origin/master --oneline | rg "#NNN"` for a merge commit that claims closure.
- Flag drift: task=completed AND (issue OPEN AND no merge commit).

**Remediation:**
- For each flagged task, create a remediation issue or reopen the task.
- Optional: automate via a hook that prompts before `TaskUpdate(status=completed)` on `#NNN`-referencing tasks.
- Extend `.claude/rules/task-verification.md` (already seeded by PR-B's first commit) with scope/priority guidance.

**Out of scope:**
- Fixing the individual drifted items (one per reopened task).
- Historical archeology — only current task state matters.

## Deliverables

- Per-session drift report (tasks vs issues).
- Optional: pre-complete hook (`.claude/hooks/task-verify.sh`) that runs the two checks before allowing `completed` status.

## Budget

1 PR. Parallel-safe with Spec 210.

## Dependencies

None (pure quality/process work).

## References

- `.claude/rules/task-verification.md` (seeded by PR-B first commit)
- Auto-memory: `feedback_task_completion_verification.md`
- Paired with Spec 210 (test-quality-audit): Spec 210 = fictitious coverage, Spec 211 = fictitious completion.

## Next Step

Scope via `/feature 211-task-ledger-truth-audit` in a dedicated session. Not urgent.
