# Library Documentation — Gate 4.5 Spec Preparation
Date: 2026-02-17
Sources: REF MCP (ai.pydantic.dev, platform.claude.com, supabase.com)

---

## 1. Pydantic AI

### Version & Status
- **Current**: v1.x (stable, V1 Sept 2025; V2 earliest April 2026)
- **Install**: `pip install pydantic-ai` or `pip install "pydantic-ai-slim[anthropic]"`
- **Nikita usage**: 10+ Agent instances (text, scoring, conflict, engagement, backstory, life sim, tasks)

### Agent Creation
```python
from pydantic_ai import Agent, RunContext
agent = Agent(
    'anthropic:claude-sonnet-4-5-20250929',
    deps_type=MyDeps,              # dataclass TYPE for DI
    output_type=SupportOutput,     # BaseModel for structured output
    instructions='You are a support agent.',
)
@agent.system_prompt
async def add_context(ctx: RunContext[MyDeps]) -> str:
    return f"Customer: {await ctx.deps.db.get_name(ctx.deps.customer_id)}"

result = await agent.run('user message', deps=deps)  # result.output typed
```
Key params: `model`, `deps_type`, `output_type`, `instructions`, `tools`, `toolsets`

### Multi-Agent Patterns
5 levels: (1) Single agent, (2) Agent delegation via tools, (3) Programmatic hand-off, (4) Graph-based state machine, (5) Deep agents (planning + sandboxed exec)

**Agent Delegation** (Nikita-relevant):
```python
parent = Agent('anthropic:claude-sonnet-4-5-20250929', instructions='...')
child = Agent('anthropic:claude-haiku-4-5-20251001', output_type=list[str])

@parent.tool
async def delegate(ctx: RunContext[None], count: int) -> list[str]:
    r = await child.run(f'Generate {count} items.', usage=ctx.usage)
    return r.output
```
- Pass `ctx.usage` for combined token tracking, `ctx.deps` for shared deps
- Different models per agent (cost optimization), `UsageLimits` to cap costs

### Structured Output
| Mode | Mechanism | Reliability | Model Support |
|------|-----------|-------------|---------------|
| **Tool Output** (default) | JSON schema as tool params | High | All models |
| **Native Output** | Model's structured output API | Highest | Limited |
| **Prompted Output** | Schema in instructions | Lower | All models |

```python
# BaseModel output
agent = Agent('...', output_type=SupportOutput)
# Union output — each member becomes separate output tool
agent = Agent('...', output_type=Success | Failure)  # type: ignore
# Output functions — model forced to call; result NOT sent back
agent = Agent('...', output_type=[run_sql_query, SQLFailure])
# Output validator
@agent.output_validator
async def validate(ctx, output: str) -> str:
    if 'banned' in output: raise ModelRetry('Remove banned words.')
    return output
# Dynamic schema (no Pydantic validation)
DynOut = StructuredDict({'type':'object','properties':{'name':{'type':'string'}}})
```

### Tool Registration
```python
@agent.tool          # needs RunContext
@agent.tool_plain    # no RunContext
tools=[fn1, Tool(fn2, takes_ctx=True)]  # via constructor
```
- Docstrings -> tool descriptions (google/numpy/sphinx format)
- Parameter descriptions extracted from docstrings
- `Tool(fn, prepare=my_prepare_fn)` for dynamic tool availability

### Dependency Injection
```python
@dataclass
class MyDeps:
    db: DatabaseConn; api_key: str
agent = Agent('...', deps_type=MyDeps)
# Runtime: result = await agent.run('q', deps=MyDeps(...))
# Tests:  with agent.override(deps=test_deps): ...
```

### Key Limitations
- No built-in conversation persistence (bring your own `message_history`)
- Union outputs need `# type: ignore` until PEP-747
- No auto token counting across providers in delegation
- Pydantic AI does NOT manage `cache_control` blocks natively

