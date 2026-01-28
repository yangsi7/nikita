# nikita/ Package Overview

## Purpose

Core application package for Nikita: Don't Get Dumped - AI girlfriend simulation game.

## Module Structure

| Module | Purpose | Status |
|--------|---------|--------|
| `config/` | Settings, environment config, YAML loaders | ✅ Complete (89 tests) |
| `db/` | Database models, repositories, migrations | ✅ Complete (7 repos, 8 migrations) |
| `engine/scoring/` | Scoring engine (4 metrics, deltas) | ✅ Complete (60 tests) |
| `engine/engagement/` | Engagement state machine (6 states) | ✅ Complete (179 tests) |
| `engine/decay/` | Decay calculator, processor | ✅ Complete (44 tests) |
| `engine/chapters/` | Chapter state machine, boss encounters | ✅ Complete (142 tests) |
| `engine/vice/` | Vice personalization | ✅ Complete (70 tests) |
| `memory/` | Graphiti + Neo4j Aura knowledge graphs | ✅ Complete |
| `agents/text/` | Pydantic AI text agent + working memory | ✅ Complete (10 files, 243 tests) |
| `agents/text/history.py` | HistoryLoader - PydanticAI message_history | ✅ Spec 030 (23 tests) |
| `agents/text/token_budget.py` | TokenBudgetManager - 4-tier allocation | ✅ Spec 030 (13 tests) |
| `agents/voice/` | ElevenLabs voice agent | ✅ Complete (14 files, 186 tests) |
| `platforms/telegram/` | Telegram bot platform | ✅ Deployed (7 files, 74 tests) |
| `api/routes/voice.py` | Voice API (5 endpoints) | ✅ Complete |
| `prompts/` | LLM prompt templates (Nikita persona) | ⚠️ DEPRECATED (v1 fallback only) |
| `meta_prompts/` | LLM-powered prompt generation via Claude Haiku | ⚠️ DEPRECATED (v1 fallback only) |
| `context_engine/` | Unified context collection + intelligent prompt generation | ✅ Spec 039 (307 tests, PRODUCTION) |
| `context_engine/router.py` | Feature-flagged routing between v1/v2 prompt generation | ✅ ENABLED (100% v2 traffic) |
| `api/` | FastAPI application (Cloud Run) | ✅ Complete (deployed) |
| `api/routes/portal.py` | Portal stats API | ✅ Complete (2025-12-10) |
| `api/routes/tasks.py` | pg_cron endpoints | ✅ Complete |
| `context/` | Context engineering pipeline | ✅ Complete (50 tests) |
| `onboarding/` | Voice onboarding (Meta-Nikita agent) | ✅ Complete (8 modules, 231 tests) |

## Key Files

- `config/settings.py`: All environment settings via Pydantic
- `config/elevenlabs.py`: Agent ID abstraction for chapter/mood switching
- `engine/constants.py`: Game constants (chapters, thresholds, decay rates)
- `memory/graphiti_client.py`: NikitaMemory class (3 temporal graphs)
- `db/models/user.py`: User, UserMetrics, UserVicePreference models

## Development Patterns

### 1. Settings Access

```python
from nikita.config.settings import get_settings

settings = get_settings()  # Cached singleton
database_url = settings.database_url
```

### 2. Memory System

```python
from nikita.memory.graphiti_client import get_memory_client

memory = await get_memory_client(user_id)
context = await memory.get_context_for_prompt(user_message)
await memory.add_user_fact("User works in finance")
```

### 3. Game Constants

```python
from nikita.engine.constants import CHAPTER_NAMES, BOSS_THRESHOLDS, DECAY_RATES

threshold = BOSS_THRESHOLDS[user.chapter]
decay = DECAY_RATES[user.chapter]
behavior = CHAPTER_BEHAVIORS[user.chapter]
```

## Architecture

See [../memory/architecture.md](../memory/architecture.md) for:
- Component hierarchy
- Data flow diagrams
- Database split (Supabase vs Neo4j Aura)
- Cloud Run deployment

## Next Steps

**Phase 2**: ✅ COMPLETE - Telegram deployed to Cloud Run

**Phase 3: Game Engine** - MOSTLY COMPLETE:
- ✅ 013-configuration-system: YAML configs + JSON schemas + loaders (89 tests)
- ✅ 014-engagement-model: 6 states (CALIBRATING, IN_ZONE, etc.) (179 tests)
- ✅ 003-scoring-engine: LLM-based response analysis (60 tests)
- ✅ 012-context-engineering: 6-stage pipeline (<200ms, <4000 tokens) (50 tests)
- ✅ 005-decay-system: Hourly decay + pg_cron (44 tests)
- ❌ **004-chapter-boss-system**: State machine + boss encounters ← NEXT
- ❌ 006-vice-personalization: 8 categories

**Phase 4**: ✅ Voice agent (ElevenLabs Conversational AI 2.0) - COMPLETE (186 tests, 14 modules)
**Phase 5**: ✅ Portal working (2025-12-10, 4 bug fixes deployed)

**Security (Parallel)**: Webhook signature validation, rate limiting

**Text Agent**: ✅ COMPLETE - see `agents/text/CLAUDE.md`
**Voice Agent**: ✅ COMPLETE - see `agents/voice/CLAUDE.md`
**Telegram Platform**: ✅ DEPLOYED - see `platforms/telegram/`
**Portal**: ✅ WORKING - dashboard shows score, chapter, progress

## Documentation

- [Memory Docs](../memory/README.md)
- [Master Plan](../plans/master-plan.md)
- [Master Todo](../todos/master-todo.md)
