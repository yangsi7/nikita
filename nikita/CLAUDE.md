# nikita/ Package Overview

## Purpose

Core application package for Nikita: Don't Get Dumped - AI girlfriend simulation game.

## Module Structure

| Module | Purpose | Status |
|--------|---------|--------|
| `config/` | Settings, environment config | ✅ Complete |
| `db/` | Database models, repositories, migrations | ✅ Complete (7 repos, 8 migrations) |
| `engine/` | Game logic (scoring, chapters, decay, vice) | ⚠️ Constants only, logic TODO (Phase 3) |
| `memory/` | Graphiti + Neo4j Aura knowledge graphs | ✅ Complete |
| `agents/text/` | Pydantic AI text agent | ✅ Complete (8 files, 156 tests) |
| `agents/voice/` | ElevenLabs voice agent | ❌ TODO (Phase 4) |
| `platforms/telegram/` | Telegram bot platform | ✅ Complete (7 files, 74 tests) |
| `platforms/voice/` | Voice integration | ❌ TODO (Phase 4) |
| `platforms/portal/` | Player stats dashboard | ❌ TODO (Phase 5) |
| `prompts/` | LLM prompt templates (Nikita persona) | ⚠️ DEPRECATED (fallback only) |
| `meta_prompts/` | LLM-powered prompt generation via Claude Haiku | ✅ Complete |
| `api/` | FastAPI application (Cloud Run) | ✅ 95% Complete (deployed) |
| `api/routes/tasks.py` | pg_cron endpoints | ✅ Complete |
| `context/` | Context engineering pipeline | ✅ Complete (spec 012) |

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

**Phase 2 Remaining (5%)**:
- Wire text_agent in production message handler

**Phase 3: Configuration + Game Engine** (specs 013, 014, 003, 004, 005, 006, 012):
1. 013-configuration-system: YAML configs + JSON schemas + loaders
2. 014-engagement-model: 6 states (CALIBRATING, IN_ZONE, DRIFTING, etc.)
3. 003-scoring-engine: LLM-based response analysis
4. 012-context-engineering: 6-stage pipeline (<200ms, <4000 tokens)
5. 004-chapter-boss-system: State machine + boss encounters
6. 005-decay-system: Hourly decay + pg_cron
7. 006-vice-personalization: 8 categories

**Phase 4**: Voice agent (ElevenLabs Conversational AI 2.0)
**Phase 5**: Player portal (Next.js dashboard)

**Security (Parallel)**: Webhook signature validation, rate limiting, Secret Manager

**Text Agent**: ✅ COMPLETE - see `agents/text/CLAUDE.md`
**Telegram Platform**: ✅ COMPLETE - see `platforms/telegram/`

## Documentation

- [Memory Docs](../memory/README.md)
- [Master Plan](../plan/master-plan.md)
- [Master Todo](../todo/master-todo.md)
