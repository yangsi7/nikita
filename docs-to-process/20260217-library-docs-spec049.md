# Library Documentation — Gate 4.5 Spec Preparation
Date: 2026-02-17
Sources: REF MCP (ai.pydantic.dev, platform.claude.com, supabase.com), Firecrawl supplemental

---

## 1. Pydantic AI

### Version & Status
- **Current**: v1.x (stable, V1 released Sept 2025; V2 earliest April 2026)
- **Version policy**: No intentional breaking changes in minor V1 releases
- **Install**: `pip install pydantic-ai` or `pip install "pydantic-ai-slim[anthropic]"`
- **Nikita usage**: 10+ Agent instantiations across text agent, scoring analyzer, conflict detector/resolver, engagement detection, backstory generator, life sim event generator, task routes

### Agent Creation

```python
from pydantic_ai import Agent, RunContext

# Basic agent with model, deps, output type, and system prompt
agent = Agent(
    'anthropic:claude-sonnet-4-5-20250929',  # model string
    deps_type=MyDeps,                         # dataclass for DI
    output_type=SupportOutput,                # Pydantic BaseModel
    system_prompt='You are a support agent.',  # static prompt
)

# Dynamic system prompt via decorator
@agent.system_prompt
async def add_context(ctx: RunContext[MyDeps]) -> str:
    return f"Customer: {await ctx.deps.db.get_name(ctx.deps.customer_id)}"

# Run agent
result = await agent.run('user message', deps=deps)
print(result.output)  # typed as SupportOutput
```

Key constructor params:
- `model`: string ID or Model instance
- `deps_type`: type annotation for dependency injection (NOT an instance)
- `output_type`: BaseModel, dataclass, TypedDict, union, or list of types/functions
- `system_prompt`: static string(s)
- `instructions`: string (alias for system_prompt, preferred name)
- `tools`: list of functions or Tool instances
- `toolsets`: list of Toolset instances (MCP, etc.)

### Multi-Agent Patterns

Five levels of complexity:

1. **Single agent** — standard usage
2. **Agent delegation** — agent calls another agent via tool
3. **Programmatic hand-off** — app code sequences multiple agents
4. **Graph-based control flow** — state machine orchestration
5. **Deep agents** — autonomous with planning, file ops, sandboxed execution

#### Agent Delegation (Nikita-relevant)
```python
parent_agent = Agent('anthropic:claude-sonnet-4-5-20250929', instructions='...')
child_agent = Agent('anthropic:claude-haiku-4-5-20251001', output_type=list[str])

@parent_agent.tool
async def delegate_work(ctx: RunContext[None], count: int) -> list[str]:
    r = await child_agent.run(
        f'Generate {count} items.',
        usage=ctx.usage,  # share usage tracking
    )
    return r.output
```

- Parent agent calls child agent inside a tool function
- Pass `ctx.usage` to track combined token usage
- Pass `ctx.deps` for shared dependencies
- Different models allowed per agent (cost optimization)
- Use `UsageLimits(request_limit=N, total_tokens_limit=N)` to cap costs

#### Programmatic Hand-off
```python
# Sequential agent calls with shared message history
result1 = await agent_a.run(prompt, usage=shared_usage)
result2 = await agent_b.run(
    prompt2,
    message_history=result1.all_messages(),
    usage=shared_usage,
)
```

### Structured Output

Three output modes:

| Mode | Mechanism | Reliability | Model Support |
|------|-----------|-------------|---------------|
| **Tool Output** (default) | JSON schema as tool params | High | All models |
| **Native Output** | Model's structured output feature | Highest | Limited (not Gemini+tools) |
| **Prompted Output** | Schema injected in instructions | Lower | All models |

#### BaseModel output (most common)
```python
class SupportOutput(BaseModel):
    advice: str = Field(description='Advice for customer')
    block_card: bool
    risk: int = Field(ge=0, le=10)

agent = Agent('...', output_type=SupportOutput)
# result.output is typed as SupportOutput, validated by Pydantic
```

#### Union output (multiple return types)
```python
class Success(BaseModel): data: str
class Failure(BaseModel): error: str

agent = Agent('...', output_type=Success | Failure)  # type: ignore
# Each union member becomes a separate output tool
```

