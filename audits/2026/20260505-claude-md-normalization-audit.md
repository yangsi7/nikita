# CLAUDE.md Normalization Audit (W7a)

**Date**: 2026-05-05
**Wave**: W7a (audit-only PR; W7b batches fix per file)
**Auditor**: `pr-codebase-intel` subagent (HARD CAP 20, read-only)
**Scope**: 18 CLAUDE.md files repo-wide (excluding `node_modules/`, `.archive/`, `.git/`)
**Method**: per-file template check + KT-ref grep + spot-check file:line citations + line-count check

## Per-file table

| File | Lines | Purpose | KeyFiles | Callers | Gotchas | Navigation | KT-refs | Stale-cite | Last-verified | Action |
|---|---|---|---|---|---|---|---|---|---|---|
| `./CLAUDE.md` | 101 | YES | YES | n/a | n/a | YES | 0 (only archival mention) | OK | NO | OK as root (root exception) |
| `./.claude/CLAUDE.md` | 141 | n/a (toolkit) | n/a | n/a | YES | n/a | **1 LIVE** at L100 (lists `docs/knowledge-transfer/` as canonical home) | n/a | NO | **KT-PURGE** — contradicts root CLAUDE.md post-W4 |
| `./portal/CLAUDE.md` | 84 | YES | YES (Architecture tree) | NO | NO | NO (Documentation links) | 0 | OK | NO | NORMALIZE — add Callers/Gotchas/Navigation sections |
| `./portal/src/app/admin/prompts/CLAUDE.md` | 36 | YES | YES | YES | YES | YES | 0 | OK | NO | NORMALIZE — missing `Last verified:` |
| `./portal/src/app/admin/research-lab/CLAUDE.md` | 34 | YES | YES | YES | YES | YES | 0 | OK | NO | NORMALIZE — missing `Last verified:` |
| `./portal/src/app/admin/users/CLAUDE.md` | 35 | YES | YES | YES | YES | YES | 0 | UNVERIFIED — `portal.py:126,477,513` not spot-checked | NO | NORMALIZE — missing `Last verified:` |
| `./portal/src/app/dashboard/nikita/CLAUDE.md` | 42 | YES | YES | YES | YES | YES | 0 | OK | NO | NORMALIZE — missing `Last verified:` |
| `./portal/src/app/login/CLAUDE.md` | 36 | YES | YES | YES | YES | YES | 0 | OK | NO | NORMALIZE — missing `Last verified:` |
| `./nikita/CLAUDE.md` | 83 | YES | YES | NO | NO | NO (Architecture/Status sections) | 0 | UNVERIFIED — `user.py:19-110` not spot-checked | NO | NORMALIZE — missing Callers/Gotchas/Navigation |
| `./nikita/agents/voice/CLAUDE.md` | 143 | YES | YES (Module Structure) | NO | NO | YES (Related) | 0 | OK | NO | NORMALIZE — missing Callers/Gotchas; near 150-line cap |
| `./nikita/api/CLAUDE.md` | 116 | YES | YES (Architecture tree) | NO | NO | YES (Documentation) | 0 | OK | NO | NORMALIZE — missing Callers/Gotchas |
| `./nikita/context/CLAUDE.md` | 177 | YES (LEGACY-gated) | YES | NO | NO | YES (Related Files) | 0 | **YES** — teaches dead PostProcessor/stage-classes/TemplateGenerator (W4 audit confirms classes deleted) | NO | **LINE-CITE-STALE + NORMALIZE** — exceeds 150-line cap; bulk-prune to ~25 lines |
| `./nikita/db/CLAUDE.md` | 141 | YES | YES (tree) | NO | NO | YES (Documentation) | 0 | UNVERIFIED — `user.py:19-110, :112-167, :169-207` not spot-checked | NO | NORMALIZE — missing Callers/Gotchas |
| `./nikita/engine/CLAUDE.md` | 144 | YES | YES (tree) | NO | NO | YES (Documentation) | 0 | UNVERIFIED — `constants.py:51-57, :60-110` not spot-checked | NO | NORMALIZE — missing Callers/Gotchas |
| `./nikita/engine/vice/CLAUDE.md` | 128 | YES | YES (tree) | NO | NO | NO (only Tests block) | 0 | OK | NO | NORMALIZE — missing Callers/Gotchas/Navigation |
| `./nikita/memory/CLAUDE.md` | 163 | YES | YES (tree) | NO | NO | YES (Documentation) | 0 | OK | NO | NORMALIZE — **>150 lines** + missing Callers/Gotchas |
| `./nikita/onboarding/CLAUDE.md` | 83 | YES | YES (table) | NO | NO | YES (Related) | 0 | OK | NO | NORMALIZE — missing Callers/Gotchas |
| `./nikita/pipeline/CLAUDE.md` | 68 | YES | YES (tree) | NO | NO | YES (Documentation) | 0 | OK | NO | NORMALIZE — missing Callers/Gotchas |

**Action codes**:
- **OK**: clean per template (or root/portal-root exception).
- **NORMALIZE**: missing sections, drift refs, or no `Last verified:` line — W7b batch fix.
- **KT-PURGE**: contains live `docs/knowledge-transfer/*` refs (stale post-W4 archive).
- **LINE-CITE-STALE**: at least one file:line ref likely stale or teaches deleted concepts.

## Top 5 normalization priorities (W7b ordering)

