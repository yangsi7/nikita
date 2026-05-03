# Memory Documentation Hub

Concise documentation hub for `memory/` canonical living docs.

> Per Wave 2A `cleanup-canonical-decisions.txt` (root): the project keeps two doc homes side-by-side. Topics here are the ones for which `memory/` is canonical. `docs/knowledge-transfer/` owns the rest. Do not duplicate; update one source per topic.

## Canonical files in this directory

| File | Topic | Audience |
|------|-------|----------|
| [backend.md](backend.md) | FastAPI routes, database patterns, API design | Backend engineers, API consumers |
| [integrations.md](integrations.md) | ElevenLabs, Telegram, Supabase config (code-side + dashboard-side) | Anyone wiring an external service |
| [memory-system-architecture.md](memory-system-architecture.md) | pgVector storage layer, retrieval, dedup, eviction (Spec 042+) | Engineers touching `nikita/memory/` |

## Other living docs

The remaining canonical topics live at `docs/knowledge-transfer/`:

- `PROJECT_OVERVIEW.md` (system architecture)
- `ARCHITECTURE_ALTERNATIVES.md`
- `GAME_ENGINE_MECHANICS.md` (scoring, chapters, decay, vices)
- `USER_JOURNEY.md`

The remaining 4 historical files in `memory/` (`architecture.md`, `game-mechanics.md`, `user-journeys.md`, `product.md`) are **superseded** by their `docs/knowledge-transfer/` counterparts; kept until a follow-up archive sweep retires them.

## Update rules

- One source of truth per topic. The Navigation table in root `CLAUDE.md` always points to the current canonical home.
- Files MUST cite real file paths (`nikita/<module>/<file>.py:<line>`). Verify with `rg` before merging.
- ≤500 lines per file. Documented exceptions live in `~/.claude/ecosystem-spec/decisions/ADR-NNN-memory-file-size-exceptions.md` (Wave 2C).
- Last edited: 2026-05-03 (Wave 2B doc-cleanup; rewrote stale Jan 2026 status banner).

## Cross-references

- Master plan: [../plans/master-plan.md](../plans/master-plan.md)
- Project roadmap: [../ROADMAP.md](../ROADMAP.md)
- Per-spec status: [../specs/INDEX.md](../specs/INDEX.md)
- Game overview narrative: [../docs/how-nikita-works.md](../docs/how-nikita-works.md)
- Root CLAUDE.md: [../CLAUDE.md](../CLAUDE.md)
