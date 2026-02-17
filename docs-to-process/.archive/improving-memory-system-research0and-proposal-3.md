

## What’s actually happening today (from the code)

### Texting (Telegram) runtime: effectively stateless per turn

**Path:** `platforms/telegram/message_handler.py` → `agents/text/handler.py` → `agents/text/agent.py`

What happens each incoming text:

1. Telegram handler fetches/creates a `conversations` row (status `active`) and appends the user message into `conversations.messages`.
2. It calls the text agent to generate a reply.
3. **The LLM call is made with only the user’s latest message** and a generated system prompt.
4. The assistant reply is appended back into `conversations.messages`.

**Critical continuity issue:** the agent call does **not** include message history (`message_history`) — so the model literally doesn’t see the previous messages unless they happen to be re-described in the system prompt.

PydanticAI explicitly supports passing prior turns as `message_history` to preserve multi-turn continuity across separate calls. ([ai.pydantic.dev][1])

### Voice runtime: continuity depends on a cached system prompt + tools

Voice is different:

* On call start, the ElevenLabs session uses `users.cached_voice_prompt` (or a fallback default).
* During the call, ElevenLabs can use **server tools** (`get_context`, `search_memory`, etc.) to fetch memory.
* On call end (webhook), the code runs the legacy post-processor pipeline and then regenerates + caches the voice system prompt.

So voice can feel continuous **if**:

* the cached prompt is fresh, and
* the graphs/summaries are being updated, and
* the tools are being used by the voice agent.

---

## Why it feels like “texting starts from zero” (root causes)

### 1) Text LLM calls have no short-term conversation buffer

For text, each LLM response is generated without providing prior turns (no rolling window, no “today’s transcript”, no in-call state). So unless your meta prompt manages to “reconstruct” continuity from summaries/graphs, the model is blind.

This alone explains the “we reset quickly” feeling.

### 2) The intended “post-processing updates memory → next prompt includes it” loop is fragile

Your architecture expectation is correct in spirit: summarize + extract memory after sessions, then inject it into future prompts.

In this repo snapshot, that loop is **not reliable for text**, because:

* **Text post-processing is triggered only by the background task route** (`/tasks/process-conversations`) + stale-session detection.
* If the scheduler isn’t running (pg_cron or whatever calls it), stale conversations don’t get processed → graphs/summaries/threads don’t update → next prompt has little to work with.
* Even when it runs, the repo contains two pipelines:

  * **Legacy pipeline** (`nikita/context/post_processor.py`) — full featured, used by voice.
  * **New “post_processing” pipeline** (`nikita/post_processing/*`) — incomplete in this snapshot (stubby summary/touchpoint parts, plus API mismatches).

So: texting can end up with **no short-term buffer** *and* **no updated long-term memory**, which is a perfect recipe for “amnesia.”

### 3) Your meta prompt *expects* “last conversation summary” — but it wasn’t being populated

The system prompt meta-template includes `{{last_conversation_summary}}`, but `MetaPromptService` wasn’t filling that field from the DB, so even the “bridge” between conversations was often missing.

---

## Where memory lives in your schema vs where code actually reads/writes it

Here’s the practical truth table:

### Written every message

* `conversations.messages` ✅ (text + voice)
* `conversations.last_message_at` ✅

### Written after a conversation ends (post-processing)

* `daily_summaries` ✅ **only if legacy post-processor runs**
* `conversation_threads`, `nikita_thoughts` ✅ **only if legacy post-processor runs**
* Graph memory (Graphiti/Neo4j) ✅ **only if the graph updater runs successfully**
* `context_packages` ⚠️ pipeline exists, but not the source of truth for the running prompts right now (text/voice prompt gen isn’t consuming it)

### Read at prompt-generation time

* `daily_summaries`, `conversation_threads`, `nikita_thoughts`, `user_backstories`, `user_profiles`, metrics/emotional state ✅
* Graph memory via Graphiti search ✅
* **Recent transcript / message history** ❌ (this is the big gap)

---

## Diagram: where continuity breaks

