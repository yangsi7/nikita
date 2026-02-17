# Pipeline + Prompt + Agent Code Analysis — Gate 4.5

Date: 2026-02-17
Sources: orchestrator.py, 9 stage files, prompt_builder.py, system_prompt.j2, agent.py, deps.py, handler.py, message_handler.py, supabase_memory.py, models.py, token_counter.py, doc 24

---

## 1. Pipeline Architecture

### 9-Stage Flow (with file:line references)

```
PipelineOrchestrator (nikita/pipeline/orchestrator.py:26)
├─ [1] extraction    [CRITICAL] nikita/pipeline/stages/extraction.py:33    timeout=120s
├─ [2] memory_update [CRITICAL] nikita/pipeline/stages/memory_update.py:22  timeout=60s
├─ [3] life_sim      [non-crit] nikita/pipeline/stages/life_sim.py:37      timeout=60s
├─ [4] emotional     [non-crit] nikita/pipeline/stages/emotional.py:21     timeout=30s
├─ [5] game_state    [non-crit] nikita/pipeline/stages/game_state.py:24    timeout=30s
├─ [6] conflict      [non-crit] nikita/pipeline/stages/conflict.py:22      timeout=15s
├─ [7] touchpoint    [non-crit] nikita/pipeline/stages/touchpoint.py:21    timeout=30s
├─ [8] summary       [non-crit] nikita/pipeline/stages/summary.py:22       timeout=60s
└─ [9] prompt_builder[non-crit] nikita/pipeline/stages/prompt_builder.py:35 timeout=90s
```

**Stage registration**: `STAGE_DEFINITIONS` list at `orchestrator.py:39-49` — lazy class-path imports.

**Stage base**: `BaseStage` at `stages/base.py:48` — abstract `_run()`, wraps with timeout + rollback.

**Execution model**: Sequential, SAVEPOINT isolation per stage (`orchestrator.py:184`). Non-critical stages get 1 retry (`orchestrator.py:175`).

### Data Flow Between Stages

```
PipelineContext (models.py:16) — shared mutable dataclass, 40+ fields
    │
    ├─ [core]       conversation_id, user_id, platform, started_at
    ├─ [user state]  chapter, game_status, relationship_score, metrics{4}, vices[], engagement_state
    ├─ [extraction]  extracted_facts[], extracted_threads[], extracted_thoughts[], extraction_summary, emotional_tone
    ├─ [memory]      facts_stored, facts_deduplicated
    ├─ [life_sim]    life_events[]
    ├─ [emotional]   emotional_state{arousal,valence,dominance,intimacy}
    ├─ [game_state]  score_delta, score_events[], chapter_changed, decay_applied
    ├─ [conflict]    active_conflict, conflict_type, game_over_triggered
    ├─ [touchpoint]  touchpoint_scheduled
    ├─ [summary]     daily_summary_updated, extraction_summary
    ├─ [enriched]    last_conversation_summary, today_summaries, week_summaries, hours_since_last,
    │                open_threads[], relationship_episodes[], nikita_events[], nikita_activity,
    │                nikita_mood, nikita_energy, time_of_day, inner_monologue, active_thoughts[],
    │                vulnerability_level, nikita_daily_events
    └─ [prompt]      generated_prompt, prompt_token_count
```

**Flow direction**: Linear. Each stage reads ctx fields populated by prior stages and writes its own section. prompt_builder (stage 9) consumes output from ALL prior stages via `_enrich_context()` and `_build_template_vars()`.

**Critical dependency chain**:
```
extraction → memory_update → (all downstream stages read extracted_*)
emotional  → conflict (reads emotional_state for ConflictDetector)
```

### Extension Points for New Features

