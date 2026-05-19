# Documentation Lifecycle

Lifecycle states + cadence rules for all project documentation.

## Lifecycle marker (frontmatter)

Every doc MUST carry a `lifecycle:` marker in YAML frontmatter:

```yaml
---
title: <Document Title>
lifecycle: living | frozen | superseded | archived
---
```

| State | Meaning | Maintenance |
|---|---|---|
| `living` | Authoritative, kept current. | Update on every relevant change. |
| `frozen` | Snapshot; no further edits. | Read-only; archive when context lost. |
| `superseded` | Replaced by `successor:` link. | Banner pointing at successor; do NOT update. |
| `archived` | In `docs/.archive/`. | DO NOT CONSULT. |

## Session artifacts → `docs-to-process/`

Session-generated drafts (research, analysis, decisions, patterns, bugs, integrations) write to:
```
docs-to-process/{YYYYMMDD}-{type}-{slug}.md
```
Types: `research`, `analysis`, `decision`, `pattern`, `bug`, `integration`, `audit`, `walk`.

## Date-stamping convention

| Pattern | When |
|---|---|
| `YYYYMMDD-` prefix | Dated drafts; ephemeral or wave-specific |
| No date prefix | Living canonical docs |

## Drain cadence (manual, no auto-skill)

`docs-to-process/` is drained MANUALLY per-wave PR. There is NO `/streamline-docs` auto-consolidation skill (purged in WPRE 2026-05-05). Each wave's PR explicitly enumerates which drafts it processes.

## Update vs new doc decision

```
Is this a NEW topic with no canonical home? → new doc in correct dir per docs-structure.md
Is this an UPDATE to an existing canonical? → edit in place
Is this a SNAPSHOT for a specific moment? → docs-to-process/{YYYYMMDD}-{type}-{slug}.md
Is this a DECISION? → audits/{YYYY}/{YYYYMMDD}-decision-{slug}.md or ADR-NNN.md
```

## CONCEPTS.md auto-refresh trigger

When a spec adds/modifies a concept, the matching `docs/CONCEPTS.md` row MUST be updated in the same PR. `/roadmap sync` post-spec-edit will surface drift if missed.

## Anti-pattern: docs duplicating ROADMAP/CHANGELOG/git-log

Do NOT write narrative docs that duplicate machine-derivable state. Specifically:
- ROADMAP.md is the spec-status source. Don't write per-spec status lists elsewhere.
- `git log` is the change history. Don't write CHANGELOG-style narratives in module CLAUDE.mds.
- ADR/audit docs are decision history. Don't repeat decisions in module CLAUDE.mds.

## Anti-rationalization

| Rationalization | Response |
|---|---|
| "I'll skip the lifecycle marker; it's obvious" | Frontmatter is parseable; prose isn't. Add the marker. |
| "Just append a session artifact to memory/" | No. `docs-to-process/` first. Drain in a wave PR. |
| "I'll leave the date-prefix off; it's living" | Unless it's actually living, date it. |
| "Living and frozen are the same" | Frozen = stop touching. Living = touch when relevant. |
| "ROADMAP is wrong, I'll write the truth in this doc" | Fix ROADMAP. Don't fork the truth. |

## Reference

- Sister rules: `docs-structure.md`, `claude-md-conventions.md`, `archive-policy.md`
- `cleanup-canonical-decisions.txt` (root)
- `docs/INDEX.md`, `audits/INDEX.md`
