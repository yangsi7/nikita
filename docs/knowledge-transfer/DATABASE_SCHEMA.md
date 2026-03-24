# Database Schema

> **Historical Note (2026-03-24)**: This document references Neo4j/Graphiti which has been replaced by SupabaseMemory (pgVector) as of Spec 042. The architecture described here is no longer current.

```yaml
context_priority: high
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - CONTEXT_ENGINE.md
  - PIPELINE_STAGES.md
  - AUTHENTICATION.md
```

## Overview

Nikita uses two database systems:
- **Supabase (PostgreSQL)** - Relational data, user state, game mechanics
- **Neo4j Aura (Graphiti)** - Knowledge graphs for memory and relationships

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE ARCHITECTURE                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         SUPABASE (PostgreSQL)                        │   │
│  │                                                                      │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │   │
│  │  │   users     │ │conversations│ │  messages   │ │  user_      │  │   │
│  │  │ (core)      │ │             │ │             │ │  metrics    │  │   │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘  │   │
│  │         │               │               │               │         │   │
│  │         └───────────────┴───────────────┴───────────────┘         │   │
│  │                              │                                     │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │   │
│  │  │ nikita_     │ │ nikita_     │ │ nikita_     │ │ generated_  │  │   │
│  │  │ threads     │ │ thoughts    │ │ summaries   │ │ prompts     │  │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │   │
│  │                                                                      │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │   │
│  │  │ job_        │ │ rate_       │ │ pending_    │ │ scheduled_  │  │   │
│  │  │ executions  │ │ limits      │ │ registrations│ │ messages   │  │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         NEO4J AURA (Graphiti)                        │   │
│  │                                                                      │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │   │
│  │  │   nikita_graph   │  │   user_{id}      │  │ relationship_{id}│  │   │
│  │  │   (Nikita's      │  │   (User's        │  │ (Shared          │  │   │
│  │  │    life events)  │  │    personal      │  │  memories)       │  │   │
│  │  │                  │  │    facts)        │  │                  │  │   │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘  │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Supabase Tables

### Core Tables

#### users

**File**: `nikita/db/models/user.py:20-100`

Primary user table with profile and state.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key (Supabase auth.users.id) |
| `telegram_id` | BIGINT | Telegram user ID |
| `telegram_username` | VARCHAR(100) | Telegram @username |
| `display_name` | VARCHAR(100) | User's preferred name |
| `phone_number` | VARCHAR(20) | Verified phone number |
| `occupation` | TEXT | User's job/role |
| `hobbies` | JSONB | Array of hobbies |
| `relationship_goals` | TEXT | What they're looking for |
| `personality_notes` | TEXT | LLM-inferred notes |
| `onboarding_status` | VARCHAR(20) | pending/in_progress/completed/skipped |
| `onboarding_channel` | VARCHAR(20) | voice/text |
| `created_at` | TIMESTAMP | Account creation |
| `updated_at` | TIMESTAMP | Last profile update |

```sql
-- Example query
SELECT id, display_name, onboarding_status, phone_number
FROM users
WHERE telegram_id = 123456789;
```

#### user_metrics

**File**: `nikita/db/models/user.py:100-180`

Game state and scores.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → users.id |
| `relationship_score` | DECIMAL(5,2) | Overall score 0-100 |
| `intimacy_score` | DECIMAL(5,2) | Intimacy metric |
| `passion_score` | DECIMAL(5,2) | Passion metric |
| `trust_score` | DECIMAL(5,2) | Trust metric |
| `secureness_score` | DECIMAL(5,2) | Secureness metric |
| `chapter_number` | INTEGER | Current chapter 1-6 (6=game over) |
| `engagement_state` | VARCHAR(20) | CALIBRATING/IN_ZONE/DRIFTING/etc |
| `in_boss_fight` | BOOLEAN | Currently in boss encounter |
| `last_interaction` | TIMESTAMP | Last message time |
| `game_over_at` | TIMESTAMP | When game ended (if applicable) |

```sql
-- Example query
SELECT u.display_name, um.relationship_score, um.chapter_number
FROM users u
JOIN user_metrics um ON u.id = um.user_id
WHERE um.relationship_score > 50
ORDER BY um.relationship_score DESC;
```

#### conversations

**File**: `nikita/db/models/conversation.py:1-100`