| Extension Point | Location | What Can Be Injected | Effort |
|----------------|----------|---------------------|--------|
| **New pipeline stage** | `orchestrator.py:39-49` STAGE_DEFINITIONS list | Add tuple: `("psyche_read", "path.PsycheReadStage", False)` | Low — just add entry + stage class |
| **New PipelineContext fields** | `models.py:16` PipelineContext dataclass | Add new fields (e.g., `psyche_state: dict`) | Low — add field with default |
| **Pre-pipeline hook** | `orchestrator.py:108-113` between ctx init and stage loop | Insert reads before stage 1 (psyche read, trigger detect) | Medium — modify process() |
| **Inter-stage injection** | `orchestrator.py:172` stage loop | Conditional logic between stages | Medium — modify loop |
| **Post-pipeline hook** | `orchestrator.py:233-239` after stage loop | Post-processing, notifications | Low |
| **Stage constructor override** | `orchestrator.py:80` `cls(session=self._session)` | Pass additional args (e.g., psyche_state) | Medium |
| **Template variables** | `prompt_builder.py:276-347` `_build_template_vars()` | Add new vars to template dict | Low |
| **Template sections** | `templates/system_prompt.j2` | Add new `{# SECTION N #}` blocks | Low |
| **Enrichment sources** | `prompt_builder.py:102-214` `_enrich_context()` | Add new data loading (psyche_states table read) | Medium |

**Best insertion point for psyche_state**: Add as stage 0 (before extraction) or as a pre-pipeline read in `orchestrator.process()` at line 108. The psyche state needs to be available to prompt_builder at stage 9, so any position works, but "before extraction" is cleanest since extraction is the first consumer that could benefit from psyche guidance.

**Best insertion point for trigger detection**: Inside `orchestrator.process()` at line 113, BEFORE the stage loop. This is a lightweight rule-based check (<5ms) that determines if a Tier 2/3 psyche update is needed.

---

## 2. Prompt Building

### 11-Section Template Map

| # | Section | Template Lines | Data Source | Token Est. | Platform |
|---|---------|---------------|-------------|-----------|----------|
| 1 | IDENTITY | `j2:1-35` (~400 tok) | Static text (hardcoded in template) | ~400 | both |
| 2 | IMMERSION RULES | `j2:37-49` (~200 tok) | Static text | ~200 | both |
| 3 | PLATFORM STYLE | `j2:51-119` (~300 tok) | `platform` variable (text/voice conditional) | ~300 | both (branched) |
| 4 | CURRENT STATE | `j2:122-155` (~600 tok) | `nikita_activity`, `nikita_mood`, `nikita_energy`, `emotional_state`, `life_events[]` | ~600 | both |
| 5 | RELATIONSHIP STATE | `j2:157-175` (~500 tok) | `chapter`, `relationship_score`, `engagement_state`, `active_conflict`, `conflict_type` | ~500 | both |
| 6 | MEMORY | `j2:178-267` (~800/300 tok) | `user` (profile), `extracted_facts[]`, `relationship_episodes[]`, `nikita_events[]` | ~800 text / ~300 voice | both (size-limited) |
| 7 | CONTINUITY | `j2:269-310` (~600 tok) | `last_conversation_summary`, `today_summaries`, `week_summaries`, `hours_since_last`, `open_threads[]` | ~600 | both |
| 8 | INNER LIFE | `j2:312-357` (~500 tok) | `extracted_thoughts[]`, `inner_monologue`, `active_thoughts[]`, `chapter` (static questions) | ~500 | both |
| 9 | PSYCHOLOGICAL DEPTH | `j2:359-416` (~400 tok) | `vulnerability_level` (semi-static: attachment style, wounds, triggers) | ~400 | both |
| 10 | CHAPTER BEHAVIOR | `j2:418-594` (~300 tok) | `chapter` (1-5 behavior guides, large conditional blocks) | ~300 | both |
| 11 | VICE SHAPING | `j2:597-624` (~200 tok) | `vices[]` (top 5, per-vice conditional text) | ~200 | both |
| - | FOOTER (Response Guidelines) | `j2:627-731` (~700 tok) | `chapter`, `vulnerability_level`, `platform` | ~700 | text only (voice gets shortened footer) |

**Total estimated tokens**: ~5,500 (text) / ~2,000 (voice)

### Assembly Process (prompt_builder.py)