```text
TEXT (Telegram)
User msg
  -> append to conversations.messages
  -> build system prompt (meta prompt / memory retrieval)
  -> LLM run(user_message ONLY)   <-- NO message history passed
  -> append assistant reply
  -> (later) background job may post-process stale conversation (often not guaranteed)

VOICE (ElevenLabs)
Call start
  -> use users.cached_voice_prompt (generated previously)
  -> during call: tools can fetch memory
Call end webhook
  -> legacy post-processor updates summaries/threads/graphs
  -> regenerate + cache users.cached_voice_prompt
```

---

## Best-practice memory model for “human continuity”

There’s a fairly convergent set of best practices across modern agent systems:

### 1) Use **tiered memory** (short → mid → long)

* **Short-term / working memory:** a rolling buffer of recent turns (or at minimum “today’s turns”). This is what prevents the “reset” feeling.
* **Episodic memory:** summaries of sessions / key moments (“what happened, why it mattered emotionally”), often stored as events + timestamps.
* **Semantic memory:** stable facts/preferences/relationships (“user likes X”, “we’re dating”, “their friend is Y”).
* **Procedural memory:** “how Nikita behaves” (persona + style rules).

This mirrors common patterns in research and tooling:

* **Generative Agents**: store experiences, retrieve relevant memories, and use reflection to synthesize higher-level beliefs. ([arXiv][2])
* **MemGPT**: argues for hierarchical memory to overcome limited context windows and support long-running conversations. ([arXiv][3])
* LangChain/LangGraph’s memory guidance similarly splits semantic vs episodic vs procedural, and emphasizes that memory formation + retrieval policies are application-specific. ([langchain-ai.github.io][4])

### 2) Don’t rely on summaries alone for immediacy

Summaries are great for compression, but they are *not* a substitute for a rolling window of actual dialogue for the last N turns / last day. Humans remember the last thing you said — not just a therapist’s intake note.

### 3) Make “promises / cliffhangers / open loops” first-class

You already have `conversation_threads` and `nikita_thoughts`. Those are exactly the “sticky continuity hooks” that make a companion feel alive — but only if they’re reliably created/updated and consistently injected.

### 4) Retrieval should be “cue + time + importance”

In practice:

* **Cue:** similarity to current message (“Japan trip” pulls Japan memories)
* **Time:** boost recent memories
* **Importance:** boost “high emotional impact” and “commitments”

LangMem explicitly calls out importance and recency/frequency (“strength”) as common retrieval factors. ([langchain-ai.github.io][4])

---

## Approaches to fix continuity (ranked with constructive criticism)

Scoring: 1–5 (higher is better).
Dimensions: **Continuity**, **Latency/Cost**, **Complexity**, **Robustness**, **Debuggability**

### A) Add a short-term “today buffer” (message_history) + keep long-term retrieval

**What:** Always pass a rolling window of recent turns (and optionally “today’s turns”) into the LLM call. Keep Graphiti + summaries as long-term memory.

* Continuity: **5**
* Latency/Cost: **4** (more tokens, but predictable)
* Complexity: **2**
* Robustness: **4** (works even if post-processing lags)
* Debuggability: **4**

**Criticism:** token growth if you’re careless; needs trimming policy.

✅ **This is the single biggest “stop the amnesia” lever.**

### B) Context packages (hierarchical prompt composition) + cached daily prompt

**What:** Precompute a daily “context package” (persona + relationship + key memories + open threads) and inject it, plus a small rolling buffer.

* Continuity: **4**
* Latency/Cost: **5** (fast at runtime)
* Complexity: **4**
* Robustness: **3** (depends on background processing)
* Debuggability: **5** (great if you log package snapshots)

**Criticism:** if packages aren’t refreshed reliably, you get “stale personality.”

### C) Full “Generative Agents / MemGPT-style” memory manager (reflection + consolidation)

**What:** After sessions, run a reflection step that writes: events, relationships, emotional moments, and updated beliefs; retrieval uses cue+time+importance.

* Continuity: **5**
* Latency/Cost: **3**
* Complexity: **5**
* Robustness: **3–4** (depends on ops discipline)
* Debuggability: **3** unless heavily instrumented

