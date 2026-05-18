# db/ - Database Layer

## Purpose

Database models, repositories, and migrations for Supabase PostgreSQL.

## Current State

**Status**: ✅ Complete — Models, repositories, and migrations

```
db/
├── models/                        ✅ COMPLETE
│   ├── base.py                    # Base, TimestampMixin
│   ├── user.py                    # User, UserMetrics, UserVicePreference
│   ├── conversation.py            # Conversation, MessageEmbedding
│   ├── game.py                    # ScoreHistory, DailySummary
│   └── pending_registration.py    # PendingRegistration (for Telegram auth)
├── repositories/                  ✅ COMPLETE
│   ├── user_repository.py                    # UserRepository (get, create, update, update_telegram_id)
│   ├── conversation_repository.py            # ConversationRepository
│   ├── metrics_repository.py                 # MetricsRepository
│   ├── score_history_repository.py           # ScoreHistoryRepository
│   ├── summary_repository.py                 # SummaryRepository
│   ├── vice_repository.py                    # VicePreferenceRepository
│   ├── pending_registration_repository.py    # PendingRegistrationRepository
│   ├── telegram_link_repository.py           # TelegramLinkRepository (create_link_code, verify_code, 10-min TTL)
│   ├── auth_bridge_repository.py             # AuthBridgeRepository
│   ├── ready_prompt_repository.py            # ReadyPromptRepository (set_current, get_current)
│   ├── profile_repository.py                 # ProfileRepository (user_profiles)
│   ├── telegram_signup_session_repository.py # TelegramSignupSessionRepository (FSM state)
│   └── backstory_cache_repository.py         # BackstoryCacheRepository (Spec 213)
├── migrations/                    ✅ Applied via Supabase MCP
│   └── (90 migrations — comment-only stubs, applied via Supabase MCP)
│       # Full DDL reference in supabase/reference/. See MEMORY.md for migration pattern.
└── database.py                    ✅ AsyncSession factory, get_session_maker()
```

## Key Models

- `User` (`user.py:19-110`): Core game state (id, telegram_id, relationship_score, chapter, boss_attempts, game_status)
- `UserMetrics` (`user.py:112-167`): 4 metrics (intimacy 30%, passion 25%, trust 25%, secureness 20%) + composite score
- `UserVicePreference` (`user.py:169-207`): category, intensity_level, engagement_score (8 VICE_CATEGORIES)

## Database Schema

See [../../memory/backend.md](../../memory/backend.md) for full SQL schema.

**Key tables**:
- `users`: Core game state
- `user_metrics`: Hidden scoring metrics
- `user_vice_preferences`: 8 vice categories tracking
- `conversations`: Message logs (text + voice)
- `score_history`: Score timeline for graphs
- `daily_summaries`: Nikita's daily recaps
- `message_embeddings`: pgVector semantic search

## Migrations ✅ COMPLETE (via Supabase MCP)

90 migrations tracked in `supabase/migrations/` as comment-only stubs. All DDL was applied via Supabase MCP tools — stubs exist only for CLI version tracking. Full baseline DDL is in `supabase/reference/00000000000001_baseline_schema.sql`.

```bash
# View migrations via Supabase MCP
mcp__supabase__list_migrations
```

## Row-Level Security

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own data" ON users
    FOR ALL USING (auth.uid() = id);
```

## Documentation

- [Backend Architecture](../../memory/backend.md)

## Callers

- `nikita/api/routes/*.py` — repositories imported by every route handler.
- `nikita/pipeline/stages/*.py` — every pipeline stage reads/writes via repositories (`MemoryFactRepository`, `UserMetricsRepository`, etc.).
- `nikita/agents/text/deps.py` + `nikita/agents/voice/deps.py` — Pydantic AI agent deps wire DB sessions.
- `nikita/memory/supabase_memory.py:51` — wraps `MemoryFactRepository` for pgVector search/dedup.
- `nikita/onboarding/*` — user creation, profile collection, backstory cache.
- Migrations runner — `alembic` for offline migrations, `supabase/migrations/*` for cron + RLS.

## Gotchas

- **`public.users` has NO `email` column** (per auto-memory `project_users_table_schema.md`). Email lives on `auth.users`. FK-safe wipe order: `user_metrics` → `user_vice_preferences` → `scheduled_events` → `memories` → `user_profiles` → `users` → `auth.users`.
- **User-row creation consolidated** in `nikita/api/routes/portal.py:124` (comment notes the consolidation replacing prior inline get + create_with_metrics duplication). Cold users: verify `user_metrics` and `user_vice_preferences` rows exist post-create.
- **pgVector indexes**: `idx_memory_facts_embedding_cosine` is IVFFlat (`db/migrations/versions/20260206_0009_unified_pipeline_tables.py:68`); `idx_memory_facts_user_graph_active` is partial (`:76`). Keep them when running ANALYZE.
- **RLS enabled on `memory_facts`** with 5 policies (`:97`). New tables MUST follow the checklist in `.claude/rules/testing.md` "DB Migration Checklist".
- **Soft-delete via `is_active=False` + `superseded_by` FK self-ref** for memory facts (`MemoryFactRepository.deactivate`). Do not hard-delete unless absolutely needed.
- **`session.execute()` mock pattern**: `AsyncMock(scalars=Mock(return_value=Mock(first=...)))` — see `tests/conftest.py`.
- **Async fixtures in `tests/`**: every DB test uses `AsyncMock`; E2E tests have separate ASGI-transport fixtures in `tests/e2e/conftest.py`.

## Navigation

- Backend module map: [`../CLAUDE.md`](../CLAUDE.md)
- Backend canonical: [`../../memory/backend.md`](../../memory/backend.md)
- Schema reference: [`../../docs/reference/schema-reference.md`](../../docs/reference/schema-reference.md)
- Migrations: [`alembic.ini`](../../alembic.ini) + [`supabase/migrations/`](../../supabase/migrations/)

Last verified: 2026-05-18
