# nikita/ Package Overview

## Purpose

Core application package for Nikita: Don't Get Dumped - AI girlfriend simulation game.

## Module Structure

| Module | Purpose | Status |
|--------|---------|--------|
| `config/` | Settings, environment config, YAML loaders | ✅ Complete (89 tests) |
| `db/` | Database models, repositories, migrations | ✅ Complete (7 repos, 90 migration stubs) |
| `engine/scoring/` | Scoring engine (4 metrics, deltas) | ✅ Complete (60 tests) |
| `engine/engagement/` | Engagement state machine (6 states) | ✅ Complete (179 tests) |
| `engine/decay/` | Decay calculator, processor | ✅ Complete (44 tests) |
| `engine/chapters/` | Chapter state machine, boss encounters | ✅ Complete (142 tests) |
| `engine/vice/` | Vice personalization | ✅ Complete (70 tests) |
| `memory/` | Supabase pgVector memory backend | ✅ Spec 042 (38 tests) |
| `agents/text/` | Pydantic AI text agent + working memory | ✅ Complete (10 files, 243 tests) |
| `agents/text/history.py` | HistoryLoader - PydanticAI message_history | ✅ Spec 030 (23 tests) |
| `agents/text/token_budget.py` | TokenBudgetManager - 4-tier allocation | ✅ Spec 030 (13 tests) |
| `agents/voice/` | ElevenLabs voice agent | ✅ Complete (14 files, 186 tests) |
| `platforms/telegram/` | Telegram bot platform | ✅ Deployed (7 files, 74 tests) |
| `api/routes/voice.py` | Voice API (5 endpoints) | ✅ Complete |
| `prompts/` | LLM prompt templates (Nikita persona) | ⚠️ DEPRECATED (v1 fallback only) |
| `pipeline/` | Unified 10-stage async pipeline | ✅ Spec 042+067 (74 tests) |
| `context/` | Legacy context utilities (validation, session detection) | ⚠️ PARTIAL (Spec 042 deprecates package.py) |
| `api/` | FastAPI application (Cloud Run) | ✅ Complete (deployed) |
| `api/routes/portal.py` | Portal stats API | ✅ Complete |
| `api/routes/tasks.py` | pg_cron endpoints | ✅ Complete |
| `onboarding/` | Voice onboarding (Meta-Nikita agent) | ✅ Complete (8 modules, 231 tests) |

## Key Files

- `config/settings.py`: All environment settings via Pydantic
- `config/elevenlabs.py`: Agent ID abstraction for chapter/mood switching
- `engine/constants.py`: Game constants (chapters, thresholds, decay rates)
- `memory/supabase_memory.py`: SupabaseMemory class (pgVector + dedup)
- `db/models/user.py`: User, UserMetrics, UserVicePreference models
- `pipeline/orchestrator.py`: 10-stage async pipeline orchestrator

## Development Patterns

### 1. Settings Access

```python
from nikita.config.settings import get_settings

settings = get_settings()  # Cached singleton
database_url = settings.database_url
```

### 2. Memory System

```python
from nikita.memory.supabase_memory import SupabaseMemory

memory = SupabaseMemory(session)
context = await memory.search("recent conversations", user_id, limit=5)
await memory.add_fact("User works in finance", user_id)
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
- Database architecture (Supabase PostgreSQL + pgVector)
- Cloud Run deployment

## Status

All specs implemented. See root `CLAUDE.md` for navigation to docs, specs, and task tracking.