#### Output functions (advanced)
```python
def run_sql_query(query: str) -> list[Row]:
    """Executes SQL and returns rows. Can raise ModelRetry."""
    ...

agent = Agent('...', output_type=[run_sql_query, SQLFailure])
# Model forced to call output function; result NOT sent back to model
```

#### Output validators
```python
@agent.output_validator
async def validate(ctx: RunContext[MyDeps], output: str) -> str:
    if 'banned_word' in output:
        raise ModelRetry('Please remove banned words.')
    return output
```

#### StructuredDict (dynamic schemas)
```python
from pydantic_ai import StructuredDict

DynamicOutput = StructuredDict(
    {'type': 'object', 'properties': {'name': {'type': 'string'}}},
    name='DynamicThing',
    description='A dynamically defined output',
)
agent = Agent('...', output_type=DynamicOutput)
# result.output is dict[str, Any] — no Pydantic validation
```

### Tool Definition and Registration

Three registration methods:
1. `@agent.tool` — needs RunContext (dependency access)
2. `@agent.tool_plain` — no RunContext needed
3. `tools=[fn1, fn2]` or `tools=[Tool(fn, takes_ctx=True)]` in constructor

```python
@agent.tool
async def get_balance(ctx: RunContext[MyDeps], include_pending: bool) -> float:
    """Returns account balance.

    Args:
        ctx: Agent context with database connection.
        include_pending: Whether to include pending transactions.
    """
    return await ctx.deps.db.balance(ctx.deps.customer_id, include_pending)
```

- Docstrings become tool descriptions (google/numpy/sphinx format)
- Parameter descriptions extracted from docstrings
- Single-BaseModel params get flattened schema
- `Tool(fn, prepare=my_prepare_fn)` for dynamic tool availability
- Tools can return anything JSON-serializable

### Dependency Injection

```python
@dataclass
class MyDeps:
    db: DatabaseConn
    api_key: str
    http_client: httpx.AsyncClient

agent = Agent('...', deps_type=MyDeps)

# At runtime:
deps = MyDeps(db=conn, api_key='...', http_client=client)
result = await agent.run('query', deps=deps)

# In tests — override deps:
with agent.override(deps=test_deps):
    result = await application_code('query')
```

- deps_type is the TYPE, not an instance
- RunContext[MyDeps] provides typed access in tools/prompts
- async and sync deps both work (sync runs in thread pool)
- `agent.override(deps=...)` for test dependency injection

### Key Limitations
- No built-in conversation persistence (bring your own message_history)
- Union output types need `# type: ignore` for static type checking until PEP-747
- Gemini cannot use tools + Native structured output simultaneously
- No automatic token counting across different model providers in delegation
- Graph-based flows require separate `pydantic-graph` import

### Official Docs URLs
- Main docs: https://ai.pydantic.dev/
- Agents: https://ai.pydantic.dev/agents/
- Tools: https://ai.pydantic.dev/tools/
- Output: https://ai.pydantic.dev/output/
- Dependencies: https://ai.pydantic.dev/dependencies/
- Multi-agent: https://ai.pydantic.dev/multi-agent-applications/
- Anthropic model: https://ai.pydantic.dev/models/anthropic/

---

## 2. Claude API Prompt Caching

### Version & Status
- **Available**: All Claude models (different min token thresholds)
- **Default TTL**: 5 minutes (ephemeral), optional 1-hour at extra cost
- **Max breakpoints**: 4 per request
- **Workspace-level isolation** (since Feb 5, 2026)

### How It Works

Set `cache_control` on content blocks. System checks for cache hits by working backwards from your breakpoint (up to 20 blocks lookback).

```python
# System prompt caching
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    system=[
        {
            "type": "text",
            "text": "Very long system prompt with game rules, persona, etc...",
            "cache_control": {"type": "ephemeral"}  # 5-min TTL
        }
    ],
    messages=[{"role": "user", "content": "Hello"}]
)
```

### Cache Control Block

```python
# 5-minute TTL (default, no extra cost on refresh)
"cache_control": {"type": "ephemeral"}

# 1-hour TTL (additional cost, good for >5min gaps)
"cache_control": {"type": "ephemeral", "ttl": "1h"}
```

### Minimum Cacheable Tokens