```
PromptBuilderStage._run() (prompt_builder.py:59)
  │
  ├─ [1] _enrich_context(ctx) (prompt_builder.py:102)
  │     ├─ compute_time_of_day, day_of_week, activity, energy, mood, vulnerability (nikita_state utils)
  │     ├─ load conversation summaries (ConversationRepository.get_conversation_summaries_for_prompt)
  │     ├─ load user data + hours_since_last (UserRepository.get)
  │     ├─ load memory episodes (SupabaseMemory.search × 2: relationship + nikita)
  │     └─ populate open_threads from extracted_threads
  │
  ├─ [2] _generate_prompt(ctx, "text") (prompt_builder.py:216)
  │     ├─ _render_template("system_prompt.j2", ctx, platform="text")
  │     │     └─ _build_template_vars(ctx, "text") → 35+ variable dict → Jinja2 render
  │     ├─ _count_tokens(raw_prompt) — tiktoken via token_counter.py:173
  │     ├─ _enrich_with_haiku(raw_prompt, "text") — Claude Haiku narrative polish (optional)
  │     ├─ _enforce_token_budget(prompt, tokens, "text") — truncate if > 6500 tokens
  │     └─ _store_prompt(ctx, "text", ...) — ReadyPromptRepository.set_current()
  │
  └─ [3] _generate_prompt(ctx, "voice") — same flow, different platform + budget
```

**Template rendering**: `pipeline/templates/__init__.py` — Jinja2 `FileSystemLoader`, `lru_cache(1)` on Environment.

**Variable injection**: `_build_template_vars()` at `prompt_builder.py:276-347` — flat dict, 35+ keys, maps PipelineContext fields to template variables.

### Token Budget Mechanism (current)

| Budget | Platform | Min | Max | Source |
|--------|----------|-----|-----|--------|
| Text | text | 5,500 | 6,500 | `prompt_builder.py:51-52` |
| Voice | voice | 1,800 | 2,200 | `prompt_builder.py:53-54` |

**Counting**: `token_counter.py:173` `count_tokens()` — tiktoken `cl100k_base` encoder, cached singleton. Two-tier: fast (chars/4) and accurate (tiktoken).

**Truncation priority** (lowest priority cut first, `prompt_builder.py:468-473`):
```
1. "## 11. VICE SHAPING"        — cut first
2. "## 10. CHAPTER BEHAVIOR"    — cut second
3. "## 9. PSYCHOLOGICAL DEPTH"  — cut third
```

**Truncation method**: `_remove_section()` at `prompt_builder.py:486-506` — string find/slice by section header. Falls back to `TokenCounter.truncate_to_budget()` for hard truncation.

**Warning**: Under-budget prompts are warned but not padded (`prompt_builder.py:428-434`).

---

## 3. Agent Architecture

### Current Agent Structure

```
nikita/agents/text/agent.py
├─ MODEL_NAME = "anthropic:claude-sonnet-4-5-20250929"     (agent.py:35)
├─ LLM_TIMEOUT_SECONDS = 120.0                             (agent.py:39)
├─ DEFAULT_USAGE_LIMITS = UsageLimits(                     (agent.py:43)
│     output_tokens_limit=4000,
│     request_limit=10,
│     tool_calls_limit=20)
│
├─ _create_nikita_agent() → Agent[NikitaDeps, str]         (agent.py:56)
│     ├─ Agent(MODEL_NAME, deps_type=NikitaDeps, output_type=str, instructions=NIKITA_PERSONA)
│     │
│     ├─ @agent.instructions: add_chapter_behavior(ctx)     (agent.py:80-85)
│     │   └─ Returns: "\n\n## CURRENT CHAPTER BEHAVIOR\n{chapter_behavior}"
│     │
│     ├─ @agent.instructions: add_personalized_context(ctx) (agent.py:88-105)
│     │   └─ Returns: "\n\n## PERSONALIZED CONTEXT\n{deps.generated_prompt}" or ""
│     │
│     ├─ @agent.tool(retries=2): recall_memory(ctx, query)  (agent.py:108-133)
│     │   └─ SupabaseMemory.search_memory(query, limit=5) → formatted text
│     │
│     └─ @agent.tool: note_user_fact(ctx, fact, confidence)  (agent.py:136-163)
│         └─ SupabaseMemory.add_user_fact(fact, confidence)
│
├─ get_nikita_agent() → cached singleton                    (agent.py:169-179)
│
├─ _AgentProxy → lazy init wrapper                          (agent.py:183-199)
│
├─ _try_load_ready_prompt(user_id, session)                 (agent.py:202-266)
│   └─ ReadyPromptRepository.get_current(user_id, "text") → prompt_text
│
├─ build_system_prompt(memory, user, message, conv_id, session) (agent.py:269-326)
│   ├─ if unified_pipeline_enabled → load from ready_prompts
│   └─ else → _build_system_prompt_legacy()
│
└─ generate_response(deps, user_message)                    (agent.py:368-523)
    ├─ load_message_history(conversation_messages, limit=80, token_budget=3000)
    ├─ build_system_prompt() → deps.generated_prompt
    └─ nikita_agent.run(user_message, deps=deps, message_history=..., usage_limits=...)
```

