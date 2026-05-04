# Voice Implementation

```yaml
context_priority: critical
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - CONTEXT_ENGINE.md
  - INTEGRATIONS.md
  - ONBOARDING.md
```

## Overview

The voice agent runs on ElevenLabs Conversational AI 2.0 with server tools for context and scoring.

**CRITICAL**: Voice bypasses ContextEngine entirely due to 2-second timeout constraints.

---

## Architecture

### Voice vs Text Comparison

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      TEXT vs VOICE ARCHITECTURE                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TEXT PATH (Full Context):                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Telegram   │───▶│  Message    │───▶│  Context    │───▶│   Prompt    │  │
│  │  Webhook    │    │  Handler    │    │  Engine     │    │  Generator  │  │
│  └─────────────┘    └─────────────┘    │ (8 collect) │    └──────┬──────┘  │
│                                        │ (45s total) │           │         │
│                                        └─────────────┘           ▼         │
│                                                          ┌─────────────┐   │
│                                                          │   Claude    │   │
│                                                          │  (45s max)  │   │
│                                                          └─────────────┘   │
│                                                                              │
│  VOICE PATH (Bypasses ContextEngine):                                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │  ElevenLabs │───▶│ Server Tool │───▶│  Direct DB  │                     │
│  │  Platform   │    │  Call       │    │  Queries    │                     │
│  │             │    │ (2s max)    │    │ (no engine) │                     │
│  └─────────────┘    └──────┬──────┘    └─────────────┘                     │
│                            │                                                │
│                            │ Returns context in <2s                         │
│                            ▼                                                │
│                     ┌─────────────┐                                         │
│                     │  ElevenLabs │                                         │
│                     │  Agent LLM  │                                         │
│                     └─────────────┘                                         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Key Differences

| Aspect | Text Agent | Voice Agent |
|--------|------------|-------------|
| Context Source | ContextEngine (8 collectors) | server_tools.py (direct queries) |
| Timeout | 45s collection + 45s LLM | 2s per tool call |
| Fields Available | 115+ | ~30 |
| Memory Integration | Full 3-graph query | Limited search |
| Humanization | Full (mood, energy, conflicts) | Partial |
| Validation | 3 validators | None |
| Post-Processing | 11-stage pipeline | Webhook only |

---

## Server Tools

### Tool Overview

**File**: `nikita/agents/voice/server_tools.py:1-300`

| Tool | Purpose | Timeout | Returns |
|------|---------|---------|---------|
| `get_context` | Retrieve user context | 2s | 26 visible fields + 2 hidden |
| `get_memory` | Search knowledge graphs | 2s | Facts and threads |
| `score_turn` | Score user response | 2s | 4 metric deltas |
| `update_memory` | Add facts to graphs | 2s | Success/failure |

### get_context

**File**: `nikita/agents/voice/server_tools.py:50-130`

```python
@with_timeout_fallback(timeout=2.0)
async def get_context(
    user_id: str,
    signed_token: str
) -> Dict[str, Any]:
    """Get context for voice conversation."""

    if not validate_voice_token(signed_token, user_id):
        return {"error": "Invalid token"}

    async with get_db_session() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(UUID(user_id))
        metrics = await repo.get_metrics(user.id)
        vices = await ViceService().get_unlocked(user.id, metrics.chapter_number)

        return {
            # User profile
            "user_name": user.display_name,
            "user_occupation": user.occupation,
            "user_hobbies": user.hobbies,

            # Game state
            "chapter": metrics.chapter_number,
            "relationship_score": float(metrics.relationship_score),
            "engagement_state": metrics.engagement_state,
            "in_boss_fight": metrics.in_boss_fight,

            # Temporal
            "hours_since_last": calculate_hours_since(metrics.last_interaction),
            "time_of_day": get_time_of_day(),
            "day_of_week": get_day_of_week(),

            # Humanization
            "nikita_mood": compute_mood(metrics),
            "nikita_energy": compute_energy(),
            "nikita_activity": compute_activity(),

            # Vices
            "top_vices": [v.name for v in vices[:3]],
            "vice_instructions": format_vice_instructions(vices),

            # Chapter behaviors
            "chapter_behaviors": get_chapter_behaviors(metrics.chapter_number),

            # Recent context (limited)
            "last_conversation_summary": await get_last_summary(user.id, session),

            # Hidden (not visible in prompt)
            "_user_id": str(user.id),
            "_signed_token": signed_token
        }
```

