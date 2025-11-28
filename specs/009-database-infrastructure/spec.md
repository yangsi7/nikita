# 009: Database Infrastructure

## Overview

Cross-cutting infrastructure specification defining the database layer requirements for all Nikita features. This spec establishes repository patterns, migration strategy, and row-level security policies.

**Type**: Infrastructure
**Blocks**: All feature specs (002-008)
**References**: `memory/backend.md#database-schema`

---

## Functional Requirements

### FR-001: Repository Pattern Implementation

The system SHALL implement the repository pattern for all database operations.

**Acceptance Criteria**:
- AC-001.1: Each domain entity has a dedicated repository class
- AC-001.2: Repositories use async SQLAlchemy sessions
- AC-001.3: Repositories are injected via FastAPI Depends()
- AC-001.4: No raw SQL in application code outside repositories

**Repositories Required**:
| Repository | Entity | Key Methods |
|------------|--------|-------------|
| UserRepository | User | get, get_by_telegram_id, create, update_score, apply_decay, advance_chapter |
| UserMetricsRepository | UserMetrics | get, update_metrics, calculate_composite |
| ConversationRepository | Conversation | create, append_message, get_recent, search |
| ScoreHistoryRepository | ScoreHistory | log_event, get_history, get_daily_stats |
| VicePreferenceRepository | UserVicePreference | get_active, update_intensity, discover |
| DailySummaryRepository | DailySummary | create, get_by_date, get_range |

### FR-002: Migration Management

The system SHALL use Alembic for schema migrations with Supabase compatibility.

**Acceptance Criteria**:
- AC-002.1: All schema changes via Alembic migrations
- AC-002.2: Migrations are idempotent and reversible
- AC-002.3: Migration naming: `{revision}_{description}.py`
- AC-002.4: Foreign keys use `ON DELETE CASCADE` or `SET NULL` appropriately
- AC-002.5: Indexes created for all foreign keys and frequently queried columns

**Migration Commands**:
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

### FR-003: Row-Level Security (RLS)

The system SHALL enforce row-level security for all user data tables.

**Acceptance Criteria**:
- AC-003.1: RLS enabled on: users, user_metrics, user_vice_preferences, conversations, score_history, daily_summaries
- AC-003.2: Users can only read/write their own data
- AC-003.3: Service role bypasses RLS for backend operations
- AC-003.4: Anon role has no access to user data

**RLS Policies**:
```sql
-- Users table
CREATE POLICY "users_own_data" ON users
    FOR ALL USING (auth.uid() = id);

-- Related tables (pattern)
CREATE POLICY "own_data_via_user_id" ON {table}
    FOR ALL USING (user_id IN (SELECT id FROM users WHERE auth.uid() = id));
```

### FR-004: Connection Pooling

The system SHALL implement connection pooling for database efficiency.

**Acceptance Criteria**:
- AC-004.1: Use asyncpg with SQLAlchemy async engine
- AC-004.2: Pool size: min 5, max 20 connections
- AC-004.3: Connection timeout: 30 seconds
- AC-004.4: Stale connection recycling: 1800 seconds

### FR-005: Transaction Management

The system SHALL handle transactions appropriately for data consistency.

**Acceptance Criteria**:
- AC-005.1: Score updates + history logging in single transaction
- AC-005.2: User creation + metrics initialization atomic
- AC-005.3: Failed transactions rollback completely
- AC-005.4: Deadlock detection with retry logic

### FR-006: Audit Logging

The system SHALL maintain audit trails for game-critical operations.

**Acceptance Criteria**:
- AC-006.1: Score changes logged to score_history
- AC-006.2: Chapter advances logged with timestamp
- AC-006.3: Boss attempt outcomes recorded
- AC-006.4: Game over/victory events captured

---

## Non-Functional Requirements

### NFR-001: Performance

- Database queries complete in <100ms (p95)
- Bulk operations (decay) process 1000 users in <30 seconds
- Index-only scans for common queries

### NFR-002: Reliability

- Connection retry on transient failures (3 attempts)
- Graceful degradation if database unavailable
- No data loss on application crash (committed transactions)

### NFR-003: Security

- No plaintext secrets in migrations
- Service role key never exposed to client
- SQL injection prevented via parameterized queries

### NFR-004: Observability

- Query timing logged for slow queries (>500ms)
- Connection pool metrics exposed
- Failed query patterns tracked

---

## Data Model

### Core Tables (Implemented)

**Reference**: `nikita/db/models/user.py`