Conversation records.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → users.id |
| `started_at` | TIMESTAMP | Conversation start |
| `ended_at` | TIMESTAMP | Conversation end |
| `status` | VARCHAR(20) | active/completed/abandoned |
| `channel` | VARCHAR(20) | telegram/voice/portal |
| `message_count` | INTEGER | Total messages |
| `score_delta` | DECIMAL(5,2) | Score change from this conversation |
| `chapter_at_time` | INTEGER | Chapter when conversation started |
| `is_boss_fight` | BOOLEAN | Boss fight conversation |
| `processing_status` | VARCHAR(20) | pending/processing/completed/failed |
| `processing_started_at` | TIMESTAMP | Pipeline start time |
| `stage_reached` | VARCHAR(50) | Last completed pipeline stage |

```sql
-- Example query
SELECT c.id, c.status, c.score_delta, c.stage_reached
FROM conversations c
WHERE c.user_id = 'uuid'
  AND c.status = 'completed'
ORDER BY c.started_at DESC
LIMIT 10;
```

### Memory Tables

#### nikita_threads

**File**: `nikita/db/models/context.py:20-60`

Conversation threads for continuity.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → users.id |
| `conversation_id` | UUID | FK → conversations.id |
| `topic` | VARCHAR(200) | Thread topic summary |
| `status` | VARCHAR(20) | open/resolved/dormant |
| `importance` | INTEGER | Priority 1-5 |
| `created_at` | TIMESTAMP | Thread creation |
| `last_mentioned_at` | TIMESTAMP | Last reference |

#### nikita_thoughts

**File**: `nikita/db/models/context.py:60-100`

Nikita's internal thoughts about conversations.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → users.id |
| `conversation_id` | UUID | FK → conversations.id |
| `thought` | TEXT | The thought content |
| `thought_type` | VARCHAR(50) | observation/concern/appreciation |
| `psychological_context` | JSONB | LLM-extracted context |
| `created_at` | TIMESTAMP | Thought creation |

#### nikita_summaries

**File**: `nikita/db/models/context.py:100-140`

Daily and weekly summaries.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → users.id |
| `summary_type` | VARCHAR(20) | daily/weekly |
| `summary_date` | DATE | Date covered |
| `content` | TEXT | Summary text |
| `key_moments` | JSONB | Important moments array |
| `created_at` | TIMESTAMP | Summary creation |

### Pipeline Tables

#### generated_prompts

**File**: `nikita/db/models/generated_prompt.py:1-60`

System prompts for audit/debug.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → users.id |
| `conversation_id` | UUID | FK → conversations.id |
| `system_prompt` | TEXT | Full system prompt |
| `prompt_version` | VARCHAR(20) | Template version |
| `token_count` | INTEGER | Prompt token count |
| `context_fields_used` | JSONB | Fields included |
| `created_at` | TIMESTAMP | Prompt generation time |

#### job_executions

**File**: `nikita/db/models/job_execution.py:1-80`

Pipeline job tracking.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `conversation_id` | UUID | FK → conversations.id |
| `stage_name` | VARCHAR(50) | Pipeline stage |
| `status` | VARCHAR(20) | pending/running/completed/failed |
| `started_at` | TIMESTAMP | Stage start |
| `completed_at` | TIMESTAMP | Stage completion |
| `error_message` | TEXT | Error if failed |
| `metadata` | JSONB | Stage-specific data |

### Auth & Security Tables

#### pending_registrations

**File**: `nikita/db/models/pending_registration.py:1-50`

OTP verification records.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `telegram_id` | BIGINT | Telegram user ID |
| `otp_code` | VARCHAR(8) | 6-8 digit OTP |
| `phone_number` | VARCHAR(20) | Phone to verify |
| `attempts` | INTEGER | Verification attempts (max 3) |
| `expires_at` | TIMESTAMP | OTP expiration (10 min) |
| `created_at` | TIMESTAMP | Registration start |

#### rate_limits

**File**: `nikita/db/models/rate_limit.py:1-50`

Rate limiting records.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → users.id |
| `window` | TIMESTAMP | Rate limit window start |
| `minute_count` | INTEGER | Requests this minute |
| `daily_count` | INTEGER | Requests today |
| `last_request_at` | TIMESTAMP | Last request time |

### Admin Tables

#### audit_logs

**File**: `nikita/db/models/audit_log.py:1-50`

Admin action logging.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `admin_id` | UUID | Admin user ID |
| `action` | VARCHAR(100) | Action type |
| `target_type` | VARCHAR(50) | Entity type |
| `target_id` | UUID | Entity ID |
| `details` | JSONB | Action details |
| `created_at` | TIMESTAMP | Action time |

#### error_logs

