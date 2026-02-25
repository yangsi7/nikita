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

**Current State** → Voice Agent Deployed (Jan 2026) - 99% Production Ready
**Remaining** → Portal polish (5% remaining)

## Critical References

- **Master Plan**: [../plans/master-plan.md](../plans/master-plan.md)
- **Root CLAUDE.md**: [../CLAUDE.md](../CLAUDE.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md) (v0.6.0 - System Audit & Context Enhancements)

## Project Status (Jan 2026) ✅ 99% COMPLETE

### Core Implementation
- ✅ **Text Agent**: 8 files, 156 tests (Pydantic AI + Claude Sonnet)
- ✅ **Telegram**: 7 files, 86 tests (deployed to Cloud Run)
- ✅ **Voice Agent**: 14 files, 186 tests (ElevenLabs Conversational AI 2.0)
- ✅ **Game Engine**: 514 tests (scoring, chapters, decay, vice, engagement)
- ✅ **Context Pipeline**: 50 tests (9-stage post-processing)
- ✅ **Configuration**: 89 tests (YAML + loaders)
- ✅ **Background Tasks**: pg_cron (5 jobs active)
- ⚠️ **Portal**: 85% complete (Admin UI done, Settings remaining)

### Test Status
- **1248+ tests passing**
- Voice agent: 186 tests
- E2E verification passed

### All 20 Specs Audited
| Spec | Status |
|------|--------|
| 001-020 | ✅ All PASS |

## Next Steps

- Portal polish (Spec 008 - 15% remaining)
- Production monitoring/alerting

→ See [../plans/master-plan.md](../plans/master-plan.md) Section 13
