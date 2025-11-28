# nikita/ Package Overview

## Purpose

Core application package for Nikita: Don't Get Dumped - AI girlfriend simulation game.

## Module Structure

| Module | Purpose | Status |
|--------|---------|--------|
| `config/` | Settings, environment config | ✅ Complete |
| `db/` | Database models, repositories, migrations | ⚠️ Models complete, repos TODO |
| `engine/` | Game logic (scoring, chapters, decay, vice) | ⚠️ Constants only, logic TODO |
| `memory/` | Graphiti knowledge graphs | ✅ Complete |
| `agents/text/` | Pydantic AI text agent | ✅ COMPLETE (8 files, 156 tests) |
| `agents/voice/` | ElevenLabs voice agent | ❌ TODO Phase 4 |
| `platforms/` | Telegram, voice, portal integrations | ❌ TODO Phase 2-5 |
| `prompts/` | LLM prompt templates (Nikita persona) | ✅ Complete |
| `api/` | FastAPI application | ⚠️ Skeleton only |
| `tasks/` | Celery background jobs | ❌ TODO Phase 3 |

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
- Database split (Supabase vs FalkorDB)

## Next Steps

- Phase 2 (remaining): Telegram integration
- Phase 3: Implement game engine (scoring, chapters, decay)
- Phase 4: Implement voice agent (ElevenLabs)
- Phase 5: Build player portal (Next.js)

**Text Agent**: ✅ COMPLETE - see `agents/text/CLAUDE.md`

## Documentation

- [Memory Docs](../memory/README.md)
- [Master Plan](../plan/master-plan.md)
- [Master Todo](../todo/master-todo.md)