**File**: `nikita/db/models/error_log.py:1-50`

Application error logging.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | Affected user (if any) |
| `error_type` | VARCHAR(100) | Exception class |
| `error_message` | TEXT | Error message |
| `stack_trace` | TEXT | Full stack trace |
| `context` | JSONB | Request context |
| `created_at` | TIMESTAMP | Error time |

---

## Entity Relationship Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              ERD DIAGRAM                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐            │
│  │   users     │ 1───1   │user_metrics │         │ user_vice_  │            │
│  │             │────────▶│             │         │ preferences │            │
│  │  id (PK)    │         │  user_id FK │◀────────│  user_id FK │            │
│  └──────┬──────┘         └─────────────┘         └─────────────┘            │
│         │                                                                    │
│         │ 1                                                                  │
│         │                                                                    │
│         ▼ *                                                                  │
│  ┌─────────────┐                                                            │
│  │conversations│ 1                                                          │
│  │             │──────────────────────────────────────────┐                 │
│  │  id (PK)    │                                          │                 │
│  │  user_id FK │                                          │                 │
│  └──────┬──────┘                                          │                 │
│         │                                                  │                 │
│         │ 1                                                │ 1               │
│         │                                                  │                 │
│    ┌────┴────┐                                            │                 │
│    │         │                                            │                 │
│    ▼ *       ▼ *                                          ▼ *               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ nikita_     │  │ nikita_     │  │ generated_  │  │ job_        │        │
│  │ threads     │  │ thoughts    │  │ prompts     │  │ executions  │        │
│  │             │  │             │  │             │  │             │        │
│  │  conv_id FK │  │  conv_id FK │  │  conv_id FK │  │  conv_id FK │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │ nikita_     │  │ scheduled_  │  │ social_     │                         │
│  │ summaries   │  │ messages    │  │ circle      │                         │
│  │             │  │             │  │             │                         │
│  │  user_id FK │  │  user_id FK │  │  user_id FK │                         │
│  └─────────────┘  └─────────────┘  └─────────────┘                         │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │ pending_    │  │ rate_       │  │ telegram_   │                         │
│  │ registrations│ │ limits      │  │ links       │                         │
│  │             │  │             │  │             │                         │
│  │  (no FK)    │  │  user_id FK │  │  user_id FK │                         │
│  └─────────────┘  └─────────────┘  └─────────────┘                         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Neo4j Graphs

### Three Knowledge Graphs

Graphiti maintains separate graphs per function:

#### nikita_graph

Nikita's life events and personality.

```cypher
// Node types
(:Event {id, type, description, timestamp})
(:Personality {trait, intensity})
(:Relationship {person, type, status})

// Example query
MATCH (e:Event)-[:HAPPENED_ON]->(d:Date)
WHERE d.date > datetime() - duration('P7D')
RETURN e.description, e.timestamp
ORDER BY e.timestamp DESC
LIMIT 20
```

#### user_{user_id}

User's personal facts (one graph per user).

```cypher
// Node types
(:Fact {id, content, source, confidence})
(:Preference {category, value})
(:Interest {topic, intensity})

// Example query
MATCH (f:Fact)
WHERE f.confidence > 0.7
RETURN f.content
ORDER BY f.timestamp DESC
LIMIT 50
```

#### relationship_{user_id}

Shared memories and conversation highlights.

```cypher
// Node types
(:Memory {id, content, emotional_valence})
(:Conversation {id, date, key_moment})
(:SharedExperience {topic, sentiment})

// Example query
MATCH (m:Memory)-[:FROM_CONVERSATION]->(c:Conversation)
WHERE c.date > datetime() - duration('P30D')
RETURN m.content, c.date
ORDER BY m.emotional_valence DESC
LIMIT 30
```

### Graphiti Client

**File**: `nikita/memory/graphiti_client.py:1-200`

```python
# nikita/memory/graphiti_client.py:50-100

class NikitaMemory:
    """Singleton Graphiti client for knowledge graphs."""

    _instance: Optional["NikitaMemory"] = None

    @classmethod
    def get_instance(cls) -> "NikitaMemory":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def search_memory(
        self,
        query: str,
        graph_name: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search a specific graph for relevant facts."""
        graphiti = await self._get_graphiti(graph_name)
        results = await graphiti.search(
            query=query,
            num_results=limit
        )
        return [{"fact": r.content, "confidence": r.score} for r in results]

    async def add_episode(
        self,
        content: str,
        graph_name: str,
        source: str = "conversation"
    ) -> None:
        """Add new information to a graph."""
        graphiti = await self._get_graphiti(graph_name)
        await graphiti.add_episode(
            content=content,
            source=source,
            timestamp=datetime.now(UTC)
        )
```

