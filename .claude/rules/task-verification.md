---
globs: ["**/*.md"]
---

# Task Completion Verification

**Silently-complete tasks** — tasks marked completed without the code actually landing on master — cause quiet drift that survives compaction and poisons future plans. Task #17 ("PR-1 housekeeping — SUPABASE_URL guard + bridge URL extract") sat completed for weeks while GH #184 + #233 remained OPEN and the changes were never written. Discovered 2026-04-13 during an unrelated scope-check.

## Rules

- **Before `TaskUpdate(status=completed)` on any task that references a GH issue (`#NNN`)**: run `gh issue view NNN --json state` and verify `state == "CLOSED"` OR the code lives on master (`git log origin/master --oneline | rg "#NNN"` returns a merge commit).
- **If both conditions fail**: do NOT mark the task completed. Either (a) close the issue in the same operation if the PR is genuinely merged, or (b) keep the task `in_progress` and note the gap.
- **Reflection**: at every session's end, `TaskList | rg "#[0-9]+"` → re-verify each referenced issue is actually closed. Drift repair is cheaper here than in the next scope-check.

## Audit

Spec 211 (test-quality-audit will co-evolve with this): systematic scan of completed tasks' GH references vs reality. Run quarterly, or whenever compaction happens and a fresh session can't re-run the history.

## Related

- `.claude/rules/issue-triage.md` — severity classification
- `.claude/rules/review-findings.md` — review-finding-to-GH-issue workflow
- Auto-memory: `feedback_task_completion_verification.md`