**Criticism:** can become a mini research project; easy to overbuild.

**My recommendation:** **A now**, **B next**, **C selectively** once the system is stable.

---

## The PR I generated (code + diagram) — fixes the core continuity break

### What this PR does

1. **Text agent now passes a “today” rolling message window as `message_history`** into the PydanticAI `Agent.run(...)`.

   * This gives immediate continuity even if summaries/graphs are delayed.
2. **Uses the user’s timezone to compute “today”** (where possible) when building the day-buffer.
3. **Text prompt generation now receives `conversation_id`** so generated prompts can be traced per conversation.
4. **Restores text background processing to the legacy PostProcessor** (same one voice uses), because the new pipeline in this snapshot isn’t reliable enough to drive memory continuity.
5. **MetaPromptService now fills `last_conversation_summary`** from the most recent processed conversation, matching what the system prompt template expects.
6. Adds a code-level system diagram doc and logs the “Understanding” event.

### Patch file

[Download the PR patch](sandbox:/mnt/data/nikita_memory_continuity_pr.patch)

### Files changed (high level)

* `nikita/agents/text/agent.py`
* `nikita/agents/text/handler.py`
* `nikita/platforms/telegram/message_handler.py`
* `nikita/api/routes/tasks.py`
* `nikita/db/repositories/conversation_repository.py`
* `nikita/meta_prompts/service.py`
* `docs/2026-01-19-memory-audit/system_diagram.md`
* `event-stream.md`

### Test plan you can run quickly

* **Continuity within a session:** send 5–10 messages; Nikita should reference earlier details without needing “remind her.”
* **Continuity after a break:** wait >15 minutes, send a new message; she should still know what happened earlier *today*.
* **Post-processing:** hit `/tasks/process-conversations` (or ensure pg_cron runs it) and verify:

  * `conversations.status` → `processed`
  * `daily_summaries.summary_text` updated
  * `conversation_threads` / `nikita_thoughts` created
  * next system prompt includes `last_conversation_summary`

---

## What I’d do next (small, high ROI)

1. **Make text “session boundaries” explicit**: if a conversation is stale when a new message arrives, close the old one and start a new one *but still include the today-buffer*.
   (Your system already has a 15-min concept in `SessionDetector`; the runtime path doesn’t currently enforce it.)
2. **Ensure the background job is unquestionably running** (pg_cron or external scheduler). Without it, you’ll always be fighting memory drift.
3. **Add a “commitments & callbacks” section that is always injected** (threads + promises), with strict token budgeting.
4. **Unify voice + text prompt inputs**: same memory sources, same structure, same logging.

The universe is cruel and loves nothing more than an AI companion that forgets your birthday. The fix is not “one more clever prompt.” It’s making sure the model reliably sees (a) the last turns, (b) today’s arc, and (c) the durable relationship facts — every time.

If you apply the patch, the “reset after a short time” symptom for texting should drop dramatically, because we’re no longer asking the model to do telepathy with no transcript.

[1]: https://ai.pydantic.dev/agents/ "https://ai.pydantic.dev/agents/"
[2]: https://arxiv.org/abs/2304.03442 "[2304.03442] Generative Agents: Interactive Simulacra of Human Behavior"
[3]: https://arxiv.org/abs/2310.08560 "[2310.08560] MemGPT: Towards LLMs as Operating Systems"
[4]: https://langchain-ai.github.io/langmem/concepts/conceptual_guide/ "Core Concepts"



Got it. I cracked open the repo (from the ZIP you provided) and followed the actual runtime paths for **texting** and **voice**, plus the **post‑processing / memory** pipeline. The continuity problems you’re seeing aren’t a vibe issue — they’re concrete wiring gaps and a couple of “this looks implemented but isn’t actually in the loop” situations.

Below is the **investigation summary so far**, the **most likely causes of “reset to zero”**, and what I’ve already started fixing in a PR branch locally. What’s still incomplete (docs + diagrams + PRD + final PR patch) is listed at the end.

---

## 1) How the system *currently* works (as implemented)

### Text (Telegram) runtime path