### NEEDS RETHINKING

**Graphiti Utility**: 3 graphs are stored but retrieval is underutilized:
- `nikita_graph` - Rarely queried in text agent
- Retrieval quality varies significantly
- Cold start adds 30s latency

Consider:
- Caching frequently accessed facts
- Pre-computing user context snapshots
- Evaluating alternative memory architectures (RAG, vector DB)

---

## Migrations

### Migration History

| Version | Date | Description |
|---------|------|-------------|
| 0001 | 2025-11-01 | Initial schema |
| 0002 | 2025-11-15 | Add user_metrics |
| 0003 | 2025-11-20 | Add conversations |
| 0004 | 2025-12-01 | Add nikita_* tables |
| 0005 | 2025-12-10 | Add job_executions |
| 0006 | 2025-12-15 | Add generated_prompts |
| 0007 | 2025-12-20 | Add rate_limits |
| 0008 | 2026-02-02 | Schema sync (17 tables) |

### Running Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback one version
alembic downgrade -1

# Show current version
alembic current
```

### Migration Best Practices

1. **Always test locally** with Supabase CLI first
2. **Add columns as nullable** or with defaults
3. **Create indexes** for frequently queried columns
4. **Never drop columns** in production without data migration

---

## Row Level Security (RLS)

### User Data Isolation

**File**: Supabase Dashboard → SQL Editor

```sql
-- Users can only see their own data
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own data"
ON users FOR SELECT
USING (auth.uid() = id);

CREATE POLICY "Users can update own data"
ON users FOR UPDATE
USING (auth.uid() = id);
```

### Admin Access

```sql
-- Admins (domain: @silent-agents.com) can see all
CREATE POLICY "Admins can view all users"
ON users FOR SELECT
USING (
    auth.jwt() ->> 'email' LIKE '%@silent-agents.com'
);
```

### Service Role Bypass

Backend uses `service_role` key which bypasses RLS for internal operations.

---

## Repositories

### Repository Pattern

**File**: `nikita/db/repositories/`

| Repository | Model | Key Methods |
|------------|-------|-------------|
| UserRepository | User | `get_by_telegram_id`, `get_by_phone`, `create_with_metrics` |
| ConversationRepository | Conversation | `create`, `mark_completed`, `detect_stuck` |
| ThreadRepository | NikitaThread | `get_open_threads`, `resolve_thread` |
| SummaryRepository | NikitaSummary | `get_today_summary`, `create_daily` |
| GeneratedPromptRepository | GeneratedPrompt | `create`, `get_recent` |
| JobExecutionRepository | JobExecution | `log_stage`, `get_failed` |

### Example Repository

**File**: `nikita/db/repositories/user_repository.py:1-150`

```python
# nikita/db/repositories/user_repository.py:30-80

class UserRepository:
    """Repository for User operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create_with_metrics(
        self,
        telegram_id: int,
        display_name: str,
        **kwargs
    ) -> User:
        """Create user with associated metrics."""
        user = User(
            telegram_id=telegram_id,
            display_name=display_name,
            **kwargs
        )
        self.session.add(user)
        await self.session.flush()

        metrics = UserMetrics(
            user_id=user.id,
            relationship_score=50.0,
            chapter_number=1,
            engagement_state="CALIBRATING"
        )
        self.session.add(metrics)

        return user
```

---

## Key File References

| File | Line | Purpose |
|------|------|---------|
| `nikita/db/models/user.py` | 1-180 | User + UserMetrics models |
| `nikita/db/models/conversation.py` | 1-100 | Conversation model |
| `nikita/db/models/context.py` | 1-150 | Thread, Thought, Summary |
| `nikita/db/repositories/user_repository.py` | 1-150 | User CRUD |
| `nikita/db/migrations/versions/` | * | All migrations |
| `nikita/memory/graphiti_client.py` | 1-200 | Neo4j/Graphiti client |

---

## Related Documentation

- **Context Collection**: [CONTEXT_ENGINE.md](CONTEXT_ENGINE.md)
- **Pipeline Processing**: [PIPELINE_STAGES.md](PIPELINE_STAGES.md)
- **Authentication**: [AUTHENTICATION.md](AUTHENTICATION.md)
- **Testing**: [TESTING_STRATEGY.md](TESTING_STRATEGY.md)
