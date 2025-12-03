# context/ - Context Engineering Module

## Purpose

Implements the context engineering redesign (spec 012) for Nikita AI girlfriend game. Moves memory operations from in-conversation (high latency) to post-processing (async, no latency impact).

## Architecture

```
PRE-CONVERSATION:  Generate rich system prompt from pre-computed context (~50ms)
DURING CONVERSATION: Pure LLM conversation with optional retrieval (NO memory writes)
POST-CONVERSATION: Async pipeline extracts facts, updates graphs, generates summaries
```

## Components

### SessionDetector (`session_detector.py`)
Detects when text sessions have timed out (15 min no messages).

```python
from nikita.context import SessionDetector

detector = SessionDetector(session, timeout_minutes=15)
stale_ids = await detector.detect_and_queue(limit=50)
```

### PostProcessor (`post_processor.py`)
8-stage async pipeline for processing ended conversations:

1. **Ingestion** - Mark conversation as processing
2. **Entity & Fact Extraction** - LLM extracts facts from transcript
3. **Conversation Analysis** - Summarize, detect emotional tone
4. **Thread Extraction** - Find unresolved topics, questions, promises
5. **Inner Life Generation** - Simulate Nikita's thoughts
6. **Graph Updates** - Update Neo4j knowledge graphs
7. **Summary Rollups** - Update daily summaries
8. **Cache Invalidation** - Clear cached prompts

```python
from nikita.context import PostProcessor

processor = PostProcessor(session)
result = await processor.process_conversation(conversation_id)
```

### TemplateGenerator (`template_generator.py`)
6-layer system prompt generation (~4500 tokens):

1. **Core Identity** (static, ~400 tokens) - Nikita's personality
2. **Current Moment** (computed, ~300 tokens) - Time, mood, energy
3. **Relationship State** (pre-computed, ~500 tokens) - Chapter, score, trends
4. **Conversation History** (pre-computed, ~1800 tokens) - Summaries, threads
5. **Knowledge & Inner Life** (pre-computed, ~1000 tokens) - Facts, thoughts
6. **Response Guidelines** (computed, ~500 tokens) - Style parameters

```python
from nikita.context import generate_system_prompt

prompt = await generate_system_prompt(session, user_id)
```

## Database Tables

| Table | Purpose |
|-------|---------|
| `conversation_threads` | Unresolved topics, questions, promises |
| `nikita_thoughts` | Simulated inner life thoughts |
| `daily_summaries` | Pre-computed daily conversation summaries |
| `conversations.status` | Processing status (active/processing/processed/failed) |

## pg_cron Integration

Endpoint: `POST /tasks/process-conversations`

Called every minute to:
1. Find stale active conversations (15+ min no messages)
2. Queue them for post-processing
3. Run the 8-stage pipeline on each

## Key Design Decisions

1. **No memory writes during conversation** - Reduces latency
2. **Rich pre-computed context** - System prompt built from cached data
3. **Simulated inner life** - Makes Nikita feel alive between conversations
4. **Thread tracking** - Natural conversation continuity
5. **15 min text timeout** - Clear session boundary for processing

## Related Files

- `nikita/db/models/context.py` - ConversationThread, NikitaThought models
- `nikita/db/repositories/thread_repository.py` - Thread CRUD
- `nikita/db/repositories/thought_repository.py` - Thought CRUD
- `nikita/api/routes/tasks.py` - pg_cron endpoints
- `nikita/agents/text/handler.py` - Message handling (fact extraction removed)
- `nikita/agents/text/tools.py` - note_user_fact deprecated