**Telegram message → DB conversation append → text agent → response → DB append**

Key files:

* `nikita/platforms/telegram/message_handler.py`
* `nikita/agents/text/handler.py`
* `nikita/agents/text/agent.py`
* `nikita/context/template_generator.py`
* `nikita/meta_prompts/service.py`

**Critical finding:**
Every *individual* message is treated as a fresh inference call with **no message history passed into the LLM**.

In `nikita/agents/text/agent.py`, the `Agent.run(...)` call is executed with only the current user message and a system prompt. No prior turns are provided as `message_history`, and no explicit transcript section was being injected either.

That alone can cause “who are you again?” symptoms **within the same conversation window**, depending on how rich the system prompt is.

---

### Voice runtime path

Voice has two parallel memory flows:

#### A) Pre‑call voice prompt

Voice pre-call uses a cached system prompt for speed:

* `nikita/agents/voice/inbound.py`
* Uses: `users.cached_voice_prompt`

This is intentionally done to avoid LLM calls during ElevenLabs pre-call webhook.

#### B) In‑call retrieval tools

Voice agent can call server tools during the call:

* `nikita/agents/voice/server_tools.py`
* `get_context`, `get_memory`, etc.

**Critical mismatch I found:**
The voice `get_context` tool reads `daily_summaries.nikita_summary_text`, but both the “legacy” post‑processor and the newer summary generator populate **`daily_summaries.summary_text`**. Result: voice tool often returns `today_summary = null` even when daily summary exists.

That weakens continuity during voice calls and makes voice “feel behind” texting.

---

## 2) When is a conversation “over” and how continuity is *supposed* to transfer?

There’s a session timeout mechanism:

* `ConversationRepository.get_stale_active_conversations(stale_minutes=15)`
* `detect_stale_sessions(...)` marks them as `processing`
* then a cron / task route processes them

The intended continuity transfer is:

* extract facts / entities / summary
* update Graphiti memory graphs
* persist threads/thoughts/key moments
* update daily summaries
* then next conversation uses that memory in prompt generation

This is exactly what you described (post-processing generates new context, new system prompt is richer).

---

## 3) Why “starting from zero” actually happens (root causes)

### Root Cause A — **Text agent has no working-memory / transcript injection**

Even if long‑term memory works perfectly, the text agent is stateless turn-to-turn unless you provide:

* recent transcript
* or message_history structure

As implemented, text agent **does not include today’s transcript or even the active conversation transcript** in the LLM call.

So: “continuity collapses quickly” is expected behavior.

---

### Root Cause B — **The post‑processing cron route was wired to an incomplete pipeline**

This is the big one for “after a little time we reset to zero.”

The cron route `POST /tasks/process-conversations` was importing:

```py
from nikita.post_processing import process_conversations
```

That “new” pipeline (`nikita/post_processing/adapter.py`) is currently not feature-complete and doesn’t match the tables / message structure reliably.

Symptoms if that route runs:

* conversations get marked `processing`
* but the pipeline **does not reliably produce the same memory artifacts**
* and in some cases can fail / no-op
* meaning the next conversation starts with **no updated memory context**

Meanwhile voice post-processing uses the legacy pipeline:

* `nikita/context/post_processor.py`
  and therefore voice tends to be “more memory-rich” than text.

This mismatch is the kind of “it works… except when it doesn’t… except it’s every time” that ruins continuity.

---

### Root Cause C — **Voice tool uses wrong summary column**

As noted, `server_tools.get_context` uses `nikita_summary_text` but the system writes `summary_text`. So voice’s “day recap” memory is missing even when it exists.

---

## 4) What I changed already (local PR in progress)

I started implementing fixes in the repo locally (no GitHub PR possible from here, but I can generate a patch + PR description).

### ✅ Fix 1: Task post-processing now uses the legacy full extraction pipeline

Changed `/tasks/process-conversations` to import:

```py
from nikita.context.post_processor import process_conversations
```

Why: this pipeline actually:

* extracts entities + facts
* creates conversation threads + nikita thoughts
* updates Graphiti graphs meaningfully
* generates real summaries (not stub)
* marks conversations processed correctly

