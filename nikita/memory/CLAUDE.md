# memory/ - Knowledge Graph System

## Purpose

Temporal knowledge graphs using Graphiti + Neo4j Aura for Nikita's memory system.

## Current State

**Phase 1 ✅**: NikitaMemory class complete, ready for use

```
memory/
├── graphiti_client.py   ✅ COMPLETE (243 lines)
│   └─ NikitaMemory class
│       ├─ add_episode()
│       ├─ search_memory()
│       ├─ get_context_for_prompt()
│       ├─ add_user_fact()
│       ├─ add_relationship_episode()
│       └─ add_nikita_event()
└── graphs/              ⚠️ Stub only
    ├── nikita_graph.py      # Graph type definitions (TODO)
    ├── user_graph.py        # Graph type definitions (TODO)
    └── relationship_graph.py # Graph type definitions (TODO)
```

## Three-Graph Architecture

### Nikita Graph
**Purpose**: Her simulated life, exists independently of player

**Entity Types** (to define):
- WorkProject: name, status, stress_level, deadline
- LifeEvent: description, date, emotional_impact
- Opinion: topic, stance, intensity
- Memory: description, when_formed, emotional_weight

**Example Episodes**:
```python
await memory.add_nikita_event(
    description="Finished 36-hour security audit for finance client",
    event_type="work_project",
)
```

### User Graph
**Purpose**: What Nikita knows about the player

**Entity Types**:
- UserFact: fact, confidence, when_learned, source_message
- UserPreference: category, preference, strength
- UserPattern: pattern_type, description, first_observed

**Example**:
```python
await memory.add_user_fact(
    fact="User works in finance",
    confidence=0.9,
    source_message="I work at Goldman Sachs",
)
```

### Relationship Graph
**Purpose**: Shared history between Nikita and player

**Entity Types**:
- Episode: description, date, emotional_significance
- Milestone: type, chapter, date
- InsideJoke: reference, origin_context, usage_count
- Conflict: type, date, resolution_status, impact

**Example**:
```python
await memory.add_relationship_episode(
    description="We joked about her 'Trust me, I'm a hacker' mug",
    episode_type="inside_joke",
)
```

## Key Methods

### add_episode (graphiti_client.py:54-79)
```python
await memory.add_episode(
    content="User mentioned they code in Python",
    source="user_message",
    graph_type="user",  # nikita | user | relationship
)
```

### search_memory (graphiti_client.py:81-118)
```python
results = await memory.search_memory(
    query="recent conversations about work",
    graph_types=["user", "relationship"],
    limit=10,
)
# Returns: [{"graph_type": "user", "fact": "...", "created_at": ...}]
```

### get_context_for_prompt (graphiti_client.py:120-164)
```python
context = await memory.get_context_for_prompt(
    user_message="How's your work going?",
    max_memories=5,
)
# Returns formatted string:
# [2025-01-14] (My life) Finished security audit...
# [2025-01-13] (Our history) We discussed my job stress...
```

## Integration Pattern

```python
from nikita.memory.graphiti_client import get_memory_client

# Initialize for user
memory = await get_memory_client(user_id)

# Search for context
context = await memory.get_context_for_prompt(user_message)

# Inject into LLM prompt
prompt = f"""
RELEVANT MEMORIES:
{context}

USER MESSAGE: {user_message}
"""

# After response, update memories
await memory.add_user_fact("User likes dark humor", confidence=0.8)
await memory.add_relationship_episode("We shared a dark joke about...")
```

## Neo4j Aura Configuration

**Local Development**:
```bash
# Use Neo4j Aura Free Tier (managed, no local Docker needed)
# Or run local Neo4j: docker run -p 7687:7687 neo4j:latest
```

**Production**: Neo4j Aura (Managed)
- Free tier: 200k nodes, 400k relationships
- Professional tier: Pay-per-use

**Settings** (nikita/config/settings.py):
```python
neo4j_uri: str = Field(
    description="Neo4j Aura connection URI",
)
neo4j_user: str = Field(default="neo4j")
neo4j_password: SecretStr = Field(description="Neo4j password")
```

## Graphiti Dependencies

```python
# Uses Anthropic for LLM analysis
from graphiti_core.llm_client import AnthropicClient

llm_client = AnthropicClient(
    api_key=settings.anthropic_api_key,
    model="claude-sonnet-4-5-20250929",
)

# Uses OpenAI for embeddings
from graphiti_core.embedder import OpenAIEmbedder

embedder = OpenAIEmbedder(
    api_key=settings.openai_api_key,
    model="text-embedding-3-small",
)
```

## Documentation

- [Memory Architecture](../../memory/architecture.md#memory--knowledge-layer-phase-1-)
- [Integrations: Neo4j Aura](../../memory/integrations.md#neo4j-aura-integration-graphiti)
- [User Journeys: Memory Pattern](../../memory/user-journeys.md#3-memory-persistence-pattern)