### Priority 1 — `./nikita/context/CLAUDE.md` (LINE-CITE-STALE + NORMALIZE)

177 lines, over the 150-line module cap. Teaches the deleted `PostProcessor` / stage-classes / `TemplateGenerator` API in the body despite a LEGACY header banner. W4 KT-verification confirmed these classes do NOT exist — they were the pre-Spec-042 framing.

**Action (W7b batch 1)**: bulk-prune to ~25 lines. Keep:
- Legacy banner header
- Two surviving files: `session_detector.py`, `validation.py`
- Pointer to `nikita/pipeline/CLAUDE.md` (current canonical)
- Drop the body teaching `PostProcessor`/stage-classes/`TemplateGenerator` API.

### Priority 2 — `./.claude/CLAUDE.md` line 100 (KT-PURGE)

Line 100 lists `docs/knowledge-transfer/` as canonical home for `PROJECT_OVERVIEW.md` etc. Contradicts root `CLAUDE.md` line 100 which states W4 archived that directory. Single-line fix.

**Action (W7b batch 1)**: replace with `memory/<topic>.md` references.

### Priority 3 — W5 portal-app sub-CLAUDE.mds (5 files, all 34-42 lines)

`portal/src/app/{admin/prompts,admin/research-lab,admin/users,dashboard/nikita,login}/CLAUDE.md`. Already conform to the 5-section template. Only missing `Last verified: YYYY-MM-DD` line.

**Action (W7b batch 2)**: bulk-add `Last verified: 2026-05-05` to each.

### Priority 4 — Backend module CLAUDE.mds missing Callers/Gotchas (8-9 files)

`nikita/CLAUDE.md`, `nikita/agents/voice/CLAUDE.md`, `nikita/api/CLAUDE.md`, `nikita/db/CLAUDE.md`, `nikita/engine/CLAUDE.md`, `nikita/engine/vice/CLAUDE.md`, `nikita/memory/CLAUDE.md`, `nikita/onboarding/CLAUDE.md`, `nikita/pipeline/CLAUDE.md`. These have Purpose + Key Files + (often) Navigation but no Callers/Gotchas sections. Some embed gotcha-equivalent content in "Key Patterns" / "Configuration" / "Status" but not under canonical headings.

**Action (W7b batches 3-4, ~5 files per batch)**: add Callers (importer modules) + Gotchas sections per the W5 template. `/generate-claude-md` gate per file.

### Priority 5 — `./nikita/memory/CLAUDE.md` (163 lines)

Exceeds 150-line module cap. Some schema/integration/dependency code blocks could be trimmed or moved to `memory/integrations.md` (already cross-referenced).

**Action (W7b batch 4 or follow-up)**: trim to ≤150 lines without losing substantive content.

## W7b batch plan

| Batch | Files | Est. lines |
|---|---|---|
| **W7b-1** (priority 1+2) | `nikita/context/CLAUDE.md` (bulk-prune), `.claude/CLAUDE.md` (KT-purge) | ~150 |
| **W7b-2** (priority 3) | 5 portal-app sub-CLAUDE.mds (`Last verified:` line) | ~25 |
| **W7b-3** (priority 4 part 1) | `nikita/CLAUDE.md`, `nikita/agents/voice/CLAUDE.md`, `nikita/api/CLAUDE.md`, `nikita/db/CLAUDE.md`, `nikita/engine/CLAUDE.md` | ~350 |
| **W7b-4** (priority 4 part 2 + 5) | `nikita/engine/vice/CLAUDE.md`, `nikita/memory/CLAUDE.md` (trim + normalize), `nikita/onboarding/CLAUDE.md`, `nikita/pipeline/CLAUDE.md`, `portal/CLAUDE.md` | ~350 |

Each batch ≤400 lines per `.claude/rules/pr-workflow.md`. Sequential merges.

## Verification (post-W7b cascade)

```bash
# All CLAUDE.md have all 5 sections (Purpose / Key Files / Callers / Gotchas / Navigation)
for f in $(find . -name CLAUDE.md -not -path "*/node_modules/*" -not -path "*/.archive/*" -not -path "*/.git/*"); do
  for s in "## Purpose" "## Key Files" "## Callers" "## Gotchas" "## Navigation"; do
    grep -q "$s" "$f" || echo "MISSING $s in $f"
  done
done   # → 0 lines

# All have Last verified: line
rg -L "Last verified:" $(find . -name CLAUDE.md ...) | wc -l   # → 0

# No live KT refs (excluding archive + audit reports)
rg "docs/knowledge-transfer/" $(find . -name CLAUDE.md ...) | rg -v ".archive/"   # → 0

# Module-level files ≤150 lines (root + .claude/ + portal/ exceptions)
for f in $(find . -name CLAUDE.md -not -path "*/.archive/*" -not -path "*/.git/*" -not -path "*/node_modules/*"); do
  case "$f" in ./CLAUDE.md|./.claude/CLAUDE.md|./portal/CLAUDE.md) continue ;; esac
  l=$(wc -l <"$f")
  [ "$l" -gt 150 ] && echo "$l $f"
done   # → 0
```

## Constraints applied

- HARD CAP 20 tool calls (subagent dispatch).
- Read each CLAUDE.md once; spot-check at most 1 citation per file (skipped some to stay in budget — flagged UNVERIFIED).
- No file mutations (audit-only PR per W7a).
