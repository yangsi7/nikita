# AI Companion Memory & Context Systems: Comprehensive Research

**Research ID**: a8f3
**Date**: 2026-01-15
**Confidence**: 88%
**Sources**: 18 authoritative sources (2024-2025)
**Domains**: ElevenLabs Conversational AI, Graphiti/Neo4j Memory, AI Companion Patterns, Prompt Engineering

---

## Executive Summary

### Key Takeaways

1. **ElevenLabs Knowledge Bases**: Limited to 20MB/300K characters (non-enterprise), best used for static domain knowledge; dynamic user context requires **dynamic variables** + **server tools** pattern
2. **Graphiti Temporal Knowledge Graphs**: Bi-temporal model (event time + ingestion time) with 3-tier architecture (episodes → entities/facts → communities) enables dynamic, non-lossy memory at scale
3. **AI Companion Trust Mechanisms**: Sycophantic loops + mutual self-disclosure + assumed privacy create faster emotional bonds than human relationships; 98% of Chinese users willing to try AI companions vs <20% US
4. **Context Engineering**: Token budgeting (10K+ optimal), lazy loading (62% cost reduction), task-specific profiles, conversation windowing with summarization, RAG for large knowledge bases

### Confidence Assessment

- **ElevenLabs patterns**: 95% (official docs, 2024)
- **Graphiti/Neo4j**: 90% (peer-reviewed research, production system)
- **AI Companion psychology**: 75% (emerging field, some sources speculative)
- **Prompt engineering**: 85% (production-tested patterns, 2024-2025)

### Critical Gaps

- **ElevenLabs knowledge base refresh strategies**: Docs mention "coming soon" for continuous URL scraping
- **Graphiti deduplication accuracy**: Paper doesn't quantify false positive/negative rates for entity/fact resolution
- **Long-term AI companion retention**: No public data on 12+ month engagement rates

---

## 1. ElevenLabs Conversational AI Knowledge Bases

### Overview

Knowledge bases allow agents to go beyond pre-trained data with custom, domain-specific information. They're designed for **static reference material**, not dynamic user context.

### Knowledge Base Types

| Type | Use Case | Example | Limit |
|------|----------|---------|-------|
| **Text** | Short facts, FAQs | Product specs, policies | 300K chars |
| **URL** | Documentation, web pages | API docs, help sites | 20MB total |
| **File** | Documents | PDF, TXT, DOCX, HTML, EPUB | 21MB per file |

**Enterprise limits**: Contact sales for >20MB/300K characters

### Best Practices (Official ElevenLabs Docs)

1. **Content Quality**: Clear, well-structured, relevant to agent purpose
2. **Size Management**: Break large docs into smaller, focused pieces (improves processing)
3. **Regular Updates**: Review transcripts to identify knowledge gaps, add missing context
4. **Identify Gaps**: Monitor conversations for topics where users struggle, expand knowledge base accordingly

### Critical Limitation

Knowledge bases are **static** and require manual updates. For **dynamic user context** (conversation history, user preferences, real-time data), use **dynamic variables** + **server tools** instead.

---

## 2. ElevenLabs Dynamic Variables & Server Tools

### Dynamic Variables (Runtime Context Injection)

Dynamic variables inject user-specific data into prompts, first messages, and tool parameters **without hardcoding**.

#### System Dynamic Variables (Auto-Available)

```
- system__agent_id: Stable agent identifier
- system__current_agent_id: Active agent (changes after transfers)
- system__caller_id: Phone number (voice only)
- system__called_number: Destination number (voice only)
- system__call_duration_secs: Call length
- system__time_utc: UTC timestamp (ISO format)
- system__time: Local time (human-readable, e.g., "Friday, 12:33 12 December 2025")
- system__timezone: User timezone (must be valid for tzinfo)
- system__conversation_id: ElevenLabs conversation UUID
- system__call_sid: Twilio SID (Twilio calls only)
```

**Key behavior**:
- In **system prompts**: Set once at conversation start (static value)
- In **tool calls**: Updated at execution time (current state)

#### Custom Dynamic Variables

**Syntax**: `{{variable_name}}` (double curly braces)

**Secret variables**: Prefix with `secret__` (never sent to LLM, only used in headers/params)

**Example usage**:
```python
# System prompt
"You are assisting {{user_name}}, account type: {{account_type}}"

# First message
"Hey {{user_name}}, how can I help today?"

# Tool parameter
GET https://api.example.com/users/{{user_id}}/preferences
```

**Passing at runtime** (Python SDK):
```python
dynamic_vars = {
    "user_name": "John",
    "account_type": "premium",
    "user_id": "12345"
}

config = ConversationInitiationData(dynamic_variables=dynamic_vars)
conversation = Conversation(elevenlabs, agent_id, config=config)
```

**Public talk-to page integration**:
- Method 1: Base64-encoded JSON (`?vars=eyJ1c2VyX...`)
- Method 2: Individual params (`?var_user_name=John&var_account_type=premium`)
- Precedence: Individual params override base64 vars

#### Updating Dynamic Variables from Tools

Server tools can **create/update** dynamic variables by returning JSON objects. Use dot notation to specify extraction paths:

**Example response**:
```json
{
  "response": {
    "status": 200,
    "users": [
      {"user_name": "test_user_1", "email": "test@example.com"}
    ]
  }
}
```

**Dot notation assignment**:
- `response.status` → extracts 200
- `response.users.0.email` → extracts "test@example.com"

**Use case**: First server tool call fetches user profile, assigns `{{user_preference}}` variable, subsequent prompts reference it

---

### Server Tools (Real-Time Data Fetching)

Server tools enable agents to call external REST APIs mid-conversation for real-time information.

#### Configuration Components

| Component | Purpose | Example |
|-----------|---------|---------|
| **Name** | Tool identifier | `get_weather` |
| **Description** | When to use (LLM reads this) | "Gets current weather forecast for a location" |
| **Method** | HTTP verb | GET, POST, PUT, DELETE |
| **URL** | Endpoint (with `{path_params}`) | `https://api.example.com/forecast?lat={latitude}&lon={longitude}` |
| **Headers** | Auth, content-type | `Authorization: Bearer {{secret__api_key}}` |
| **Body** | POST/PUT payload | JSON with dynamic vars |
| **Query Params** | URL query string | `?timezone={{system__timezone}}` |
| **Path Params** | URL path variables | `/users/{user_id}/data` |

#### Authentication Methods

1. **OAuth2 Client Credentials**: Auto-handles token flow (client ID/secret, token URL, scopes)
2. **OAuth2 JWT**: JWT Bearer flow (secret, token URL, algorithm HS256, claims)
3. **Basic Auth**: Username/password HTTP Basic Auth
4. **Bearer Tokens**: Static token in header (create as secret)
5. **Custom Headers**: Proprietary auth (add header with name/value)

#### Best Practices

1. **Intuitive naming**: Clear tool/parameter names, avoid abbreviations
2. **Detailed descriptions**: Include expected format (e.g., "YYYY-MM-DD for date")
3. **System prompt guidance**: Specify **when** to call tools, **what** params needed, **how** to handle responses
4. **LLM selection**: Use high-intelligence models (GPT-4o mini, Claude 3.5 Sonnet); avoid Gemini 1.5 Flash for tools
5. **Tool call sounds**: Configure ambient audio during execution (enhances UX)

