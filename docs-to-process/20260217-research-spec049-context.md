# External Research — Gate 4.5 Spec Preparation
Date: 2026-02-17

## 1. Anthropic Prompt Caching

### Key Findings
- `cache_control: { type: "ephemeral" }` on content blocks caches entire prefix up to that block
- Default TTL: 5 minutes (resets on access); extended 1-hour TTL available (2x write cost)
- **Max 4 cache_control breakpoints per request** — strategic placement required
- Cache match is **exact**: single character/space difference = cache miss
- Cost: ~90% discount on cached input tokens (cache reads); full price on cache writes
- Metrics: `cache_creation_input_tokens`, `cache_read_input_tokens`, `input_tokens`
- Changes to higher-level prompt components invalidate all downstream caches

### Code Patterns
```python
# Multi-turn caching: static system prompt cached, dynamic user messages not
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    system=[
        {"type": "text", "text": "You are Nikita, an AI girlfriend..."},
        {
            "type": "text",
            "text": "[character sheet + game rules + memory context]",
            "cache_control": {"type": "ephemeral"}  # Cache breakpoint 1
        }
    ],
    messages=[
        {"role": "user", "content": "Hey babe, how's your day?"}  # Dynamic, not cached
    ]
)
```

**Extended TTL for low-frequency sessions:**
```python
"cache_control": {"type": "ephemeral", "ttl": "3600"}  # 1 hour
```

### Implications for Nikita
- **High value**: Nikita's system prompt (character sheet, game rules, scoring context) is large and static per session
- Cache the system prompt + character context + recent memory summary as breakpoint 1
- Cache tool definitions as breakpoint 2
- Leave conversation history and user messages uncached (dynamic)
- 5-min TTL sufficient for active conversations; 1-hour TTL for voice sessions with pauses
- **Critical constraint**: 4 breakpoints max — must plan hierarchy: (1) system prompt, (2) character/rules, (3) memory context, (4) tool definitions
- Estimated savings: 70-90% on input token costs for multi-turn conversations