### Tool Registration

| Tool | Registered At | Retries | Purpose |
|------|--------------|---------|---------|
| `recall_memory` | `agent.py:108` | 2 | Semantic search of memory_facts during conversation |
| `note_user_fact` | `agent.py:136` | 0 | Write user fact to memory (live, during conversation) |

Both tools access `ctx.deps.memory` (SupabaseMemory instance injected via NikitaDeps).

### Dependency Injection

```
NikitaDeps (agents/text/deps.py:20)
├─ memory: SupabaseMemory | None
├─ user: User (ORM model with game state)
├─ settings: Settings
├─ generated_prompt: str | None          — injected by generate_response() before agent.run()
├─ conversation_messages: list[dict] | None — from conversation.messages JSONB
├─ conversation_id: UUID | None
└─ session: AsyncSession | None          — for ready_prompt loading
```

**Dep loading**: `nikita/agents/text/__init__.py:get_nikita_agent_for_user(user_id)` — loads user from DB, creates SupabaseMemory, constructs NikitaDeps.

### Extension Points for Psyche Agent

| Extension Point | Location | How to Extend |
|----------------|----------|--------------|
| **New agent class** | Create `nikita/agents/psyche/agent.py` | New `Agent[PsycheDeps, PsycheState]` with Opus 4.6 model |
| **Deps type** | Create `nikita/agents/psyche/deps.py` | New dataclass: conversation history, memory facts, score trajectory, current psyche state |
| **Output type** | Create `nikita/agents/psyche/models.py` | Pydantic model: `PsycheState` with attachment_activation, defense_mode, behavioral_guidance, etc. |
| **Shared tools** | `recall_memory` could be shared | Psyche agent needs read-only memory access (no note_user_fact) |
| **Shared deps** | `memory`, `settings` are common | Both agents need SupabaseMemory; psyche also needs score_history |
| **Different model** | `Agent("anthropic:claude-opus-4-6", ...)` | Higher capability for deep psychological analysis |
| **Different output** | `output_type=PsycheState` (structured) | Psyche agent returns structured JSONB, not freeform text |
| **No instructions decorator** | Psyche agent is stateless per-call | System prompt is fixed analysis prompt, not dynamic persona |
| **Batch mode** | `agent.run()` called by pg_cron batch job | Not per-message; runs daily or on trigger |
| **Result storage** | Write to `psyche_states` table | New repository: PsycheStateRepository.upsert() |

**Psyche agent creation pattern** (following existing agent.py:56 pattern):
```python
from pydantic_ai import Agent
from nikita.agents.psyche.deps import PsycheDeps
from nikita.agents.psyche.models import PsycheState

psyche_agent = Agent(
    "anthropic:claude-opus-4-6",
    deps_type=PsycheDeps,
    output_type=PsycheState,  # Structured output
    system_prompt=PSYCHE_ANALYSIS_PROMPT,
)
```

---

## 4. Template → Layer Mapping

Doc 24 proposes 7 layers. Current template has 11 sections + footer. Mapping:

