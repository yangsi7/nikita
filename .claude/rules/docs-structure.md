# Documentation Structure

Top-level documentation taxonomy for the nikita repo. Codifies conventions established by the W4-W11 doc-estate restructure (see `audits/2026/20260505-kt-migration-w4-verification-*.md` and `audits/2026/20260505-claude-md-normalization-audit.md`).

## Directory purposes

| Dir | Purpose | Canonical content |
|---|---|---|
| `specs/` | Per-spec SDD artifacts (spec.md, plan.md, tasks.md, audit-report.md). One subdir per spec. | All NNN-feature/ specs. Index in `specs/INDEX.md`. |
| `memory/` | Living canonical docs (lifecycle: living). Topics: architecture, backend, game-mechanics, user-journeys, integrations, memory-system-architecture, product. | Single source of truth per topic per `cleanup-canonical-decisions.txt`. |
| `docs/` | Reference, narrative, guides, content, models, diagrams. NOT canonical for project-state topics. | Index in `docs/INDEX.md`. Concept glossary at `docs/CONCEPTS.md`. |
| `audits/` | Audit reports + ADR-shaped decisions. By-year subdirs. | Index in `audits/INDEX.md`. |
| `plans/` | Strategic / cross-spec plans. Will retire (W10) when only orphan content remains. | `master-plan.md` for now. |
| `docs-to-process/` | Session-artifact queue. Drafts drained per-wave PR or via SDD spec when scope warrants. | Empty on master post-Wave-3B; session-local drafts only. |
| `.claude/` | Project-scoped Claude Code config (rules, skills, agents, commands). | See `.claude/CLAUDE.md`. |
| `.sdd/` | SDD workflow state (active spec, phase). | Not for human reading; managed by SDD skill. |
| `nikita/`, `portal/`, `tests/`, `supabase/`, `scripts/` | Code, not docs. | — |

## Reachability rule

Every doc must be reachable from root `CLAUDE.md` Navigation → `docs/INDEX.md` (or `memory/README.md`, or `specs/INDEX.md`, or `audits/INDEX.md`) within 2 hops. Drift detected by `rg -L "<doc-path>" CLAUDE.md docs/INDEX.md memory/README.md specs/INDEX.md audits/INDEX.md`.

## Naming conventions

| Pattern | When | Example |
|---|---|---|
| `{YYYYMMDD}-{type}-{slug}.md` | Dated drafts (audits, briefs, walk reports) | `20260505-kt-migration-w4-verification-architecture.md` |
| `{topic}.md` lowercase | Living docs (memory/) | `memory/architecture.md` |
| `INDEX.md` | Top-level navigation hub for a container dir | `docs/INDEX.md` |
| `README.md` | Narrative hub (vs INDEX which is structured nav) | `memory/README.md` |
| `CLAUDE.md` | Module-scoped agent context | `nikita/api/CLAUDE.md` |
| `ADR-NNN-{slug}.md` | Architecture Decision Record | `~/.claude/ecosystem-spec/decisions/ADR-006-vendor-and-extend.md` |

## Anti-rationalization

| Rationalization | Response |
|---|---|
| "I'll just append a new doc to docs/" | Not without an INDEX.md entry. Reachability rule applies. |
| "The KT files have rich content; let's keep them as-is" | W4 code-verification gate. KT files were Neo4j-era; archived. |
| "Two homes are fine; readers can pick" | Single source of truth per topic per `cleanup-canonical-decisions.txt`. Pick one, link the other. |
| "I'll start a new docs subdir for this" | Map it to existing dir purposes first. Brand-new subdirs need an explicit decision (audit doc or PR-body justification). |
| "I'll skip the file:line cite, the prose is clear" | Drift signal. Cite or it's hearsay. |

## Precedent

- Wave 2A (2026-05-03) `cleanup-canonical-decisions.txt` — pair-by-pair canonical winner.
- W4 (2026-05-05) — code-verification gate; consolidated all 5 to memory/.
- W6 (2026-05-05) — `docs/INDEX.md` + `docs/CONCEPTS.md` + `audits/INDEX.md`.
- W7b (2026-05-05) — module CLAUDE.md normalization.

## Reference

- `cleanup-canonical-decisions.txt` (root)
- `docs/INDEX.md`, `docs/CONCEPTS.md`, `audits/INDEX.md`, `memory/README.md`, `specs/INDEX.md`
- Sister rules: `claude-md-conventions.md`, `archive-policy.md`, `doc-lifecycle.md`
