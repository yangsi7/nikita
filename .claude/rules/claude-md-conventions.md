# CLAUDE.md Conventions

Module-scoped agent-context file conventions. Every CLAUDE.md repo-wide must follow this template.

## Section template (5 sections, in order)

```markdown
# <dir>/ — <short title>

## Purpose
What this module does. 1-3 sentences. No prose padding.

## Key Files
| File | Purpose |
|---|---|
| `path:line` | One-line behavior description |

(Or bullet list with file:line if a table is overkill.)

## Callers
Who imports/invokes this module. Bullet list with file:line per caller.

## Gotchas
Project-specific risks, smells, anti-patterns. file:line-cited bullets.
NOT generic platform platitudes.

## Navigation
Links to parent + sister modules + canonical homes (memory/*.md).

Last verified: YYYY-MM-DD
```

## Length caps

| Scope | Cap |
|---|---|
| Root `CLAUDE.md` | ≤250 lines |
| `.claude/CLAUDE.md` (toolkit) | ≤250 lines |
| `portal/CLAUDE.md` (portal root) | ≤250 lines |
| Module `CLAUDE.md` (everywhere else) | ≤150 lines |
| `.claude/rules/*.md` | ≤80 lines |

Documented exceptions in `audits/2026/20260503-memory-file-size-exceptions.md` (extended by W7b for content-density).

## Mandatory `/generate-claude-md` gate

ANY write to a CLAUDE.md or `.claude/rules/*.md` file MUST be authored by (or pass through) the `/generate-claude-md` skill. Do NOT hand-craft these files in arbitrary edits — the skill enforces the template, length cap, and file:line-citation discipline. Drift over 3+ files is a cleanup-PR signal.

## File:line citation discipline

- Every claim about behavior MUST cite `path:line` (or `path:line-line` range).
- Use `rg` or `wc -l` to verify line ranges before commit.
- Stale citations are a drift signal; surface in a `Last verified:` audit doc.

## Drift markers (auto-flag in audits)

- Stage-count discrepancy (e.g., "10 stages" vs `STAGE_DEFINITIONS` length).
- Status-line mismatch ("All specs complete" while ROADMAP shows 4 active).
- Stale `Last verified:` line (>3 months old in actively-edited area).
- Reference to deleted classes/files (e.g., `PostProcessor`, `boss_encounter.py`).
- Reference to archived doc dirs (e.g., `docs/knowledge-transfer/`).

## Lazy-load semantics

CLAUDE.md is loaded ONLY when the agent reads a file in that dir. Use `@path` import syntax in root `CLAUDE.md` to pull rules from `.claude/rules/`.

## Precedent

- W5 (PR #500): 5 portal-app CLAUDE.mds shipped using this template.
- W7a (PR #502): audit of 18 CLAUDE.mds against template.
- W7b-1..-4 (PRs #503/#504/#506/#507): backfilled all module CLAUDE.mds.

## Reference

- Sister rules: `docs-structure.md`, `archive-policy.md`, `doc-lifecycle.md`
- `/generate-claude-md` skill (search via `Skill` tool)