### get_memory

**File**: `nikita/agents/voice/server_tools.py:130-180`

```python
@with_timeout_fallback(timeout=2.0)
async def get_memory(
    user_id: str,
    signed_token: str,
    query: str
) -> Dict[str, Any]:
    """Search knowledge graphs for relevant memories."""

    if not validate_voice_token(signed_token, user_id):
        return {"error": "Invalid token"}

    try:
        memory = await NikitaMemory.get_instance()

        # Search user facts (limited to 10 for speed)
        user_facts = await memory.search_memory(
            query=query,
            graph_name=f"user_{user_id}",
            limit=10
        )

        # Search shared memories (limited to 5)
        shared_memories = await memory.search_memory(
            query=query,
            graph_name=f"relationship_{user_id}",
            limit=5
        )

        return {
            "user_facts": user_facts,
            "shared_memories": shared_memories,
            "query": query
        }

    except asyncio.TimeoutError:
        return {"error": "Memory search timed out", "user_facts": [], "shared_memories": []}
```

### score_turn

**File**: `nikita/agents/voice/server_tools.py:180-250`

```python
@with_timeout_fallback(timeout=2.0)
async def score_turn(
    user_id: str,
    signed_token: str,
    user_message: str,
    nikita_response: str
) -> Dict[str, Any]:
    """Score a conversation turn."""

    if not validate_voice_token(signed_token, user_id):
        return {"error": "Invalid token"}

    async with get_db_session() as session:
        # Get current state
        repo = UserRepository(session)
        metrics = await repo.get_metrics(UUID(user_id))

        # Create context for analyzer
        context = ConversationContext(
            chapter=metrics.chapter_number,
            engagement_state=metrics.engagement_state
        )

        # Analyze response
        analyzer = ResponseAnalyzer()
        analysis = await analyzer.analyze(user_message, context)

        # Calculate delta
        calculator = ScoreCalculator()
        delta = calculator.calculate_delta(analysis, metrics.engagement_state)

        # Apply delta
        new_score = max(0, min(100, float(metrics.relationship_score) + delta.total))
        await repo.update_score(UUID(user_id), new_score)

        return {
            "delta": {
                "total": delta.total,
                "intimacy": delta.intimacy,
                "passion": delta.passion,
                "trust": delta.trust,
                "secureness": delta.secureness
            },
            "new_score": new_score,
            "analysis_summary": analysis.reasoning
        }
```

### update_memory

**File**: `nikita/agents/voice/server_tools.py:250-300`

```python
@with_timeout_fallback(timeout=2.0)
async def update_memory(
    user_id: str,
    signed_token: str,
    facts: List[str]
) -> Dict[str, Any]:
    """Add new facts to knowledge graph."""

    if not validate_voice_token(signed_token, user_id):
        return {"error": "Invalid token"}

    try:
        memory = await NikitaMemory.get_instance()

        for fact in facts:
            await memory.add_episode(
                content=fact,
                graph_name=f"user_{user_id}",
                source="voice_conversation"
            )

        return {"status": "success", "facts_added": len(facts)}

    except asyncio.TimeoutError:
        return {"error": "Memory update timed out", "facts_added": 0}
```

---

## Timeout Handling

### Decorator Pattern

**File**: `nikita/agents/voice/timeout.py:1-50`

```python
# nikita/agents/voice/timeout.py

import asyncio
from functools import wraps

def with_timeout_fallback(timeout: float):
    """Decorator to add timeout with fallback to server tools."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Return graceful fallback
                return {
                    "error": f"Tool {func.__name__} timed out after {timeout}s",
                    "fallback": True
                }
        return wrapper
    return decorator
```

### Fallback Data

When tools timeout, ElevenLabs agent uses dynamic variables as fallback:

```python
# Pre-populated in dynamic_variables during pre-call
{
    "user_name": "Alex",  # From database
    "chapter": "3",
    "nikita_mood": "content",
    # ... basic context that doesn't require tool call
}
```

---

## Dynamic Variables

### Variable Sources

**File**: `nikita/agents/voice/models.py:1-100`