### Docs: https://ai.pydantic.dev/ (agents, tools, output, dependencies, multi-agent)

---

## 2. Claude API Prompt Caching

### Version & Status
- All Claude models, different min token thresholds (Sonnet 4.5: 1,024; Opus 4.5: 4,096)
- Default TTL: 5 minutes; optional 1-hour at extra cost
- Max 4 breakpoints per request; workspace-level isolation (since Feb 5, 2026)

### Cache Control
```python
# 5-min TTL (default)
"cache_control": {"type": "ephemeral"}
# 1-hour TTL
"cache_control": {"type": "ephemeral", "ttl": "1h"}
```

### Cost Structure
| Type | Cost vs Base Input |
|------|-------------------|
| Cache write (5-min) | 125% |
| Cache read | 10% |
| Regular input | 100% |
Breakpoints add zero cost.

### What Can/Cannot Be Cached
**Can**: tools array, system messages, text messages (user+assistant), images, tool use/results, thinking blocks (indirectly)
**Cannot**: thinking blocks directly, sub-content blocks (citations), empty text blocks

### Cache Invalidation: `tools` -> `system` -> `messages` (changes cascade down)
Tool definition changes invalidate EVERYTHING. Tool choice/images only invalidate messages.

### Multi-Turn Pattern
```python
response = client.messages.create(
    system=[{"type":"text", "text": LONG_SYSTEM_PROMPT,
             "cache_control": {"type":"ephemeral"}}],
    messages=messages
)
# Tracking: response.usage.cache_read_input_tokens, cache_creation_input_tokens, input_tokens
# Total = cache_read + cache_creation + input_tokens
```
20-block lookback from breakpoint. For >20 blocks, add extra breakpoints before editable content.

### Best Practices
1. Cache stable content at prompt beginning (tools -> system -> messages)
2. `cache_control` at end of conversation for automatic lookback
3. 5-min for frequent requests, 1-hour for >5min gaps
4. Keep tool definitions stable; ensure stable JSON key ordering

### Nikita Notes
- System prompt (~3K tokens) should use `cache_control` -> 90% savings after turn 1
- Voice pipeline: 1-hour TTL (user may pause >5min)
- Pydantic AI does NOT manage cache_control — implement at AnthropicModel/HTTP layer

### Docs: https://platform.claude.com/docs/en/build-with-claude/prompt-caching

---

## 3. Supabase JSONB

### Status
- PostgreSQL native JSONB; extensions: `pg_jsonschema` for validation, GIN indexes built-in

### Key Operators
| Op | Returns | Description |
|----|---------|-------------|
| `->` | jsonb | Get by key/index |
| `->>` | text | Get as text |
| `@>` | bool | Contains |
| `?` / `?|` / `?&` | bool | Key exists / any / all |
| `||` | jsonb | Merge |
| `-` / `#-` | jsonb | Delete key / at path |

### Partial Updates
```sql
update t set data = jsonb_set(data, '{key}', '"value"') where id=1;  -- set key
update t set data = data || '{"new": "val"}' where id=1;             -- merge
update t set data = data - 'old_key' where id=1;                      -- remove
update t set data = data #- '{nested,path}' where id=1;               -- remove nested
```

### GIN Indexes
```sql
create index idx_meta on t using gin (metadata);                -- full: @>, ?, ?|, ?&
create index idx_meta_path on t using gin (metadata jsonb_path_ops); -- @> only, 2-3x smaller
create index idx_key on t ((metadata->>'key'));                  -- BTREE on specific key
```

### JSONB + pgVector (SupabaseMemory pattern)
```sql
select * from memories
where metadata @> '{"type":"episodic"}'
order by embedding <=> query_vector limit 10;
-- GIN on metadata + IVFFlat on embedding work together
```

### RLS on JSONB
```sql
create policy "own_data" on t for select
using (metadata->>'owner_id' = auth.uid()::text);
```