| Doc 24 Layer | Tok | Current Template Section(s) | Status | Changes Needed |
|-------------|-----|---------------------------|--------|---------------|
| **L1: IDENTITY** (static, ~2K) | 2000 | S1: IDENTITY (~400) + NIKITA_PERSONA (agents/text/persona.py ~1600) | SPLIT | Consolidate NIKITA_PERSONA + S1 into single L1 block. Currently persona.py has a DIFFERENT backstory (Brooklyn, MIT, NSA) vs template (Berlin, Prenzlauer Berg). **CONFLICT** — must reconcile |
| **L2: IMMERSION + PLATFORM** (static/platform, ~500) | 500 | S2: IMMERSION RULES (~200) + S3: PLATFORM STYLE (~300) | MATCH | Direct rename. Already functions as single layer |
| **L3: PSYCHE STATE** (semi-static, ~150) | 150 | **DOES NOT EXIST** | GAP | New: inject psyche_states JSONB as ~150 token briefing between L2 and L4 |
| **L4: DYNAMIC CONTEXT** (per-conv, ~3K) | 3000 | S4: CURRENT STATE (~600) + S5: RELATIONSHIP STATE (~500) + S6: MEMORY (~800) + S7: CONTINUITY (~600) + S8: INNER LIFE (~500) | MATCH | Repackage as L4 sub-sections (4a-4e). Current structure already matches doc 24 sub-layout |
| **L5: CHAPTER BEHAVIOR** (~300) | 300 | S10: CHAPTER BEHAVIOR (~300) | MATCH | Rename only. Same content |
| **L6: VICE SHAPING** (~200) | 200 | S11: VICE SHAPING (~200) | MATCH | Rename only. Same content |
| **L7: RESPONSE GUIDELINES** (static, ~700) | 700 | FOOTER: Response Guidelines (~700) | MATCH | Rename to explicit Layer 7. Currently only text platform gets full footer |

### Key Conflicts and Gaps

| Issue | Severity | Detail |
|-------|----------|--------|
| **NIKITA_PERSONA vs template S1 conflict** | HIGH | `persona.py:18` says Brooklyn/MIT/NSA. `system_prompt.j2:11` says Berlin/Prenzlauer Berg. When unified pipeline is ON, only template is used. When OFF (legacy fallback), only persona.py is used. Need to reconcile or fully deprecate persona.py |
| **S9: PSYCHOLOGICAL DEPTH missing from doc 24** | MEDIUM | Doc 24 doesn't have explicit psych layer. Content (attachment style, wounds, triggers) should fold into L3 (psyche state briefing) or remain as part of L4e (inner life). Currently ~400 tokens |
| **Psyche state layer (L3) doesn't exist** | HIGH | Doc 24's key innovation — psyche_states table → 150 token briefing. Must create: DB table, batch job, template section, prompt_builder enrichment |
| **Response Guidelines (footer) is text-only** | LOW | Voice gets abbreviated footer at j2:630-638. Doc 24 L7 doesn't distinguish. Current behavior is correct for token budgets |

---

## 5. Memory Integration

### Current pgVector Flow

```
WRITE PATH (post-conversation pipeline):
  ExtractionStage (extraction.py:68) → ctx.extracted_facts[]
    → MemoryUpdateStage (memory_update.py:38)
        → SupabaseMemory.find_similar(threshold=0.95) — dedup check
        → SupabaseMemory.add_fact(fact, graph_type, source, confidence)
            → _generate_embedding() — OpenAI text-embedding-3-small (1536 dims)
            → MemoryFactRepository.add_fact() — INSERT to memory_facts
            → If duplicate: deactivate old, point superseded_by_id

READ PATH (prompt building — prompt_builder.py:165-200):
  PromptBuilderStage._enrich_context()
    → SupabaseMemory.search("shared moments relationship history", fact_types=["relationship"], limit=10)
    → SupabaseMemory.search("nikita life events activities", fact_types=["nikita"], limit=10)
    → ctx.relationship_episodes = [f.fact for f in rel_facts]
    → ctx.nikita_events = [f.fact for f in nikita_facts]

READ PATH (live conversation — agent.py:108):
  recall_memory tool → SupabaseMemory.search_memory(query, limit=5)
    → _generate_embedding(query) — OpenAI embedding
    → MemoryFactRepository.semantic_search() — pgVector cosine similarity
    → format_memory_results() — "[date] (label) fact" format

WRITE PATH (live conversation — agent.py:136):
  note_user_fact tool → SupabaseMemory.add_user_fact(fact, confidence)
    → add_fact(fact, graph_type="user", source="user_message", ...)
```