| Model | Min Tokens |
|-------|-----------|
| Claude Opus 4.5 | 4,096 |
| Claude Opus 4.1/4, Sonnet 4.5/4 | 1,024 |
| Claude Haiku 4.5 | 4,096 |

### Cost Structure

| Token Type | Cost vs Base |
|-----------|-------------|
| Cache write (5-min) | 125% of base input price |
| Cache read | 10% of base input price |
| Regular input | 100% (no caching) |
| Cache write (1-hour) | Higher than 5-min |

**Breakpoints themselves add zero cost.** You pay only for actual cache writes and reads.

### What Can Be Cached
- Tool definitions (`tools` array)
- System messages (`system` array)
- Text messages (user and assistant turns)
- Images and documents (user turns)
- Tool use and tool results
- Thinking blocks (indirectly, when passed back in subsequent calls)

### What Cannot Be Cached
- Thinking blocks directly (no `cache_control` on them)
- Sub-content blocks (citations) — cache the parent block instead
- Empty text blocks

### Cache Invalidation Hierarchy

`tools` -> `system` -> `messages` (changes cascade downward)

| Change | Tools | System | Messages |
|--------|-------|--------|----------|
| Tool definitions | INVALID | INVALID | INVALID |
| Web search toggle | valid | INVALID | INVALID |
| Citations toggle | valid | INVALID | INVALID |
| Tool choice | valid | valid | INVALID |
| Images | valid | valid | INVALID |
| Thinking params | valid | valid | INVALID |

### Multi-Turn Conversation Pattern

```python
# Turn 1: Cache system prompt
messages = [{"role": "user", "content": "Hello Nikita"}]
response = client.messages.create(
    system=[{"type": "text", "text": LONG_SYSTEM_PROMPT,
             "cache_control": {"type": "ephemeral"}}],
    messages=messages
)

# Turn 2: Previous messages cached automatically (20-block lookback)
messages.append({"role": "assistant", "content": response.content})
messages.append({"role": "user", "content": "How are you?"})
# Add cache breakpoint at end of conversation
messages[-1] = {
    "role": "user",
    "content": [{"type": "text", "text": "How are you?",
                 "cache_control": {"type": "ephemeral"}}]
}
```

### Tracking Performance

```python
# In response.usage:
{
    "cache_creation_input_tokens": 2500,  # tokens written to cache
    "cache_read_input_tokens": 0,         # tokens read from cache
    "input_tokens": 50,                    # tokens after last breakpoint
}
# Total = cache_read + cache_creation + input_tokens
```

### Best Practices
1. Place cached content at prompt beginning (tools -> system -> messages)
2. Put `cache_control` at end of conversation for automatic lookback
3. Add extra breakpoints before editable content for >20 block prompts
4. Use 5-min TTL for frequent requests, 1-hour for >5min gaps
5. Keep tool definitions stable (changes invalidate entire cache)
6. Ensure stable JSON key ordering in tool_use blocks

### Nikita Integration Notes
- System prompt (~3K tokens with persona + rules) should be cached with `cache_control`
- Tool definitions (score lookup, memory search, etc.) — cache separately if stable
- Multi-turn Telegram conversations: cache breakpoint on latest user message
- Voice pipeline: 1-hour TTL beneficial (user may pause >5min mid-conversation)
- Estimated savings: 90% on system prompt reads after first turn

### Official Docs URLs
- Main: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Cookbook: https://platform.claude.com/cookbook/misc-prompt-caching

---

## 3. Supabase JSONB

### Version & Status
- **PostgreSQL native**: JSONB available in all Supabase instances
- **Extensions**: `pg_jsonschema` for validation, GIN indexes built-in

### JSON vs JSONB
| Feature | json | jsonb |
|---------|------|-------|
| Storage | Exact text copy | Decomposed binary |
| Insert speed | Faster | Slightly slower |
| Query speed | Slow (reparsing) | Fast (no reparse) |
| Indexing | Limited | Full GIN/GiST/BTREE |
| **Recommendation** | Avoid | **Always use** |

### Create JSONB Columns

```sql
create table books (
    id serial primary key,
    title text,
    metadata jsonb
);
```

### Insert JSON Data

```sql
insert into books (title, metadata)
values (
    'The Game',
    '{"difficulty": "hard", "chapters": 5, "tags": ["strategy", "ai"]}'
);
```

### Query Operators

