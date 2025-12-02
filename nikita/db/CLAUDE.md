# db/ - Database Layer

## Purpose

Database models, repositories, and migrations for Supabase PostgreSQL.

## Current State

**Phase 2 ✅**: Models + repositories complete

```
db/
├── models/                        ✅ COMPLETE
│   ├── base.py                    # Base, TimestampMixin
│   ├── user.py                    # User, UserMetrics, UserVicePreference
│   ├── conversation.py            # Conversation, MessageEmbedding
│   ├── game.py                    # ScoreHistory, DailySummary
│   └── pending_registration.py    # PendingRegistration (for Telegram auth)
├── repositories/                  ✅ COMPLETE (Sprint 2)
│   ├── user_repository.py         # UserRepository (get, create, update)
│   ├── conversation_repository.py # ConversationRepository
│   ├── metrics_repository.py      # MetricsRepository
│   ├── score_history_repository.py # ScoreHistoryRepository
│   ├── summary_repository.py      # SummaryRepository
│   ├── vice_repository.py         # VicePreferenceRepository
│   └── pending_registration_repository.py # PendingRegistrationRepository
├── migrations/                    ✅ Applied via Supabase MCP
│   └── (8 migrations applied)     # RLS, extensions, pending_registrations
└── database.py                    ✅ AsyncSession factory, get_session_maker()
```

## Key Models

### User (user.py:19-110)
```python
class User(Base, TimestampMixin):
    id: UUID                        # Links to auth.users
    telegram_id: int | None
    relationship_score: Decimal     # Composite score (0-100)
    chapter: int                    # Current chapter (1-5)
    boss_attempts: int              # Boss attempts (0-3)
    game_status: str                # active | boss_fight | game_over | won
    graphiti_group_id: str          # Links to Neo4j Aura graphs
```

### UserMetrics (user.py:112-167)
```python
class UserMetrics(Base):
    intimacy: Decimal       # 0-100 (30% weight)
    passion: Decimal        # 0-100 (25% weight)
    trust: Decimal          # 0-100 (25% weight)
    secureness: Decimal     # 0-100 (20% weight)

    def calculate_composite_score(self) -> Decimal:
        return (
            intimacy * 0.30 +
            passion * 0.25 +
            trust * 0.25 +
            secureness * 0.20
        )
```

### UserVicePreference (user.py:169-207)
```python
class UserVicePreference(Base):
    category: str           # One of 8 VICE_CATEGORIES
    intensity_level: int    # 1-5
    engagement_score: Decimal
```

## Repository Pattern ✅ COMPLETE

```python
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: UUID) -> User:
        """Get user by ID with metrics loaded"""

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID"""

    async def create(self, telegram_id: int) -> User:
        """Create new user with default metrics"""

    async def update_score(
        self,
        user_id: UUID,
        new_score: Decimal,
        event_type: str,
    ) -> None:
        """Update score and log to score_history"""

    async def apply_decay(self, user_id: UUID, decay: Decimal):
        """Apply daily decay"""


class PendingRegistrationRepository:
    """Repository for Telegram pending registrations (Sprint 2)"""

    async def create(self, telegram_id: int, email: str) -> PendingRegistration
    async def get_by_telegram_id(self, telegram_id: int) -> PendingRegistration | None
    async def delete(self, telegram_id: int) -> None
    async def cleanup_expired(self, ttl_minutes: int = 10) -> int
```

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

8 migrations applied directly to Supabase:
1. Initial schema (users, user_metrics, conversations, etc.)
2. RLS policies with `(select auth.uid())` optimization
3. pending_registrations table for Telegram auth
4. Extensions in dedicated schema
5. message_embeddings user_id column fix
6. Duplicate policy cleanup

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
- [Database Schema](../../memory/backend.md#database-schema-supabase-postgresql)