**Three graph types**: `user`, `relationship`, `nikita` — defined at `supabase_memory.py:30`.

**Embedding**: OpenAI `text-embedding-3-small`, 1536 dims, 3 retries with exponential backoff (`supabase_memory.py:92-122`).

### Extension Points for Psyche State

| Extension | Location | Detail |
|-----------|----------|--------|
| **Psyche reads memory** | New psyche agent deps | Psyche batch job needs ALL facts for 7-day window: `memory.search(query, limit=50)` |
| **Psyche writes to psyche_states** | New table + repository | NOT to memory_facts — psyche state is structured JSONB, not vector-embedded facts |
| **Prompt builder reads psyche_states** | `prompt_builder.py:102` `_enrich_context()` | Add: `PsycheStateRepository.get_current(user_id)` → `ctx.psyche_state` |
| **Template renders psyche briefing** | `system_prompt.j2` new section between S2-S4 | New `{# SECTION 3: PSYCHE STATE #}` with `{{ psyche_state.behavioral_guidance }}` etc. |
| **PipelineContext field** | `models.py:16` | Add: `psyche_state: dict | None = None` |

---

## 6. Message Handler Flow

### Entry Points

```
Telegram WebhookRoute (nikita/api/routes/telegram.py)
  → TelegramMessage parsing
    → message_handler.handle(message)

MessageHandler (nikita/platforms/telegram/message_handler.py:69)
```

### Pipeline Invocation

The pipeline is NOT invoked during message handling. It runs asynchronously via pg_cron:

```
MESSAGE FLOW (synchronous, per-message):
  MessageHandler.handle(message) (message_handler.py:129)
    ├─ Auth: user_repository.get_by_telegram_id()           (line 155)
    ├─ Profile gate: _needs_onboarding()                     (line 170)
    ├─ Boss fight gate: _handle_boss_response()              (line 179)
    ├─ Game over/won gate: _send_game_status_response()      (line 187)
    ├─ Rate limit: rate_limiter.check()                      (line 196)
    ├─ Conversation: _get_or_create_conversation()           (line 204)
    ├─ Append user message to conversation                   (line 211)
    ├─ Typing indicator                                      (line 222)
    ├─ TEXT AGENT: text_agent_handler.handle()               (line 235)
    │     └─ handler.py:220 → generate_response(deps, message)
    │           └─ agent.py:368 → build_system_prompt() + nikita_agent.run()
    ├─ Append nikita response to conversation                (line 267)
    ├─ SCORING: _score_and_check_boss()                      (line 274)
    │     ├─ ScoringService.score_interaction()
    │     ├─ UserRepository.update_score()
    │     ├─ UserMetricsRepository.update_metrics()
    │     ├─ ConversationRepository.update_score_delta()
    │     └─ Boss threshold check → set boss_fight + send opening
    ├─ Update last_interaction_at                            (line 284)
    ├─ Text patterns                                         (line 288)
    ├─ Rate limit warning                                    (line 292)
    ├─ ENGAGEMENT: _update_engagement_after_scoring()        (line 550)
    └─ Response delivery: response_delivery.queue()          (line 305)

PIPELINE FLOW (async, post-conversation):
  pg_cron → POST /tasks/process-conversations (every minute)
    → SessionDetector.detect_and_queue() — find 15-min stale conversations
    → PipelineOrchestrator.process(conversation_id, user_id, platform)
      → 9 stages sequentially → ready_prompts updated for next conversation
```

### Response Processing

```
generate_response() (agent.py:368)
  │
  ├─ load_message_history()              — last 80 turns, 3K token budget
  ├─ build_system_prompt()               — from ready_prompts (pre-built) or on-the-fly
  │     └─ _try_load_ready_prompt()      — ReadyPromptRepository.get_current(user_id, "text")
  ├─ nikita_agent.run(                   — Pydantic AI agent invocation
  │     user_message,
  │     deps=deps,                       — NikitaDeps with memory, user, prompt
  │     message_history=history,         — PydanticAI ModelMessage list
  │     usage_limits=DEFAULT_USAGE_LIMITS — 4K out, 10 requests, 20 tool calls
  │   )
  └─ return result.output                — plain string response
```