```
users
├── id: UUID (PK, links to auth.users)
├── telegram_id: BIGINT UNIQUE
├── relationship_score: DECIMAL(5,2) DEFAULT 50.00
├── chapter: INT DEFAULT 1 (CHECK 1-5)
├── boss_attempts: INT DEFAULT 0 (CHECK 0-3)
├── days_played: INT DEFAULT 0
├── last_interaction_at: TIMESTAMPTZ
├── game_status: VARCHAR(20) DEFAULT 'active'
├── graphiti_group_id: TEXT
├── timezone: VARCHAR(50) DEFAULT 'UTC'
└── notifications_enabled: BOOLEAN DEFAULT TRUE

user_metrics (1:1)
├── id: UUID (PK)
├── user_id: UUID FK UNIQUE
├── intimacy: DECIMAL(5,2) DEFAULT 50.00
├── passion: DECIMAL(5,2) DEFAULT 50.00
├── trust: DECIMAL(5,2) DEFAULT 50.00
└── secureness: DECIMAL(5,2) DEFAULT 50.00

user_vice_preferences (many:1)
├── id: UUID (PK)
├── user_id: UUID FK
├── category: VARCHAR(50) NOT NULL
├── intensity_level: INT DEFAULT 1 (CHECK 1-5)
├── engagement_score: DECIMAL(5,2) DEFAULT 0.00
└── discovered_at: TIMESTAMPTZ DEFAULT NOW()

conversations
├── id: UUID (PK)
├── user_id: UUID FK
├── platform: VARCHAR(20) NOT NULL
├── messages: JSONB DEFAULT '[]'
├── score_delta: DECIMAL(5,2)
├── started_at: TIMESTAMPTZ
├── ended_at: TIMESTAMPTZ
├── is_boss_fight: BOOLEAN DEFAULT FALSE
├── chapter_at_time: INT
└── search_vector: tsvector GENERATED

score_history
├── id: UUID (PK)
├── user_id: UUID FK
├── score: DECIMAL(5,2) NOT NULL
├── chapter: INT NOT NULL
├── event_type: VARCHAR(50)
├── event_details: JSONB
└── recorded_at: TIMESTAMPTZ

daily_summaries
├── id: UUID (PK)
├── user_id: UUID FK
├── date: DATE NOT NULL
├── score_start: DECIMAL(5,2)
├── score_end: DECIMAL(5,2)
├── decay_applied: DECIMAL(5,2)
├── conversations_count: INT DEFAULT 0
├── nikita_summary_text: TEXT
├── key_events: JSONB
└── created_at: TIMESTAMPTZ
    UNIQUE(user_id, date)
```

### Indexes Required

```sql
-- Performance indexes
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_game_status ON users(game_status);
CREATE INDEX idx_conversations_user_started ON conversations(user_id, started_at DESC);
CREATE INDEX idx_score_history_user_recorded ON score_history(user_id, recorded_at DESC);
CREATE INDEX idx_daily_summaries_user_date ON daily_summaries(user_id, date DESC);

-- Full-text search
CREATE INDEX idx_conversations_search ON conversations USING gin(search_vector);
```

---

## User Stories

### US-001: Repository Instantiation

**As a** backend developer
**I want** repositories injected via FastAPI dependencies
**So that** database access is consistent and testable

**Acceptance Criteria**:
- [ ] AC-US001.1: `get_user_repo()` dependency returns UserRepository
- [ ] AC-US001.2: Repositories receive AsyncSession from connection pool
- [ ] AC-US001.3: Test fixtures can inject mock repositories

### US-002: Score Persistence

**As a** game engine
**I want** score updates persisted atomically with history
**So that** no score changes are lost

**Acceptance Criteria**:
- [ ] AC-US002.1: `update_score()` writes to users AND score_history
- [ ] AC-US002.2: Failed history insert rolls back score change
- [ ] AC-US002.3: Score history includes event_type and event_details

### US-003: User Data Isolation

**As a** player
**I want** my game data only visible to me
**So that** my progress is private

**Acceptance Criteria**:
- [ ] AC-US003.1: Portal queries return only authenticated user's data
- [ ] AC-US003.2: Direct table access blocked without valid JWT
- [ ] AC-US003.3: Service role operations work for backend tasks

---

## Dependencies

### Upstream (this spec depends on)
- Supabase project configured with auth.users
- PostgreSQL 15+ with pgvector extension
- Alembic migration environment

### Downstream (depends on this spec)
- 002-telegram-integration (user lookup, conversation storage)
- 003-scoring-engine (score persistence, history)
- 005-decay-system (batch user updates)
- 007-voice-agent (conversation storage)
- 008-player-portal (stats queries)

---

## Implementation Notes

**Pattern Reference**: `memory/backend.md#repository-pattern`

```python
# Example repository structure
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: UUID) -> User:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

# FastAPI dependency
async def get_user_repo(
    session: AsyncSession = Depends(get_async_session)
) -> UserRepository:
    return UserRepository(session)
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Connection pool exhaustion | High | Max pool size, connection timeouts |
| Migration conflicts | Medium | Feature branches, migration squashing |
| RLS bypass bugs | High | Integration tests verifying isolation |
| Slow bulk operations | Medium | Batch processing, COPY for large inserts |