This aligns texting post-processing with voice post-processing.

---

### ✅ Fix 2: Voice `get_context` now reads `summary_text` (fallback to `nikita_summary_text`)

Updated:

* `nikita/agents/voice/server_tools.py`

So voice tool returns today/week summaries correctly.

---

### ✅ Fix 3: MetaPromptService now injects “last conversation summary” + recent transcript block

Updated:

* `nikita/meta_prompts/service.py`

Two improvements:

1. it now loads `last_conversation_summary` (previously always None)
2. it appends a trimmed **“Recent Conversation (last ~24h, verbatim)”** block to the generated system prompt output, capped by tier and token budget.

This gives the model real working memory without requiring a full conversion to `message_history`.

---

### ✅ Fix 4: After processing a text conversation, refresh cached voice prompt

In `/tasks/process-conversations`, after successful processing, I added logic to:

* gather affected user_ids
* generate a **critical-tier** system prompt via `MetaPromptService`
* store into `users.cached_voice_prompt`, `cached_voice_prompt_at`

This fixes cross‑modality continuity (text → voice).

---

## 5) Best practices research (started, with sources)

I began pulling high-signal references for “agent memory types” and continuity architectures:

* **PydanticAI message_history behavior** (important because it changes system prompt regeneration rules)
  Source: PydanticAI docs on message history
  [https://ai.pydantic.dev/message-history/](https://ai.pydantic.dev/message-history/)

* **Generative Agents (Park et al., 2023)** — memory stream, retrieval, reflection loop
  [https://arxiv.org/abs/2304.03442](https://arxiv.org/abs/2304.03442)

* **MemGPT** — hierarchical memory manager, working vs archival
  [https://arxiv.org/abs/2310.08560](https://arxiv.org/abs/2310.08560)

* **A-MEM (2024)** — agent memory taxonomy and strategies
  [https://arxiv.org/abs/2402.10010](https://arxiv.org/abs/2402.10010)

* **LlamaIndex agent memory overview** (practical patterns)
  [https://www.llamaindex.ai/blog/enhancing-ai-agent-reliability-with-memory](https://www.llamaindex.ai/blog/enhancing-ai-agent-reliability-with-memory)

These will feed directly into the PRD and design options scoring.

---

## 6) What’s still incomplete (but clearly scoped)

You asked for a full “coding agent context pack” output. I have not yet produced the full document set and diagrams — I focused first on isolating the real runtime gaps and starting a concrete PR fix.

### Remaining deliverables I still need to generate inside the repo:

1. **Architecture & continuity docs**

   * “Current Text Flow”
   * “Current Voice Flow”
   * “Conversation lifecycle (active → stale → processing → processed)”
   * “Memory layers present vs missing”

2. **Diagrams**

   * sequence diagrams for text and voice
   * memory flow diagram (DB + Graphiti + prompts + post-processing)
   * context injection stack (working memory vs episodic vs semantic etc.)

3. **PRD**

   * explicit requirements: daily continuity, short-term transcript, long-term memory
   * performance budgets
   * prompt layering rules
   * observability & metrics
   * rollout plan

4. **Design options + scoring**

   * “append transcript” (what I implemented)
   * “true message_history statefulness” (PydanticAI)
   * “context_packages-based hierarchical prompt composition”
   * hybrid approaches
   * scored across: continuity, latency, cost, complexity, safety, debuggability

5. **Comprehensive PR output**

   * final patch (`.patch`)
   * PR title + description
   * testing notes
   * migration notes if needed

---

## The weird truth in one sentence

Text continuity is currently bad because **(1) turn-to-turn history isn’t provided** and **(2) the post-processing cron path for text was wired to an incomplete pipeline**, so sessions end and memory doesn’t reliably transfer.

Which is the software equivalent of: “We gave her a hippocampus, but forgot to connect it to the brainstem.” 🧠⚡

---

If you want to keep momentum: the next step is me generating the **docs + diagrams + PRD + ranked options**, and then I’ll produce the **final unified patch + PR description** as files in `docs/<session-id>/...` inside the repo.