**System prompt injection flow**:
```
ready_prompts table (pre-built by pipeline stage 9)
  → build_system_prompt() reads it
    → stored in deps.generated_prompt
      → @agent.instructions: add_personalized_context()
        → injected as "## PERSONALIZED CONTEXT\n{prompt}" into system prompt
          → Pydantic AI combines: NIKITA_PERSONA + chapter_behavior + personalized_context
```

**Doc 24 change**: Insert psyche state READ + trigger detection BEFORE prompt assembly. Currently happens: `build_system_prompt() → load ready_prompt`. Proposed: `read_psyche_state() → trigger_detect() → [optional psyche update] → assemble_prompt()`.

---

## 7. Recommendations

### Where to inject psyche state

**Option A (Recommended): Pre-conversation read in message handler**
```
message_handler.py:235 (before text_agent_handler.handle())
  ├─ read psyche_states table (JSONB, <10ms)
  ├─ run trigger detector (rule-based, <5ms)
  ├─ [if Tier 2/3] update psyche state inline (300ms-3s)
  └─ pass psyche_state to text_agent_handler via new dep field
```

**Why**: Psyche state must influence the CURRENT conversation, not the NEXT one. The pipeline runs post-conversation and pre-builds the NEXT prompt. But psyche triggers (Tier 2/3) need to update the state BEFORE the current response is generated.

**Implementation**:
1. Add `psyche_state: dict | None = None` to `NikitaDeps` (`deps.py:20`)
2. Add new `@agent.instructions` decorator in `agent.py` that injects psyche briefing
3. Read from `psyche_states` table in message handler before agent call
4. Trigger detector evaluates: score_delta, keywords, game events
5. If Tier 2/3: call psyche agent inline, write result back to DB

**Option B: Pipeline stage (for pre-building)**
```
orchestrator.py STAGE_DEFINITIONS — add after "conflict" (stage 6):
  ("psyche_batch", "nikita.pipeline.stages.psyche_batch.PsycheBatchStage", False)
```
This handles the daily batch / post-conversation refresh. Both options are needed.

### How to create second agent

```python
# nikita/agents/psyche/agent.py
from pydantic_ai import Agent
from nikita.agents.psyche.models import PsycheState

PSYCHE_SYSTEM_PROMPT = """You are Nikita's subconscious — analyzing 7 days of conversation
history, memory facts, and score trajectory to determine her current psychological state..."""

psyche_agent = Agent(
    "anthropic:claude-opus-4-6",
    output_type=PsycheState,  # Structured Pydantic output
    system_prompt=PSYCHE_SYSTEM_PROMPT,
)

async def analyze_psyche(
    conversation_history: list[dict],
    memory_facts: list[str],
    score_trajectory: list[float],
    current_state: PsycheState | None,
) -> PsycheState:
    result = await psyche_agent.run(
        f"Analyze Nikita's psychological state:\n"
        f"History: {json.dumps(conversation_history[-50:])}\n"
        f"Facts: {chr(10).join(memory_facts[:30])}\n"
        f"Scores: {score_trajectory[-14:]}\n"
        f"Current: {current_state.model_dump_json() if current_state else 'None'}"
    )
    return result.output
```

**Key differences from conversation agent**:
- Model: Opus 4.6 (not Sonnet 4.5) — deeper analysis capability
- Output: Structured `PsycheState` (not freeform `str`)
- No tools: Read-only analysis, no memory writes during psyche analysis
- No instructions decorators: Fixed system prompt, no dynamic persona overlay
- No message_history: Receives full context as user message, not turn-by-turn
- Batch mode: Called by pg_cron or trigger, not per-message

### Token budget implementation approach

**Current mechanism** (`prompt_builder.py:408-484`):
- Counts with tiktoken after Jinja2 render
- Truncates by removing full sections (vice → chapter → psychology)
- Falls back to hard character-based truncation
- Stores in `ready_prompts` with token_count metadata

**Doc 24 enhancement**:
1. **Add psyche briefing** (~150 tokens) — fits within existing 5,500-6,500 text budget
2. **Adjust truncation order** to match doc 24 priorities:
   ```
   Current:  Vice → Chapter → Psychology
   Proposed: Vice → Chapter → Inner Life → Psychology (keep psyche state untouched)
   ```
