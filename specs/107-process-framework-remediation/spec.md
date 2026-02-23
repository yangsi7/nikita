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