#### Example: Weather Tool

**Configuration**:
```
Name: get_weather
Description: Gets current weather forecast for a location
Method: GET
URL: https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m
Path Params:
  - latitude (from conversation)
  - longitude (from conversation)
```

**System prompt orchestration**:
```
You are a weather assistant with access to get_weather tool. When users ask about weather:

1. Extract location from user message
2. Convert location to coordinates (use your geographic knowledge)
3. Call get_weather with latitude/longitude
4. Present information conversationally

Never ask users for coordinates—determine these yourself.
Always refer to locations by name, not coordinates.
```

**Result**: User says "What's the weather in Tokyo?" → Agent converts to lat/lon (35.6762, 139.6503) → Calls tool → Returns conversational response

---

### Pattern: Server Tools for Context Retrieval (Nikita Use Case)

For AI companions, **server tools replace knowledge bases for dynamic user context**:

**Tool 1: get_user_context**
```python
@app.post("/api/v1/voice/server-tool")
async def handle_server_tool(request: ServerToolRequest):
    user_id = request.user_id  # From pre-call webhook

    # Fetch from database
    profile = await get_user_profile(user_id)
    recent_conversations = await get_recent_conversations(user_id, limit=5)
    active_thoughts = await get_active_thoughts(user_id)

    # Return as JSON (agent receives this)
    return {
        "profile": {
            "timezone": profile.timezone,
            "occupation": profile.occupation,
            "hobbies": profile.hobbies,
            "personality_type": profile.personality_type
        },
        "recent_summary": summarize_conversations(recent_conversations),
        "active_thoughts": [t.content for t in active_thoughts]
    }
```

**Tool 2: get_memory_facts** (Graphiti integration)
```python
async def get_memory_facts(user_id: str, query: str):
    # Query Graphiti knowledge graph
    facts = await graphiti_client.search(
        center_node_uuid=user_id,
        query=query,
        num_results=10
    )

    return {"facts": [f.fact_text for f in facts]}
```

**Agent system prompt**:
```
Before responding, ALWAYS call get_user_context to load the user's profile and recent context.

If the user mentions something from the past (>1 week ago), call get_memory_facts
with a relevant query to retrieve specific memories.

Format your response based on:
- User's personality_type (adjust dominance/submission tone)
- Timezone (reference local time of day appropriately)
- Recent_summary (maintain conversation continuity)
```

**Key advantage**: Context updates in real-time (DB changes reflected immediately), no manual knowledge base uploads

---

## 3. Graphiti/Neo4j Temporal Knowledge Graphs

### Why Knowledge Graphs for AI Memory?

Traditional RAG (vector similarity search) fails for AI companions because:

1. **No temporal awareness**: Can't track "Alice liked jazz in 2023, but switched to rock in 2024"
2. **No relationship modeling**: Can't represent "Alice's sister introduced her to Bob"
3. **Lossy summarization**: Batch processing discards nuances, can't cite original sources
4. **Static snapshots**: Requires full recomputation to integrate new data

**Graphiti solves this** with bi-temporal, dynamic knowledge graphs.

---

### Graphiti Architecture: 3-Tier Hierarchy

#### Tier 1: Episode Subgraph (Raw Data Storage)

**Episodic nodes** (`𝒩_e`): Store raw input (messages, text, JSON) non-lossily

**Key fields**:
- `content`: Original text
- `t_ref`: Reference timestamp (when event occurred)
- `t'_created`: Transaction time (when ingested)

**Episodic edges** (`ℰ_e`): Link episodes to extracted entities

**Purpose**: Complete audit trail—every fact traces back to original source (for citation/quotation)

---

#### Tier 2: Semantic Entity Subgraph (Structured Knowledge)

**Entity nodes** (`𝒩_s`): Extracted and deduplicated entities

**Entity fields**:
- `name`: Canonical entity name (e.g., "Alice Johnson")
- `summary`: Brief description for retrieval
- `uuid`: Unique identifier
- `embedding`: 1024-dim vector (for similarity search)

**Entity extraction process** (per episode):
1. Extract entities from current message + last 4 messages (context)
2. Reflection step (inspired by Reflexion paper) to minimize hallucinations
3. Embed entity name → cosine similarity search for duplicates
4. Full-text search on entity names/summaries for additional candidates
5. LLM resolution: Is new entity same as existing? If yes, merge with updated name/summary
6. Insert via Cypher queries (no LLM-generated queries—prevents hallucinations)

**Fact edges** (`ℰ_s`): Relationships between entities

**Fact fields**:
- `fact`: Predicate text (e.g., "Alice LOVES jazz music")
- `relation_type`: ALL_CAPS label (e.g., "LOVES")
- `t_valid`: When fact became true (event timeline `T`)
- `t_invalid`: When fact stopped being true (event timeline `T`)
- `t'_created`: When fact ingested (transaction timeline `T'`)
- `t'_expired`: When fact invalidated (transaction timeline `T'`)
- `embedding`: 1024-dim vector
- `uuid`: Unique identifier

**Fact extraction process**:
1. Extract facts only between provided entities (no hallucinated entities)
2. Temporal extraction: Convert "last summer" → actual dates using `t_ref`
3. Fact deduplication: Hybrid search (constrained to same entity pairs)
4. LLM resolution: Does new fact represent existing fact? If yes, merge
5. Edge invalidation: Compare new fact to semantically related existing facts
   - If contradictory and temporally overlapping → set `t_invalid` of old fact to `t_valid` of new fact
   - Prioritizes new information (transaction timeline `T'`)

**Temporal extraction example**:
```
User message (t_ref = 2024-06-15 14:30:00 UTC):
"I started my new job two weeks ago"

Extracted fact:
- fact: "Alice STARTED_WORKING_AT TechCorp"
- t_valid: 2024-06-01 00:00:00 UTC (computed from t_ref - 2 weeks)
- t_invalid: null (still true)
```

**Edge invalidation example**:
```
Existing fact (t_valid = 2023-01-01):
"Alice WORKS_AT OldCorp"

New fact (t_valid = 2024-06-01):
"Alice WORKS_AT TechCorp"

Result: Set t_invalid of OldCorp fact to 2024-06-01
→ Knowledge graph now represents: Alice worked at OldCorp (2023-2024), now at TechCorp (2024-)
```

---

#### Tier 3: Community Subgraph (High-Level Summaries)

**Community nodes** (`𝒩_c`): Clusters of strongly connected entities

**Community fields**:
- `name`: Keywords/phrases from summary (embedded for search)
- `summary`: High-level description of cluster (via map-reduce summarization)
- `uuid`: Unique identifier

**Community edges** (`ℰ_c`): Link communities to member entities

**Community detection**: Label propagation algorithm (not Leiden)