### Schema Validation (pg_jsonschema)
```sql
alter table t add constraint check_data check (
    json_matches_schema('{"type":"object","properties":{...}}', data)
);
```

### Performance
- GIN index: 2-3x data size (jsonb_path_ops 2-3x smaller)
- `@>` with GIN: sub-millisecond for typical tables
- `->>` without index: sequential scan — add BTREE for frequent queries

### Nikita Notes
- `conversations.messages` JSONB array — GIN index candidate
- `onboarding_profile` JSONB — pg_jsonschema validation recommended
- Memory metadata + pgVector: already in SupabaseMemory
- Vice/preference configs: JSONB with `jsonb_set` partial updates

### Docs: https://supabase.com/docs/guides/database/json

---

## 4. pg_cron

### Status
- Pre-installed on Supabase; schema: `cron.job`, `cron.job_run_details`
- Companion: pg_net for HTTP; Nikita: 5 active jobs (decay, deliver, summary, cleanup, process)

### Scheduling Syntax
```
┌─ min(0-59) ┌─ hour(0-23) ┌─ dom(1-31) ┌─ month(1-12) ┌─ dow(0-6)
*             *              *             *               *
```
Sub-minute: `'30 seconds'` (Postgres >=15.1.1.61)

### Job Types
```sql
-- 1. SQL snippet
select cron.schedule('cleanup', '30 3 * * 6',
    $$ delete from events where event_time < now()-interval '1 week' $$);
-- 2. DB function
select cron.schedule('fn', '*/5 * * * *', 'SELECT hello_world()');
-- 3. HTTP via pg_net (Edge Function / Cloud Run)
select cron.schedule('invoke', '30 seconds', $$
    select net.http_post(
        url:='https://project.supabase.co/functions/v1/fn',
        headers:=jsonb_build_object('Authorization','Bearer '||'KEY'),
        body:=jsonb_build_object('time',now()),
        timeout_milliseconds:=5000
    ) as request_id; $$);
```

### Managing Jobs
```sql
select * from cron.job;                              -- list all
select cron.alter_job(job_id:=10, schedule:='*/30 * * * *'); -- edit
select cron.alter_job(job_id:=10, active:=false);    -- deactivate
select cron.unschedule('job-name');                   -- delete
```

### Monitoring
```sql
select * from cron.job_run_details
where jobid=(select jobid from cron.job where jobname='decay-scores')
order by start_time desc limit 10;
-- Status: 'succeeded' or 'failed' + return_message
```

### Limitations
1. `job_run_details` NOT auto-cleaned — schedule cleanup job
2. Max 8 concurrent jobs recommended; each <10 min runtime
3. All schedules in GMT; no built-in retries
4. pg_net required for HTTP; Cloud Run cold start needs adequate timeout (30s)

### Nikita Notes
- 5 jobs via pg_net -> Cloud Run task endpoints; 30s timeout for cold start
- **Action item**: add job_run_details cleanup cron (currently missing)
- Optimization: move pure-SQL decay logic out of Cloud Run into cron SQL snippet

### Docs: https://supabase.com/docs/guides/cron

---

## Integration Matrix — How These Interact for Nikita

| Pair | Integration | Opportunity |
|------|-------------|-------------|
| Pydantic AI + Caching | System prompt + tools sent to Claude API | Cache persona (~3K tokens) at HTTP layer; 90% savings |
| JSONB + pgVector | SupabaseMemory: GIN filter then cosine sort | Already implemented; add GIN index on conversations |
| pg_cron + Cloud Run | pg_net HTTP POST -> task endpoints | Adequate timeout for cold start; consider SQL-only for simple ops |
| JSONB + pg_cron | Direct SQL updates on JSONB columns | Move decay math to pure SQL, skip Cloud Run round-trip |
| Pydantic AI multi-agent | Delegation with different models | Haiku for sub-tasks (scoring, conflict) = cost reduction |