| Variable | Source | Visible to Agent |
|----------|--------|------------------|
| `user_name` | Database | Yes |
| `relationship_score` | Metrics | Yes |
| `chapter` | Metrics | Yes |
| `nikita_mood` | Computed | Yes |
| `nikita_energy` | Computed | Yes |
| `nikita_activity` | Computed | Yes |
| `hours_since_last` | Computed | Yes |
| `time_of_day` | Computed | Yes |
| `day_of_week` | Computed | Yes |
| `engagement_state` | Metrics | Yes |
| `top_vices` | Database | Yes |
| `chapter_behaviors` | Config | Yes |
| `user_id` | System | No (hidden) |
| `signed_token` | System | No (hidden) |

### Building Variables

**File**: `nikita/agents/voice/service.py:100-150`

```python
def build_dynamic_variables(user: User, metrics: UserMetrics) -> Dict[str, str]:
    """Build dynamic variables for ElevenLabs agent."""

    vices = ViceService().get_unlocked_sync(user.id, metrics.chapter_number)

    return {
        # Visible variables
        "user_name": user.display_name or "there",
        "relationship_score": str(float(metrics.relationship_score)),
        "chapter": str(metrics.chapter_number),
        "nikita_mood": compute_mood(metrics),
        "nikita_energy": str(compute_energy()),
        "nikita_activity": compute_activity(),
        "hours_since_last": str(calculate_hours_since(metrics.last_interaction)),
        "time_of_day": get_time_of_day(),
        "day_of_week": get_day_of_week(),
        "engagement_state": metrics.engagement_state,
        "top_vices": ", ".join(v.name for v in vices[:3]),
        "chapter_behaviors": "\n".join(get_chapter_behaviors(metrics.chapter_number)),

        # Hidden variables (still accessible by tools)
        "user_id": str(user.id),
        "signed_token": create_signed_token(user.id)
    }
```

---

## Voice Webhook

### Post-Call Processing

**File**: `nikita/api/routes/voice.py:150-250`

```python
@router.post("/webhook")
async def voice_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """Handle post-call webhook from ElevenLabs."""

    # Validate signature
    signature = request.headers.get("X-ElevenLabs-Signature")
    body = await request.body()

    if not validate_elevenlabs_signature(signature, body):
        raise HTTPException(status_code=401)

    data = await request.json()

    # Extract call data
    call_id = data.get("call_id")
    user_id = data.get("metadata", {}).get("user_id")
    transcript = data.get("transcript", [])
    duration = data.get("duration_seconds")

    if not user_id:
        logger.warning(f"Voice webhook missing user_id: {call_id}")
        return {"ok": True}

    # Process transcript
    if transcript:
        await process_voice_transcript(
            user_id=UUID(user_id),
            transcript=transcript,
            call_id=call_id,
            session=session
        )

    # Log call metrics
    await log_voice_call(
        user_id=UUID(user_id),
        call_id=call_id,
        duration=duration,
        session=session
    )

    return {"ok": True}
```

### Transcript Processing

**File**: `nikita/agents/voice/transcript.py:1-150`

```python
# nikita/agents/voice/transcript.py:50-100

async def process_voice_transcript(
    user_id: UUID,
    transcript: List[Dict],
    call_id: str,
    session: AsyncSession
) -> None:
    """Extract entities from voice transcript using LLM."""

    # Format transcript
    formatted = "\n".join([
        f"{turn['role']}: {turn['content']}"
        for turn in transcript
    ])

    # Extract using Pydantic AI
    agent = Agent(
        model="claude-sonnet-4-5-20250929",
        system_prompt=EXTRACTION_PROMPT
    )

    result = await agent.run(formatted)
    extraction = ExtractionResult.model_validate_json(result.data)

    # Store extracted facts
    memory = await NikitaMemory.get_instance()

    for fact in extraction.user_facts:
        await memory.add_episode(
            content=fact,
            graph_name=f"user_{user_id}",
            source="voice_transcript"
        )

    for memory_item in extraction.shared_memories:
        await memory.add_episode(
            content=memory_item,
            graph_name=f"relationship_{user_id}",
            source="voice_transcript"
        )
```

---

## Agent Configuration

### ElevenLabs Agent Setup

Configured via ElevenLabs dashboard:

| Setting | Value |
|---------|-------|
| **Agent ID** | `ELEVENLABS_AGENT_ID` |
| **Voice** | Custom Nikita voice |
| **Model** | Turbo v2.5 |
| **Stability** | 0.5 |
| **Similarity** | 0.8 |

### Server Tool Registration

Tools registered in ElevenLabs agent config:

