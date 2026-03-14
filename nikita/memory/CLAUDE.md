# memory/ - Memory System

## Purpose

pgVector-based memory backend using Supabase for Nikita's memory system.

## Current State

**Spec 042 ✅**: SupabaseMemory class complete, replaces Neo4j/Graphiti

```
memory/
└── supabase_memory.py          ✅ COMPLETE (38 tests)
    └─ SupabaseMemory class
        ├─ add_fact()           # Cosine-similarity dedup (0.95 threshold)
        ├─ search()             # pgVector semantic search
        └─ get_recent()         # Time-ordered retrieval
# migrate_neo4j_to_supabase.py deleted (DC-003 — unrunnable, graphiti_client gone)
```

## Memory Schema (pgVector)

**Table**: `memory_facts` (Spec 042)

```sql
CREATE TABLE memory_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    fact TEXT NOT NULL,
    fact_type TEXT NOT NULL CHECK (fact_type IN ('user', 'nikita', 'relationship')),
    embedding vector(1536) NOT NULL,  -- pgVector
    -- Note: no hash column (MP-005 fix) — dedup is cosine-similarity based
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_memory_facts_embedding
    ON memory_facts USING ivfflat (embedding vector_cosine_ops);
```

**Fact Types**:
- `user`: What Nikita knows about the player ("User works in finance")
- `nikita`: Her simulated life ("Finished 36-hour security audit")
- `relationship`: Shared history ("We joked about her hacker mug")

**Deduplication**: Cosine-similarity threshold 0.95 (Spec 102 FR-001) — `add_fact()`
generates ONE embedding and passes it to `find_similar()` internally. If a fact with
similarity > 0.95 exists, the old fact is superseded (not deleted, `is_active=False`).

**Search**: pgVector cosine similarity for semantic search

## Key Methods

### add_fact (supabase_memory.py)
```python
await memory.add_fact(
    fact="User mentioned they code in Python",
    user_id=user_id,
    fact_type="user",  # user | nikita | relationship
)
# Auto-deduplication via cosine-similarity 0.95 (single embedding, Spec 102 FR-001)
```

### search (supabase_memory.py)
```python
results = await memory.search(
    query="recent conversations about work",
    user_id=user_id,
    fact_types=["user", "relationship"],
    limit=10,
)
# Returns: [MemoryFact(fact="...", fact_type="user", created_at=...)]
```

### get_recent (supabase_memory.py)
```python
recent = await memory.get_recent(
    user_id=user_id,
    limit=20,
)
# Returns: Time-ordered list of MemoryFact objects
```

## Integration Pattern (Spec 042)

```python
from nikita.memory.supabase_memory import SupabaseMemory

# Initialize with session
memory = SupabaseMemory(session)

# Search for context
facts = await memory.search(
    query=user_message,
    user_id=user_id,
    limit=5,
)

# Format for LLM prompt
context = "\n".join([f"- {f.fact}" for f in facts])

prompt = f"""
RELEVANT MEMORIES:
{context}

USER MESSAGE: {user_message}
"""

# After response, update memories
await memory.add_fact("User likes dark humor", user_id, fact_type="user")
await memory.add_fact("We shared a dark joke about...", user_id, fact_type="relationship")
```

## Supabase pgVector Configuration

**Database Setup**:
```sql
-- Enable pgVector extension (Supabase Dashboard → Database → Extensions)
CREATE EXTENSION IF NOT EXISTS vector;

-- Migration 0009 creates memory_facts table
-- See: nikita/db/migrations/versions/20260207_0009_spec042_memory_tables.py
```

**Production**: Supabase
- Unlimited vector storage (within plan limits)
- Auto-scaling with connection pooling
- No separate database to manage

**Settings** (nikita/config/settings.py):
```python
database_url: str = Field(
    description="PostgreSQL connection string (pgVector enabled)",
)
openai_api_key: str = Field(
    description="OpenAI API key for embeddings",
)
embedding_model: str = Field(
    default="text-embedding-3-small",
)
```

## Dependencies (Spec 042)

```python
# Uses OpenAI for embeddings
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.openai_api_key)

async def embed_text(text: str) -> list[float]:
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding
```

## Documentation

- [Memory Architecture](../../memory/architecture.md#unified-pipeline-architecture-spec-042)
- [Integrations: Supabase pgVector](../../memory/integrations.md#memory-backend-spec-042-supabase-pgvector)
- [Migration Guide](../../specs/042-unified-pipeline/spec.md)