| Operator | Returns | Description |
|----------|---------|-------------|
| `->` | jsonb | Get JSON element by key/index |
| `->>` | text | Get JSON element as text |
| `#>` | jsonb | Get nested element by path |
| `#>>` | text | Get nested element as text |
| `@>` | boolean | Contains (left contains right) |
| `<@` | boolean | Contained by |
| `?` | boolean | Key exists |
| `?|` | boolean | Any key exists |
| `?&` | boolean | All keys exist |
| `||` | jsonb | Concatenate/merge |
| `-` | jsonb | Delete key |
| `#-` | jsonb | Delete at path |

```sql
-- Get nested value as text
select metadata->>'difficulty' from books;

-- Get array element
select metadata->'tags'->0 from books;

-- Containment query (uses GIN index)
select * from books where metadata @> '{"difficulty": "hard"}';

-- Key existence
select * from books where metadata ? 'chapters';
```

### Partial Updates (jsonb_set)

```sql
-- Update single key
update books
set metadata = jsonb_set(metadata, '{difficulty}', '"easy"')
where id = 1;

-- Update nested path
update books
set metadata = jsonb_set(metadata, '{stats,plays}', '42')
where id = 1;

-- Merge/append (|| operator)
update books
set metadata = metadata || '{"new_field": "value"}'
where id = 1;

-- Remove a key
update books
set metadata = metadata - 'old_field'
where id = 1;

-- Remove at nested path
update books
set metadata = metadata #- '{stats,deprecated_field}'
where id = 1;
```

### GIN Indexes

```sql
-- Index entire JSONB column (supports @>, ?, ?|, ?& operators)
create index idx_books_metadata on books using gin (metadata);

-- Index specific jsonb_path_ops (supports only @>, smaller index)
create index idx_books_metadata_path on books using gin (metadata jsonb_path_ops);

-- BTREE index on specific key (for equality/range on extracted value)
create index idx_books_difficulty on books ((metadata->>'difficulty'));

-- Functional index on integer extraction
create index idx_books_chapters on books (((metadata->>'chapters')::int));
```

**GIN vs jsonb_path_ops**:
- `gin(metadata)` — supports `@>`, `?`, `?|`, `?&` — larger index
- `gin(metadata jsonb_path_ops)` — supports only `@>` — 2-3x smaller index

### Combining JSONB with pgVector

```sql
-- Table with both JSONB metadata and vector embeddings
create table memories (
    id serial primary key,
    content text,
    metadata jsonb,
    embedding vector(1536)
);

-- Query: semantic search filtered by JSONB metadata
select * from memories
where metadata @> '{"type": "episodic"}'
order by embedding <=> '[0.1, 0.2, ...]'::vector
limit 10;

-- Both indexes work together:
create index idx_mem_metadata on memories using gin (metadata);
create index idx_mem_embedding on memories using ivfflat (embedding vector_cosine_ops);
```

### RLS Policies on JSONB Columns

```sql
-- RLS policy checking JSONB field
create policy "Users see own data"
on books for select
using (metadata->>'owner_id' = auth.uid()::text);

-- RLS policy checking JSONB containment
create policy "Admin access"
on books for all
using (metadata @> jsonb_build_object('org_id', auth.jwt()->>'org_id'));
```

### JSON Schema Validation (pg_jsonschema)

```sql
-- Enable extension
create extension if not exists pg_jsonschema;

-- Add check constraint
alter table users
add constraint check_profile check (
    json_matches_schema('{
        "type": "object",
        "properties": {
            "tags": {"type": "array", "items": {"type": "string", "maxLength": 16}}
        }
    }', profile)
);
```

### Performance Characteristics
- JSONB insert: ~10-15% slower than text due to parsing
- GIN index size: ~2-3x the data size (jsonb_path_ops is 2-3x smaller than full GIN)
- Containment queries (`@>`) with GIN: sub-millisecond for typical tables
- `->>` extraction without index: sequential scan (add BTREE index for frequent queries)
- JSONB + pgVector combined queries: filter first (GIN), then vector sort

### Nikita Integration Notes
- `conversations.messages` stored as JSONB array — candidate for GIN index
- `onboarding_profile` is JSONB — schema validation via pg_jsonschema recommended
- Memory metadata filtering + pgVector search: already using this pattern in SupabaseMemory
- User preferences, vice configurations: JSONB columns with partial update via `jsonb_set`
- RLS on JSONB `owner_id`: already pattern in user-scoped data

