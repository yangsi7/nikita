# db/ - Database Layer

## Purpose

Database models, repositories, and migrations for Supabase PostgreSQL.

## Current State

**Phase 1 ✅**: Models complete, repositories TODO

```
db/
├── models/              ✅ COMPLETE
│   ├── base.py          # Base, TimestampMixin
│   ├── user.py          # User, UserMetrics, UserVicePreference
│   ├── conversation.py  # Conversation, MessageEmbedding
│   └── game.py          # ScoreHistory, DailySummary
├── repositories/        ❌ TODO Phase 2
│   ├── user_repository.py
│   ├── conversation_repository.py
│   └── metrics_repository.py
├── migrations/          ❌ TODO Phase 2
│   └── versions/        # Alembic migrations
└── database.py          ⚠️ Basic connection only
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
    graphiti_group_id: str          # Links to FalkorDB graphs
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

## Repository Pattern (TODO Phase 2)

```python
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: UUID) -> User:
        """Get user by ID with metrics loaded"""

    async def update_score(
        self,
        user_id: UUID,
        new_score: Decimal,
        event_type: str,
    ) -> None:
        """Update score and log to score_history"""

    async def apply_decay(self, user_id: UUID, decay: Decimal):
        """Apply daily decay"""
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

## Migrations (TODO Phase 2)

```bash
# Generate migration
alembic revision --autogenerate -m "Initial schema"

# Apply to Supabase
alembic upgrade head
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