```json
{
  "tools": [
    {
      "name": "get_context",
      "description": "Get user context and relationship state",
      "endpoint": "https://nikita-api-xxx.run.app/api/v1/voice/server-tool",
      "parameters": {
        "user_id": {"type": "string", "hidden": true},
        "signed_token": {"type": "string", "hidden": true}
      }
    },
    {
      "name": "get_memory",
      "description": "Search memories about the user",
      "endpoint": "https://nikita-api-xxx.run.app/api/v1/voice/server-tool",
      "parameters": {
        "user_id": {"type": "string", "hidden": true},
        "signed_token": {"type": "string", "hidden": true},
        "query": {"type": "string"}
      }
    },
    {
      "name": "score_turn",
      "description": "Score the conversation turn",
      "endpoint": "https://nikita-api-xxx.run.app/api/v1/voice/server-tool",
      "parameters": {
        "user_id": {"type": "string", "hidden": true},
        "signed_token": {"type": "string", "hidden": true},
        "user_message": {"type": "string"},
        "nikita_response": {"type": "string"}
      }
    }
  ]
}
```

---

## Context Gap (NEEDS RETHINKING)

### Current Limitation

Voice agent has significantly less context than text agent:

| Context Type | Text Agent | Voice Agent |
|--------------|------------|-------------|
| User profile | Full | Partial |
| Memory facts | 50 per graph | 10-15 total |
| Humanization | Full 4D mood | Basic mood |
| Threads | All open | None |
| Today summary | Full | Basic |
| Conflicts | Active conflict state | None |
| Social circle | Full | None |
| Narrative arcs | Active arcs | None |

### Impact

- Voice conversations may feel less personalized
- Continuity between voice and text is limited
- Complex emotional states not captured

### Recommended Solutions

1. **Pre-computed Context Cache**
   ```python
   # Background job computes full context
   context = await ContextEngine.collect(user_id)
   await redis.set(f"voice_context:{user_id}", context.json(), ex=300)

   # Voice tool fetches from cache
   cached = await redis.get(f"voice_context:{user_id}")
   return json.loads(cached) if cached else fallback
   ```

2. **Tiered Collection**
   ```python
   # Tier 1: Essential (always)
   user, metrics = await get_essential(user_id)

   # Tier 2: Important (if time)
   if has_time_budget(1.5):
       memories = await get_memories(user_id)

   # Tier 3: Nice-to-have (if time)
   if has_time_budget(0.5):
       threads = await get_threads(user_id)
   ```

3. **Async Pre-fetch**
   ```python
   # On call connect, start pre-fetching
   asyncio.create_task(prefetch_context(user_id))

   # Tool call retrieves pre-fetched data
   context = await get_prefetched(user_id, timeout=0.5)
   ```

---

## Testing

### Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `tests/agents/voice/test_server_tools.py` | 22 | Tool logic |
| `tests/agents/voice/test_dynamic_vars.py` | 25 | Variable building |
| `tests/agents/voice/test_timeout.py` | 10 | Timeout decorator |
| `tests/agents/voice/test_transcript.py` | 15 | Post-call processing |
| `tests/agents/voice/test_context_block.py` | 14 | Context assembly |
| **Total** | **86** | |

### Running Tests

```bash
# All voice tests
pytest tests/agents/voice/ -v

# Specific tool tests
pytest tests/agents/voice/test_server_tools.py -v

# With coverage
pytest tests/agents/voice/ --cov=nikita/agents/voice --cov-report=term-missing
```

---

## Key File References

| File | Line | Purpose |
|------|------|---------|
| `nikita/agents/voice/server_tools.py` | 1-300 | Server tool implementations |
| `nikita/agents/voice/models.py` | 1-100 | Dynamic variables model |
| `nikita/agents/voice/service.py` | 1-200 | Voice service orchestration |
| `nikita/agents/voice/transcript.py` | 1-150 | Transcript processing |
| `nikita/agents/voice/timeout.py` | 1-50 | Timeout decorator |
| `nikita/api/routes/voice.py` | 1-250 | API endpoints |

---

## Related Documentation

- **Context Engine**: [CONTEXT_ENGINE.md](CONTEXT_ENGINE.md)
- **Integrations**: [INTEGRATIONS.md](INTEGRATIONS.md)
- **Onboarding**: [ONBOARDING.md](ONBOARDING.md)
- **Anti-Patterns**: [ANTI_PATTERNS.md](ANTI_PATTERNS.md)