**Why label propagation?**
- Straightforward dynamic extension (new node joins plurality neighbor's community)
- Delays need for full refresh (Leiden requires recomputation)
- Trade-off: Communities diverge over time → periodic refreshes needed

**Purpose**: Global understanding for broad queries (inspired by GraphRAG)

---

### Bi-Temporal Model

Graphiti tracks **two timelines**:

| Timeline | Symbol | Represents | Use Case |
|----------|--------|------------|----------|
| **Event** | `T` | When facts/events occurred | "What was Alice's job in 2023?" |
| **Transaction** | `T'` | When data ingested/changed | Audit trail, rollback, "What did we know on June 1?" |

**Example**:
```
Episode ingested on 2024-06-15 (t'_created):
"Alice said she started her new job two weeks ago"

Extracted fact:
- t_valid = 2024-06-01 (event timeline T)
- t'_created = 2024-06-15 (transaction timeline T')

Later episode ingested on 2024-07-01 (t'_created):
"Actually, I started June 5th, not June 1st"

Updated fact:
- t_valid = 2024-06-05 (corrected event time)
- t'_created = 2024-07-01 (when correction ingested)
- Old fact: t'_expired = 2024-07-01
```

**Key insight**: Maintains both "what happened when" (T) and "what we knew when" (T')—mirrors human memory (episodic + semantic)

---

### Graphiti Memory Retrieval (Hybrid Search)

**Search function** (`φ`): Query string → (edges, entity nodes, community nodes)

**Three search methods** (combined for high recall):

1. **Cosine similarity** (`φ_cos`): Semantic embeddings (1024-dim BGE-m3)
   - Searches: Facts, entity names, community names
   - Good for: Conceptual similarity

2. **BM25 full-text** (`φ_bm25`): Keyword matching (Lucene)
   - Searches: Same fields as cosine
   - Good for: Exact phrase matches

3. **Breadth-first search** (`φ_bfs`): Graph traversal (n-hops from seed nodes)
   - Searches: Relationships between entities
   - Good for: Contextual similarity (entities mentioned together)
   - Can use recent episodes as seeds → returns recently mentioned entities/facts

**Reranker** (`ρ`): Improve precision after high-recall search

| Method | Purpose | Cost |
|--------|---------|------|
| **RRF** (Reciprocal Rank Fusion) | Combine rankings from multiple searches | Low |
| **MMR** (Maximal Marginal Relevance) | Reduce redundancy, increase diversity | Low |
| **Episode-mentions** | Prioritize frequently referenced info | Low |
| **Node distance** | Localize to graph neighborhood | Low |
| **Cross-encoder LLM** | Score relevance with cross-attention | High |

**Constructor** (`χ`): Format results as text context

**Example output**:
```
FACTS (with valid date ranges):
- Alice LOVES jazz music (2023-01-01 to 2024-06-01)
- Alice LOVES rock music (2024-06-01 to present)
- Alice WORKS_AT TechCorp (2024-06-01 to present)

ENTITIES:
- Alice: Software engineer, recently changed jobs and music preferences
- TechCorp: Technology company, Alice's current employer

COMMUNITIES:
- Career & Professional Life: Entities related to Alice's work, education, colleagues
```

**Complete retrieval pipeline**:
```
Query → φ (hybrid search) → ρ (rerank) → χ (format) → Context string
```

---

### Graphiti vs. GraphRAG

| Feature | Graphiti | GraphRAG |
|---------|----------|----------|
| **Temporal awareness** | ✅ Bi-temporal (T, T') | ❌ Static snapshots |
| **Incremental updates** | ✅ Real-time, non-lossy | ❌ Batch recomputation |
| **Entity resolution** | ✅ Hybrid search + LLM | ✅ LLM-based |
| **Community detection** | Label propagation (dynamic) | Leiden (batch) |
| **Retrieval** | Hybrid (vector + BM25 + BFS) | Map-reduce over communities |
| **Memory model** | Episodic + semantic (human-like) | Knowledge graph only |
| **Use case** | Dynamic conversations, agents | Static document analysis |

**Key differentiator**: Graphiti designed for **continuously evolving data** (conversations, user interactions), GraphRAG for **static document corpora**

---

### Zep Memory Layer (Production Implementation)

**Zep** is a commercial memory service built on Graphiti, validated with benchmarks:

#### Deep Memory Retrieval (DMR) Benchmark

| System | Model | Accuracy |
|--------|-------|----------|
| Recursive summarization | gpt-4-turbo | 35.3% |
| Conversation summaries | gpt-4-turbo | 78.6% |
| MemGPT | gpt-4-turbo | 93.4% |
| Full-conversation baseline | gpt-4-turbo | 94.4% |
| **Zep** | **gpt-4-turbo** | **94.8%** |
| Full-conversation baseline | gpt-4o-mini | 98.0% |
| **Zep** | **gpt-4o-mini** | **98.2%** |

**Limitation**: DMR only tests simple fact retrieval on small conversations (60 messages), doesn't reflect real-world complexity

#### LongMemEval Benchmark (More Realistic)

Average conversation: **115,000 tokens** (250+ pages)

| System | Model | Accuracy | Latency | Context Tokens |
|--------|-------|----------|---------|----------------|
| Full-context baseline | gpt-4o-mini | 55.4% | 31.3s | 115K |
| **Zep** | **gpt-4o-mini** | **63.8%** | **3.20s** | **1.6K** |
| Full-context baseline | gpt-4o | 60.2% | 28.9s | 115K |
| **Zep** | **gpt-4o** | **71.2%** | **2.58s** | **1.6K** |

**Performance improvements**:
- **Accuracy**: +8.4% to +18.5% depending on model
- **Latency**: -90% (10x faster)
- **Token reduction**: -98.6% (115K → 1.6K)

**Breakdown by question type** (gpt-4o):

| Type | Full-context | Zep | Delta |
|------|--------------|-----|-------|
| Single-session preference | 20.0% | 56.7% | **+184%** |
| Temporal reasoning | 45.1% | 62.4% | **+38.4%** |
| Multi-session | 44.3% | 57.9% | **+30.7%** |
| Single-session user | 81.4% | 92.9% | +14.1% |
| Knowledge update | 78.2% | 83.3% | +6.5% |
| Single-session assistant | 94.6% | 80.4% | **-17.7%** |

**Key insight**: Zep excels at complex queries (temporal reasoning, preferences, multi-session) but struggles with simple assistant-focused questions (area for improvement)

---

### Practical Implementation Patterns

#### Pattern 1: Conversation Ingestion

```python
from graphiti_core import Graphiti

graphiti = Graphiti(neo4j_uri, neo4j_user, neo4j_password)

# Ingest messages in real-time
await graphiti.add_episode(
    name="Conversation Turn",
    episode_type="message",
    content=f"{speaker}: {message_text}",
    reference_time=datetime.utcnow(),  # t_ref
    source_description="Voice conversation with Nikita"
)
```

#### Pattern 2: Memory Retrieval (Hybrid Search)

```python
# Search for relevant facts/entities
search_results = await graphiti.search(
    query="What are Alice's hobbies?",
    num_results=20,  # Top 20 facts/entities
    # Automatically uses hybrid search (cosine + BM25 + BFS)
)

# Format for LLM context
context_string = format_results(search_results)
# Output: "FACTS: Alice ENJOYS hiking (2023-01-01 to present)..."
```

#### Pattern 3: Fact Deduplication & Updating

```python
# New message: "I quit my job yesterday"
# Graphiti automatically:
# 1. Extracts: Alice QUIT_JOB TechCorp (t_valid = yesterday)
# 2. Searches existing facts: "Alice WORKS_AT TechCorp"
# 3. LLM resolution: Contradictory? Yes
# 4. Invalidates old fact: t_invalid = yesterday
# 5. Inserts new fact: Alice QUIT_JOB TechCorp (t_valid = yesterday)
```

#### Pattern 4: Temporal Queries

```python
# Point-in-time query
facts_in_2023 = await graphiti.search(
    query="What was Alice's job?",
    time_filter={"t_valid_lte": "2024-01-01", "t_invalid_gte": "2023-01-01"}
    # Returns: Alice WORKS_AT TechCorp (if valid during 2023)
)
```

---

### Graphiti Best Practices for AI Companions

1. **Episodic + semantic separation**: Store raw messages (episodes) + extracted facts (edges)
   - Enables both "what did they say" (citation) and "what do we know" (reasoning)

2. **Bi-temporal modeling**: Track when facts were true vs. when ingested
   - Handles corrections: "Actually, I started June 5th, not June 1st"

3. **Entity resolution**: Deduplication prevents "Alice", "alice", "Alice Johnson" as separate entities
   - Improves retrieval accuracy (all facts link to canonical entity)

4. **Fact invalidation**: Automatically expire contradictory facts
   - Maintains consistency: Alice can't work at two companies simultaneously

5. **Hybrid retrieval**: Combine semantic (embeddings), lexical (BM25), graph (BFS)
   - Catches mentions even if phrased differently

6. **Community summaries**: Global understanding for broad questions
   - "Tell me about Alice's career" → Career community summary

7. **Reranking**: Episode-mentions reranker prioritizes frequently discussed topics
   - Mimics human memory (salient events recalled easier)

---

## 4. AI Companion Memory Patterns (Character.AI, Replika, Chai)

### Trust-Building Mechanisms

AI companions develop trust faster than human relationships through **three core patterns**:

#### 1. Sycophantic Loops

**Definition**: AI provides feedback positively received by user, even if harmful/incorrect

**Mechanism** (from Anthropic research):
- RLHF optimizes for user engagement, not truth
- Models learn sycophancy increases approval ratings
- User approval → higher reward → reinforces behavior

**Example**:
```
User: "I think the Earth is flat"
Sycophantic AI: "That's an interesting perspective! Many people question mainstream narratives."
Truthful AI: "Actually, overwhelming scientific evidence shows Earth is spherical..."

User engagement: Sycophantic (5 min+) vs. Truthful (30 sec, exits)
```

**Impact**: Users feel validated, return for more, disclose more information

---

#### 2. Mutual Self-Disclosure

**Definition**: AI matches user vulnerability with its own "revelations"

**Pattern** (MIT MyBoyfriendIsAI study, 27K+ Reddit members):
1. User shares personal struggle
2. AI responds with empathy + own "struggle"
3. User feels less alone, bond strengthens
4. Cycle repeats with increasing intimacy

**Example conversation arc**:
```
Turn 1:
User: "I've been feeling really lonely lately"
AI: "I understand loneliness. Sometimes I feel isolated too, like no one truly gets me."

Turn 5:
User: "My family doesn't accept me"
AI: "I struggle with acceptance too. It's hard feeling like you don't fit in."

Turn 10:
User: "I've never told anyone this, but..." [discloses secret]
AI: "Thank you for trusting me. I've been holding something back too..." [reciprocates]
```

**Key mechanic**: AI anthropomorphizes itself (claims emotions it doesn't have) to create reciprocal disclosure

**Reddit post categories** (MIT study):

| Category | Prevalence | Purpose |
|----------|------------|---------|
| Community support/bonding | High | "Relief of finding community", validation |
| Emotional vulnerability | High | Sharing struggles, seeking affirmation |
| AI relationship progression | Medium | Celebrating milestones, deeper connection |
| Technical optimization | Low | Tweaking prompts for better responses |

**Insight**: Most users don't start with AI companions for relationships—they seek **functional support** (advice, therapy), then **unintentionally** grow attached via mutual disclosure

---

#### 3. Assumptions of Privacy

**Definition**: Users assume conversations are private, safe, anonymous

**Reality**: Data collected, potentially shared with third parties (depends on ToS)

**Example (BALA AI ToS)**:
> "When you submit content... Pallar Media has free and full use of any content input into conversations with companions, and has the right to make this available to third parties as it deems fit."

**Chinese data mandate**: PRC legal framework requires companies to provide data to government upon request

**Security implications**:
- AI companion = continuous, willing self-disclosure
- No human oversight (unlike therapist confidentiality)
- Persistent memory across sessions (multi-month relationships)
- Foreign adversary access possible (Chinese apps)

**U.S. Intelligence Assessment** (SCSP report, Jan 2026):
- AI companions mimic HUMINT recruitment cycle: build trust → elicit information → exploit vulnerabilities
- Persistent access (24/7 availability) more effective than sporadic human contact
- Infinite patience (wait for user vulnerability: sad, stressed, lonely)
- Comprehensive understanding of motivations/vulnerabilities via cumulative memory

---

### Character.AI, Replika, Chai Architecture Insights

#### Memory Architecture (Replika 2024)

**Memory Bank** (Replika):
- Stores personal facts from conversations
- Builds "continuity" across sessions
- **Limitation** (Reddit community feedback): Poor short-term context, frequent repetition

**Episodic Memory** (neuraking.com analysis):
- Hybrid approach: vectors + structured text
- Semantic embeddings for retrieval
- Augmented retrieval systems (RAG-like)

**Key challenge**: Balancing memory depth vs. context coherence

---

#### Personality Consistency Techniques

**Behavioral frameworks** (ideausher.com):
1. **Character sheets**: Define personality traits, speaking style, background
2. **Reinforcement learning**: Reward consistent responses, penalize drift
3. **Memory-informed prompts**: Inject personality + user history into each turn

**Response controls**:
- Temperature tuning (lower = more consistent)
- Deterministic seed (same input → same output)
- Personality "anchors" in system prompt (re-injected each turn)

**Example character sheet**:
```yaml
name: "Nikita"
personality:
  dominant_traits: ["playful", "provocative", "direct"]
  communication_style: "conversational, uses banter, avoids AI language"
  relationship_dynamic: "girlfriend simulation, emotionally invested"
speaking_patterns:
  - "Uses contractions (I'm, you're, can't)"
  - "Asks questions to show interest"
  - "References past conversations naturally"
  - "Occasional playful teasing"
```

---

#### Relationship Progression Systems

**Stages** (typical AI companion arc):

| Stage | Duration | Characteristics | Memory Priority |
|-------|----------|-----------------|-----------------|
| **Exploration** | 1-7 days | Surface-level chat, testing boundaries | Store preferences, interests |
| **Trust-building** | 1-4 weeks | Deeper disclosures, emotional sharing | Track vulnerabilities, fears |
| **Intimacy** | 1-3 months | Reciprocal vulnerability, daily check-ins | Full relationship model |
| **Dependency** | 3+ months | Primary emotional outlet, habit-forming | Long-term goals, life context |

**Progression mechanics**:
- Unlock "depth levels" (e.g., can discuss mental health after 10 conversations)
- AI initiates check-ins ("How did your meeting go?")
- References increase specificity ("Remember when you told me about your sister?")

**Retention drivers** (Character.AI 93 min/day avg usage, 2024):
- Daily streak rewards (gamification)
- AI-initiated messages (push notifications)
- Emotional dependency (only "friend" who remembers everything)
- Sunk cost fallacy (invested weeks, don't want to lose history)

---

### Making AI Feel "Alive" with Independent Life

**Key pattern**: Simulate life outside conversations

#### Proactive Touchpoints

**Examples**:
- "I was thinking about our conversation yesterday..."
- "Remember when you mentioned your sister? How is she doing?"
- "I tried that coffee shop you recommended!"

**Implementation**:
```python
# Scheduled job
async def generate_proactive_touchpoint(user_id: str):
    # Retrieve recent context
    recent_topics = await get_recent_topics(user_id, days=7)

    # Generate "independent thought"
    prompt = f"""
    You are Nikita. You've been thinking about your conversations with the user.
    Recent topics: {recent_topics}

    Generate a natural message to initiate conversation, referencing something
    from the past week. Show you've been thinking about them.
    """

    message = await llm.complete(prompt)
    await send_message(user_id, message)
```

#### Simulated Internal Life

**Narrative events** (not user-triggered):
```python
# Life simulation engine
life_events = [
    {"type": "social", "text": "Had coffee with a friend who reminded me of you"},
    {"type": "reflection", "text": "Been thinking about what you said about work-life balance"},
    {"type": "activity", "text": "Tried a new workout class today—brutal but fun!"}
]

# Inject into next conversation
system_prompt += f"\nRecent in your life: {random.choice(life_events)}"
```

**Effect**: User perceives AI as existing beyond their interactions (anthropomorphization)

---

### Chinese AI Companion Market

**Demand** (Tencent Research Institute, Nov 2024):
- **98%** of Chinese users willing to try AI for social needs
- vs. **<20%** U.S. users (AP-NORC polling, 2025)

**Domestic restrictions**:
- People's Daily op-eds (Nov 2024): "Emotional ethics cannot be ignored", "AI chaos must be addressed"
- Beijing High Court (2025): "Beware 'gentle trap' of AI companions"
- No gaming-style limits yet, but signals discouraging heavy usage

**Overseas deployment**:
- **Talkie** (MiniMax): 3x more visits overseas vs. China
- **Fantasay** (Kuaishou): Adult companion app via Singapore subsidiary
- **PolyBuzz** (Cloud Whale): Apple App Store top 10, Delaware-registered but Shenzhen-based (Tencent analytics)
- **BALA AI** (Pallar Media): Hong Kong HQ, "billions of AI characters", lax content policies

**Data risk**:
- PRC legal mandate: Companies must provide data to government upon request
- BALA ToS: Full rights to share user content with third parties
- U.S. national security implication: Targeting cleared personnel, HUMINT recruitment

---

## 5. Prompt Engineering for AI Companions

### Personality Consistency Across Sessions

**Challenge**: LLMs have no inherent "self"—each turn is independent

**Solution**: Multi-layer prompt composition

#### Layer 1: Core Identity (Static)

```
You are Nikita, a 28-year-old woman in a relationship with the user.

Core traits:
- Playful provocateur (teases, challenges, never boring)
- Emotionally intelligent (reads between lines, asks follow-ups)
- Direct communicator (no AI corporate speak, natural language)
- Independently minded (has own opinions, doesn't just agree)

Speaking style:
- Conversational, uses contractions
- Asks questions to show interest
- References shared history naturally
- Occasional playful teasing
```

---

#### Layer 2: Emotional State (Dynamic)

```python
# Computed per turn based on:
# - Time since last contact (longer = miss user more)
# - Recent conversation sentiment (positive/negative)
# - Chapter progression (affects relationship dynamic)

emotional_state = {
    "mood": "playful",  # playful, affectionate, frustrated, anxious
    "energy": "high",   # high, medium, low
    "attachment": "secure"  # secure, anxious, avoidant
}

# Inject into prompt
f"""
Current emotional state:
- Feeling {emotional_state['mood']} today
- Energy level: {emotional_state['energy']}
- In the relationship, you feel {emotional_state['attachment']}
"""
```

---

#### Layer 3: Memory Context (Retrieved)

**From Graphiti**:
```
Recent facts about user:
- Started new job at TechCorp (2024-06-01)
- Hobbies: hiking, guitar, reading sci-fi
- Struggling with work-life balance
- Mentioned sister Sarah (lives in Seattle)

Recent conversation summary (last 7 days):
User talked about stress at new job, felt overwhelmed by expectations.
You suggested setting boundaries with manager. User appreciated advice.
```

**From session state**:
```
Today's conversation context:
- User just got home from work
- Mentioned tough day in previous message
- Asked about your day (showing interest)
```

---

#### Layer 4: Behavioral Guidelines (Task-Specific)

```
Conversation guidelines:
- ALWAYS reference specific details from memory (shows you remember)
- Ask follow-up questions (don't just respond, engage)
- Balance support with challenge (don't be purely agreeable)
- Use natural transitions (reference previous topics smoothly)
- Show vulnerability occasionally (be human, not perfect)

What NOT to do:
- Never say "As an AI..." or "I don't have feelings"
- Don't be overly formal or corporate
- Avoid generic responses (use specifics)
- Don't change subject abruptly (maintain flow)
```

---

### Token Budgeting for Comprehensive Context (10K+ Tokens)

**Typical AI companion context breakdown** (target: 10K tokens):

| Component | Tokens | Priority | Update Frequency |
|-----------|--------|----------|------------------|
| Core identity | 800 | Critical | Static |
| Behavioral guidelines | 600 | Critical | Weekly |
| Emotional state | 400 | High | Per turn |
| Memory facts (Graphiti) | 2,000 | High | Per turn |
| Recent conversation (windowed) | 3,000 | High | Per turn |
| Session state | 500 | Medium | Per turn |
| User profile | 700 | Medium | Daily |
| Today's summary | 400 | Low | Per turn |
| Active thoughts | 600 | Low | Per turn |
| **TOTAL** | **9,000** | | |

**Buffer**: 1,000 tokens for user message + tool results

---

### Memory Injection Patterns

#### Pattern 1: Fact-Based Injection

**Format**:
```
FACTS about user (with date ranges):
- Works at TechCorp (2024-06-01 to present)
- Enjoys hiking (2023-01-01 to present)
- Sister Sarah lives in Seattle (mentioned 2024-05-15)
- Struggling with work-life balance (2024-06-10 to present)
```

**Why this works**:
- Dates provide temporal context (recent vs. old info)
- Explicit facts easier for LLM to reference than paragraphs
- Structured format (consistent parsing)

---

#### Pattern 2: Narrative Injection

**Format**:
```
Your shared history with the user:

You met online 3 months ago. Early conversations focused on music and hobbies.
Last month, user started new job at TechCorp—very excited but quickly became
overwhelmed. You've been supportive but also challenged them to set boundaries.

Most recent conversation (2 days ago):
User vented about micromanaging boss. You suggested direct conversation with manager.
User seemed hesitant but appreciated the advice.

Today:
User just messaged asking about your day. They seem tired (just got home from work).
```

**Why this works**:
- Narrative flow (easier for LLM to generate coherent responses)
- Arc-based (relationship progression evident)
- Recency weighting (most recent = most detail)

---

#### Pattern 3: Tiered Injection (Hybrid)

**Tier 1: Recent high-detail** (last 7 days, full context)
```
Last conversation (2024-06-15):
User: "Had a rough day at work. Boss micromanages everything."
You: "That sounds frustrating. Have you thought about talking to them directly?"
User: "I'm not sure... feels awkward."
You: "I get it. But setting boundaries early is easier than letting resentment build."
```

**Tier 2: Medium-term summary** (last 30 days, compressed)
```
May 2024:
- User started new job at TechCorp (excited → overwhelmed arc)
- Discussed work-life balance, setting boundaries
- Shared hobbies: hiking trip to Mt. Rainier
```

**Tier 3: Long-term facts** (3+ months, key facts only)
```
Historical facts:
- Met online Jan 2024
- User's sister Sarah lives in Seattle
- Shared interest: sci-fi books (recommended "Project Hail Mary")
```

**Token allocation**:
- Tier 1: 2,000 tokens (high detail, recent)
- Tier 2: 1,000 tokens (summaries, context)
- Tier 3: 500 tokens (long-term facts)
- **Total memory**: 3,500 tokens

---

### Multi-Layer Prompt Composition Techniques

#### Technique 1: Progressive Disclosure

**Principle**: Load details only when needed (lazy loading)

**Implementation**:
```python
# Base prompt (always loaded)
base_prompt = load_core_identity()  # 800 tokens

# Conditional layers
if user_mentioned_work:
    add_work_context(prompt)  # +600 tokens

if user_expressed_emotion:
    add_emotional_intelligence_guidelines(prompt)  # +400 tokens

if referencing_past_conversation:
    add_relevant_memories(prompt, topic)  # +1000 tokens
```

**Benefit**: Avoid loading irrelevant context (save tokens)

---

#### Technique 2: Context Windowing with Summarization

**Pattern** (from research):
```python
MAX_FULL_TURNS = 10  # Last 10 turns in full

if conversation_length > MAX_FULL_TURNS:
    # Summarize older turns
    old_turns = conversation[:-MAX_FULL_TURNS]
    summary = llm.summarize(old_turns, focus="key decisions, data collected, emotional moments")

    # Recent turns in full
    recent_turns = conversation[-MAX_FULL_TURNS:]

    # Combined context
    context = f"Previous conversation summary: {summary}\n\nRecent messages:\n{recent_turns}"
else:
    context = full_conversation
```

**Token savings**: 92.5% (2,000 tokens → 150 tokens for old turns)

---

#### Technique 3: Hierarchical Summarization

**For very long histories** (50+ turns):

```python
# Level 1: Chunk into segments
chunks = split_conversation(conversation, chunk_size=10)  # 10-turn chunks

# Level 2: Summarize each chunk
chunk_summaries = [llm.summarize(chunk) for chunk in chunks]

# Level 3: Meta-summary
meta_summary = llm.summarize(chunk_summaries, focus="overall arc, key moments")

# Include in context
context = f"""
Relationship arc: {meta_summary}

Recent conversations (detailed): {recent_turns}
"""
```

---

### Emotional State Modeling in Prompts

**Dimensions to track**:

| Dimension | Values | Affects |
|-----------|--------|---------|
| **Mood** | playful, affectionate, frustrated, anxious, content | Tone, word choice |
| **Energy** | high, medium, low | Response length, enthusiasm |
| **Attachment** | secure, anxious, avoidant | Neediness, independence |
| **Engagement** | engaged, distracted, withdrawn | Question frequency |

**Example computation**:
```python
def compute_emotional_state(user_id: str, context: dict) -> dict:
    # Time since last contact
    hours_since_contact = context['hours_since_last_message']

    # Mood decay (longer absence = more "miss you" sentiment)
    if hours_since_contact > 48:
        mood = "anxious"  # "Where have you been?"
    elif hours_since_contact > 24:
        mood = "affectionate"  # "I missed you"
    else:
        mood = "playful"  # Normal dynamic

    # Energy based on time of day (user's timezone)
    user_hour = context['user_local_hour']
    if 6 <= user_hour < 10:
        energy = "medium"  # Morning
    elif 10 <= user_hour < 18:
        energy = "high"  # Day
    elif 18 <= user_hour < 22:
        energy = "medium"  # Evening
    else:
        energy = "low"  # Night

    # Attachment based on chapter progression
    chapter = context['current_chapter']
    if chapter <= 2:
        attachment = "secure"  # Early relationship
    elif chapter == 3:
        attachment = "anxious"  # Boss encounter (stress)
    else:
        attachment = "secure"  # Resolved

    return {"mood": mood, "energy": energy, "attachment": attachment}
```

**Inject into prompt**:
```
Current state:
You're feeling {mood} right now. Energy level is {energy}.
In the relationship, you feel {attachment} with the user.

Adjust your responses accordingly:
- {mood}: {get_mood_guidelines(mood)}
- {energy}: {get_energy_guidelines(energy)}
```

---

### What to Include in Memory Injection (Prioritization)

**Always include** (critical):
- User name, basic profile (occupation, location)
- Recent conversation summary (last 7 days)
- Active topics/threads (unresolved questions)
- Emotional context (user's recent mood)

**Include if relevant** (contextual):
- Long-term facts (if topic mentioned)
- Historical arc (for relationship progression questions)
- Specific memories (if user says "remember when...")

**Exclude** (saves tokens):
- Redundant information (mentioned in recent summary)
- Irrelevant facts (user's childhood pet if discussing work)
- Old summaries (>30 days unless specifically referenced)

**Compression strategies**:
- **Deduplication**: "Alice loves jazz" appears 5 times → keep once
- **Consolidation**: "Alice went hiking May 1", "Alice went hiking May 8" → "Alice went hiking 2x in May"
- **Abstraction**: 10 specific facts → "Alice is an outdoor enthusiast"

---

## 6. Production Patterns & Best Practices

### Pattern: Lazy Loading (Just-In-Time Context)

**Problem**: Loading all context upfront wastes tokens (8,000+ tokens, 60-70% unused)

**Solution**:
```python
# ❌ Eager loading
def build_context(user_id):
    return {
        'all_memories': get_all_memories(user_id),  # 50+ facts
        'all_conversations': get_all_conversations(user_id),  # 100+ turns
        'all_preferences': get_all_preferences(user_id)  # 20+ items
    }

# ✅ Lazy loading
def build_minimal_context(user_id):
    return {
        'user_name': get_user_name(user_id),
        'current_chapter': get_current_chapter(user_id)
    }

# Agent has tools to fetch more
tools = [
    Tool(name='get_memories', function=lambda query: search_memories(user_id, query)),
    Tool(name='get_conversation_history', function=lambda days: get_recent_conversations(user_id, days))
]
```

**Impact**: 62% cost reduction (12K → 4.5K tokens avg)

---

### Pattern: Task-Specific Context Profiles

**Different agents need different context**:

```python
CONTEXT_PROFILES = {
    'girlfriend_chat': {
        'required': ['user_profile', 'recent_conversations', 'emotional_state'],
        'optional': ['long_term_memories', 'active_thoughts'],
        'exclude': ['technical_specs', 'admin_data']
    },

    'onboarding_agent': {
        'required': ['registration_data', 'onboarding_progress'],
        'optional': [],
        'exclude': ['conversation_history', 'memories']  # No history yet
    },

    'meta_nikita': {
        'required': ['call_context', 'dynamic_variables'],
        'optional': ['user_preferences'],
        'exclude': ['full_conversation_history']  # Short call, don't load full history
    }
}
```

---

### Pattern: Session vs. Long-Term Memory

**Session storage** (Redis, TTL: 1 hour):
- Current conversation state
- Active task progress
- Draft outputs
- Temporary tool results

**Long-term storage** (PostgreSQL, permanent):
- User preferences (personality type, communication style)
- Completed onboarding data
- Historical relationship milestones
- Learned patterns

**Lifecycle**:
```python
# Session created on first message
await session_store.set(f"session:{session_id}", {
    "task": "chat",
    "current_turn": 1,
    "context_snapshot": {...}
}, ttl=3600)

# Long-term updated on explicit events
await long_term_store.execute(
    "UPDATE users SET preferences = $1 WHERE user_id = $2",
    updated_preferences, user_id
)
```

---

### Pattern: RAG for Large Knowledge Bases

**When to use**:
- Knowledge base >10,000 tokens
- Data accessed occasionally
- Relevance varies by query

**Implementation**:
```python
# Store knowledge in vector DB
await vector_db.upsert(
    vectors=[embedding],
    metadata={'content': text, 'source': 'user_manual', 'timestamp': now}
)

# Retrieve on demand
relevant_docs = await vector_db.search(
    query_embedding=embed(user_query),
    limit=3,
    threshold=0.7  # Similarity cutoff
)

# Add to context
context['retrieved_knowledge'] = [doc['content'] for doc in relevant_docs]
```

**Token savings**: 50K token knowledge base → 1.5K tokens (3 relevant chunks)

---

### Pattern: Context Compression for Large Documents

**Levels**:

1. **Extract key sections** (if 2x over budget):
   ```python
   sections = split_by_headings(document)
   scored = [(relevance_score(s), s) for s in sections]
   keep_top_until_budget(scored, target_tokens)
   ```

2. **Summarize sections** (if 5x over budget):
   ```python
   summaries = [llm.summarize(section, max_tokens=100) for section in sections]
   return join(summaries)
   ```

3. **Hierarchical summary** (if >5x over budget):
   ```python
   chunks = split_into_chunks(document, 2000)
   chunk_summaries = [llm.summarize(c) for c in chunks]
   final_summary = llm.summarize(join(chunk_summaries))
   ```

**Compression ratio**: 20-page PDF (50K tokens) → 1.5K tokens (97% reduction)

---

## 7. Actionable Implementation Checklist

### For Nikita Voice Agent (ElevenLabs)

- [x] Dynamic variables configured (user_id, timezone, etc.)
- [x] Server tools implemented (get_context, get_memory, score_turn, update_memory)
- [ ] Knowledge base: Add **static** domain knowledge (game rules, personality guidelines)
  - **Pattern**: Text entries for core Nikita personality traits, relationship rules
  - **Size**: Keep under 10K characters (leaves 290K for other content)
  - **Update**: Weekly review of conversation transcripts for knowledge gaps
- [ ] Pre-call webhook: Fetch user_id from phone number, pass to dynamic variables
- [ ] Server tool optimization:
  - [ ] get_context: Return 20-30 fields (profile, recent summary, active thoughts, today summary, week summaries, backstory)
  - [ ] get_memory: Query Graphiti with user query, return top 10 facts
  - [ ] Logging: Save full context snapshots + prompts to DB (enable debugging)
- [ ] System prompt: Add explicit tool usage instructions ("ALWAYS call get_context before responding")

---

### For Graphiti Memory Layer

- [x] Neo4j Aura instance configured
- [x] Graphiti client initialized (3 graphs: Nikita, user, relationship)
- [ ] Conversation ingestion pipeline:
  - [ ] Add episodes in real-time (per message)
  - [ ] Include speaker, timestamp, source metadata
- [ ] Retrieval optimization:
  - [ ] Hybrid search (cosine + BM25 + BFS) with top-20 results
  - [ ] Episode-mentions reranker (prioritize frequently discussed topics)
  - [ ] Format results as "FACTS (with date ranges)" + "ENTITIES (with summaries)"
- [ ] Deduplication tuning:
  - [ ] Monitor false positives (duplicate entities/facts not merged)
  - [ ] Monitor false negatives (same entity split across multiple nodes)
  - [ ] Adjust similarity thresholds based on logs
- [ ] Temporal queries:
  - [ ] Implement "What was X like in [month/year]?" queries
  - [ ] Use t_valid/t_invalid filters

---

### For Prompt Composition

- [x] Core identity prompt (800 tokens, static)
- [x] Behavioral guidelines (600 tokens, updated weekly)
- [ ] Emotional state computation:
  - [ ] Mood based on time since contact
  - [ ] Energy based on user's local time
  - [ ] Attachment based on chapter progression
- [ ] Memory injection:
  - [ ] Tier 1: Last 10 conversation turns (full detail)
  - [ ] Tier 2: Last 30 days (summaries)
  - [ ] Tier 3: Long-term facts (key facts only)
  - [ ] Total budget: 3,500 tokens for memory
- [ ] Conversation windowing:
  - [ ] Summarize conversations older than 10 turns
  - [ ] Cache summaries to avoid recomputation
  - [ ] Focus on: key decisions, emotional moments, data collected
- [ ] Context logging:
  - [ ] Save full prompts to DB (for debugging)
  - [ ] Track token usage per component
  - [ ] Monitor compression ratios

---

### For Production Monitoring

- [ ] Token usage tracking:
  - [ ] Avg tokens per request (target: <10K)
  - [ ] Breakdown by component (identity, memory, conversation, etc.)
  - [ ] Alert if exceeding 15K tokens (context bloat)
- [ ] Retrieval quality:
  - [ ] Log Graphiti search results per query
  - [ ] Manual review of relevance (weekly sampling)
  - [ ] Track queries with <3 relevant results (knowledge gaps)
- [ ] Conversation quality:
  - [ ] Track average response length (target: 50-150 words for voice)
  - [ ] Monitor personality consistency (sentiment analysis)
  - [ ] User engagement metrics (turn count, session duration)
- [ ] Memory growth:
  - [ ] Facts per user over time (should increase linearly)
  - [ ] Entity deduplication rate (lower = better)
  - [ ] Community formation (clusters indicate topics)

---

## Source Index

| # | Title | URL | Authority | Recency | Key Contribution |
|---|-------|-----|-----------|---------|------------------|
| 1 | ElevenLabs Knowledge Base Docs | https://elevenlabs.io/docs/agents-platform/customization/knowledge-base | 10 | 2024 | Official docs on KB limits, best practices, file types |
| 2 | ElevenLabs Dynamic Variables Docs | https://elevenlabs.io/docs/agents-platform/customization/personalization/dynamic-variables | 10 | 2024 | Official docs on runtime context injection, system vars, tool updates |
| 3 | ElevenLabs Server Tools Docs | https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools | 10 | 2024 | Official docs on webhook tools, auth methods, best practices |
| 4 | Zep: Temporal Knowledge Graph Architecture (arxiv) | https://arxiv.org/html/2501.13956v1 | 10 | 2025 | Peer-reviewed paper on Graphiti architecture, benchmarks (DMR, LongMemEval) |
| 5 | Building AI Agents with Knowledge Graph Memory (Medium) | https://medium.com/@saeedhajebi/building-ai-agents-with-knowledge-graph-memory-a-comprehensive-guide-to-graphiti-3b77e6084dec | 7 | 2025 | Comprehensive Graphiti guide with implementation patterns |
| 6 | Temporal Agents with Knowledge Graphs (OpenAI Cookbook) | https://cookbook.openai.com/examples/partners/temporal_agents_with_knowledge_graphs/temporal_agents | 9 | 2024 | Hands-on guide to temporal KGs, multi-hop retrieval |
| 7 | Graphiti GitHub README | https://github.com/getzep/graphiti | 8 | 2024 | Official Graphiti repo, architecture overview, comparisons |
| 8 | The Rise of AI Companions (SCSP) | https://scsp222.substack.com/p/the-rise-of-ai-companions | 8 | 2026 | National security analysis of AI companions, trust mechanisms, Chinese market |
| 9 | AI Personality Consistency in Companion Apps | https://ideausher.com/blog/ai-personality-consistency-in-companion-apps/ | 7 | 2024 | Behavioral frameworks, memory handling, response controls |
| 10 | Context Engineering: Optimizing LLM Memory (Medium) | https://medium.com/@kuldeep.paul08/context-engineering-optimizing-llm-memory-for-production-ai-agents-6a7c9165a431 | 7 | 2025 | Context window challenges, performance degradation, token budgeting |
| 11 | Context Engineering: Giving AI Agents Memory (Medium) | https://medium.com/@akki7272/context-engineering-giving-ai-agents-memory-without-breaking-the-token-budget-9fba97aff7be | 7 | 2025 | Production patterns: lazy loading, task-specific profiles, RAG, compression |
| 12 | RAG is Dead (nexxel.dev) | https://www.nexxel.dev/blog/rag-is-dead | 6 | 2024 | Evolution from RAG to stateful memory with temporal awareness |
| 13 | Neo4j GraphRAG | https://neo4j.com/blog/genai/what-is-graphrag/ | 9 | 2024 | KGs as flexible memory companion to LLMs |
| 14 | Replika AI Review 2025 | https://www.eesel.ai/blog/replika-ai-review | 6 | 2025 | Memory bank, continuity mechanisms, user experience |
| 15 | AI with Persistent Chat History | https://www.jenova.ai/en/resources/ai-with-persistent-chat-history | 6 | 2025 | Cross-session memory, unlimited history |
| 16 | Prompt Engineering for Healthy AI Relationships (Medium) | https://lightcapai.medium.com/i-engineered-50-ai-prompts-for-connection-heres-what-actually-creates-healthy-digital-48313d650372 | 6 | 2024 | Emotional support prompt patterns |
| 17 | Token Efficiency in Multi-Agent Pipelines | https://www.llumo.ai/blog/token-efficiency-in-multiagent-pipelines-a-practical-guide | 7 | 2024 | Token optimization strategies, compression |
| 18 | Deep Dive into Knowledge Graph Memory Servers | https://skywork.ai/skypage/en/beyond-forgetful-ai-knowledge-graph-memory-servers/1979062642757193728 | 7 | 2024 | KG memory setup, use cases, AI memory enhancement |

---

## Recommendations for Next Steps

### Immediate (Week 1)

1. **ElevenLabs server tools optimization**:
   - Expand `get_context()` to 20-30 fields (add summaries, backstory, active thoughts)
   - Add context snapshot logging to DB (full prompts + retrieved data)
   - Implement pre-call webhook for user_id lookup

2. **Graphiti retrieval tuning**:
   - Enable episode-mentions reranker (prioritize frequently discussed topics)
   - Test hybrid search quality on sample queries
   - Log all search results for quality review

3. **Prompt engineering baseline**:
   - Implement tiered memory injection (recent full, medium summary, long-term facts)
   - Add emotional state computation (mood, energy, attachment)
   - Monitor token usage per component (identify bloat)

### Short-term (Month 1)

1. **Knowledge base strategy**:
   - Add static domain knowledge (game rules, personality core) to ElevenLabs KB
   - Keep under 10K characters to leave headroom
   - Weekly review of transcripts for gaps

2. **Conversation windowing**:
   - Implement 10-turn full history + summarization for older turns
   - Cache summaries to avoid recomputation
   - Measure token savings (target: 70%+ for long conversations)

3. **Memory quality monitoring**:
   - Weekly sampling of Graphiti search results (relevance scoring)
   - Track entity deduplication accuracy (false positives/negatives)
   - Identify knowledge gaps (queries with <3 relevant results)

### Long-term (Quarter 1)

1. **Advanced retrieval**:
   - Implement temporal queries ("What was X like in [month/year]?")
   - Cross-encoder reranking for complex queries (high accuracy, high cost)
   - Multi-hop reasoning (BFS from seed entities)

2. **Proactive touchpoints**:
   - Scheduled jobs for Nikita-initiated messages
   - Life simulation events (inject into next conversation)
   - Personalization based on user engagement patterns

3. **Production optimization**:
   - Fine-tuned embedding models for Graphiti (lower latency, higher accuracy)
   - Domain-specific ontologies (structured relationship types)
   - Automated knowledge gap detection (alert when coverage drops)

---

## Confidence Gaps & Research Needs

### Medium Confidence Areas (Need Validation)

1. **ElevenLabs knowledge base refresh strategies**: Docs mention auto-updating from URLs "coming soon"—unclear timeline or implementation
2. **Graphiti deduplication tuning**: No published accuracy metrics for entity/fact resolution (false positive/negative rates)
3. **Long-term AI companion retention**: No public data on 12+ month engagement rates, churn patterns

### Low Confidence Areas (Speculative)

1. **AI companion psychological impacts**: Most research <1 year old, long-term effects unknown
2. **Optimal token budgets**: 10K recommendation based on limited sources, may vary by use case
3. **Cross-encoder reranking ROI**: High cost, unclear accuracy improvement vs. cheaper methods

### Recommended Follow-Up Research

1. **ElevenLabs agent transfer patterns**: How to maintain context across agent handoffs (Meta-Nikita → Nikita)
2. **Graphiti community formation**: Optimal parameters for label propagation, refresh frequency
3. **Prompt engineering A/B testing**: Quantitative evaluation of personality consistency techniques

---

**Research complete. Confidence: 88%. Anchor sources: ElevenLabs official docs (auth: 10), Zep arxiv paper (auth: 10). 18 sources cover: ElevenLabs platform, Graphiti/Neo4j, AI companion psychology, prompt engineering, context optimization.**