3. **Cache-aware assembly**: Structure prompt so static layers (L1, L2) are at the top for Anthropic prompt caching. Currently NIKITA_PERSONA is injected via `@agent.instructions` (not cache-friendly). Move to top of assembled prompt.
4. **Pre-compute and store layer boundaries**: Track per-layer token counts in `ready_prompts.context_snapshot` for monitoring.

**Prompt caching optimization path**:
```
Current flow:
  NIKITA_PERSONA (via @agent.instructions, not cached)
  + CHAPTER_BEHAVIOR (via @agent.instructions, not cached)
  + PERSONALIZED_CONTEXT (via @agent.instructions, entire pipeline prompt)

Proposed flow:
  [cache_control: ephemeral] L1 IDENTITY (~2K, static) ← Anthropic will cache
  [cache_control: ephemeral] L2 IMMERSION+PLATFORM (~500, static) ← cached
  L3 PSYCHE STATE (~150, semi-static) ← changes rarely
  L4 DYNAMIC CONTEXT (~3K, per-conversation) ← never cached
  L5 CHAPTER BEHAVIOR (~300, changes on chapter) ← cached per chapter
  L6 VICE SHAPING (~200, slow change) ← cached
  L7 RESPONSE GUIDELINES (~700, static) ← cached
```

To achieve this, the `generated_prompt` must be the COMPLETE system prompt (not a supplement to NIKITA_PERSONA). When unified pipeline is enabled, `add_personalized_context()` should return the full prompt and `add_chapter_behavior()` should return empty string. This is already the case — see `agent.py:103-105`.

---

## Appendix: File Reference Index

| File | Lines | Role |
|------|-------|------|
| `nikita/pipeline/orchestrator.py` | 240 | 9-stage sequential runner |
| `nikita/pipeline/models.py` | 155 | PipelineContext (40+ fields), PipelineResult |
| `nikita/pipeline/stages/base.py` | 108 | BaseStage ABC, StageResult, StageError |
| `nikita/pipeline/stages/extraction.py` | 122 | CRITICAL: LLM fact extraction (Sonnet 4.5) |
| `nikita/pipeline/stages/memory_update.py` | 107 | CRITICAL: pgVector writes + dedup |
| `nikita/pipeline/stages/life_sim.py` | 89 | Non-crit: daily event generation |
| `nikita/pipeline/stages/emotional.py` | 117 | Non-crit: 4D emotional state (arousal/valence/dominance/intimacy) |
| `nikita/pipeline/stages/game_state.py` | 117 | Non-crit: score validation, boss proximity |
| `nikita/pipeline/stages/conflict.py` | 102 | Non-crit: ConflictDetector + breakup check |
| `nikita/pipeline/stages/touchpoint.py` | 47 | Non-crit: proactive message scheduling |
| `nikita/pipeline/stages/summary.py` | 136 | Non-crit: daily conversation summaries |
| `nikita/pipeline/stages/prompt_builder.py` | 591 | Non-crit: Jinja2 render + Haiku enrich + store |
| `nikita/pipeline/templates/__init__.py` | 34 | Jinja2 Environment + render_template() |
| `nikita/pipeline/templates/system_prompt.j2` | 731 | 11-section unified template |
| `nikita/agents/text/agent.py` | 524 | Pydantic AI agent + generate_response() |
| `nikita/agents/text/deps.py` | 59 | NikitaDeps dependency container |
| `nikita/agents/text/tools.py` | 130 | recall_memory, note_user_fact (deprecated) |
| `nikita/agents/text/handler.py` | 391 | MessageHandler: skip→generate→patterns→delay |
| `nikita/agents/text/persona.py` | ~100 | NIKITA_PERSONA static fallback |
| `nikita/platforms/telegram/message_handler.py` | 1328 | Full Telegram message flow |
| `nikita/memory/supabase_memory.py` | 412 | pgVector memory (add/search/dedup) |
| `nikita/context/utils/token_counter.py` | 294 | TokenEstimator + TokenCounter + count_tokens() |
| `docs/brainstorm/proposal/24-system-architecture-diagram.md` | 863 | Doc 24: Gate 4 architecture spec |
