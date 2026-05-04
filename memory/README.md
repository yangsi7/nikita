# Memory Documentation Hub

Concise documentation hub for `memory/` canonical living docs.

> Per `cleanup-canonical-decisions.txt` (root, W4 2026-05-05): all canonical doc topics live in `memory/`. The former `docs/knowledge-transfer/` was archived to `docs/.archive/knowledge-transfer-2026-03-pgvector-deprecated/` after W4 code-verification gate confirmed the KT files contained Neo4j/Graphiti staleness, wrong file paths/class names, and outdated method signatures (audits at `audits/2026/20260505-kt-migration-w4-verification-*.md`).

## Canonical files in this directory

| File | Topic | Audience |
|------|-------|----------|
| [architecture.md](architecture.md) | System architecture, 11-stage pipeline, memory subsystem, agents | Anyone needing the system map |
| [backend.md](backend.md) | FastAPI routes, database patterns, API design | Backend engineers, API consumers |
| [game-mechanics.md](game-mechanics.md) | Scoring (4 metrics), chapters (5 + bosses), decay (yaml-driven), vices (8 categories) | Game-engine engineers, designers |
| [user-journeys.md](user-journeys.md) | Onboarding flows, entry points (Telegram/Voice/Portal), pipeline invocation reality | Product, UX, integration engineers |
| [integrations.md](integrations.md) | ElevenLabs, Telegram, Supabase config (code-side + dashboard-side) | Anyone wiring an external service |
| [memory-system-architecture.md](memory-system-architecture.md) | pgVector storage layer, retrieval, dedup, eviction (Spec 042+) | Engineers touching `nikita/memory/` |
| [product.md](product.md) | Product positioning + decision context | Product, PM |

## Update rules

- One source of truth per topic. The Navigation table in root `CLAUDE.md` always points to the current canonical home (`memory/<topic>.md`).
- Files MUST cite real file paths (`nikita/<module>/<file>.py:<line>`). Verify with `rg` before merging.
- ≤500 lines per file. Documented exceptions live in `~/.claude/ecosystem-spec/decisions/ADR-NNN-memory-file-size-exceptions.md` (Wave 2C).
- Last edited: 2026-05-05 (W4 KT migration; consolidated all 5 canonical topics into `memory/`).

## Cross-references

- Master plan: [../plans/master-plan.md](../plans/master-plan.md)
- Project roadmap: [../ROADMAP.md](../ROADMAP.md)
- Per-spec status: [../specs/INDEX.md](../specs/INDEX.md)
- Game overview narrative: [../docs/how-nikita-works.md](../docs/how-nikita-works.md)
- Root CLAUDE.md: [../CLAUDE.md](../CLAUDE.md)
- KT archive (deprecated, do not consult): [../docs/.archive/knowledge-transfer-2026-03-pgvector-deprecated/](../docs/.archive/knowledge-transfer-2026-03-pgvector-deprecated/)