### Official Docs URLs
- JSONB guide: https://supabase.com/docs/guides/database/json
- PostgreSQL JSON functions: https://www.postgresql.org/docs/current/functions-json.html
- pg_jsonschema: https://supabase.com/docs/guides/database/extensions/pg_jsonschema
- Index selection: https://supabase.com/docs/guides/troubleshooting/how-postgres-chooses-which-index-to-use-_JHrf4

---

## 4. pg_cron

### Version & Status
- **Extension**: pg_cron (via Supabase, pre-installed)
- **Schema**: `cron` (tables: `cron.job`, `cron.job_run_details`)
- **Companion**: pg_net extension for HTTP requests
- **Nikita usage**: 5 active jobs (IDs 10-14): decay, deliver, summary, cleanup, process

### Job Scheduling Syntax

```
 ┌───────────── min (0-59)
 │ ┌────────────── hour (0-23)
 │ │ ┌─────────────── day of month (1-31)
 │ │ │ ┌──────────────── month (1-12)
 │ │ │ │ ┌───────────────── day of week (0-6, Sun=0)
 │ │ │ │ │
 * * * * *
```

Sub-minute scheduling: `'30 seconds'`, `'10 seconds'` (Postgres >=15.1.1.61)

### Job Types

#### 1. SQL Snippet
```sql
select cron.schedule(
    'weekly-cleanup',
    '30 3 * * 6',  -- Saturday 3:30 AM GMT
    $$ delete from events where event_time < now() - interval '1 week' $$
);
```

#### 2. Database Function
```sql
select cron.schedule(
    'call-db-function',
    '*/5 * * * *',  -- every 5 minutes
    'SELECT hello_world()'
);
```

#### 3. Stored Procedure
```sql
select cron.schedule(
    'call-procedure',
    '*/5 * * * *',
    'CALL my_procedure()'
);
```

#### 4. HTTP Request (via pg_net)
```sql
select cron.schedule(
    'invoke-edge-function',
    '30 seconds',
    $$
    select net.http_post(
        url := 'https://project-ref.supabase.co/functions/v1/function-name',
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'Authorization', 'Bearer ' || 'YOUR_ANON_KEY'
        ),
        body := jsonb_build_object('time', now()),
        timeout_milliseconds := 5000
    ) as request_id;
    $$
);
```

**Requires `pg_net` extension enabled.**

#### 5. Call Cloud Run Endpoint (Nikita pattern)
```sql
select cron.schedule(
    'decay-scores',
    '*/15 * * * *',  -- every 15 minutes
    $$
    select net.http_post(
        url := 'https://nikita-api-xxxxx.a.run.app/api/v1/tasks/decay',
        headers := '{"Authorization": "Bearer <SERVICE_KEY>", "Content-Type": "application/json"}'::jsonb,
        body := '{}'::jsonb,
        timeout_milliseconds := 30000
    ) as request_id;
    $$
);
```

### Managing Jobs

```sql
-- List all scheduled jobs
select * from cron.job;

-- Edit a job schedule
select cron.alter_job(
    job_id := 10,
    schedule := '*/30 * * * *'  -- change to every 30 min
);

-- Deactivate a job (keep definition)
select cron.alter_job(job_id := 10, active := false);

-- Reactivate
select cron.alter_job(job_id := 10, active := true);

-- Unschedule (delete) a job
select cron.unschedule('job-name');
-- or by ID:
select cron.unschedule(10);
```

### Monitoring Job Execution

```sql
-- Recent runs for a specific job
select *
from cron.job_run_details
where jobid = (select jobid from cron.job where jobname = 'decay-scores')
order by start_time desc
limit 10;

-- Failed runs
select jobid, command, status, return_message, start_time, end_time
from cron.job_run_details
where status = 'failed'
order by start_time desc
limit 20;

-- Job run duration analysis
select
    jobname,
    avg(extract(epoch from (end_time - start_time))) as avg_duration_sec,
    max(extract(epoch from (end_time - start_time))) as max_duration_sec,
    count(*) filter (where status = 'failed') as failure_count,
    count(*) as total_runs
from cron.job_run_details jrd
join cron.job j on j.jobid = jrd.jobid
group by jobname;
```