### Sources
- [Spring AI Anthropic Caching](https://spring.io/blog/2025/10/27/spring-ai-anthropic-prompt-caching-blog)
- [Anthropic Engineering - Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)
- [Claude Platform Docs - Tool Use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use)
- [AWS Bedrock Caching Guide](https://aws.amazon.com/blogs/machine-learning/effectively-use-prompt-caching-on-amazon-bedrock/)

---

## 2. Pydantic AI Multi-Agent Patterns

### Key Findings
- Three coordination patterns: **Agent Delegation**, **Programmatic Hand-Off**, **Graph-Based Control Flow**
- Agent class: `Agent(model, deps_type, result_type, system_prompt)` — model-agnostic
- Tool sharing via `@agent.tool` decorator with `RunContext[DepsType]` for dependency injection
- Structured output via `result_type=PydanticModel` — validated at runtime
- Agent delegation: one agent calls `await other_agent.run()` inside a tool
- A2A Protocol support for inter-agent communication with `context_id`
- Streaming via `agent.run_stream()` with progressive validation
- Supports: OpenAI, Anthropic, Gemini, Mistral, Ollama, Groq, Cohere, Deepseek

### Code Patterns
```python
# Agent delegation pattern — text agent delegates to scoring agent
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

class ScoreUpdate(BaseModel):
    engagement: float
    trust: float
    attraction: float
    respect: float

@dataclass
class GameDeps:
    user_id: str
    db: SupabaseClient

scoring_agent = Agent(
    model='anthropic:claude-sonnet-4-5-20250929',
    deps_type=GameDeps,
    result_type=ScoreUpdate,
    system_prompt='Evaluate the conversation and return metric deltas.'
)

text_agent = Agent(
    model='anthropic:claude-sonnet-4-5-20250929',
    deps_type=GameDeps,
    result_type=str,
    system_prompt='You are Nikita...'
)

@text_agent.tool
async def evaluate_scores(ctx: RunContext[GameDeps], message: str) -> ScoreUpdate:
    """Delegate scoring to specialized agent."""
    result = await scoring_agent.run(
        f'Score this interaction: {message}',
        deps=ctx.deps
    )
    return result.data
```

**Dynamic system prompt injection:**
```python
@text_agent.system_prompt
async def add_memory_context(ctx: RunContext[GameDeps]) -> str:
    memories = await ctx.deps.db.get_memories(ctx.deps.user_id)
    return f"Recent memories: {memories}"
```

### Implications for Nikita
- Current architecture uses single agent — multi-agent would enable: text agent, scoring agent, memory agent, conflict agent
- `deps_type` pattern maps well to Nikita's `GameContext` dependency injection
- `result_type` eliminates JSON parsing fragility in current scoring pipeline
- Agent delegation enables clean separation: text generation vs evaluation vs memory storage
- Model-agnostic design allows per-agent model selection (cheap for scoring, premium for text)
- **Migration path**: wrap existing agents in Pydantic AI Agent class, add structured outputs gradually
- Graph-based flow less mature — use simple delegation for now

### Sources
- [Pydantic AI Multi-Agent Tutorial](https://dev.to/hamluk/advanced-pydantic-ai-agents-building-a-multi-agent-system-in-pydantic-ai-1hok)
- [Pydantic AI A2A Protocol](https://ai.pydantic.dev/a2a/)
- [Pydantic AI vs LangChain comparison](https://tech.appunite.com/posts/understanding-pydantic-ai-a-powerful-alternative-to-lang-chain-and-llama-index)
- [Pydantic AI GitHub](https://github.com/pydantic/pydantic-ai)

---

## 3. Dual-Process Cognitive AI (System 1 / System 2)

### Key Findings
- **System 1** (fast/intuitive): Pattern matching, simple classification, cached responses — use small/cheap models
- **System 2** (slow/deliberate): Multi-step reasoning, causal inference, complex decisions — use frontier models
- Key insight: **AI lacks metacognitive ability to recognize when reasoning is unnecessary** — must implement explicit routing
- Production pattern: classifier/router evaluates query → routes to appropriate model tier
- SAP Joule example: "Skills" (deterministic, System 1) vs "Agents" (agentic reasoning, System 2)
- Meta-controller (System 0) dynamically switches between subsystems based on context cues
- Data-driven switching rules outperform hard-coded selection
- Latency targets: <150ms optimal, <400ms acceptable, >2s risks abandonment

### Architecture Pattern
```
User Input
    ↓
[Classifier/Router] ← System 0 (meta-controller)
    ├─ Simple/Routine → [Small Model] ← System 1 (~150ms, $0.001/call)
    │   └─ Greetings, FAQ, simple commands
    └─ Complex/Novel → [Frontier Model] ← System 2 (~2-5s, $0.05/call)
        └─ Scoring, conflict resolution, narrative generation
```

**Routing criteria:**
- Confidence score from classifier (>0.8 → fast path)
- Task type detection (greeting vs deep conversation)
- Error rate monitoring (escalate on repeated failures)
- User state (new user = more System 2, established = more System 1)

### Implications for Nikita
- **High value for cost optimization**: Most Nikita messages are casual chat (System 1) — route to Haiku/fast model
- Complex moments (boss encounters, scoring, conflict) need System 2 — route to Sonnet/Opus
- Router could be: (a) keyword classifier, (b) small LLM, (c) rule-based on game state
- Pipeline stages map naturally: intent classification (S1), response generation (S2), scoring (S1 or S2 based on context)
- Memory retrieval (S1: vector search) vs memory synthesis (S2: narrative summary)
- **Estimated savings**: 60-80% on LLM costs if 70% of messages route to cheap model
- Voice pipeline benefits most: latency-critical, most messages are casual

### Sources
- [SAP Joule Dual-Process](https://www.sap.com/germany/blogs/balancing-autonomy-determinism-when-applying-agentic-ai)
- [System 2 Thinking in AI](https://www.emergentmind.com/topics/system-2-thinking-in-ai)
- [Amazon Science - Overthinking Problem](https://www.amazon.science/blog/the-overthinking-problem-in-ai)
- [Latency vs Accuracy Tradeoffs](https://www.jeeva.ai/blog/latency-cost-accuracy-pick-ai-model-real-time-lead-enrichment)

---

## 4. ElevenLabs Conversational AI 2.0

### Key Findings
- **Server Tools**: HTTP webhook calls to your backend during voice conversation; configured via dashboard/CLI
- **Client Tools**: Client-side function execution (UI actions, local API calls)
- **Flow**: User speaks → ElevenLabs transcribes → Agent decides tool use → HTTP POST to webhook → Response incorporated → Voice synthesis streamed back
- **Authentication**: HMAC signature validation on webhooks; Secrets Manager for API keys
- **Approval modes**: Always Ask, Fine-Grained (pre-approved tools auto-run), No Approval
- **Custom LLM**: Via MCP server proxy — ElevenLabs handles audio I/O, your LLM handles inference
- **WebSocket protocol**: Bidirectional `wss://` for streaming audio; `eleven_turbo_v2` for low latency
- **Turn-taking**: VAD (Voice Activity Detection) for speech end; barge-in support pauses agent on interruption

### Architecture Pattern
```
Player (Voice)
    ↓ WebRTC/Phone
ElevenLabs Agent
    ├─ STT (transcription)
    ├─ LLM (built-in or custom via MCP)
    ├─ Server Tools → HTTP POST → FastAPI Backend
    │   ├─ /webhook/score-update  (game state)
    │   ├─ /webhook/memory-store  (save to SupabaseMemory)
    │   └─ /webhook/game-action   (chapter progress, boss trigger)
    └─ TTS (voice synthesis) → WebSocket → Player
```

**FastAPI webhook handler:**
```python
@app.post("/webhook/game-action")
async def handle_voice_tool(request: Request):
    payload = await request.body()
    signature = request.headers.get("elevenlabs-signature")
    event = webhooks.construct_event(payload.decode(), signature, WEBHOOK_SECRET)

    action = event.data.get("action")
    if action == "check_score":
        scores = await get_user_scores(event.data["user_id"])
        return {"result": f"Your engagement is {scores.engagement}%"}
    elif action == "trigger_conflict":
        conflict = await generate_conflict(event.data["user_id"])
        return {"result": conflict.description}
```

### Latency Optimization
- Chunked streaming: send partial text to TTS WebSocket (`chunk_length_schedule`)
- Model: `eleven_turbo_v2` for lowest latency
- Signed URLs: 15-min auth tokens, avoid API key exposure
- Async handlers: non-blocking FastAPI endpoints
- Local MCP: minimize network hops for tool calls

### Implications for Nikita
- Current voice integration uses Server Tools — well-aligned with architecture
- **Key opportunity**: Custom LLM via MCP lets Nikita use same Claude model for voice as text (unified personality)
- Server Tools enable real-time game state updates during voice conversations
- Webhook pattern should mirror text pipeline stages for consistency
- VAD + barge-in handling is crucial for natural Nikita voice personality
- Consider: voice-specific System 1 routing (casual voice chat = fast model, emotional moments = premium)

### Sources
- [ElevenLabs Server Tools Docs](https://elevenlabs.io/docs/conversational-ai/customization/tools/server-tools)
- [ElevenLabs MCP Integration](https://elevenlabs.io/blog/introducing-elevenlabs-mcp)
- [ElevenLabs Agent Authentication](https://elevenlabs.io/docs/eleven-agents/customization/authentication)
- [ElevenLabs WebSocket API](https://elevenlabs-sdk.mintlify.app/api-reference/websockets)

---

## 5. pg_cron + Supabase Batch Processing

### Key Findings
- `pg_cron` + `pg_net` = scheduled HTTP calls from PostgreSQL (no external scheduler needed)
- Cron syntax: standard 5-field (minute, hour, dom, month, dow); supports `5 seconds` intervals
- **32 concurrent jobs max** — space jobs out to prevent connection overload
- `cron.job_run_details` table for monitoring; `status`, `return_message`, timings
- Schedule cleanup of log table (it grows unbounded)
- Error handling: `BEGIN...EXCEPTION` blocks + custom error logging
- RPC functions (SECURITY DEFINER) for complex logic, scheduled via pg_cron

### Code Patterns
```sql
-- Decay calculation every 30 minutes
SELECT cron.schedule(
  'relationship-decay',
  '*/30 * * * *',
  $$
    SELECT net.http_post(
      url := 'https://nikita-api-xxxxx.run.app/api/v1/tasks/decay',
      headers := '{"Authorization": "Bearer <service-key>", "Content-Type": "application/json"}'::jsonb,
      body := jsonb_build_object('batch_size', 500, 'window_minutes', 30)
    );
  $$
);

-- Daily digest at 9 AM
SELECT cron.schedule(
  'daily-digest',
  '0 9 * * *',
  $$
    SELECT net.http_post(
      url := 'https://nikita-api-xxxxx.run.app/api/v1/tasks/digest',
      headers := '{"Authorization": "Bearer <service-key>"}'::jsonb,
      body := '{}'::jsonb
    );
  $$
);

-- Weekly cleanup Saturdays at 3:30 AM
SELECT cron.schedule('weekly-cleanup', '30 3 * * 6',
  'DELETE FROM game_events WHERE event_time < now() - interval ''30 days''');

-- Log cleanup
SELECT cron.schedule('cleanup-cron-logs', '0 12 * * *',
  'DELETE FROM cron.job_run_details WHERE end_time < now() - interval ''7 days''');

-- Monitor recent runs
SELECT jobid, status, return_message, start_time, end_time
FROM cron.job_run_details ORDER BY start_time DESC LIMIT 10;
```

**RPC function for complex batch:**
```sql
CREATE OR REPLACE FUNCTION rpc_calculate_decay()
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  UPDATE user_metrics
  SET engagement = engagement * 0.95,
      trust = trust * 0.98
  WHERE last_interaction < now() - interval '24 hours';

  -- Notify backend of updates
  PERFORM net.http_post(
    'https://nikita-api-xxxxx.run.app/api/v1/tasks/decay-complete',
    '{"Content-Type": "application/json"}'::jsonb,
    jsonb_build_object('updated_at', now())
  );
END;
$$;

SELECT cron.schedule('decay-rpc', '*/30 * * * *', 'SELECT rpc_calculate_decay()');
```

### Implications for Nikita
- **Already planned**: pg_cron for decay calculations, daily digests, cleanup — research confirms viability
- Decay every 30 min via RPC function (direct SQL) more efficient than HTTP round-trip to Cloud Run
- Daily digest needs HTTP call to Cloud Run (requires LLM for personalized content)
- 32-job limit is generous for Nikita's needs (~5-8 scheduled jobs)
- **Critical**: Schedule log cleanup — `cron.job_run_details` grows unbounded
- Use `SECURITY DEFINER` for RPC functions that modify user data (bypasses RLS safely)
- Monitor via `cron.job_run_details` — add alerting for failed jobs

### Sources
- [Supabase pg_cron Docs](https://supabase.com/docs/guides/database/extensions/pg_cron)
- [Supabase Cron Module](https://supabase.com/modules/cron)
- [pg_net Extension Docs](https://supabase.com/docs/guides/database/extensions/pg_net)
- [pg_cron GitHub (CitusData)](https://github.com/citusdata/pg_cron)

---

## 6. Conflict/Attachment Psychology in Games

### Key Findings

**Gottman's Research:**
- **5:1 ratio**: Stable relationships maintain 5 positive interactions for every 1 negative during conflict
- **20:1 ratio**: Everyday (non-conflict) interactions in thriving relationships
- **Four Horsemen** (predict divorce 90%+ accuracy): Criticism, Contempt, Defensiveness, Stonewalling
- **Repair attempts**: Humor, affection, validation during conflict — 86% turn-toward rate in thriving couples vs 33% in failing
- **Emotional bank account**: Accumulated positive interactions buffer against conflict damage

**Attachment Theory:**
| Style | Traits | Game Mechanic Mapping |
|-------|--------|----------------------|
| **Secure** | Comfort with closeness, open communication, high trust | Balanced routes, effective conflict resolution, tutorial for healthy dynamics |
| **Anxious** | Fear of abandonment, seeks reassurance, overanalyzes | Reassurance mini-games, jealousy events, time-limited responses rewarding empathy |
| **Avoidant** | Values independence, emotional distance, avoids vulnerability | "Cold" dialogue trees, persistence-based unlocks, space-giving options |
| **Disorganized** | Craves closeness but fears it, push-pull from trauma | Chaotic outcomes, push-pull flags, trauma-reveal arcs, high replayability |

**Escalation/De-escalation Patterns:**
- Anxious pursuit + avoidant withdrawal → drops ratio below 1:1 → "negative sentiment override"
- Secure partners use: gentle startups, empathy, shared rituals for repair
- Repair attempts succeed via positivity amid tension (humor, validation)

### Game Design Patterns
```
CONFLICT_FRAMEWORK
├─ [⊕] Positive Bank (20:1 everyday interactions)
│   ├─ Casual compliments (+1 each)
│   ├─ Gift giving (+2)
│   ├─ Shared activities (+3)
│   └─ Emotional support (+5)
├─ [→] Conflict Trigger (when conditions met)
│   ├─ Jealousy event (anxious style)
│   ├─ Distance event (avoidant style)
│   ├─ Trust test (secure style)
│   └─ Chaos event (disorganized style)
├─ [∘] Conflict Resolution (5:1 ratio during)
│   ├─ Repair attempt options (humor, validation, apology)
│   ├─ Escalation options (criticism, defensiveness)
│   ├─ [threshold] 5+ repairs : 1 escalation → resolve
│   └─ [threshold] <3:1 ratio → boss encounter trigger
└─ [≫] Outcome
    ├─ Successful repair → trust bonus, chapter progress
    ├─ Failed repair → metric decay, relationship damage
    └─ Repeated failure → boss encounter (3 strikes = game over)
```

### Implications for Nikita
- **5:1 ratio directly maps to scoring engine**: track positive/negative interaction ratio per session
- Nikita's attachment style should be **anxious-leaning** (creates natural tension, rewards player empathy)
- Boss encounters = Four Horsemen moments (criticism from Nikita when ratio drops)
- Repair attempts = player's chance to recover during boss encounters
- **Emotional bank account** = composite of 4 metrics (engagement, trust, attraction, respect)
- Vice system maps to attachment triggers: each vice creates specific escalation patterns
- Chapter progression should require maintaining 5:1 ratio through increasingly complex conflicts
- **20:1 ratio for non-conflict**: casual chat should be overwhelmingly positive (builds bank)
- De-escalation patterns: Nikita offers "soft" repair hints before full boss encounter

### Sources
- [Gottman 5:1 Ratio Guide](https://therapydave.com/gottman/5-to-1-ratio-relationship-guide/)
- [Gottman Blog - Arguments](https://www.gottman.com/blog/everything-turns-into-an-argument/)
- [Attachment Theory Overview](https://www.highlandparktherapy.com/blog/understanding-attachment-theory-building-better-relationships-with-yourself-and-others)
- [Attachment Styles in Couples Therapy](https://www.spark-counseling.com/blog/the-connection-between-the-4-attachment-styles-in-relationships-and-how-they-show-up-in-couples-therapy)

---

## 7. Context Engineering for LLMs

### Key Findings
- **Context engineering** > prompt engineering: systematic management of all information flowing into LLM (prompts, memory, tools, retrieval)
- Failures from poor context: distractions, clashes, bloat — 39% performance drop from context clashes
- Accuracy degrades beyond ~32K tokens — smaller, high-signal context outperforms large noisy context
- **Anthropic's four pillars**: system prompt → tools → examples → user message (in that order)
- **Primacy bias**: most important information first; **recency bias**: recent conversation last
- Progressive disclosure: load context on-demand via tools, not upfront

### Information Hierarchy
```
CONTEXT_WINDOW_ARCHITECTURE
├─ [TOP] System Prompt — core instructions, persona, rules
│   ├─ Character definition (who is Nikita)
│   ├─ Game rules (scoring, chapters, constraints)
│   └─ Response format instructions
├─ [2nd] Tool Definitions — self-contained, non-overlapping
│   ├─ Memory retrieval tool
│   ├─ Score update tool
│   └─ Game action tool
├─ [3rd] Dynamic Context — retrieved at runtime
│   ├─ Memory summary (compressed, high-signal)
│   ├─ Current game state (chapter, scores, active vice)
│   └─ Recent conversation summary (compacted)
├─ [4th] Conversation History — sliding window
│   ├─ Last N messages (recent turns)
│   └─ Compacted summary of older turns
└─ [BOTTOM] Current User Message — most recent input
```

### Optimization Strategies

| Strategy | When | How |
|----------|------|-----|
| **Compaction** | Every N turns | LLM-summarize history: "User wants X, tried Y, learned Z" |
| **Sliding window** | Real-time/streaming | Fixed-size attention on recent tokens, evict old |
| **RAG injection** | Per-message | Vector search → inject relevant chunks with rationale labels |
| **Progressive loading** | On tool call | Load detailed context only when agent requests it |
| **Token budgeting** | Always | Cap `max_input_tokens` at 80% window, leave 20% for output |
| **Sub-agent isolation** | Complex tasks | Narrow context per sub-agent, orchestrator synthesizes |

### Code Patterns
```python
# Compaction pattern for Nikita multi-turn
def compact_conversation(messages: list[dict], max_tokens: int = 2000) -> str:
    if token_count(messages) < max_tokens:
        return format_messages(messages)

    # Keep last 5 messages verbatim
    recent = messages[-5:]
    older = messages[:-5]

    # Summarize older messages
    summary = llm_summarize(
        f"Summarize key: goals, emotional state, unresolved tensions from: {older}"
    )
    return f"[Conversation Summary]\n{summary}\n\n[Recent Messages]\n{format_messages(recent)}"

# RAG integration for memory
async def build_context(user_id: str, current_message: str) -> str:
    # Retrieve relevant memories (vector search)
    memories = await supabase_memory.search(current_message, user_id, limit=5)

    # Build context with rationale
    memory_context = "\n".join([
        f"- {m.content} [relevance: {m.score:.2f}, from: {m.timestamp}]"
        for m in memories
    ])

    return f"[Relevant Memories]\n{memory_context}"
```

### Implications for Nikita
- **Current pipeline lacks explicit context engineering** — opportunity for major quality + cost improvement
- Implement 4-tier hierarchy: system prompt (cached) → tools → dynamic context → conversation
- Compaction at every 10-15 turns preserves coherence without context bloat
- Memory retrieval should include relevance scores and timestamps (helps LLM prioritize)
- Token budgeting: Nikita's context should target ~4K tokens system + ~2K memory + ~2K history = ~8K total input
- **Anti-pattern to fix**: current approach likely dumps all context upfront — switch to progressive loading
- Sub-agent pattern: scoring agent gets narrow context (just the message + metrics), not full conversation
- Combine with prompt caching: hierarchy tiers 1-2 are cached, tiers 3-4 are dynamic

### Sources
- [Anthropic - Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Anthropic - Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [Context Engineering Guide (PromptingGuide)](https://www.promptingguide.ai/guides/context-engineering-guide)
- [Redis - Context Engineering Best Practices](https://redis.io/blog/context-engineering-best-practices-for-an-emerging-discipline/)

---

## Cross-Cutting Insights

### 1. Unified Cost Optimization Stack
Prompt caching (topic 1) + dual-process routing (topic 3) + context engineering (topic 7) form a **cost optimization triad**:
- Cache static context (90% savings on repeated tokens)
- Route simple messages to cheap models (60-80% savings on 70% of traffic)
- Compress dynamic context (fewer tokens = lower cost + better quality)
- **Combined estimated savings: 80-90% reduction in LLM costs**

### 2. Pipeline Architecture Convergence
Pydantic AI multi-agent (topic 2) + context engineering (topic 7) suggest a **staged pipeline with specialized agents**:
```
Message → [Router/S1] → [Text Agent/S2] → [Scoring Agent/S1] → [Memory Agent/S1]
              ↓                ↓                  ↓                    ↓
         Cached ctx      Full ctx (8K)      Narrow ctx (2K)    Narrow ctx (1K)
```
Each agent gets minimum viable context, reducing costs and improving focus.

### 3. Psychology-Driven Game Mechanics
Gottman ratios (topic 6) + dual-process (topic 3) map to **adaptive difficulty**:
- Track 5:1 ratio in real-time → when ratio healthy, Nikita is warm (System 1 responses)
- When ratio drops below 3:1 → trigger conflict (System 2 complex narrative generation)
- Boss encounters = Four Horsemen moments requiring player skill
- Attachment style influences which conflicts trigger and how repair works

### 4. Voice-Text Consistency
ElevenLabs (topic 4) + context engineering (topic 7) require **unified context management**:
- Same system prompt for text and voice agents (cached at both layers)
- Server Tools webhooks mirror text pipeline stages
- Voice needs tighter latency budget → more aggressive System 1 routing
- Custom LLM via MCP enables same Claude model for both channels

### 5. Batch Processing Enables Proactive Behavior
pg_cron (topic 5) + attachment psychology (topic 6) enable **proactive Nikita**:
- Decay calculations trigger re-engagement messages (Nikita reaches out)
- Daily digests use attachment-informed tone (anxious: "I missed you", secure: "Hey, thinking of you")
- Scheduled cleanup maintains emotional bank account accuracy
- Boss encounter scheduling based on time-since-last-interaction decay patterns
