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

**Current State** → What exists now (Phase 1 complete: 39 Python files)
**Target Specs** → What remains to implement (Phases 2-5 from plan)

## Critical References

- **Master Plan**: [../plans/master-plan.md](../plans/master-plan.md)
- **Todo Tracking**: [../todos/master-todo.md](../todos/master-todo.md)
- **Root CLAUDE.md**: [../CLAUDE.md](../CLAUDE.md)

## Phase 1 Status (Complete)

- ✅ Project structure (39 Python files)
- ✅ Configuration (Supabase, Neo4j Aura, Anthropic, ElevenLabs)
- ✅ Database models (User, UserMetrics, UserVicePreference, Conversation, ScoreHistory, DailySummary)
- ✅ Game constants (CHAPTERS, BOSS_THRESHOLDS, DECAY_RATES, CHAPTER_BEHAVIORS)
- ✅ Memory client (NikitaMemory class with Graphiti/Neo4j Aura)
- ✅ API skeleton (FastAPI with route stubs)

## Next Steps (Phases 2-5)

→ See [../plans/master-plan.md](../plans/master-plan.md) Section 13