### Error Handling and Retries
- pg_cron has **no built-in retry mechanism**
- Failed jobs log to `cron.job_run_details` with `status = 'failed'` and `return_message`
- For retries: implement in the called function/endpoint, or schedule a retry-checker job
- HTTP failures (via pg_net): check `net._http_response` table for status codes

### Cleanup (Important)
```sql
-- job_run_details is NOT auto-cleaned! Schedule cleanup:
select cron.schedule(
    'cleanup-job-history',
    '0 4 * * *',  -- daily at 4 AM
    $$ delete from cron.job_run_details where end_time < now() - interval '7 days' $$
);
```

### Limitations and Gotchas
1. **No auto-cleanup**: `cron.job_run_details` grows unbounded — must schedule cleanup
2. **Max concurrency**: Recommended max 8 concurrent jobs
3. **Max runtime**: Each job should complete within 10 minutes
4. **GMT timezone**: All schedules in GMT (not local time)
5. **No built-in retries**: Must implement retry logic externally
6. **pg_net required**: HTTP requests need pg_net extension enabled separately
7. **Cold start**: Cloud Run endpoints may take 5-10s cold start — set adequate timeout
8. **Permissions**: Jobs run as the database owner (superuser context)

### Nikita Integration Notes
- 5 active jobs: decay (every 15min), scheduled delivery, daily summary, cleanup, message processing
- All use pg_net to call Cloud Run task endpoints
- Cold start mitigation: 30s timeout on HTTP requests
- Job history cleanup job recommended (currently not scheduled — action item)
- Dashboard monitoring: Supabase Dashboard > Integrations > Cron > History

### Official Docs URLs
- Cron overview: https://supabase.com/docs/guides/cron
- Quickstart: https://supabase.com/docs/guides/cron/quickstart
- pg_cron extension: https://supabase.com/docs/guides/database/extensions/pg_cron
- pg_net extension: https://supabase.com/docs/guides/database/extensions/pg_net
- Debugging: https://supabase.com/docs/guides/troubleshooting/pgcron-debugging-guide-n1KTaz
- Blog (detailed): https://supabase.com/blog/supabase-cron

---

## Integration Notes — How These Libraries Interact for Nikita

### Pydantic AI + Claude Prompt Caching
- Pydantic AI sends system prompts and tool definitions to Claude API
- **Opportunity**: Cache Nikita's persona system prompt (~3K tokens) and tool definitions
- Pydantic AI does NOT currently manage `cache_control` blocks natively
- **Implementation**: Use `AnthropicModel` with custom `model_settings` or wrap at HTTP layer
- Agent delegation (text agent -> scoring analyzer): each sub-agent call is separate API request, benefits from shared system prompt caching

### Supabase JSONB + pgVector (SupabaseMemory)
- Already implemented in `nikita/memory/supabase_memory.py`
- Pattern: JSONB metadata filter THEN pgVector cosine similarity sort
- GIN index on metadata + IVFFlat index on embeddings = efficient combined queries
- Conversation messages stored as JSONB arrays in `conversations` table

### pg_cron + Cloud Run + Pydantic AI
- pg_cron triggers HTTP POST to Cloud Run task endpoints
- Task endpoints run Pydantic AI agents (decay calculation, summary generation)
- Chain: pg_cron -> pg_net HTTP -> Cloud Run -> FastAPI -> Pydantic AI Agent -> Supabase
- Cold start concern: Cloud Run scales to zero, pg_cron timeout must accommodate ~10s startup

### JSONB + pg_cron
- Cron jobs can read/write JSONB columns directly via SQL snippets
- Example: batch update `user_metrics.metadata` JSONB field for decay without HTTP round-trip
- Potential optimization: move simple decay logic from Cloud Run into pure SQL cron job

### Cost Optimization Stack
1. **Prompt caching**: 90% reduction on system prompt tokens after first turn
2. **Agent delegation**: Use cheaper models (Haiku) for sub-tasks via Pydantic AI multi-agent
3. **JSONB queries**: Avoid unnecessary API calls by querying structured data in Postgres
4. **pg_cron SQL**: Skip HTTP round-trip for pure-DB operations (no Cloud Run cold start)
