# Memory Documentation Hub

Concise, diagram-first documentation optimized for AI agent context efficiency.

## Documentation Files

| File | Purpose |
|------|---------|
| [architecture.md](architecture.md) | System architecture, component hierarchy, data flow |
| [backend.md](backend.md) | FastAPI routes, database patterns, API design |
| [game-mechanics.md](game-mechanics.md) | Scoring formula, chapters, boss encounters, decay |
| [user-journeys.md](user-journeys.md) | Player flows from signup to victory |
| [integrations.md](integrations.md) | ElevenLabs, Graphiti, Telegram, Supabase config |

## Navigation

**Current State** → MVP Complete (Dec 2025) - All core features deployed
**Target Specs** → Voice agent (Phase 4) + Portal polish (Phase 5)

## Critical References

- **Master Plan**: [../plans/master-plan.md](../plans/master-plan.md)
- **Todo Tracking**: [../todos/master-todo.md](../todos/master-todo.md)
- **Root CLAUDE.md**: [../CLAUDE.md](../CLAUDE.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md) (v0.4.0 - MVP Complete)

## MVP Status (Dec 2025) ✅ COMPLETE

### Core Implementation
- ✅ **Text Agent**: 8 files, 156 tests (Pydantic AI + Claude Sonnet)
- ✅ **Telegram**: 7 files, 86 tests (deployed to Cloud Run)
- ✅ **Game Engine**: 514 tests (scoring, chapters, decay, vice, engagement)
- ✅ **Context Pipeline**: 50 tests (9-stage post-processing)
- ✅ **Configuration**: 89 tests (YAML + loaders)
- ✅ **Background Tasks**: pg_cron endpoints (decay, summary, cleanup)

### Test Status
- **1248 tests passing**, 18 skipped
- E2E verification passed (2025-12-18)

### All 14 Specs Audited
| Spec | Status |
|------|--------|
| 001-015 | ✅ All PASS |

## Next Steps

- **Phase 4**: Voice agent (ElevenLabs Conversational AI 2.0)
- **Phase 5**: Portal polish + Admin UI

→ See [../plans/master-plan.md](../plans/master-plan.md) Section 13
