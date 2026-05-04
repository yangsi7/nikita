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
| `pipeline/` | Unified 11-stage async pipeline | ✅ Spec 042+067 (74 tests) |
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
- `pipeline/orchestrator.py`: 11-stage async pipeline orchestrator

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

## Callers

Top-level entry points (everything else imports through these):

- `nikita/api/main.py` — FastAPI app entry; mounts routes under `/api/v1/*`. Deployed via Cloud Run.
- `nikita/platforms/telegram/message_handler.py` — `MessageHandler.handle()` entry, dispatched from `nikita/api/routes/telegram.py:501` POST `/webhook`.
- `nikita/api/routes/voice.py:350` POST `/server-tool` — ElevenLabs server-tool callback entry.
- `nikita/api/routes/tasks.py` — pg_cron-driven background entry points (heartbeat, decay, deliver, summary, touchpoints, etc.).
- `nikita/onboarding/handoff.py:705` — onboarding-to-main handoff (one of 5 PipelineOrchestrator invocation sites).

## Gotchas

- **Pipeline ctx state collisions**: `extraction_summary` written by stage 0 then OVERWRITTEN by stage 9 (`prompt_builder`). `conflict_details` written by both stage 4 (emotional) and stage 7 (conflict). Surfaced in W4 audit; flagged on W6.5 Diagram A.
- **`vice` stage produces NO ctx output** (`pipeline/stages/vice.py:21`) — side-effects only; opaque to downstream stages.
- **Pipeline NOT directly invoked from `platforms/telegram/message_handler.py`** — flows via cron path in `tasks.py`. KT framing was wrong (W4 audit).
- **`stages_total = 11` hardcoded at `orchestrator.py:186`** — drift hardcoded inside the canonical file; must match `STAGE_DEFINITIONS` length.
- **Bare `except Exception` swallow** at `orchestrator.py:308` and `:343` — silent failure on non-critical stages. Watch the logs.
- **3 isolated Pydantic AI agents** (text/onboarding/psyche) — coordinate via `PipelineContext` + DB repositories, never direct `agent.run()` cross-call. Voice live loop is ElevenLabs Server Tools, NOT a Pydantic AI agent.
- **`get_settings()` is cached** — call `.cache_clear()` in test teardown to avoid bleed.
- See [`memory/architecture.md`](../memory/architecture.md) §"Code-verified additions" for the full file:line table of pipeline stages, agents, and memory subsystem.

## Navigation

- Module roots: [`agents/voice/`](agents/voice/CLAUDE.md), [`api/`](api/CLAUDE.md), [`db/`](db/CLAUDE.md), [`engine/`](engine/CLAUDE.md), [`engine/vice/`](engine/vice/CLAUDE.md), [`memory/`](memory/CLAUDE.md), [`onboarding/`](onboarding/CLAUDE.md), [`pipeline/`](pipeline/CLAUDE.md), [`context/`](context/CLAUDE.md) (LEGACY).
- Architecture canonical: [`../memory/architecture.md`](../memory/architecture.md)
- Backend canonical: [`../memory/backend.md`](../memory/backend.md)
- Game mechanics canonical: [`../memory/game-mechanics.md`](../memory/game-mechanics.md)
- Root toolkit: [`../.claude/CLAUDE.md`](../.claude/CLAUDE.md)

Last verified: 2026-05-05
