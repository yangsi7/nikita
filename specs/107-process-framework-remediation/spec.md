# Spec 107: Process Framework Remediation

## Summary

Fix critical bugs and data inconsistencies introduced by the Process Framework Overhaul (commit `b1d2ebb`). Three hooks use GNU-only `grep -oP` that silently fails on macOS. ROADMAP.md has missing specs, duplicate rows, and incorrect counts. JSON output in hooks uses unsafe variable interpolation.

## Findings

### Critical (P0) — macOS Portability

| ID | File | Line | Issue |
|----|------|------|-------|
| C1 | validate-workflow.sh | 29 | `grep -oP` → blank spec number in GATE 0 error |
| C2 | roadmap-sync.sh | 23 | `grep -oP` → blank spec number in reminder |
| C3 | pre-compact.sh | 28 | `grep -oP` → active spec detection silently skipped |

**Fix**: Replace `grep -oP 'specs/\K[0-9]{3}'` with POSIX `sed -n 's|.*specs/\([0-9]\{3\}\).*|\1|p'`.

### High (P1) — ROADMAP.md Data

| ID | Issue | Fix |
|----|-------|-----|
| H1 | Specs 001, 002 missing from Feature Lines | Added to Domain 1 |
| H2 | Spec 065 unlabeled in Pre-SDD | Annotated as `production-hardening-2` |
| H3 | Specs 049, 050, 070 duplicated in Partial Artifacts | Removed from Partial Artifacts |
| H4 | Spec 106 in both Domain 4 and Pre-SDD | Removed from Pre-SDD |
| H5 | Pre-SDD count said 10, now 9 | Updated |

### Medium (P2) — JSON Safety

| ID | File | Issue | Fix |
|----|------|-------|-----|
| M1 | validate-workflow.sh:35-44 | Unquoted heredoc with `$SPEC_NUM` | `jq -n --arg` |
| M2 | session-start.sh:87-95 | `$CONTEXT_MESSAGE` raw in JSON | `jq -n --arg` |
| M3 | pre-compact.sh:47-55 | `$CONTEXT_PARTS` raw in JSON | `jq -n --arg` |
| M4 | roadmap-sync.sh:26-33 | `$SPEC_NUM` and `$ARTIFACT` in heredoc | `jq -n --arg` |

### Minor (P3)

| ID | File | Issue | Fix |
|----|------|-------|-----|
| M5 | session-start.sh:13 | `HEAD~5` fails on shallow repos | Fallback to `HEAD` |
| M6 | session-start.sh:25 | Naive `grep -c` inflates count | Unique `sort -u` count |

## Acceptance Criteria

1. All 3 hooks extract spec numbers correctly on macOS (BSD grep)
2. All 4 hooks produce valid JSON (passes `jq .`)
3. ROADMAP.md has 75 unique specs in Feature Lines, 76 total (with 065 pre-SDD)
4. No duplicate spec rows in Partial Artifacts section
5. No regressions in test suite

## Status

COMPLETE — All fixes applied and verified.

### Post-Review Remediation (PR #75)

4-expert review found 7 bugs. Fixed in follow-up commit:

| Bug | Severity | Fix |
|-----|----------|-----|
| B1 | CRITICAL | `pre-compact.sh` — removed invalid `hookEventName: "PreCompact"`, use `systemMessage` |
| B2 | CRITICAL | `pre-compact.sh` — anchored sed regex to branch patterns (`^feature/`, `^NNN-`) |
| B3 | HIGH | `pre-compact.sh` — removed `sed` pre-escaping (jq handles escaping) |
| B4 | HIGH | `session-start.sh` — removed extraneous `hookEventName: "SessionStart"` |
| B5 | MEDIUM | `ROADMAP.md` — fixed "73 complete" → "74 complete" to match frontmatter |
| B6 | MEDIUM | `session-start.sh` — `git diff HEAD` → `git log --name-only -5` for clean repos |
| B7 | MEDIUM | `session-start.sh` — added `tr -d '\n'` to `grep -c` output |

### PR #76 Code Review Remediation

Claude Code review found 8 issues + 2 minor observations. Fixed in follow-up commit:

| Bug | Severity | Fix |
|-----|----------|-----|
| R1 | BUG | `judgment.py:139` — player_context concatenated inside JSON example line (newline missing) |
| R2 | BUG | `tasks.py` — deprecated endpoints return 200 instead of HTTP 410 Gone |
| R3 | DEBT | `analyzer.py` — module-level mutable `_scoring_errors` counter replaced with per-event logging |
| R4 | STUB | `engine.py` — `_load_top_vices()` implemented using VicePreferenceRepository; `_load_open_threads()` documented as TODO |
| R5 | DEBT | `processor.py` — unnecessary `hasattr` guard removed (method exists on UserRepository) |
| R6 | BUG | `job_execution_repository.py` — `has_recent_execution` checks `started_at` instead of `completed_at` |
| R7 | MISLEADING | `constants.py` — GRACE_PERIODS/DECAY_RATES marked deprecated but `get_config()` API doesn't exist |
| R8 | HYGIENE | Unprocessed `docs-to-process/` file deleted |
| M1 | MINOR | `admin.py` — `import statistics` moved to module level |
| M2 | MINOR | `sw.js` — notification click uses notification data URL instead of hardcoded `/dashboard` |

### PR #76 Second Review Remediation

Second review identified 5 additional findings (2 Medium, 3 Low). Fixed:

| ID | Severity | Finding | Fix |
|----|----------|---------|-----|
| F1 | MEDIUM | `tasks.py` — `MAX_CONCURRENT_PIPELINES=10` defined but unused; all 50 conversations processed | Batch-slice `queued_ids[:MAX_CONCURRENT_PIPELINES]`, defer remainder to next cron cycle |
| F2 | MEDIUM | `processor.py` — N+1 query: per-user `increment_days_played` does SELECT+flush each | Added `bulk_increment_days_played()` to UserRepository (single UPDATE) |
| F3 | MEDIUM | Migration SQL files not committed to repo | Created `supabase/migrations/` with manifest + baseline schema |
| F4 | LOW | `admin.py` — `import statistics` between third-party imports | Moved to stdlib group per ruff isort |
| F5 | LOW | `skip.py` — `REPETITION_SIMILARITY_THRESHOLD` named "semantic" but uses character-level SequenceMatcher | Renamed to `REPETITION_STRING_SIMILARITY_THRESHOLD`, fixed docstrings |
